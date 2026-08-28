"""Transformação (T do ETL): limpeza e normalização dos dados brutos."""

import pandas as pd

# Nomes de colunas "seguros" para qualquer base de dados (sem acentos/espaços).
# O SQLite tolera nomes com acentos e espaços, mas o Oracle não - por isso
# normalizamos aqui, logo após a limpeza, para os dois backends usarem os
# mesmos nomes de coluna.
STOCK_COLUMN_MAP = {
    "Código Produto": "codigo_produto",
    "Produto": "produto",
    "Categoria": "categoria",
    "Stock Inicial": "stock_inicial",
    "Entradas na Semana": "entradas_semana",
    "Unidades Vendidas": "unidades_vendidas",
    "Stock Final": "stock_final",
    "Stock Mínimo": "stock_minimo",
    "Reposição Necessária": "reposicao_necessaria",
    "Preço Venda (MT)": "preco_venda_mt",
    "Custo Unitário (MT)": "custo_unitario_mt",
}

SALES_COLUMN_MAP = {
    "Data": "data",
    "Código Produto": "codigo_produto",
    "Produto": "produto",
    "Categoria": "categoria",
    "Quantidade": "quantidade",
    "Preço Unitário (MT)": "preco_unitario_mt",
    "Vendas Líquidas (MT)": "vendas_liquidas_mt",
    "Custo (MT)": "custo_mt",
    "Margem Bruta (MT)": "margem_bruta_mt",
    "Desconto": "desconto",
}


def clean_stock(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Código Produto"] = df["Código Produto"].str.strip()
    df["Produto"] = df["Produto"].str.strip()
    df["Categoria"] = df["Categoria"].str.strip()
    numeric_cols = [
        "Stock Inicial", "Entradas na Semana", "Unidades Vendidas", "Stock Final",
        "Stock Mínimo", "Reposição Necessária", "Preço Venda (MT)", "Custo Unitário (MT)",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.drop_duplicates(subset=["Código Produto"], keep="last")
    df = df.rename(columns=STOCK_COLUMN_MAP)
    return df


def clean_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Código Produto"] = df["Código Produto"].str.strip()
    df["Produto"] = df["Produto"].str.strip()
    df["Categoria"] = df["Categoria"].str.strip()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    numeric_cols = [
        "Quantidade", "Preço Unitário (MT)", "Vendas Líquidas (MT)",
        "Custo (MT)", "Margem Bruta (MT)", "Desconto",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.dropna(subset=["Data"])
    df = df.drop_duplicates()
    df = df.rename(columns=SALES_COLUMN_MAP)
    return df
