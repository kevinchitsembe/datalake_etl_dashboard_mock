"""Configuração central do ETL: caminhos, colunas esperadas e thresholds de negócio."""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_LAKE_DIR = BASE_DIR / "data"
ANALYTICS_DB_PATH = BASE_DIR / "db" / "analytics.db"

# Backend da Base de Dados Cloud: "sqlite" (default, para testes rápidos) ou "oracle".
# Podes definir isto no ambiente: set DB_BACKEND=oracle  (Windows)  /  export DB_BACKEND=oracle (Linux/Mac)
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite").lower()

ORACLE_CONFIG_PATH = BASE_DIR / "oracle_config.json"


def get_oracle_config() -> dict:
    """
    Vai buscar as credenciais Oracle, primeiro a variáveis de ambiente,
    depois a um ficheiro local oracle_config.json (não deve ir para o git).

    Suporta dois formatos:
      1) {"user", "password", "host", "port", "service_name"} -> monta o dsn com oracledb.makedsn
      2) {"user", "password", "dsn"} -> usa o dsn diretamente (ex: "host:1521/SERVICE")
    """
    user = os.environ.get("ORACLE_USER")
    password = os.environ.get("ORACLE_PASSWORD")
    host = os.environ.get("ORACLE_HOST")
    port = os.environ.get("ORACLE_PORT")
    service_name = os.environ.get("ORACLE_SERVICE_NAME")
    dsn = os.environ.get("ORACLE_DSN")

    if user and password and (dsn or (host and service_name)):
        return {
            "user": user, "password": password,
            "dsn": dsn, "host": host,
            "port": int(port) if port else None,
            "service_name": service_name,
        }

    if ORACLE_CONFIG_PATH.exists():
        with open(ORACLE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    raise RuntimeError(
        "Configuração Oracle não encontrada. Cria 'oracle_config.json' na raiz do "
        "projeto (a partir de oracle_config.example.json) ou define as variáveis de "
        "ambiente ORACLE_USER, ORACLE_PASSWORD e (ORACLE_DSN ou ORACLE_HOST/ORACLE_PORT/ORACLE_SERVICE_NAME)."
    )

# Colunas obrigatórias por tipo de ficheiro (nomes exatamente como vêm do Excel)
STOCK_REQUIRED_COLUMNS = [
    "Código Produto", "Produto", "Categoria", "Stock Inicial",
    "Entradas na Semana", "Unidades Vendidas", "Stock Final",
    "Stock Mínimo", "Preço Venda (MT)", "Custo Unitário (MT)",
]

SALES_REQUIRED_COLUMNS = [
    "Data", "Código Produto", "Produto", "Categoria", "Quantidade",
    "Preço Unitário (MT)", "Vendas Líquidas (MT)", "Custo (MT)",
    "Margem Bruta (MT)", "Desconto",
]

# Thresholds de negócio para classificar o estado do stock
RUPTURA_MULTIPLICADOR = 1.0    # stock_final <= stock_minimo * este valor -> Ruptura
ALERTA_MULTIPLICADOR = 1.2     # stock_final <= stock_minimo * este valor -> Alerta

# Tolerância percentual para o cruzamento "Unidades Vendidas" (stock) vs soma (vendas diárias)
DATA_QUALITY_TOLERANCE_PCT = 0.02  # 2%
