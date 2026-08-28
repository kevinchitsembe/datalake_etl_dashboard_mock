"""
Script de linha de comandos para adicionar um novo cliente (ex: um novo supermercado)
ao portal, sem teres de editar clients.json à mão.

Uso:
    python add_client.py
"""

import getpass
import auth

if __name__ == "__main__":
    print("== Adicionar novo cliente ao portal ==")
    client_id = input("client_id (ex: supermercado_c): ").strip()
    name = input("Nome do cliente (ex: Supermercado C): ").strip()
    username = input("Username de login: ").strip()
    password = getpass.getpass("Password: ").strip()

    try:
        auth.add_client(client_id, username, password, name)
        print(f"Cliente '{name}' adicionado com sucesso.")
    except ValueError as e:
        print(f"Erro: {e}")
