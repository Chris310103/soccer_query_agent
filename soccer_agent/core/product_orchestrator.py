from __future__ import annotations

from typing import Any, Dict, Optional


def run_product_query(query: str, parser, controller) -> Dict[str, Any]:
    """
    Product-mode query runner.

    Behavior:
    1. Ask the parser for both sql_spec and parse_meta.
    2. If parse_meta says confirmation is required, do NOT execute yet.
       Return a structured 'needs_confirmation' response.
    3. Otherwise, execute immediately through controller.run(sql_spec).

    Expected parser interface:
        parser.parse_query_with_meta(query) -> (sql_spec, parse_meta)

    Expected controller interface:
        controller.run(sql_spec) -> result dict
    """
    sql_spec, parse_meta = parser.parse_query_with_meta(query)

    parse_meta = parse_meta or {}
    requires_confirmation = bool(parse_meta.get("requires_confirmation", False))

    if requires_confirmation:
        return {
            "status": "needs_confirmation",
            "query": query,
            "message": parse_meta.get("message")
            or "The system inferred missing information. Please confirm before execution.",
            "proposed_sql_spec": sql_spec,
            "parse_meta": parse_meta,
            "result": None,
        }

    result = controller.run(sql_spec)
    return {
        "status": "final",
        "query": query,
        "message": result.get("message"),
        "proposed_sql_spec": sql_spec,
        "parse_meta": parse_meta,
        "result": result,
    }


def confirm_and_run(proposed_sql_spec: Dict[str, Any], parse_meta: Dict[str, Any], controller) -> Dict[str, Any]:
    """
    Execute after the user confirms a proposed inference.
    """
    result = controller.run(proposed_sql_spec)

    return {
        "status": "final",
        "query": None,
        "message": result.get("message"),
        "proposed_sql_spec": proposed_sql_spec,
        "parse_meta": parse_meta,
        "result": result,
    }


def compact_product_response(product_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    A cleaner view for terminal testing / demo display.
    """
    status = product_response.get("status")
    parse_meta = product_response.get("parse_meta") or {}
    result = product_response.get("result") or {}

    summary = {
        "status": status,
        "message": product_response.get("message"),
        "requires_confirmation": parse_meta.get("requires_confirmation"),
        "inferred_fields": parse_meta.get("inferred_fields"),
    }

    if status == "needs_confirmation":
        summary["proposed_sql_spec"] = product_response.get("proposed_sql_spec")
        return summary

    validator_result = result.get("validator_result") or {}
    execution_result = result.get("execution_result") or {}

    value = None
    rows = execution_result.get("rows") or []
    if rows and len(rows) == 1 and len(rows[0]) == 1:
        value = rows[0][0]

    summary["query_type"] = result.get("query_type")
    summary["decision"] = validator_result.get("decision")
    summary["value"] = value
    return summary

def format_product_response_for_ui(product_response: dict) -> dict:
    status = product_response.get("status")
    parse_meta = product_response.get("parse_meta") or {}
    sql_spec = product_response.get("proposed_sql_spec") or {}
    result = product_response.get("result") or {}

    if status == "needs_confirmation":
        competition_mention = sql_spec.get("competition_mention") or {}
        competition_context = sql_spec.get("competition_context") or {}
        team_mention = sql_spec.get("team_mention") or {}

        seasons = competition_context.get("seasons") or []
        season_value = ", ".join(seasons) if seasons else None

        return {
            "status": "needs_confirmation",
            "title": "Need confirmation",
            "message": product_response.get("message"),
            "inferred_fields": parse_meta.get("inferred_fields", []),
            "proposed_interpretation": {
                "team": team_mention.get("team_name"),
                "league": competition_mention.get("league_name"),
                "season": season_value,
                "query_type": sql_spec.get("query_type"),
            },
            "confirm_payload": {
                "proposed_sql_spec": sql_spec,
                "parse_meta": parse_meta,
            },
        }

    validator_result = result.get("validator_result") or {}
    execution_result = result.get("execution_result") or {}
    rows = execution_result.get("rows") or []

    answer = None
    if rows and len(rows) == 1 and len(rows[0]) == 1:
        answer = rows[0][0]

    return {
        "status": "success" if result.get("status") == "success" else "error",
        "title": "Result" if result.get("status") == "success" else "Unable to complete query",
        "message": product_response.get("message") or result.get("message"),
        "answer": answer,
        "query_type": result.get("query_type"),
        "validator_decision": validator_result.get("decision"),
    }


if __name__ == "__main__":
    from pathlib import Path
    import sqlite3

    from soccer_agent.tools.resolver import EntityResolver
    from soccer_agent.core.controller import SoccerQueryController
    from soccer_agent.core.ruled_base_query_parser import Rule_Base_QueryParser
    from soccer_agent.core.llm_client import Gemini_LLM_Client
    from soccer_agent.core.llm_parser import LLMQueryParser

    queries = [
        "How many matches did Manchester City play in EPL 2021-22?",
        "Manchester City home wins in 2021-22",
    ]

    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)
    rule_parser = Rule_Base_QueryParser(resolver)
    gemini_llm = Gemini_LLM_Client()

    parser = LLMQueryParser(
        llm_client=gemini_llm,
        fallback_parser=rule_parser,
        debug=False,
    )

    controller = SoccerQueryController(cur)

    for q in queries:
        print("\n" + "=" * 80)
        print("QUERY:", q)

        response = run_product_query(q, parser, controller)
        print("PRODUCT RESPONSE:")
        print(compact_product_response(response))

        if response["status"] == "needs_confirmation":
            print("\nAUTO-CONFIRM FOR TESTING...")
            confirmed = confirm_and_run(
                proposed_sql_spec=response["proposed_sql_spec"],
                parse_meta=response["parse_meta"],
                controller=controller,
            )
            print("CONFIRMED RESULT:")
            print(compact_product_response(confirmed))

    conn.close()