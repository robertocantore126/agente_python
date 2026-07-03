"""CRUD della memoria conversazionale per utente + connessione DB condivisa."""

import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent / "db"
DB_PATH = DB_DIR / "database.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


# Apre una connessione al DB applicando lo schema ad ogni chiamata (CREATE TABLE IF NOT EXISTS
# e' idempotente), cosi' il DB si auto-inizializza al primo utilizzo senza uno script separato.
def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


# Salva un singolo messaggio (utente o assistente) nella cronologia di un utente.
def add_message(user_id: int, role: str, content: str, tool_used: str | None = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO memory (user_id, role, content, tool_used) VALUES (?, ?, ?, ?)",
            (user_id, role, content, tool_used),
        )
        conn.commit()
    finally:
        conn.close()


# Recupera gli ultimi N messaggi in ordine cronologico (ORDER BY id DESC + reversed
# per prendere i piu' recenti restando comunque in ordine di lettura naturale).
def get_recent(user_id: int, n: int = 10) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT role, content, tool_used, timestamp
            FROM memory
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, n),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in reversed(rows)]


# Costruisce la lista di messaggi da passare all'LLM: system prompt + storico recente
# dell'utente, cosi' ogni comando "ricorda" le interazioni precedenti di quella persona.
def build_context_messages(user_id: int, system_prompt: str, n: int = 10) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    for entry in get_recent(user_id, n):
        messages.append({"role": entry["role"], "content": entry["content"]})
    return messages
