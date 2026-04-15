from typing import Dict, List, Any
import sqlite3

from soccer_agent.tools.resolver import EntityResolver
from soccer_agent.tools.sql_executor import SQLExecutor
from soccer_agent.tools.validator import ResultValidator
from soccer_agent.core.spec_checks import check_execution_readiness
from soccer_agent.core.sql_spec import SQLSpec


def _build_sql(query_type: str, comp_ids: List[int], team_ids: List[int]):
    if query_type == "match_count":
        params = comp_ids + team_ids + team_ids
        placeholder_1 = ",".join(["?"] * len(comp_ids))
        placeholder_2 = ",".join(["?"] * len(team_ids))
        sql = f"""
            SELECT COUNT(*)
            FROM matches
            WHERE comp_id IN ({placeholder_1})
              AND (
                    home_team_id IN ({placeholder_2})
                    OR
                    away_team_id IN ({placeholder_2})
              )
        """
        return sql, params

    if query_type == "home_wins":
        params = comp_ids + team_ids
        placeholder_1 = ",".join(["?"] * len(comp_ids))
        placeholder_2 = ",".join(["?"] * len(team_ids))
        sql = f"""
            SELECT COUNT(*)
            FROM matches
            WHERE comp_id IN ({placeholder_1})
              AND home_team_id IN ({placeholder_2})
              AND home_goals > away_goals
        """
        return sql, params

    if query_type == "away_wins":
        params = comp_ids + team_ids
        placeholder_1 = ",".join(["?"] * len(comp_ids))
        placeholder_2 = ",".join(["?"] * len(team_ids))
        sql = f"""
            SELECT COUNT(*)
            FROM matches
            WHERE comp_id IN ({placeholder_1})
              AND away_team_id IN ({placeholder_2})
              AND away_goals > home_goals
        """
        return sql, params
    
    if query_type == "goals_scored":
        params = team_ids + team_ids + comp_ids + team_ids + team_ids
        placeholder_1 = ",".join(["?"] * len(comp_ids))
        placeholder_2 = ",".join(["?"] * len(team_ids))

        sql = f"""
            SELECT COALESCE(
                SUM(
                    CASE WHEN home_team_id IN ({placeholder_2}) THEN home_goals ELSE 0 END +
                    CASE WHEN away_team_id IN ({placeholder_2}) THEN away_goals ELSE 0 END
                ),
                0
            )
            FROM matches
            WHERE comp_id IN ({placeholder_1})
            AND (
                    home_team_id IN ({placeholder_2})
                    OR
                    away_team_id IN ({placeholder_2})
            )
        """
        return sql, params

    raise TypeError("Unsupported query type")


class SoccerQueryController:
    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur
        self.resolver = EntityResolver(cur)
        self.executor = SQLExecutor(cur)
        self.validator = ResultValidator()

    def make_result(
        self,
        comp_res: Dict[str, Any] | None,
        team_res: Dict[str, Any] | None,
        sql: str | None,
        params: List[Any] | None,
        query_type: str | None,
        execution_result: Dict[str, Any] | None = None,
        validator_result: Dict[str, Any] | None = None,
        status: str = "error",
        step: str | None = None,
        message: str | None = None,
    ):
        return {
            "status": status,
            "step": step,
            "competition_result": comp_res,
            "team_result": team_res,
            "sql": sql,
            "params": params,
            "execution_result": execution_result,
            "validator_result": validator_result,
            "message": message,
            "query_type": query_type,
        }

    def run(self, sql_spec: SQLSpec):
        readiness = check_execution_readiness(sql_spec)
        if not readiness["ready"]:
            return self.make_result(
                comp_res=None,
                team_res=None,
                sql=None,
                params=None,
                query_type=sql_spec.get("query_type"),
                execution_result=None,
                validator_result={
                    "decision": readiness["decision"],
                    "reason": readiness["reason"],
                    "missing_fields": readiness["missing_fields"],
                    "stage": "precheck",
                },
                status="error",
                step="validate",
                message=readiness["reason"],
            )

        comp_mention = sql_spec.get("competition_mention", {})
        comp_context = sql_spec.get("competition_context", {})

        team_mention = sql_spec.get("team_mention", {})
        team_context = sql_spec.get("team_context", {})

        query_type = sql_spec.get("query_type", None)

        competition_res = self.resolver.resolve_competition(comp_mention, comp_context)
        team_res = self.resolver.resolve_team(team_mention, team_context)

        sql = None
        params = None
        execution_result = None
        build_error = None

        if (
            competition_res.get("decision") == "RESOLVED"
            and team_res.get("decision") == "RESOLVED"
        ):
            comp_ids = competition_res["value"]
            team_ids = team_res["value"]

            try:
                sql, params = _build_sql(query_type, comp_ids, team_ids)
                execution_result = self.executor.execute_sql(sql, params)
            except Exception as e:
                build_error = str(e)

        validator_result = self.validator.validate(
            query_spec=sql_spec,
            competition_result=competition_res,
            team_result=team_res,
            sql=sql,
            params=params,
            execution_result=execution_result,
            build_error=build_error,
        )

        decision = validator_result["decision"]

        if decision == "OK":
            return self.make_result(
                comp_res=competition_res,
                team_res=team_res,
                sql=sql,
                params=params,
                query_type=query_type,
                execution_result=execution_result,
                validator_result=validator_result,
                status="success",
                step="done",
                message="Query executed successfully",
            )

        if decision == "CLARIFY":
            return self.make_result(
                comp_res=competition_res,
                team_res=team_res,
                sql=sql,
                params=params,
                query_type=query_type,
                execution_result=execution_result,
                validator_result=validator_result,
                status="error",
                step="validate",
                message=validator_result["reason"],
            )

        if decision == "REPAIR":
            return self.make_result(
                comp_res=competition_res,
                team_res=team_res,
                sql=sql,
                params=params,
                query_type=query_type,
                execution_result=execution_result,
                validator_result=validator_result,
                status="error",
                step="validate",
                message=validator_result["reason"],
            )

        if decision == "RELAX":
            return self.make_result(
                comp_res=competition_res,
                team_res=team_res,
                sql=sql,
                params=params,
                query_type=query_type,
                execution_result=execution_result,
                validator_result=validator_result,
                status="error",
                step="validate",
                message=validator_result["reason"],
            )

        return self.make_result(
            comp_res=competition_res,
            team_res=team_res,
            sql=sql,
            params=params,
            query_type=query_type,
            execution_result=execution_result,
            validator_result=validator_result,
            status="error",
            step="validate",
            message="Unknown validator decision",
        )

def run_controller_smoke_test():
    from pathlib import Path
    import sqlite3

    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    controller = SoccerQueryController(cur)

    test_cases = [
        {
            "name": "success_match_count_epl_mancity",
            "sql_spec": {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": "en", "seasons": ["2021-22"]},
                "team_mention": {"team_name": "Manchester City"},
                "team_context": {"league": "en"},
                "query_type": "match_count",
            },
            "expect_status": "success",
        },
        {
            "name": "success_home_wins_laliga_sociedad",
            "sql_spec": {
                "competition_mention": {"abb": "laliga", "league_name": None},
                "competition_context": {"league": "es", "seasons": ["2023-24"]},
                "team_mention": {"team_name": "Real Sociedad"},
                "team_context": {"league": "es"},
                "query_type": "home_wins",
            },
            "expect_status": "success",
        },
        {
            "name": "success_away_wins_laliga_atletico",
            "sql_spec": {
                "competition_mention": {"abb": "laliga", "league_name": None},
                "competition_context": {"league": "es", "seasons": ["2023-24"]},
                "team_mention": {"team_name": "Atletico Madrid"},
                "team_context": {"league": "es"},
                "query_type": "away_wins",
            },
            "expect_status": "success",
        },
        {
            "name": "error_team_not_found",
            "sql_spec": {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": "en", "seasons": ["2021-22"]},
                "team_mention": {"team_name": "Fake Team FC"},
                "team_context": {"league": "en"},
                "query_type": "match_count",
            },
            "expect_status": "error",
        },
        {
            "name": "error_team_ambiguous_missing_league",
            "sql_spec": {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": "en", "seasons": ["2021-22"]},
                "team_mention": {"team_name": "Manchester City"},
                "team_context": {"league": None},
                "query_type": "match_count",
            },
            "expect_status": "error",
        },
        {
            "name": "error_competition_ambiguous_missing_season",
            "sql_spec": {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": None, "seasons": None},
                "team_mention": {"team_name": "Manchester City"},
                "team_context": {"league": "en"},
                "query_type": "match_count",
            },
            "expect_status": "error",
        },
        {
            "name": "error_unsupported_query_type",
            "sql_spec": {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": "en", "seasons": ["2021-22"]},
                "team_mention": {"team_name": "Manchester City"},
                "team_context": {"league": "en"},
                "query_type": "goals_diff",
            },
            "expect_status": "error",
        },
    ]

    print("=" * 80)
    print("CONTROLLER SMOKE TEST START")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        print(f"\n[{i}] {case['name']}")
        result = controller.run(case["sql_spec"])
        print(result)

        assert isinstance(result, dict), "Controller result should be a dict"
        assert "status" in result, "Missing status"
        assert "step" in result, "Missing step"
        assert "message" in result, "Missing message"

        assert result["status"] == case["expect_status"], (
            f"Expected status {case['expect_status']}, got {result['status']}"
        )

        if case["expect_status"] == "success":
            assert result["competition_result"] is not None
            assert result["team_result"] is not None
            assert result["competition_result"]["decision"] == "RESOLVED"
            assert result["team_result"]["decision"] == "RESOLVED"
            assert result["execution_result"] is not None
            assert result["execution_result"]["status"] == "success"
            assert result["sql"] is not None
            assert result["params"] is not None
        else:
            assert result["status"] == "error"

    conn.close()

    print("\n" + "=" * 80)
    print("CONTROLLER SMOKE TEST PASSED")
    print("=" * 80)

if __name__ == "__main__":
    run_controller_smoke_test()




