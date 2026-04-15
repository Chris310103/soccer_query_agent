from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

QueryType = Literal[
    "match_count",
    "home_wins",
    "away_wins",
    "goals_scored",
]

LeagueCode = Literal["en", "es"]

class CompetitionMention(TypedDict):
    abb:Optional[str]
    league_name:Optional[str]

class CompetitionContext(TypedDict):
    league: Optional[LeagueCode]
    seasons: List[str]

class TeamMention(TypedDict):
    team_name: Optional[str]

class TeamContext(TypedDict):
    league:Optional[LeagueCode]

class SQLSpec(TypedDict):
    competition_mention: CompetitionMention
    competition_context: CompetitionContext
    team_mention: TeamMention
    team_context: TeamContext
    query_type: QueryType

ALLOWED_QUERY_TYPES={
    "match_count",
    "home_wins",
    "away_wins",
    "goals_scored",
}

ALLOWED_LEAGUES={"en","es"}

LEAGUE_ABB_TO_CODE={
    "epl": "en",
    "laliga": "es",
}

LEAGUE_NAME_TO_CODE={
    "english premier league": "en",
    "laliga":"es",
    "la liga":"es"
}

def empty_sql_spec() -> SQLSpec:
    return {
        "competition_mention":{
            "abb": None,
            "league_name": None,
        },
        "competition_context":{
            "league": None,
            "seasons":[],
        },
        "team_mention":{
            "team_name":None
        },
        "team_context":{
            "league":None
        },
        "query_type":"match_count"
    }

def normalize_season(raw:str) -> str:
    """
    Normalize season strings into the canonical form used by the system.
    Examples:
      2021/22 -> 2021-22
      2021-22 -> 2021-22
    """

    s=raw.strip()
    s=s.replace("/","-")
    return s

def normalize_sql_spec(spec: Dict[str, Any]) -> SQLSpec:
    """
    Best-effort normalization into the canonical SQLSpec shape.
    Useful for both the rule-based parser and a future LLM parser.
    """
    base=empty_sql_spec()

    comp_mention=spec.get("competition_mention", {}) or {}
    comp_context=spec.get("competition_context", {}) or {}
    team_mention=spec.get("team_mention", {}) or {}
    team_context=spec.get("team_context", {}) or {}

    abb=comp_mention.get("abb")
    league_name=comp_mention.get("league_name")
    team_name=team_mention.get("team_name")
    query_type=spec.get("query_type")

    if isinstance(abb, str):
        abb=abb.strip().lower()
    else:
        abb=None

    if isinstance(league_name, str):
        league_name=league_name.strip().lower()
    else:
        league_name=None

    if isinstance(team_name, str):
        team_name=team_name.strip().lower()
    else:
        team_name=None

    league=comp_context.get("league")
    if isinstance(league, str):
        league=league.strip().lower()
    else:
        league=None

    if league is None and abb in LEAGUE_ABB_TO_CODE:
        league = LEAGUE_ABB_TO_CODE[abb]
    if league is None and league_name in LEAGUE_NAME_TO_CODE:
        league = LEAGUE_NAME_TO_CODE[league_name]

    if league and not league_name and league in ALLOWED_LEAGUES:
        for k,v  in LEAGUE_NAME_TO_CODE.items():
            if v==league:
                league_name=k
                break

    if league not in ALLOWED_LEAGUES:
        league = None

    seasons_raw=comp_context.get("seasons", [])
    seasons: list[str]=[]
    if isinstance(seasons_raw, list):
        for s in seasons_raw:
            if isinstance(s,str) and s.strip():
                seasons.append(normalize_season(s))

    team_league=team_context.get("league")
    if isinstance(team_league,str):
        team_league=team_league.strip().lower()
    else:
        team_league=None

    if team_league not in ALLOWED_LEAGUES:
        team_league=league
    
    if query_type is not None and query_type not in ALLOWED_QUERY_TYPES:
        raise ValueError(f"Invalid query_type: {query_type}")
    
    base["competition_mention"]["abb"] = abb
    base["competition_mention"]["league_name"] = league_name
    base["competition_context"]["league"] = league
    base["competition_context"]["seasons"] = seasons
    base["team_mention"]["team_name"] = team_name
    base["team_context"]["league"] = team_league
    base["query_type"] = query_type

    return base

def validate_sql_spec(spec: Dict[str, Any]) -> SQLSpec:
    """
    Strict validaton after normalization.
    Returns a canonical SQLSpec or raises ValueError
    """
    normalized=normalize_sql_spec(spec)

    if normalized["query_type"] not in ALLOWED_QUERY_TYPES:
        raise ValueError(f"Unsupported query_type: {normalized['query_type']}")

    seasons=normalized["competition_context"]["seasons"]
    if not isinstance(seasons, list):
        raise ValueError("competition_context.seasons must be a list")
    
    if not isinstance(normalized["competition_mention"], dict):
        raise ValueError("competition_mention must be a dict")
    if not isinstance(normalized["competition_context"], dict):
        raise ValueError("competition_context must be a dict")
    if not isinstance(normalized["team_mention"], dict):
        raise ValueError("team_mention must be a dict")
    if not isinstance(normalized["team_context"], dict):
        raise ValueError("team_context must be a dict")

    return normalized