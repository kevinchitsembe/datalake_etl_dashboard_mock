"""
Camada de leitura para o dashboard: vai buscar os KPIs já calculados pelo
ETL, usando o mesmo backend configurado em config.DB_BACKEND (sqlite/oracle).
O dashboard nunca calcula nada — só lê o que o ETL já gravou.
"""

import json
import re
import pandas as pd

from . import config

if config.DB_BACKEND == "oracle":
    from . import load_oracle as _backend
elif config.DB_BACKEND == "sqlite":
    from . import load_sqlite as _backend
else:
    raise ValueError(f"DB_BACKEND desconhecido: '{config.DB_BACKEND}' (usa 'sqlite' ou 'oracle')")


def _connection():
    return _backend._get_connection()


def _safe_client_id(client_id: str) -> str:
    """Validação simples para evitar injeção de SQL ao interpolar o client_id."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", client_id):
        raise ValueError(f"client_id inválido: {client_id!r}")
    return client_id


def _read_lob(value):
    """Converte um LOB (Oracle) para string, se for o caso; texto normal (SQLite) passa direto."""
    if hasattr(value, "read"):
        return value.read()
    return value


def _query_df(sql: str) -> pd.DataFrame:
    conn = _connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def get_kpi_produto(client_id: str) -> pd.DataFrame:
    cid = _safe_client_id(client_id)
    return _query_df(f"SELECT * FROM kpi_produto WHERE client_id = '{cid}'")


def get_kpi_categoria(client_id: str) -> pd.DataFrame:
    cid = _safe_client_id(client_id)
    df = _query_df(f"SELECT * FROM kpi_categoria WHERE client_id = '{cid}'")
    return df.sort_values("vendas_liquidas_mt", ascending=False).reset_index(drop=True)


def get_kpi_diario(client_id: str) -> pd.DataFrame:
    cid = _safe_client_id(client_id)
    df = _query_df(f"SELECT * FROM kpi_diario WHERE client_id = '{cid}'")
    return df.sort_values("data").reset_index(drop=True)


def get_resumo(client_id: str) -> dict | None:
    """Devolve o resumo semanal mais recente (dict), ou None se ainda não houver."""
    cid = _safe_client_id(client_id)
    conn = _connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT data_json FROM kpi_resumo_semana WHERE client_id = '{cid}' "
        f"ORDER BY periodo_fim DESC"
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None
    return json.loads(_read_lob(row[0]))


def get_etl_runs(client_id: str, limit: int = 10) -> pd.DataFrame:
    cid = _safe_client_id(client_id)
    df = _query_df(f"SELECT * FROM etl_runs WHERE client_id = '{cid}' ORDER BY run_time DESC")
    return df.head(limit)


def has_data(client_id: str) -> bool:
    try:
        return get_resumo(client_id) is not None
    except Exception:
        return False
