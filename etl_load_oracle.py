"""
Carga (L do ETL) para Oracle. Mesma interface que load_sqlite.py:
init_analytics_db, load_dataframe, load_resumo, log_etl_run.

Usa o driver 'python-oracledb' em modo "thin" (não precisa de instalar
o Oracle Instant Client à parte).

As tabelas são criadas AUTOMATICAMENTE na primeira execução, a partir das
colunas do próprio DataFrame — não é preciso correr nenhum SQL à mão.
Se no futuro o ETL passar a produzir colunas diferentes (nova métrica,
coluna removida, etc.), a tabela é recriada automaticamente para bater
certo com o novo formato (db/schema_oracle.sql fica só como documentação
de referência do schema, não é necessário correr).
"""

import json
import datetime
import pandas as pd
import oracledb

from . import config


def _build_dsn(cfg: dict) -> str:
    """Monta o dsn a partir de host/port/service_name (estilo oracledb.makedsn), ou usa o dsn direto."""
    if cfg.get("host") and cfg.get("service_name"):
        return oracledb.makedsn(cfg["host"], cfg.get("port") or 1521, service_name=cfg["service_name"])
    if cfg.get("dsn"):
        return cfg["dsn"]
    raise RuntimeError("Configuração Oracle incompleta: falta 'dsn' ou 'host'+'service_name'.")


def _get_connection():
    cfg = config.get_oracle_config()
    dsn = _build_dsn(cfg)
    try:
        conn = oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=dsn)
        return conn
    except oracledb.Error as e:
        print(f"❌ Erro ao conectar ao Oracle: {e}")
        raise


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :t", {"t": table_name.upper()})
    return cur.fetchone()[0] > 0


def _existing_columns(cur, table_name: str) -> set:
    cur.execute("SELECT column_name FROM user_tab_columns WHERE table_name = :t", {"t": table_name.upper()})
    return {row[0] for row in cur.fetchall()}


def _infer_oracle_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DATE"
    if pd.api.types.is_bool_dtype(series):
        return "NUMBER(1)"
    if pd.api.types.is_integer_dtype(series):
        return "NUMBER(18)"
    if pd.api.types.is_float_dtype(series):
        return "NUMBER"
    return "VARCHAR2(300)"  # texto - tamanho generoso para não ter de recriar por causa de valores maiores


def _ensure_table_matches_dataframe(cur, table_name: str, df: pd.DataFrame) -> None:
    """
    Garante que a tabela existe e tem exatamente as colunas do DataFrame.
    Cria a tabela se não existir; recria (drop + create) se as colunas mudaram.
    Isto é o que permite ao cliente "atualizar os dados" sem intervenção manual:
    sempre que o ETL corre, a tabela fica sincronizada com o formato atual.
    """
    expected_cols = {c.upper() for c in df.columns}

    if _table_exists(cur, table_name):
        if _existing_columns(cur, table_name) == expected_cols:
            return  # já está tudo certo, nada a fazer
        cur.execute(f"DROP TABLE {table_name} PURGE")

    col_defs = ",\n    ".join(f"{col} {_infer_oracle_type(df[col])}" for col in df.columns)
    cur.execute(f"CREATE TABLE {table_name} (\n    {col_defs}\n)")


def _ensure_resumo_table(cur) -> None:
    if not _table_exists(cur, "kpi_resumo_semana"):
        cur.execute("""
            CREATE TABLE kpi_resumo_semana (
                client_id       VARCHAR2(50) NOT NULL,
                periodo_inicio  VARCHAR2(20) NOT NULL,
                periodo_fim     VARCHAR2(20) NOT NULL,
                data_json       CLOB,
                CONSTRAINT pk_kpi_resumo_semana PRIMARY KEY (client_id, periodo_inicio, periodo_fim)
            )
        """)


def _ensure_etl_runs_table(cur) -> None:
    if not _table_exists(cur, "etl_runs"):
        cur.execute("""
            CREATE TABLE etl_runs (
                id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                client_id    VARCHAR2(50)  NOT NULL,
                run_time     TIMESTAMP,
                stock_file   VARCHAR2(400),
                sales_file   VARCHAR2(400),
                status       VARCHAR2(20),
                issues_json  CLOB
            )
        """)


def init_analytics_db() -> None:
    """
    Garante que as tabelas 'estruturais' (que não vêm de um DataFrame do ETL)
    existem: kpi_resumo_semana e etl_runs. As restantes (stock_produtos,
    vendas_diarias, kpi_produto, kpi_categoria, kpi_diario) são criadas/
    atualizadas automaticamente em load_dataframe(), na primeira vez que
    são gravadas.
    """
    conn = _get_connection()
    cur = conn.cursor()
    _ensure_resumo_table(cur)
    _ensure_etl_runs_table(cur)
    conn.commit()
    cur.close()
    conn.close()


def _dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Converte NaN/NaT -> None e Timestamps -> datetime, para bind variables do oracledb."""
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, pd.Timestamp):
                record[key] = value.to_pydatetime()
    return records


def load_dataframe(df: pd.DataFrame, table_name: str, client_id: str) -> None:
    """Cria/atualiza a tabela se necessário, e substitui os dados desse cliente."""
    conn = _get_connection()
    cur = conn.cursor()

    df = df.copy()
    df["client_id"] = client_id

    _ensure_table_matches_dataframe(cur, table_name, df)

    cur.execute(f"DELETE FROM {table_name} WHERE client_id = :client_id", {"client_id": client_id})

    columns = list(df.columns)
    col_list = ", ".join(columns)
    bind_list = ", ".join(f":{c}" for c in columns)
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({bind_list})"

    records = _dataframe_to_records(df)
    if records:
        cur.executemany(insert_sql, records)

    conn.commit()
    cur.close()
    conn.close()


def load_resumo(resumo: dict, client_id: str) -> None:
    conn = _get_connection()
    cur = conn.cursor()
    _ensure_resumo_table(cur)
    cur.execute(
        """
        MERGE INTO kpi_resumo_semana t
        USING (SELECT :client_id AS client_id, :periodo_inicio AS periodo_inicio,
                      :periodo_fim AS periodo_fim FROM dual) s
        ON (t.client_id = s.client_id AND t.periodo_inicio = s.periodo_inicio
            AND t.periodo_fim = s.periodo_fim)
        WHEN MATCHED THEN UPDATE SET t.data_json = :data_json
        WHEN NOT MATCHED THEN INSERT (client_id, periodo_inicio, periodo_fim, data_json)
            VALUES (:client_id, :periodo_inicio, :periodo_fim, :data_json)
        """,
        {
            "client_id": client_id,
            "periodo_inicio": resumo["periodo_inicio"],
            "periodo_fim": resumo["periodo_fim"],
            "data_json": json.dumps(resumo, ensure_ascii=False),
        },
    )
    conn.commit()
    cur.close()
    conn.close()


def log_etl_run(client_id: str, stock_file: str, sales_file: str, status: str, issues: list) -> None:
    conn = _get_connection()
    cur = conn.cursor()
    _ensure_etl_runs_table(cur)
    cur.execute(
        """INSERT INTO etl_runs (client_id, run_time, stock_file, sales_file, status, issues_json)
           VALUES (:client_id, :run_time, :stock_file, :sales_file, :status, :issues_json)""",
        {
            "client_id": client_id,
            "run_time": datetime.datetime.now(),
            "stock_file": stock_file,
            "sales_file": sales_file,
            "status": status,
            "issues_json": json.dumps([str(i) for i in issues], ensure_ascii=False),
        },
    )
    conn.commit()
    cur.close()
    conn.close()