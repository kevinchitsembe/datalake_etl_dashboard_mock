"""
Carga (L do ETL): grava os dados limpos e os KPIs calculados numa base de
dados. Por agora usamos SQLite como placeholder da "Base de Dados Cloud" —
no ponto #3 esta camada passa a apontar para o Oracle, mantendo a mesma
interface (as funções de load não deviam precisar de mudar na app/dashboard).
"""

import sqlite3
import json
import pandas as pd
from . import config


def _get_connection() -> sqlite3.Connection:
    config.ANALYTICS_DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(config.ANALYTICS_DB_PATH)


def init_analytics_db() -> None:
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS etl_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            run_time TEXT NOT NULL,
            stock_file TEXT,
            sales_file TEXT,
            status TEXT NOT NULL,
            issues_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def load_dataframe(df: pd.DataFrame, table_name: str, client_id: str) -> None:
    """Substitui os dados de um cliente numa tabela (cada run reflete o estado mais recente)."""
    conn = _get_connection()
    df = df.copy()
    df["client_id"] = client_id

    existing = pd.read_sql(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'", conn
    )
    if not existing.empty:
        existing_cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
        if existing_cols != set(df.columns):
            # O schema mudou desde a última vez (ex: nomes de coluna foram atualizados) -
            # recriar a tabela em vez de falhar com "no column named ...".
            conn.execute(f"DROP TABLE {table_name}")
            conn.commit()
        else:
            conn.execute(f"DELETE FROM {table_name} WHERE client_id = ?", (client_id,))
            conn.commit()

    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()


def load_resumo(resumo: dict, client_id: str) -> None:
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kpi_resumo_semana (
            client_id TEXT,
            periodo_inicio TEXT,
            periodo_fim TEXT,
            data_json TEXT,
            PRIMARY KEY (client_id, periodo_inicio, periodo_fim)
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO kpi_resumo_semana (client_id, periodo_inicio, periodo_fim, data_json) "
        "VALUES (?, ?, ?, ?)",
        (client_id, resumo["periodo_inicio"], resumo["periodo_fim"], json.dumps(resumo, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def log_etl_run(client_id: str, stock_file: str, sales_file: str, status: str, issues: list) -> None:
    import datetime
    conn = _get_connection()
    conn.execute(
        "INSERT INTO etl_runs (client_id, run_time, stock_file, sales_file, status, issues_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            client_id, datetime.datetime.now().isoformat(timespec="seconds"),
            stock_file, sales_file, status,
            json.dumps([str(i) for i in issues], ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()