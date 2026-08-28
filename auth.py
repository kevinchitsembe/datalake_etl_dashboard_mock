"""
Autenticação simples para o portal (simula multi-tenant).
Cada cliente (ex: um supermercado) tem um client_id, username e password_hash
guardados em clients.json. Isto é suficiente para o teste local; num sistema
real isto passaria para uma tabela na base de dados, com passwords com salt.
"""

import json
import hashlib
from pathlib import Path

CLIENTS_FILE = Path(__file__).parent / "clients.json"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_clients() -> list[dict]:
    if not CLIENTS_FILE.exists():
        return []
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clients(clients: list[dict]) -> None:
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)


def authenticate(username: str, password: str) -> dict | None:
    """Retorna o dicionário do cliente se as credenciais forem válidas, senão None."""
    clients = load_clients()
    hashed = _hash_password(password)
    for client in clients:
        if client["username"] == username and client["password_hash"] == hashed:
            return client
    return None


def add_client(client_id: str, username: str, password: str, name: str) -> None:
    clients = load_clients()
    if any(c["client_id"] == client_id for c in clients):
        raise ValueError(f"client_id '{client_id}' já existe.")
    if any(c["username"] == username for c in clients):
        raise ValueError(f"username '{username}' já existe.")
    clients.append({
        "client_id": client_id,
        "username": username,
        "password_hash": _hash_password(password),
        "name": name,
    })
    save_clients(clients)
