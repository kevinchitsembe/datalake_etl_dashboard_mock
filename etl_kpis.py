"""
Cálculo de KPIs e métricas de negócio a partir dos dados limpos de
stock e vendas. Cada função devolve um DataFrame pronto a carregar na BD.

Nota: recebe os DataFrames já com nomes de coluna normalizados
(ver etl/transform.py -> STOCK_COLUMN_MAP / SALES_COLUMN_MAP).
"""

import pandas as pd
from . import config


def classify_stock_status(row) -> str:
    if row["stock_final"] <= row["stock_minimo"] * config.RUPTURA_MULTIPLICADOR:
        return "Ruptura"
    elif row["stock_final"] <= row["stock_minimo"] * config.ALERTA_MULTIPLICADOR:
        return "Alerta"
    return "OK"


def kpis_por_produto(df_stock: pd.DataFrame, df_sales: pd.DataFrame) -> pd.DataFrame:
    """KPIs semanais por produto, combinando stock e vendas diárias."""
    vendas_agg = df_sales.groupby(["codigo_produto"]).agg(
        vendas_liquidas_semana=("vendas_liquidas_mt", "sum"),
        margem_bruta_semana=("margem_bruta_mt", "sum"),
        desconto_total=("desconto", "sum"),
        unidades_vendidas_diarias=("quantidade", "sum"),
    ).reset_index()

    df = df_stock.merge(vendas_agg, on="codigo_produto", how="left")
    df[["vendas_liquidas_semana", "margem_bruta_semana", "desconto_total",
        "unidades_vendidas_diarias"]] = df[[
        "vendas_liquidas_semana", "margem_bruta_semana", "desconto_total",
        "unidades_vendidas_diarias"
    ]].fillna(0)

    df["stock_medio"] = (df["stock_inicial"] + df["stock_final"]) / 2
    df["rotatividade_semanal"] = df.apply(
        lambda r: r["unidades_vendidas"] / r["stock_medio"] if r["stock_medio"] > 0 else 0, axis=1
    )
    df["venda_media_diaria"] = df["unidades_vendidas"] / 7
    df["cobertura_dias"] = df.apply(
        lambda r: r["stock_final"] / r["venda_media_diaria"] if r["venda_media_diaria"] > 0 else 999,
        axis=1,
    )
    df["margem_unitaria_mt"] = df["preco_venda_mt"] - df["custo_unitario_mt"]
    df["margem_unitaria_pct"] = df.apply(
        lambda r: r["margem_unitaria_mt"] / r["preco_venda_mt"] if r["preco_venda_mt"] > 0 else 0, axis=1
    )
    df["valor_stock_final_mt"] = df["stock_final"] * df["custo_unitario_mt"]
    df["ticket_medio_unidade_mt"] = df.apply(
        lambda r: r["vendas_liquidas_semana"] / r["unidades_vendidas_diarias"]
        if r["unidades_vendidas_diarias"] > 0 else 0, axis=1
    )
    df["status_stock"] = df.apply(classify_stock_status, axis=1)

    result = df[[
        "codigo_produto", "produto", "categoria",
        "stock_inicial", "entradas_semana", "unidades_vendidas", "stock_final", "stock_minimo",
        "preco_venda_mt", "custo_unitario_mt",
        "vendas_liquidas_semana", "margem_bruta_semana", "desconto_total",
        "rotatividade_semanal", "cobertura_dias", "margem_unitaria_mt", "margem_unitaria_pct",
        "valor_stock_final_mt", "ticket_medio_unidade_mt", "status_stock",
    ]].rename(columns={"unidades_vendidas": "unidades_vendidas_semana"})
    return result


def kpis_por_categoria(df_sales: pd.DataFrame, df_stock: pd.DataFrame) -> pd.DataFrame:
    vendas = df_sales.groupby("categoria").agg(
        unidades_vendidas=("quantidade", "sum"),
        vendas_liquidas_mt=("vendas_liquidas_mt", "sum"),
        margem_bruta_mt=("margem_bruta_mt", "sum"),
    ).reset_index()
    vendas["margem_pct"] = vendas.apply(
        lambda r: r["margem_bruta_mt"] / r["vendas_liquidas_mt"] if r["vendas_liquidas_mt"] > 0 else 0, axis=1
    )
    num_produtos = df_stock.groupby("categoria")["codigo_produto"].nunique().reset_index()
    num_produtos.columns = ["categoria", "num_produtos"]

    result = vendas.merge(num_produtos, on="categoria", how="left")
    return result.sort_values("vendas_liquidas_mt", ascending=False).reset_index(drop=True)


def kpis_diarios(df_sales: pd.DataFrame) -> pd.DataFrame:
    diario = df_sales.groupby(df_sales["data"].dt.date).agg(
        unidades_vendidas=("quantidade", "sum"),
        vendas_liquidas_mt=("vendas_liquidas_mt", "sum"),
        margem_bruta_mt=("margem_bruta_mt", "sum"),
        num_produtos_vendidos=("codigo_produto", "nunique"),
    ).reset_index()
    diario["ticket_medio_mt"] = diario.apply(
        lambda r: r["vendas_liquidas_mt"] / r["unidades_vendidas"] if r["unidades_vendidas"] > 0 else 0, axis=1
    )
    diario["data"] = diario["data"].astype(str)
    return diario.sort_values("data").reset_index(drop=True)


def resumo_semanal(df_produto: pd.DataFrame, df_diario: pd.DataFrame, df_sales: pd.DataFrame) -> dict:
    """Resumo executivo da semana, cruzando os KPIs já calculados."""
    total_vendas = df_produto["vendas_liquidas_semana"].sum()
    total_margem = df_produto["margem_bruta_semana"].sum()
    total_unidades = df_produto["unidades_vendidas_semana"].sum()

    melhor_dia = df_diario.loc[df_diario["vendas_liquidas_mt"].idxmax()]
    produto_mais_vendido = df_produto.loc[df_produto["unidades_vendidas_semana"].idxmax()]
    produto_mais_rentavel = df_produto.loc[df_produto["margem_bruta_semana"].idxmax()]
    produtos_risco = df_produto[df_produto["status_stock"].isin(["Ruptura", "Alerta"])]

    return {
        "periodo_inicio": str(df_sales["data"].min().date()),
        "periodo_fim": str(df_sales["data"].max().date()),
        "vendas_liquidas_totais_mt": float(total_vendas),
        "margem_bruta_total_mt": float(total_margem),
        "margem_pct_total": float(total_margem / total_vendas) if total_vendas > 0 else 0.0,
        "unidades_vendidas_totais": int(total_unidades),
        "ticket_medio_geral_mt": float(total_vendas / total_unidades) if total_unidades > 0 else 0.0,
        "melhor_dia": melhor_dia["data"],
        "melhor_dia_vendas_mt": float(melhor_dia["vendas_liquidas_mt"]),
        "produto_mais_vendido": produto_mais_vendido["produto"],
        "produto_mais_vendido_unidades": int(produto_mais_vendido["unidades_vendidas_semana"]),
        "produto_mais_rentavel": produto_mais_rentavel["produto"],
        "produto_mais_rentavel_margem_mt": float(produto_mais_rentavel["margem_bruta_semana"]),
        "num_produtos_em_risco": int(len(produtos_risco)),
        "produtos_em_risco": ", ".join(produtos_risco["produto"].tolist()) if not produtos_risco.empty else "",
    }
