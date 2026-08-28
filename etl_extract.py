"""
Extração (E do ETL): localiza os ficheiros mais recentes de um cliente no
Data Lake (pasta data/<client_id>/) e lê as folhas relevantes do Excel.
"""

from pathlib import Path
import pandas as pd

from . import config


def _latest_file(client_dir: Path, keyword: str) -> Path | None:
    """Devolve o ficheiro mais recente cujo nome contém 'keyword' (case-insensitive)."""
    candidates = [
        f for f in client_dir.glob("*.xlsx")
        if keyword.lower() in f.name.lower()
    ]
    if not candidates:
        return None
    # o timestamp está no prefixo do nome (YYYYMMDD_HHMMSS_...), ordenar por nome funciona
    return sorted(candidates)[-1]


def find_latest_files(client_id: str) -> dict:
    """
    Localiza o ficheiro de stock mais recente e o de vendas mais recente
    para um cliente. Devolve {'stock': Path|None, 'vendas': Path|None}.
    """
    client_dir = config.DATA_LAKE_DIR / client_id
    if not client_dir.exists():
        raise FileNotFoundError(f"Não existe pasta de dados para o cliente '{client_id}': {client_dir}")

    return {
        "stock": _latest_file(client_dir, "gestao"),
        "vendas": _latest_file(client_dir, "vendas"),
    }


def read_stock_file(path: Path) -> dict:
    """Lê o ficheiro de gestão de produtos/stock. Devolve as folhas como DataFrames."""
    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        sheets[name] = xl.parse(name)
    return sheets


def read_sales_file(path: Path) -> dict:
    """Lê o ficheiro de vendas. Devolve as folhas como DataFrames."""
    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        sheets[name] = xl.parse(name)
    return sheets


def extract(client_id: str, stock_path: Path | None = None, sales_path: Path | None = None) -> dict:
    """
    Ponto de entrada da extração. Se os caminhos não forem indicados,
    procura os ficheiros mais recentes desse cliente no Data Lake.
    """
    if stock_path is None or sales_path is None:
        latest = find_latest_files(client_id)
        stock_path = stock_path or latest["stock"]
        sales_path = sales_path or latest["vendas"]

    if stock_path is None:
        raise FileNotFoundError(f"Nenhum ficheiro de stock/gestão encontrado para '{client_id}'.")
    if sales_path is None:
        raise FileNotFoundError(f"Nenhum ficheiro de vendas encontrado para '{client_id}'.")

    stock_sheets = read_stock_file(stock_path)
    sales_sheets = read_sales_file(sales_path)

    return {
        "stock_path": stock_path,
        "sales_path": sales_path,
        "stock_sheets": stock_sheets,
        "sales_sheets": sales_sheets,
    }
