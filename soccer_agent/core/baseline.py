from pathlib import Path
import sqlite3
from typing import Dict, Any, List, Optional

from soccer_agent.tools.resolver import EntityResolver, canonical_key
from soccer_agent.tools.sql_executor import SQLExecutor
from soccer_agent.core.query_parser import QueryParser


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
        if query_type == "goals_scored":
            params =team_ids + team_ids + comp_ids + team_ids + team_ids
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


class SinglePassBaseline:
    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur
        self.resolver = EntityResolver(cur)
        self.executor = SQLExecutor(cur)
        self.parser = QueryParser(self.resolver)

    def make_result(
        self,
        query: str,
        sql_spec: Optional[Dict[str, Any]],
        competition_result: Optional[Dict[str, Any]],
        team_result: Optional[Dict[str, Any]],
        sql: Optional[str],
        params: Optional[List[Any]],
        execution_result: Optional[Dict[str, Any]],
        status: str,
        step: str,
        message: str,
    ):
        return {
            "mode": "weak_baseline_single_pass",
            "query": query,
            "status": status,
            "step": step,
            "message": message,
            "sql_spec": sql_spec,
            "competition_result": competition_result,
            "team_result": team_result,
            "sql": sql,
            "params": params,
            "execution_result": execution_result,
        }

    def resolve_competition_weak(self, sql_spec: Dict[str, Any]):
        comp_context = sql_spec.get("competition_context", {})
        league = comp_context.get("league", None)
        seasons = comp_context.get("seasons", [])

        result = {
            "entity_type": "competition",
            "decision": None,
            "value": None,
            "debug": {"mode": "weak_baseline"},
        }

        if not league:
            result["decision"] = "NOT_FOUND"
            return result

        if not seasons or len(seasons) != 1:
            result["decision"] = "NOT_FOUND"
            return result

        season = seasons[0]
        comp_id = self.resolver.comp_id_by_league_season.get((league, season), None)

        if comp_id is None:
            result["decision"] = "NOT_FOUND"
            return result

        result["decision"] = "RESOLVED"
        result["value"] = [comp_id]
        return result

    def resolve_team_weak(self, sql_spec: Dict[str, Any]):
        team_mention = sql_spec.get("team_mention", {})
        team_context = sql_spec.get("team_context", {})

        raw_name = team_mention.get("team_name", None)
        league = team_context.get("league", None)

        result = {
            "entity_type": "team",
            "decision": None,
            "value": None,
            "debug": {"mode": "weak_baseline"},
        }

        if not raw_name or not league:
            result["decision"] = "NOT_FOUND"
            return result

        norm_name = canonical_key(raw_name)

        candidates = []
        for team_id, info in self.resolver.team_by_id.items():
            if info.get("league") == league and info.get("norm_name") == norm_name:
                candidates.append(team_id)

        candidates = sorted(candidates)

        if not candidates:
            result["decision"] = "NOT_FOUND"
            return result

        result["decision"] = "RESOLVED"
        result["value"] = [candidates[0]]
        return result

    def run(self, query: str):
        sql_spec = self.parser.parse_query(query)
        query_type = sql_spec.get("query_type", None)

        if query_type not in ("match_count", "home_wins", "away_wins", "goals_scored"):
            return self.make_result(
                query=query,
                sql_spec=sql_spec,
                competition_result=None,
                team_result=None,
                sql=None,
                params=None,
                execution_result=None,
                status="error",
                step="parse_query",
                message="Unsupported or missing query_type in parser output",
            )

        competition_result = self.resolve_competition_weak(sql_spec)
        if competition_result.get("decision") != "RESOLVED":
            return self.make_result(
                query=query,
                sql_spec=sql_spec,
                competition_result=competition_result,
                team_result=None,
                sql=None,
                params=None,
                execution_result=None,
                status="error",
                step="resolve_competition",
                message="Competition resolution failed in weak baseline",
            )

        team_result = self.resolve_team_weak(sql_spec)
        if team_result.get("decision") != "RESOLVED":
            return self.make_result(
                query=query,
                sql_spec=sql_spec,
                competition_result=competition_result,
                team_result=team_result,
                sql=None,
                params=None,
                execution_result=None,
                status="error",
                step="resolve_team",
                message="Team resolution failed in weak baseline",
            )

        comp_ids = competition_result["value"]
        team_ids = team_result["value"]

        try:
            sql, params = _build_sql(query_type, comp_ids, team_ids)
        except Exception as e:
            return self.make_result(
                query=query,
                sql_spec=sql_spec,
                competition_result=competition_result,
                team_result=team_result,
                sql=None,
                params=None,
                execution_result=None,
                status="error",
                step="build_sql",
                message=str(e),
            )

        execution_result = self.executor.execute_sql(sql, params)

        if execution_result.get("status") != "success":
            return self.make_result(
                query=query,
                sql_spec=sql_spec,
                competition_result=competition_result,
                team_result=team_result,
                sql=sql,
                params=params,
                execution_result=execution_result,
                status="error",
                step="execute_sql",
                message="SQL execution failed in weak baseline",
            )

        return self.make_result(
            query=query,
            sql_spec=sql_spec,
            competition_result=competition_result,
            team_result=team_result,
            sql=sql,
            params=params,
            execution_result=execution_result,
            status="success",
            step="done",
            message="Weak baseline query executed successfully",
        )


def run_weak_baseline_smoke_test():
    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    baseline = SinglePassBaseline(cur)

    queries = [
        "In EPL 2021-22, how many matches did Manchester City play?",
        "Real Sociedad home wins in LaLiga 2023-24",
        "Atletico Madrid away wins in LaLiga 2023-24",
        "Real Sociedad home wins in LaLiga 2022-23 2023-24",
    ]

    print("=" * 80)
    print("WEAK BASELINE SMOKE TEST START")
    print("=" * 80)

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}] QUERY: {query}")
        result = baseline.run(query)
        print(result)

    conn.close()

    print("\n" + "=" * 80)
    print("WEAK BASELINE SMOKE TEST FINISHED")
    print("=" * 80)


if __name__ == "__main__":
    run_weak_baseline_smoke_test()