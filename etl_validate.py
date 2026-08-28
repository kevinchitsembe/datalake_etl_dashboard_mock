"""
Validação: confirma que os ficheiros têm as colunas certas, os tipos certos,
e que os dois ficheiros (stock e vendas) são consistentes entre si.

Devolve uma lista de "issues": cada uma com nível ('ERRO' ou 'AVISO'),
para que o ETL saiba se deve abortar (ERRO) ou apenas registar (AVISO).
"""

import pandas as pd
from . import config


class ValidationIssue:
    def __init__(self, level: str, message: str):
        self.level = level  # 'ERRO' ou 'AVISO'
        self.message = message

    def __repr__(self):
        return f"[{self.level}] {self.message}"


def _check_required_columns(df: pd.DataFrame, required: list[str], sheet_label: str) -> list[ValidationIssue]:
    issues = []
    missing = [c for c in required if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(
            "ERRO", f"{sheet_label}: colunas em falta: {missing}"
        ))
    return issues


def _check_no_negative(df: pd.DataFrame, columns: list[str], sheet_label: str) -> list[ValidationIssue]:
    issues = []
    for col in columns:
        if col in df.columns and (df[col] < 0).any():
            n = (df[col] < 0).sum()
            issues.append(ValidationIssue(
                "AVISO", f"{sheet_label}: {n} valor(es) negativo(s) na coluna '{col}'"
            ))
    return issues


def validate_stock(df_stock: pd.DataFrame) -> list[ValidationIssue]:
    issues = []
    issues += _check_required_columns(df_stock, config.STOCK_REQUIRED_COLUMNS, "Gestão de Stock")
    if issues and any(i.level == "ERRO" for i in issues):
        return issues  # sem colunas base não vale a pena continuar a validar esta folha

    issues += _check_no_negative(
        df_stock, ["Stock Inicial", "Entradas na Semana", "Unidades Vendidas", "Stock Final", "Stock Mínimo"],
        "Gestão de Stock",
    )

    if df_stock["Código Produto"].duplicated().any():
        dups = df_stock.loc[df_stock["Código Produto"].duplicated(), "Código Produto"].tolist()
        issues.append(ValidationIssue("ERRO", f"Gestão de Stock: códigos de produto duplicados: {dups}"))

    # Preço de venda deve ser maior que o custo (senão a margem é negativa)
    margem_negativa = df_stock[df_stock["Preço Venda (MT)"] < df_stock["Custo Unitário (MT)"]]
    if not margem_negativa.empty:
        issues.append(ValidationIssue(
            "AVISO",
            f"Gestão de Stock: {len(margem_negativa)} produto(s) com preço de venda abaixo do custo: "
            f"{margem_negativa['Código Produto'].tolist()}"
        ))

    return issues


def validate_sales(df_sales: pd.DataFrame) -> list[ValidationIssue]:
    issues = []
    issues += _check_required_columns(df_sales, config.SALES_REQUIRED_COLUMNS, "Vendas Diárias")
    if issues and any(i.level == "ERRO" for i in issues):
        return issues

    issues += _check_no_negative(
        df_sales, ["Quantidade", "Preço Unitário (MT)", "Vendas Líquidas (MT)", "Custo (MT)"],
        "Vendas Diárias",
    )

    if df_sales.duplicated().any():
        n = df_sales.duplicated().sum()
        issues.append(ValidationIssue("AVISO", f"Vendas Diárias: {n} linha(s) duplicada(s)"))

    if not pd.api.types.is_datetime64_any_dtype(df_sales["Data"]):
        issues.append(ValidationIssue("AVISO", "Vendas Diárias: coluna 'Data' não está em formato de data"))

    return issues


def validate_cross_consistency(df_stock: pd.DataFrame, df_sales: pd.DataFrame) -> list[ValidationIssue]:
    """Compara 'Unidades Vendidas' do stock com a soma de 'Quantidade' nas vendas diárias, por produto."""
    issues = []

    vendas_por_produto = df_sales.groupby("Código Produto")["Quantidade"].sum()

    for _, row in df_stock.iterrows():
        codigo = row["Código Produto"]
        vendido_stock = row["Unidades Vendidas"]
        vendido_diario = vendas_por_produto.get(codigo, 0)

        if vendido_stock == 0:
            continue

        diff_pct = abs(vendido_stock - vendido_diario) / vendido_stock
        if diff_pct > config.DATA_QUALITY_TOLERANCE_PCT:
            issues.append(ValidationIssue(
                "AVISO",
                f"Produto {codigo}: 'Unidades Vendidas' no stock ({vendido_stock}) não bate certo "
                f"com a soma das vendas diárias ({vendido_diario})"
            ))

    produtos_stock = set(df_stock["Código Produto"])
    produtos_vendas = set(df_sales["Código Produto"].unique())
    so_em_vendas = produtos_vendas - produtos_stock
    if so_em_vendas:
        issues.append(ValidationIssue(
            "AVISO", f"Produtos aparecem nas vendas mas não na gestão de stock: {sorted(so_em_vendas)}"
        ))

    return issues


def run_all_validations(df_stock: pd.DataFrame, df_sales: pd.DataFrame) -> list[ValidationIssue]:
    issues = []
    issues += validate_stock(df_stock)
    issues += validate_sales(df_sales)
    # só faz sentido cruzar dados se as validações base passaram
    if not any(i.level == "ERRO" for i in issues):
        issues += validate_cross_consistency(df_stock, df_sales)
    return issues


def has_blocking_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.level == "ERRO" for i in issues)
