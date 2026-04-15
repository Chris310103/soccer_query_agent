from pathlib import Path
import sqlite3
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from soccer_agent.core.config import has_gemini_api_key
from soccer_agent.tools.resolver import EntityResolver
from soccer_agent.core.controller import SoccerQueryController
from soccer_agent.core.ruled_base_query_parser import Rule_Base_QueryParser
from soccer_agent.core.llm_client import Gemini_LLM_Client
from soccer_agent.core.llm_parser import LLMQueryParser
from soccer_agent.core.product_orchestrator import (
    run_product_query,
    confirm_and_run,
    format_product_response_for_ui,
)


class QueryRequest(BaseModel):
    query: str


class ConfirmRequest(BaseModel):
    proposed_sql_spec: Dict[str, Any]
    parse_meta: Dict[str, Any]


app = FastAPI(title="Soccer Query Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "soccer.sqlite3"


def build_runtime():
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    cur = conn.cursor()
    resolver = EntityResolver(cur)
    rule_parser = Rule_Base_QueryParser(resolver)
    parser = LLMQueryParser(
        llm_client=Gemini_LLM_Client(),
        fallback_parser=rule_parser,
        debug=False,
    )
    controller = SoccerQueryController(cur)
    return conn, parser, controller


@app.get("/health")
def health():
    return {
        "status": "ok",
        "product_mode_available": has_gemini_api_key(),
    }


@app.post("/product/query")
def product_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    if not has_gemini_api_key():
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Product mode is unavailable.",
        )

    conn = None
    try:
        conn, parser, controller = build_runtime()
        raw_response = run_product_query(request.query, parser, controller)
        return format_product_response_for_ui(raw_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            conn.close()



@app.post("/product/confirm")
def product_confirm(request: ConfirmRequest):
    conn = None
    try:
        conn, _, controller = build_runtime()
        raw_response = confirm_and_run(
            proposed_sql_spec=request.proposed_sql_spec,
            parse_meta=request.parse_meta,
            controller=controller,
        )
        return format_product_response_for_ui(raw_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            conn.close()