from typing import Any, Dict, List

ALLOWED_QUERY_TYPES = {
    "match_count",
    "home_wins",
    "away_wins",
    "goals_scored",
}


def check_execution_readiness(spec: Dict[str, Any]) -> Dict[str, Any]:
    res = {
        "ready": False,
        "decision": None,
        "missing_fields": [],
        "reason": None,
    }

    query_type = spec.get("query_type")

    team_mention = spec.get("team_mention", {}) or {}
    competition_context = spec.get("competition_context", {}) or {}

    team_name = team_mention.get("team_name")
    league = competition_context.get("league")
    seasons = competition_context.get("seasons", [])

    missing_fields: List[str] = []

    if not query_type:
        missing_fields.append("query_type")
    elif query_type not in ALLOWED_QUERY_TYPES:
        return {
            "ready": False,
            "decision": "CLARIFY",
            "missing_fields": ["query_type"],
            "reason": f"Unsupported query type for execution: {query_type}",
        }

    if not team_name:
        missing_fields.append("team_name")

    if not league:
        missing_fields.append("league")

    if not seasons:
        missing_fields.append("season")

    if missing_fields:
        return {
            "ready": False,
            "decision": "CLARIFY",
            "missing_fields": missing_fields,
            "reason": f"Missing required fields for execution: {', '.join(missing_fields)}",
        }

    return {
        "ready": True,
        "decision": "OK",
        "missing_fields": [],
        "reason": "Spec is ready for execution.",
    }

