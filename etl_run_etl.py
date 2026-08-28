"""
Orquestrador do ETL — Ponto #2 do fluxo "Processo Automatizado".

Uso:
    python -m etl.run_etl supermercado_a
"""

import sys
from . import extract, validate, transform, kpis, load, config


def run_etl(client_id: str) -> dict:
    print(f"\n=== ETL: {client_id} ===")

    print("1. A extrair ficheiros do Data Lake...")
    raw = extract.extract(client_id)
    df_stock_raw = raw["stock_sheets"]["Gestão de Stock"]
    df_sales_raw = raw["sales_sheets"]["Vendas Diárias"]
    print(f"   Stock: {raw['stock_path'].name}")
    print(f"   Vendas: {raw['sales_path'].name}")

    print("2. A validar dados...")
    issues = validate.run_all_validations(df_stock_raw, df_sales_raw)
    for issue in issues:
        print(f"   {issue}")

    if validate.has_blocking_errors(issues):
        print("❌ ETL abortado: existem erros bloqueantes.")
        load.init_analytics_db()
        load.log_etl_run(client_id, str(raw["stock_path"]), str(raw["sales_path"]), "ERRO", issues)
        return {"status": "ERRO", "issues": issues}

    print("3. A limpar dados...")
    df_stock = transform.clean_stock(df_stock_raw)
    df_sales = transform.clean_sales(df_sales_raw)

    print("4. A calcular KPIs...")
    df_kpi_produto = kpis.kpis_por_produto(df_stock, df_sales)
    df_kpi_categoria = kpis.kpis_por_categoria(df_sales, df_stock)
    df_kpi_diario = kpis.kpis_diarios(df_sales)
    resumo = kpis.resumo_semanal(df_kpi_produto, df_kpi_diario, df_sales)

    print("5. A carregar na Base de Dados...")
    load.init_analytics_db()
    load.load_dataframe(df_stock, "stock_produtos", client_id)
    load.load_dataframe(df_sales, "vendas_diarias", client_id)
    load.load_dataframe(df_kpi_produto, "kpi_produto", client_id)
    load.load_dataframe(df_kpi_categoria, "kpi_categoria", client_id)
    load.load_dataframe(df_kpi_diario, "kpi_diario", client_id)
    load.load_resumo(resumo, client_id)
    load.log_etl_run(client_id, str(raw["stock_path"]), str(raw["sales_path"]), "OK", issues)

    print("✅ ETL concluído com sucesso.\n")
    print("--- Resumo da semana ---")
    for k, v in resumo.items():
        print(f"   {k}: {v}")

    return {
        "status": "OK",
        "issues": issues,
        "kpi_produto": df_kpi_produto,
        "kpi_categoria": df_kpi_categoria,
        "kpi_diario": df_kpi_diario,
        "resumo": resumo,
    }


if __name__ == "__main__":
    client = sys.argv[1] if len(sys.argv) > 1 else "supermercado_a"
    run_etl(client)
