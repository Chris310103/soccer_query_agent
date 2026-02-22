import json
import sqlite3
from pathlib import Path

def create_tables(conn: sqlite3.Connection) -> None:
    cur=conn.cursor()

    # create table competition(one record represents one season and one league)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS competitions(
                comp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_code TEXT NOT NULL,
                season TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(league_code, season)
                );
                """)
    
    # create a table teams, the name should be unique 
    cur.execute("""
                CREATE TABLE IF NOT EXISTS teams(
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE)
                ;
                """)
    # create a table matches which contains teams, dates, scores.etc
    cur.execute("""
                CREATE TABLE IF NOT EXISTS matches(
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                comp_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                round_name TEXT,
                match_date TEXT,
                match_time TEXT,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_goals INTEGER,
                away_goals INTEGER,
                FOREIGN KEY(comp_id) REFERENCES competitions(comp_id),
                FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
                FOREIGN KEY(away_team_id) REFERENCES teams(team_id),
                UNIQUE(comp_id, match_date, match_time, home_team_id, away_team_id)
                );
                """)
    conn.commit()

def get_or_create_team(cur:sqlite3.Cursor, team_name:str) -> int:
    cur.execute("INSERT OR IGNORE INTO teams(name) VALUES(?)", (team_name,))
    cur.execute("SELECT team_id FROM teams WHERE name = ?", (team_name,))
    return int(cur.fetchone()[0])

def parse_league_and_season(filename:str) -> tuple[str, str]:
    stem=Path(filename).stem
    league_code,short=stem.split("_", 1)
    start_yy, end_yy = short.split("-")
    start_year=2000+int(start_yy)
    season = f"{start_year}-{end_yy}"
    return league_code, season

def main():
    # point to the JSON file path
    f_path=Path("external")
    #input file
    fl=sorted(list(f_path.glob("en_*.json"))+list(f_path.glob("es_*.json")))
    #output file
    out_db=Path("soccer_agent/data/soccer.sqlite")
    out_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(out_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        create_tables(conn)
        cur = conn.cursor()
        for f in fl:
            league_code, season = parse_league_and_season(f.name)

            d = json.load(open(f, "r", encoding="utf-8"))
            comp_name = d.get("name", f"{league_code.upper()} {season}")

        #insert comp_name in table competitions and get comp_id
            cur.execute("insert or ignore into competitions(league_code, season, name) VALUES(?, ?, ?)", (league_code, season, comp_name))
            cur.execute("select comp_id from competitions where league_code=? and season=?", (league_code, season))
            comp_id = cur.fetchone()[0]
            

            match_count=0
            m = d['matches']
            for match in m:
                round_name = match.get("round")
                match_date = match.get("date")
                match_time = match.get("time") or " "
                home_name = match.get("team1")
                away_name = match.get("team2") 

                if not home_name or not away_name:
                    continue
            #extract the socre from socre.ft
                score = match.get("score", {})
                ft = score.get('ft')
                home_goals=ft[0] if isinstance(ft, list) and len(ft) == 2 else None
                away_goals=ft[1] if isinstance(ft, list) and len(ft) == 2 else None

                home_id = get_or_create_team(cur, home_name)
                away_id = get_or_create_team(cur, away_name)

                cur.execute("""
                            insert or ignore into matches(comp_id, season, round_name, match_date,
                            match_time, home_team_id, away_team_id, home_goals, away_goals) Values(?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                            (comp_id, season, round_name, match_date, match_time, home_id, away_id, home_goals, away_goals))
                
                match_count+=1
            print(f"insert {match_count} matches from {f.name}")

        conn.commit()    

        print('db:', out_db.resolve())

    finally:
        conn.close()

if __name__ == "__main__":
    main()



