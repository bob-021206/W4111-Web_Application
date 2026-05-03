from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from .AbstractBaseDataService import AbstractBaseDataService


def load_mysql_env() -> dict[str, Any]:
    import os

    return {
        "mysql_host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "mysql_port": int(os.getenv("MYSQL_PORT", "3306")),
        "mysql_user": os.getenv("MYSQL_USER", "root"),
        "mysql_password": os.getenv("MYSQL_PASSWORD", ""),
        "mysql_database": os.getenv("MYSQL_DATABASE", "classicmodels"),
    }


class MySQLDataService(AbstractBaseDataService):
    """
    Config keys:
      - mysql_host, mysql_port, mysql_user, mysql_password, mysql_database
      - table: physical table name
      - primary_key_columns: ordered list of PK column names (single or composite)
      - integer_columns: columns stored as int (template filters + PK parsing)
      - float_columns: columns stored as float/decimal
      - auto_increment_pk: if True, omit single integer PK on insert and use LAST_INSERT_ID or MAX+1
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._table = str(config["table"])
        self._pk_columns: list[str] = list(config["primary_key_columns"])
        self._integer_cols: set[str] = set(config.get("integer_columns", []))
        self._float_cols: set[str] = set(config.get("float_columns", []))
        self._auto_increment_pk = bool(config.get("auto_increment_pk", False))

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(
            host=str(self.config["mysql_host"]),
            port=int(self.config.get("mysql_port", 3306)),
            user=str(self.config["mysql_user"]),
            password=str(self.config["mysql_password"]),
            database=str(self.config["mysql_database"]),
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                out[k] = v.date().isoformat()
            elif isinstance(v, date):
                out[k] = v.isoformat()
            elif isinstance(v, Decimal):
                out[k] = float(v)
            else:
                out[k] = v
        return out

    def _coerce_value(self, col: str, value: Any) -> Any:
        if value is None:
            return None
        if col in self._integer_cols:
            return int(value)
        if col in self._float_cols:
            return float(value)
        return value

    def _coerce_template(self, template: dict) -> dict[str, Any]:
        return {
            k: self._coerce_value(k, v)
            for k, v in template.items()
            if v is not None and str(v) != ""
        }

    def _split_primary_key(self, primary_key: str) -> list[Any]:
        if len(self._pk_columns) == 1:
            col = self._pk_columns[0]
            return [self._coerce_value(col, primary_key)]
        if len(self._pk_columns) == 2:
            a, b = primary_key.split("|", 1)
            return [
                self._coerce_value(self._pk_columns[0], a),
                self._coerce_value(self._pk_columns[1], b),
            ]
        raise ValueError("Unsupported composite primary key shape")

    def encode_primary_key(self, row: dict) -> str:
        if len(self._pk_columns) == 1:
            return str(row[self._pk_columns[0]])
        parts = [row[c] for c in self._pk_columns]
        return "|".join(str(p) for p in parts)

    def retrieveByPrimaryKey(self, primary_key: str) -> dict:
        try:
            parts = self._split_primary_key(primary_key)
        except ValueError:
            return {}
        where_sql = " AND ".join(f"`{c}`=%s" for c in self._pk_columns)
        sql = f"SELECT * FROM `{self._table}` WHERE {where_sql} LIMIT 1"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(parts))
                row = cur.fetchone()
        return self._normalize_row(dict(row)) if row else {}

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        filt = self._coerce_template(template)
        if not filt:
            sql = f"SELECT * FROM `{self._table}`"
            args: tuple = ()
        else:
            where_sql = " AND ".join(f"`{k}`=%s" for k in filt)
            sql = f"SELECT * FROM `{self._table}` WHERE {where_sql}"
            args = tuple(filt[k] for k in filt)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, args)
                rows = cur.fetchall()
        return [self._normalize_row(dict(r)) for r in rows]

    def _next_int_pk(self, conn: pymysql.connections.Connection, col: str) -> int:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COALESCE(MAX(`{col}`), 0) + 1 AS n FROM `{self._table}`")
            row = cur.fetchone()
            return int(row["n"])

    def create(self, payload: dict) -> str:
        data = {k: v for k, v in payload.items() if v is not None}
        if len(self._pk_columns) == 1 and self._auto_increment_pk:
            pk_col = self._pk_columns[0]
            if pk_col not in data or data[pk_col] is None or str(data[pk_col]).strip() == "":
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        new_pk = self._next_int_pk(conn, pk_col)
                        data[pk_col] = new_pk
                        cols = list(data.keys())
                        placeholders = ", ".join(["%s"] * len(cols))
                        sql = f"INSERT INTO `{self._table}` ({','.join(f'`{c}`' for c in cols)}) VALUES ({placeholders})"
                        cur.execute(sql, tuple(self._coerce_row_for_write(data, cols)))
                    conn.commit()
                return str(new_pk)

        if len(self._pk_columns) > 1:
            for c in self._pk_columns:
                if c not in data:
                    raise ValueError(f"Missing primary key field {c!r}")

        cols = list(data.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{self._table}` ({','.join(f'`{c}`' for c in cols)}) VALUES ({placeholders})"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(self._coerce_row_for_write(data, cols)))
                last = cur.lastrowid
            conn.commit()
        row_out = dict(data)
        if len(self._pk_columns) == 1 and last:
            row_out[self._pk_columns[0]] = last
        return self.encode_primary_key(row_out)

    def _coerce_row_for_write(self, data: dict, cols: list[str]) -> list[Any]:
        out: list[Any] = []
        for c in cols:
            v = data[c]
            out.append(self._coerce_value(c, v) if c in self._integer_cols | self._float_cols else v)
        return out

    def updateByPrimaryKey(self, primary_key: str, payload: dict) -> int:
        try:
            parts = self._split_primary_key(primary_key)
        except ValueError:
            return 0
        updates = {k: v for k, v in payload.items() if k not in self._pk_columns}
        if not updates:
            return 0
        set_sql = ", ".join(f"`{k}`=%s" for k in updates)
        where_sql = " AND ".join(f"`{c}`=%s" for c in self._pk_columns)
        sql = f"UPDATE `{self._table}` SET {set_sql} WHERE {where_sql}"
        vals = [
            self._coerce_value(k, updates[k]) if k in self._integer_cols | self._float_cols else updates[k]
            for k in updates
        ]
        vals.extend(parts)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(vals))
                n = cur.rowcount
            conn.commit()
        return int(n)

    def deleteByPrimaryKey(self, primary_key: str) -> int:
        try:
            parts = self._split_primary_key(primary_key)
        except ValueError:
            return 0
        where_sql = " AND ".join(f"`{c}`=%s" for c in self._pk_columns)
        sql = f"DELETE FROM `{self._table}` WHERE {where_sql}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(parts))
                n = cur.rowcount
            conn.commit()
        return int(n)
