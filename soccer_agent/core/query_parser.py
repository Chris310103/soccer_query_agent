import re
import unicodedata
from typing import Dict, Any, Optional
from pathlib import Path
import sqlite3

from soccer_agent.core.controller import SoccerQueryController
from soccer_agent.tools.resolver import EntityResolver

class QueryParser:
    def __init__(self, resolver):
        self.resolver = resolver
        self.team_candidates = sorted(
            {
                info["norm_name"]
                for info in self.resolver.team_by_id.values()
                if info.get("norm_name")
            },
            key=len,
            reverse=True,
        )

    def remove_accent(self, x: str) -> str:
        nfd_form = unicodedata.normalize("NFD", x)
        return "".join(c for c in nfd_form if unicodedata.category(c) != "Mn")

    def normalize_query(self, q: str) -> str:
        q = q.lower()
        q = self.remove_accent(q)
        q = re.sub(r'[,:;"?!\.]', " ", q)
        q = re.sub(r"\s+", " ", q).strip()
        return q

    def extract_league(self, q: str):
        if re.search(r"\b(epl|premier league|english premier league)\b", q, flags=re.I):
            return {
                "competition_mention": {"abb": "epl", "league_name": None},
                "competition_context": {"league": "en"},
                "team_context": {"league": "en"},
            }

        if re.search(r"\b(laliga|la liga|primera division|primera division de espana)\b", q, flags=re.I):
            return {
                "competition_mention": {"abb": "laliga", "league_name": None},
                "competition_context": {"league": "es"},
                "team_context": {"league": "es"},
            }

        return {
            "competition_mention": {"abb": None, "league_name": None},
            "competition_context": {"league": None},
            "team_context": {"league": None},
        }

    def extract_seasons(self, q: str):
        seasons = re.findall(r"\b(?:19|20)\d{2}-\d{2}\b", q)
        return list(dict.fromkeys(seasons))

    def extract_query_type(self, q: str) -> Optional[str]:
        if re.search(r"\b(home wins|won at home|home win)\b", q, flags=re.I):
            return "home_wins"

        if re.search(r"\b(away wins|won away|away win)\b", q, flags=re.I):
            return "away_wins"

        if re.search(
            r"\b(how many matches|match count|how many games|number of matches|games played|matches played)\b",
            q,
            flags=re.I,
        ):
            return "match_count"

        if re.search(
            r"\b(goals scored|how many goals did .* score|goals for|scored how many goals)\b",
            q,
            flags=re.I,
        ):
            return "goals_scored"

        return None
    def extract_team_name(self, q: str) -> Optional[str]:
        for team in self.team_candidates:
            if team in q:
                return team
        return None

    def parse_query(self, query: str) -> Dict[str, Any]:
        norm_query = self.normalize_query(query)

        result = {
            "competition_mention": {"abb": None, "league_name": None},
            "competition_context": {"league": None, "seasons": []},
            "team_mention": {"team_name": None},
            "team_context": {"league": None},
            "query_type": None,
        }

        league_info = self.extract_league(norm_query)
        result["competition_mention"] = league_info["competition_mention"]
        result["competition_context"]["league"] = league_info["competition_context"]["league"]
        result["team_context"]["league"] = league_info["team_context"]["league"]

        seasons = self.extract_seasons(norm_query)
        if seasons:
            result["competition_context"]["seasons"] = seasons

        query_type = self.extract_query_type(norm_query)
        if query_type:
            result["query_type"] = query_type

        team_name = self.extract_team_name(norm_query)
        if team_name:
            result["team_mention"]["team_name"] = team_name

        return result
    


def run_end_to_end_test():
    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)
    parser = QueryParser(resolver)
    controller = SoccerQueryController(cur)

    queries = [
        "In EPL 2021-22, how many matches did Manchester City play?",
        "Real Sociedad home wins in LaLiga 2023-24",
        "Atletico Madrid away wins in LaLiga 2023-24",
        "Fake Team FC home wins in EPL 2021-22",
    ]

    print("=" * 80)
    print("END-TO-END TEST START")
    print("=" * 80)

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}] QUERY: {query}")

        sql_spec = parser.parse_query(query)
        print("sql_spec:", sql_spec)

        result = controller.run(sql_spec)
        print("result:", result)

    conn.close()

    print("\n" + "=" * 80)
    print("END-TO-END TEST FINISHED")
    print("=" * 80)

if __name__=="__main__":
    run_end_to_end_test()





    
    






    
    