from typing import List,Sequence,Any
import sqlite3
import sqlparse

class SQLInjectionError(Exception):
    pass


class SQLExecutor:
    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur

    def check_sql(self, sql: str) -> str:
        sql = sql.strip()

        parsed = sqlparse.parse(sql)
        if not parsed:
            raise SQLInjectionError("Empty SQL is not allowed")

        stmt = parsed[0]
        if stmt.get_type() != "SELECT":
            raise SQLInjectionError("Only SELECT statements are allowed")

        if ";" in sql[:-1]:
            raise SQLInjectionError("Multiple SQL statements are not allowed")

        if " limit " not in f" {sql.lower()} ":
            sql = sql.rstrip(";") + "\nLIMIT 200;"

        return sql

    def execute_sql(self, sql: str, params: Sequence[Any] | None = None):
        try:
            safe_sql = self.check_sql(sql)
            self.cur.execute(safe_sql, params or [])
            rows = self.cur.fetchall()
            columns = [col[0] for col in self.cur.description] if self.cur.description else []

            return {
                "status": "success",
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "error": None,
            }

        except Exception as e:
            return {
                "status": "error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
            }

    
            
    


