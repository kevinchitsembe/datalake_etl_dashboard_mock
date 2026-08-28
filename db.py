"""
Registo (SQLite) de metadados de cada ficheiro carregado no portal.
Isto NÃO é a "Base de Dados Cloud" final do fluxo (essa vem depois do ETL);
é apenas o registo de auditoria do próprio Data Lake: quem carregou o quê e quando.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).parent / "db"
DB_PATH = DB_DIR / "registry.db"


def init_db() -> None:
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            status TEXT NOT NULL,
            rows_detected INTEGER,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_upload(client_id: str, filename: str, filepath: str, status: str,
               rows_detected: int | None = None, message: str = "") -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO uploads (client_id, filename, filepath, upload_time, status, rows_detected, message)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (client_id, filename, filepath, datetime.now().isoformat(timespec="seconds"),
         status, rows_detected, message),
    )
    conn.commit()
    conn.close()


def get_uploads(client_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM uploads WHERE client_id = ? ORDER BY upload_time DESC",
        (client_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
