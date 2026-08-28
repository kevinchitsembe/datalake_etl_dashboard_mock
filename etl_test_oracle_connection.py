"""
Testa a ligação ao Oracle com as credenciais configuradas.
As tabelas são criadas/atualizadas automaticamente pelo ETL - não é
preciso correr nenhum script SQL antes.

Uso:
    python -m etl.test_oracle_connection
"""

from . import config, load_oracle

PROJECT_TABLE_NAMES = [
    "STOCK_PRODUTOS", "VENDAS_DIARIAS", "KPI_PRODUTO",
    "KPI_CATEGORIA", "KPI_DIARIO", "KPI_RESUMO_SEMANA", "ETL_RUNS",
]


def main():
    cfg = config.get_oracle_config()
    print(f"A ligar como utilizador: {cfg['user']} ...")
    try:
        conn = load_oracle._get_connection()
        print("✅ Ligação estabelecida com sucesso.")
    except Exception as e:
        print(f"❌ Falha na ligação: {e}")
        return

    cur = conn.cursor()
    cur.execute("SELECT table_name FROM user_tables")
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()

    present = [t for t in PROJECT_TABLE_NAMES if t in existing]
    if present:
        print(f"\nJá existem tabelas do projeto neste schema: {present}")
    else:
        print(
            "\nAinda não há tabelas do projeto neste schema — serão criadas "
            "automaticamente na primeira vez que correres 'python -m etl.run_etl <client_id>' "
            "com DB_BACKEND=oracle."
        )


if __name__ == "__main__":
    main()