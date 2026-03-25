import json
import sqlite3 
from pathlib import Path
from collections import defaultdict
import re
import unicodedata
from typing import Dict,Any

pp=Path(__file__).parent
db_path=pp.parent/"data"/"soccer.sqlite3"

conn=sqlite3.connect(db_path)
cur=conn.cursor()


def remove_accent(x: str):
    nfd_form = unicodedata.normalize("NFD", x)
    only = "".join(c for c in nfd_form if unicodedata.category(c) != "Mn")
    return only


def canonical_key(raw_name: str):
    name = raw_name.lower().strip()
    name = remove_accent(name)
    name = re.sub(r"[&'.,]", " ", name, flags=re.I)
    name = re.sub(
        r"\b(club|de|del|futbol|balompie|fc|cf|ud|afc|rcd|sd|cd|rc|deportivo|ca)\b",
        " ",
        name,
        flags=re.I,
    )
    name = re.sub(r"\s+", " ", name).strip()
    return name


def norm_comp(raw_name: str):
    name = raw_name.lower().strip()
    name = remove_accent(name)
    name = re.sub(r"/", "-", name)
    name = re.sub(r"\bPrimera División de España\b", "primera division de espana", name)
    name = re.sub(r"\Spain Primera División\b", "primera division de espana", name)
    name = re.sub(r"\bEnglish Premier League\b", "english premier league", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

from collections import defaultdict
from typing import Dict, Any
import sqlite3


def build_indexes(cur: sqlite3.Cursor):

    team_by_id = defaultdict(dict)
    team_ids_by_key = defaultdict(list)

    cur.execute("""
        SELECT 
            t.team_id, 
            t.name, 
            MAX(c.league_code) AS league_code
        FROM teams t
        LEFT JOIN matches m
            ON (t.team_id = m.home_team_id OR t.team_id = m.away_team_id)
        LEFT JOIN competitions c
            ON m.comp_id = c.comp_id
        GROUP BY t.team_id, t.name;
    """)
    datas = cur.fetchall()

    for team_id, team_name, league_code in datas:
        norm_name = canonical_key(team_name)
        team_by_id[team_id]["league"] = league_code
        team_by_id[team_id]["norm_name"] = norm_name
        team_ids_by_key[(league_code, norm_name)].append(team_id)

    comp_by_id = defaultdict(dict)
    comp_ids_by_norm = defaultdict(list)
    comp_code_map = defaultdict(list)
    comp_id_by_league_season = {}

    cur.execute("""
        SELECT comp_id, league_code, season, name
        FROM competitions;
    """)
    competitions = cur.fetchall()

    for comp_id, league_code, season, name in competitions:
        norm_name = norm_comp(name)

        comp_by_id[comp_id]["norm_name"] = norm_name
        comp_by_id[comp_id]["league"] = league_code
        comp_by_id[comp_id]["season"] = season

        comp_ids_by_norm[norm_name].append(comp_id)
        comp_id_by_league_season[(league_code, season)] = comp_id

        code = None
        if league_code == "en":
            code = "epl"
        elif league_code == "es":
            code = "laliga"

        if code is not None:
            comp_code_map[code].append(comp_id)

    for code in comp_code_map:
        comp_code_map[code] = sorted(set(comp_code_map[code]))

    for norm_name in comp_ids_by_norm:
        comp_ids_by_norm[norm_name] = sorted(set(comp_ids_by_norm[norm_name]))

    return (
        team_by_id,
        team_ids_by_key,
        comp_by_id,
        comp_code_map,
        comp_ids_by_norm,
        comp_id_by_league_season,
    )


class EntityResolver:
    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur
        (
            self.team_by_id,
            self.team_ids_by_key,
            self.comp_by_id,
            self.comp_code_map,
            self.comp_ids_by_norm,
            self.comp_id_by_league_season,
        ) = build_indexes(self.cur)

    def resolve_competition(self, mention: Dict[str, Any], context: Dict[str, Any]):
        result = {
            "entity_type": "competition",
            "decision": None,
            "confidence": 0.0,
            "value": None,
            "debug": {
                "mention": mention,
                "context": context
            }
        }

        league = context.get("league", None)
        seasons = context.get("seasons", None) or []

        league_abb = mention.get("abb", None)
        league_name = mention.get("league_name", None)

        if league and seasons:
            comp_ids = []
            for season in seasons:
                comp_id = self.comp_id_by_league_season.get((league, season), None)
                if comp_id is not None:
                    comp_ids.append(comp_id)

            comp_ids = sorted(set(comp_ids))

            if comp_ids:
                result["decision"] = "RESOLVED"
                result["confidence"] = 1.0 if len(comp_ids) == len(seasons) else 0.85
                result["value"] = comp_ids
                return result

            result["decision"] = "NOT_FOUND"
            result["confidence"] = 0.0
            return result

        if league_abb and not league_name:
            league_abb = league_abb.lower().strip()

            if league_abb in ("epl", "premier league", "english premier league"):
                league_abb = "epl"
            elif league_abb in ("laliga", "la liga", "primera division", "primera division de espana"):
                league_abb = "laliga"
            else:
                result["decision"] = "NOT_FOUND"
                result["confidence"] = 0.0
                return result

            candidate_ids = self.comp_code_map.get(league_abb, [])

            if seasons:
                comp_ids = []
                for cid in candidate_ids:
                    if self.comp_by_id[cid]["season"] in seasons:
                        comp_ids.append(cid)

                comp_ids = sorted(set(comp_ids))

                if comp_ids:
                    result["decision"] = "RESOLVED"
                    result["confidence"] = 0.95 if len(comp_ids) == len(seasons) else 0.8
                    result["value"] = comp_ids
                    return result

                result["decision"] = "AMBIGUOUS"
                result["confidence"] = 0.4
                result["value"] = candidate_ids
                return result

            result["decision"] = "AMBIGUOUS"
            result["confidence"] = 0.35
            result["value"] = candidate_ids
            return result

        if league_name and not league_abb:
            norm_name = norm_comp(league_name)
            comp_ids = self.comp_ids_by_norm.get(norm_name, [])

            if comp_ids:
                result["decision"] = "RESOLVED"
                result["confidence"] = 0.95
                result["value"] = comp_ids
                return result

            result["decision"] = "NOT_FOUND"
            result["confidence"] = 0.0
            return result

        if league_abb and league_name:
            norm_name = norm_comp(league_name)
            comp_ids = self.comp_ids_by_norm.get(norm_name, [])

            if comp_ids:
                result["decision"] = "RESOLVED"
                result["confidence"] = 0.98
                result["value"] = comp_ids
                return result

            league_abb = league_abb.lower().strip()

            if league_abb in ("epl", "premier league", "english premier league"):
                league_abb = "epl"
            elif league_abb in ("laliga", "la liga", "primera division", "primera division de espana"):
                league_abb = "laliga"
            else:
                result["decision"] = "AMBIGUOUS"
                result["confidence"] = 0.3
                return result

            candidate_ids = self.comp_code_map.get(league_abb, [])

            if seasons:
                comp_ids = []
                for cid in candidate_ids:
                    if self.comp_by_id[cid]["season"] in seasons:
                        comp_ids.append(cid)

                comp_ids = sorted(set(comp_ids))

                if comp_ids:
                    result["decision"] = "RESOLVED"
                    result["confidence"] = 0.9
                    result["value"] = comp_ids
                    return result

                result["decision"] = "AMBIGUOUS"
                result["confidence"] = 0.4
                result["value"] = candidate_ids
                return result

            result["decision"] = "AMBIGUOUS"
            result["confidence"] = 0.35
            result["value"] = candidate_ids
            return result

        result["decision"] = "AMBIGUOUS"
        result["confidence"] = 0.2
        return result

    def resolve_team(self, mention: Dict[str, Any], context: Dict[str, Any]):
        result = {
        "entity_type": "team",
        "decision": None,
        "confidence": 0.0,
        "value": None,
        "debug": {
            "mention": mention,
            "context": context
        }
    }

        raw_name = mention.get("team_name", None)
        league_code = context.get("league", None)

        if not raw_name:
            result["decision"] = "NOT_FOUND"
            result["confidence"] = 0.0
            return result

        norm_name = canonical_key(raw_name)

        if not league_code:
            result["decision"] = "AMBIGUOUS"
            result["confidence"] = 0.2
            return result

        team_ids = self.team_ids_by_key.get((league_code, norm_name), [])
        team_ids = sorted(set(team_ids))

        if not team_ids:
            result["decision"] = "NOT_FOUND"
            result["confidence"] = 0.0
            return result

        result["decision"] = "RESOLVED"
        result["confidence"] = 0.95 if len(team_ids) == 1 else 0.85
        result["value"] = team_ids
        return result
    
def run_end_to_end_smoke_test():
    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)

    print("=" * 80)
    print("ADDITIONAL SMOKE TESTS")
    print("=" * 80)

    cases = [
        {
            "name": "LaLiga competition by abb + season",
            "comp_mention": {"abb": "laliga", "league_name": None},
            "comp_context": {"league": "es", "season": "2024-25"},
            "team_mention": {"team_name": "Barcelona"},
            "team_context": {"league": "es"},
        },
        {
            "name": "Real Sociedad merged ids",
            "comp_mention": {"abb": "laliga", "league_name": None},
            "comp_context": {"league": "es", "season": "2023-24"},
            "team_mention": {"team_name": "Real Sociedad"},
            "team_context": {"league": "es"},
        },
        {
            "name": "Atletico Madrid merged ids",
            "comp_mention": {"abb": "laliga", "league_name": None},
            "comp_context": {"league": "es", "season": "2023-24"},
            "team_mention": {"team_name": "Atletico Madrid"},
            "team_context": {"league": "es"},
        },
        {
            "name": "Team missing league context",
            "team_only": True,
            "team_mention": {"team_name": "Manchester City"},
            "team_context": {"league": None},
        },
        {
            "name": "Fake team not found",
            "team_only": True,
            "team_mention": {"team_name": "Fake Team FC"},
            "team_context": {"league": "en"},
        },
    ]

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}] {case['name']}")

        if not case.get("team_only", False):
            comp_result = resolver.resolve_competition(
                case["comp_mention"],
                case["comp_context"]
            )
            print("competition result:", comp_result)
            assert comp_result["entity_type"] == "competition"
            assert comp_result["decision"] == "RESOLVED"
            assert comp_result["value"] is not None

            team_result = resolver.resolve_team(
                case["team_mention"],
                case["team_context"]
            )
            print("team result:", team_result)
            assert team_result["entity_type"] == "team"
            assert team_result["decision"] == "RESOLVED"
            assert isinstance(team_result["value"], list)
            assert len(team_result["value"]) >= 1

            comp_id = comp_result["value"]
            team_ids = team_result["value"]

            placeholders = ",".join(["?"] * len(team_ids))

            sql = f"""
                SELECT COUNT(*)
                FROM matches m
                WHERE m.comp_id = ?
                  AND (
                        m.home_team_id IN ({placeholders})
                        OR
                        m.away_team_id IN ({placeholders})
                  )
            """

            params = [comp_id] + team_ids + team_ids
            cur.execute(sql, params)
            count = cur.fetchone()[0]

            print("match count:", count)
            assert count > 0, "Expected at least one match"

        else:
            team_result = resolver.resolve_team(
                case["team_mention"],
                case["team_context"]
            )
            print("team result:", team_result)

            assert team_result["entity_type"] == "team"

            if case["name"] == "Team missing league context":
                assert team_result["decision"] == "AMBIGUOUS"

            if case["name"] == "Fake team not found":
                assert team_result["decision"] == "NOT_FOUND"

    conn.close()
    print("\n" + "=" * 80)
    print("ADDITIONAL SMOKE TESTS PASSED")
    print("=" * 80)


def debug_real_sociedad_goals(cur):
    from soccer_agent.tools.resolver import EntityResolver

    resolver = EntityResolver(cur)

    comp_res = resolver.resolve_competition(
        {"abb": "laliga", "league_name": None},
        {"league": "es", "seasons": ["2023-24"]}
    )
    team_res = resolver.resolve_team(
        {"team_name": "real sociedad"},
        {"league": "es"}
    )

    comp_ids = comp_res["value"]
    team_ids = team_res["value"]

    print("competition_result:", comp_res)
    print("team_result:", team_res)

    placeholder_1 = ",".join(["?"] * len(comp_ids))
    placeholder_2 = ",".join(["?"] * len(team_ids))

    sql = f"""
        SELECT
            match_id,
            home_team_id,
            away_team_id,
            home_goals,
            away_goals
        FROM matches
        WHERE comp_id IN ({placeholder_1})
          AND (
                home_team_id IN ({placeholder_2})
                OR
                away_team_id IN ({placeholder_2})
          )
        LIMIT 10
    """

    params = comp_ids + team_ids + team_ids
    cur.execute(sql, params)
    rows = cur.fetchall()

    print("sample rows:")
    for row in rows:
        print(row)

    sql2 = f"""
        SELECT
            COUNT(*),
            SUM(
                CASE WHEN home_team_id IN ({placeholder_2}) THEN home_goals ELSE 0 END
            ),
            SUM(
                CASE WHEN away_team_id IN ({placeholder_2}) THEN away_goals ELSE 0 END
            )
        FROM matches
        WHERE comp_id IN ({placeholder_1})
          AND (
                home_team_id IN ({placeholder_2})
                OR
                away_team_id IN ({placeholder_2})
          )
    """

    params2 = comp_ids + team_ids + team_ids + team_ids + team_ids
    cur.execute(sql2, params2)
    agg = cur.fetchone()

    print("count, sum_home_side, sum_away_side:")
    print(agg)

if __name__ == "__main__":
    from pathlib import Path
    import sqlite3

    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    debug_real_sociedad_goals(cur)

    conn.close()
    
    

        

        
        

                    


        
        

    
        



   
    



    









    



