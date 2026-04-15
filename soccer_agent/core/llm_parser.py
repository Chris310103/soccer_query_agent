import json
import re
from typing import Any

from soccer_agent.core.sql_spec import SQLSpec, normalize_sql_spec
from soccer_agent.core.ruled_base_query_parser import Rule_Base_QueryParser
from soccer_agent.core.llm_client import LLMClient


class LLMQueryParser:
    def __init__(
        self,
        llm_client: LLMClient,
        fallback_parser: Rule_Base_QueryParser,
        debug: bool = False,
    ):
        self.llm_client = llm_client
        self.fallback_parser = fallback_parser
        self.debug = debug
        self.last_debug_info: dict[str, Any] = {}

    def set_debug(self, enabled: bool) -> None:
        self.debug = enabled

    def enable_debug(self) -> None:
        self.debug = True

    def disable_debug(self) -> None:
        self.debug = False

    def _log_debug(self, *args) -> None:
        if self.debug:
            print(*args)

    def get_debug_summary(self) -> dict:
        info = self.last_debug_info or {}
        raw_output = info.get("raw_output")
        return {
            "query": info.get("query"),
            "used_fallback": info.get("used_fallback"),
            "error": info.get("error"),
            "parsed_spec": info.get("parsed_spec"),
            "parse_meta": info.get("parse_meta"),
            "raw_output_preview": (raw_output[:120] + "...") if raw_output else None,
        }

    def _build_system_prompt(self) -> str:
        return """
You are a strict semantic parser for soccer analytics queries.

Return JSON only with exactly this schema:

{
  "sql_spec": {
    "competition_mention": {
      "abb": "epl" | "laliga" | null,
      "league_name": string | null
    },
    "competition_context": {
      "league": "en" | "es" | null,
      "seasons": [string]
    },
    "team_mention": {
      "team_name": string | null
    },
    "team_context": {
      "league": "en" | "es" | null
    },
    "query_type": "match_count" | "home_wins" | "away_wins" | "goals_scored" | null
  },
  "parse_meta": {
    "explicit_fields": [string],
    "inferred_fields": [string],
    "inference_confidence": {
      "league": number | null,
      "season": number | null
    },
    "requires_confirmation": boolean,
    "message": string | null
  }
}

Rules:
1. Output JSON only. No explanation.
2. Do not generate SQL.
3. Use null for unknown scalar fields.
4. Use [] for unknown or missing season lists.
5. Only extract information that is explicitly stated in the query unless you are making a high-confidence inference.
6. If you infer a critical missing field such as league or season, record it in parse_meta.inferred_fields.
7. If any critical field is inferred, set requires_confirmation = true.
8. If a field is explicitly stated by the user, include it in explicit_fields.
9. Keep team_name as a plain lowercase soccer team name string if present.
10. Normalize likely abbreviations:
   - EPL / Premier League -> abb = "epl", league = "en", league_name = "english premier league"
   - LaLiga / La Liga -> abb = "laliga", league = "es", league_name = "laliga"

Examples:

User query:
How many matches did Manchester City play in EPL 2021-22?

JSON:
{
  "sql_spec": {
    "competition_mention": {"abb": "epl", "league_name": "english premier league"},
    "competition_context": {"league": "en", "seasons": ["2021-22"]},
    "team_mention": {"team_name": "manchester city"},
    "team_context": {"league": "en"},
    "query_type": "match_count"
  },
  "parse_meta": {
    "explicit_fields": ["team_name", "league", "season", "query_type"],
    "inferred_fields": [],
    "inference_confidence": {"league": null, "season": null},
    "requires_confirmation": false,
    "message": null
  }
}

User query:
Manchester City home wins in 2021-22

JSON:
{
  "sql_spec": {
    "competition_mention": {"abb": "epl", "league_name": "english premier league"},
    "competition_context": {"league": "en", "seasons": ["2021-22"]},
    "team_mention": {"team_name": "manchester city"},
    "team_context": {"league": "en"},
    "query_type": "home_wins"
  },
  "parse_meta": {
    "explicit_fields": ["team_name", "season", "query_type"],
    "inferred_fields": ["league"],
    "inference_confidence": {"league": 0.92, "season": null},
    "requires_confirmation": true,
    "message": "League is not explicitly specified. A likely interpretation is EPL."
  }
}

User query:
How many goals did Manchester City score in EPL?

JSON:
{
  "sql_spec": {
    "competition_mention": {"abb": "epl", "league_name": "english premier league"},
    "competition_context": {"league": "en", "seasons": []},
    "team_mention": {"team_name": "manchester city"},
    "team_context": {"league": "en"},
    "query_type": "goals_scored"
  },
  "parse_meta": {
    "explicit_fields": ["team_name", "league", "query_type"],
    "inferred_fields": [],
    "inference_confidence": {"league": null, "season": null},
    "requires_confirmation": false,
    "message": null
  }
}
""".strip()

    def _build_user_prompt(self, query: str) -> str:
        return f"User query:\n{query}\n\nReturn JSON only."

    def _extract_json_text(self, raw_output: str) -> str:
        text = raw_output.strip()

        if text.startswith("{") and text.endswith("}"):
            return text

        fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
        if fence_match:
            return fence_match.group(1).strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx + 1].strip()

        raise ValueError("No JSON object output from LLM.")

    def _normalize_parse_meta(self, parse_meta: Any) -> dict:
        if not isinstance(parse_meta, dict):
            parse_meta = {}

        explicit_fields = parse_meta.get("explicit_fields", [])
        inferred_fields = parse_meta.get("inferred_fields", [])
        inference_confidence = parse_meta.get("inference_confidence", {})
        requires_confirmation = parse_meta.get("requires_confirmation", False)
        message = parse_meta.get("message")

        if not isinstance(explicit_fields, list):
            explicit_fields = []
        if not isinstance(inferred_fields, list):
            inferred_fields = []
        if not isinstance(inference_confidence, dict):
            inference_confidence = {}

        normalized_confidence = {
            "league": inference_confidence.get("league"),
            "season": inference_confidence.get("season"),
        }

        if not isinstance(requires_confirmation, bool):
            requires_confirmation = False

        if message is not None and not isinstance(message, str):
            message = str(message)

        return {
            "explicit_fields": explicit_fields,
            "inferred_fields": inferred_fields,
            "inference_confidence": normalized_confidence,
            "requires_confirmation": requires_confirmation,
            "message": message,
        }

    def _parse_llm_output_with_meta(self, raw_output: str) -> tuple[SQLSpec, dict]:
        json_text = self._extract_json_text(raw_output)
        obj = json.loads(json_text)

        if not isinstance(obj, dict):
            raise ValueError("LLM output JSON must be an object.")

        raw_spec = obj.get("sql_spec")
        if not isinstance(raw_spec, dict):
            raise ValueError("Missing or invalid sql_spec in LLM output.")

        sql_spec = normalize_sql_spec(raw_spec)
        parse_meta = self._normalize_parse_meta(obj.get("parse_meta"))

        return sql_spec, parse_meta

    def parse_query_with_meta(self, query: str) -> tuple[SQLSpec, dict]:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query)

        self.last_debug_info = {
            "query": query,
            "system_prompt": system_prompt if self.debug else None,
            "user_prompt": user_prompt if self.debug else None,
            "raw_output": None,
            "parsed_spec": None,
            "parse_meta": None,
            "used_fallback": False,
            "error": None,
        }

        try:
            raw_output = self.llm_client.generate(system_prompt, user_prompt)
            self.last_debug_info["raw_output"] = raw_output

            self._log_debug("=" * 80)
            self._log_debug("LLM RAW OUTPUT")
            self._log_debug(raw_output)
            self._log_debug("=" * 80)

            sql_spec, parse_meta = self._parse_llm_output_with_meta(raw_output)
            self.last_debug_info["parsed_spec"] = sql_spec
            self.last_debug_info["parse_meta"] = parse_meta

            self._log_debug("LLM PARSED SPEC:")
            self._log_debug(sql_spec)
            self._log_debug("LLM PARSE META:")
            self._log_debug(parse_meta)

            return sql_spec, parse_meta

        except Exception as e:
            self.last_debug_info["used_fallback"] = True
            self.last_debug_info["error"] = str(e)

            fallback_spec = self.fallback_parser.parse_query(query)
            fallback_meta = {
                "explicit_fields": [],
                "inferred_fields": [],
                "inference_confidence": {"league": None, "season": None},
                "requires_confirmation": False,
                "message": "LLM parsing failed. Fell back to rule-based parser.",
            }

            self.last_debug_info["parsed_spec"] = fallback_spec
            self.last_debug_info["parse_meta"] = fallback_meta

            self._log_debug(f"LLM parser failed, fallback to rule-based parser. Error: {e}")
            self._log_debug("FALLBACK SPEC:")
            self._log_debug(fallback_spec)

            return fallback_spec, fallback_meta

    def parse_query(self, query: str) -> SQLSpec:
        sql_spec, _ = self.parse_query_with_meta(query)
        return sql_spec


if __name__ == "__main__":
    from pathlib import Path
    import sqlite3

    from soccer_agent.tools.resolver import EntityResolver
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

    for q in queries:
        print("\n" + "=" * 80)
        print("QUERY:", q)

        sql_spec, parse_meta = parser.parse_query_with_meta(q)

        print("SQL SPEC:")
        print(sql_spec)

        print("PARSE META:")
        print(parse_meta)

    conn.close()
    





    

    

        




