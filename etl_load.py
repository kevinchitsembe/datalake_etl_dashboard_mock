"""
Ponto único de entrada para a camada de carga (L do ETL).

O resto do pipeline (run_etl.py) só conhece este módulo — nunca importa
load_sqlite ou load_oracle diretamente. Isto permite trocar de motor de
base de dados só mudando config.DB_BACKEND, sem tocar em mais nada.
"""

from . import config

if config.DB_BACKEND == "oracle":
    from . import load_oracle as _backend
elif config.DB_BACKEND == "sqlite":
    from . import load_sqlite as _backend
else:
    raise ValueError(f"DB_BACKEND desconhecido: '{config.DB_BACKEND}' (usa 'sqlite' ou 'oracle')")


def init_analytics_db() -> None:
    return _backend.init_analytics_db()


def load_dataframe(df, table_name: str, client_id: str) -> None:
    return _backend.load_dataframe(df, table_name, client_id)


def load_resumo(resumo: dict, client_id: str) -> None:
    return _backend.load_resumo(resumo, client_id)


def log_etl_run(client_id: str, stock_file: str, sales_file: str, status: str, issues: list) -> None:
    return _backend.log_etl_run(client_id, stock_file, sales_file, status, issues)