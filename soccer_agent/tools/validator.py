from typing import Dict, Any


class ResultValidator:
    def __init__(self):
        pass

    def validate(
        self,
        query_spec: Dict[str, Any],
        competition_result: Dict[str, Any] | None = None,
        team_result: Dict[str, Any] | None = None,
        sql: str | None = None,
        params: list | None = None,
        execution_result: Dict[str, Any] | None = None,
        build_error: str | None = None,
    ):
        result = {
            "decision": None,
            "reason": None,
            "suggestion": None,
            "debug": {
                "query_spec": query_spec,
                "competition_result": competition_result,
                "team_result": team_result,
                "sql": sql,
                "params": params,
                "execution_result": execution_result,
                "build_error": build_error,
            },
        }

        query_type = query_spec.get("query_type", None)

        if query_type not in ("match_count", "home_wins", "away_wins", "goals_scored"):
            result["decision"] = "REPAIR"
            result["reason"] = "Unsupported query type."
            result["suggestion"] = "Use one of: match_count, home_wins, away_wins."
            return result

        if competition_result is None or competition_result.get("decision") != "RESOLVED":
            result["decision"] = "CLARIFY"
            result["reason"] = "Competition is not fully resolved."
            result["suggestion"] = "Provide clearer league or season information."
            return result

        if team_result is None or team_result.get("decision") != "RESOLVED":
            result["decision"] = "CLARIFY"
            result["reason"] = "Team is not fully resolved."
            result["suggestion"] = "Provide clearer team or league information."
            return result

        if build_error is not None:
            result["decision"] = "REPAIR"
            result["reason"] = f"SQL build failed: {build_error}"
            result["suggestion"] = "Check SQL template and placeholder construction."
            return result

        if execution_result is None:
            result["decision"] = "REPAIR"
            result["reason"] = "Execution result is missing."
            result["suggestion"] = "Check whether SQL was executed."
            return result

        if execution_result.get("status") != "success":
            result["decision"] = "REPAIR"
            result["reason"] = f"SQL execution failed: {execution_result.get('error')}"
            result["suggestion"] = "Check SQL syntax, columns, and parameters."
            return result

        columns = execution_result.get("columns", [])
        rows = execution_result.get("rows", [])

        if query_type not in ("match_count", "home_wins", "away_wins", "goals_scored"):
            if len(columns) != 1 or len(rows) != 1 or len(rows[0]) != 1:
                result["decision"] = "REPAIR"
                result["reason"] = "Unexpected result shape for count-style query."
                result["suggestion"] = "Expected exactly one row and one column."
                return result

            value = rows[0][0]

            if value is None:
                result["decision"] = "REPAIR"
                result["reason"] = "Aggregation returned None."
                result["suggestion"] = "Check SQL aggregation or use COALESCE."
                return result

            if value == 0:
                result["decision"] = "RELAX"
                result["reason"] = "Query executed successfully but returned zero results."
                result["suggestion"] = "Consider relaxing season/team/opponent/home-away constraints."
                return result

        result["decision"] = "OK"
        result["reason"] = "Query executed successfully and returned expected result shape."
        result["suggestion"] = None
        return result
        
            

            

        
