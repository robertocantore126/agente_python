"""CRUD della memoria conversazionale per utente + connessione DB condivisa."""

import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent / "db"
DB_PATH = DB_DIR / "database.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Apre una connessione al database SQLite, inizializzandolo se necessario.

    Lo schema viene applicato ad ogni chiamata: grazie a CREATE TABLE IF NOT
    EXISTS l'operazione e' idempotente e il database si crea da solo al primo
    utilizzo. Include inoltre una migrazione leggera che, sui database creati
    prima dell'introduzione delle password, aggiunge la colonna `password` e
    assegna agli utenti esistenti una password iniziale pari allo username.

    Returns:
        Una connessione sqlite3 con row_factory impostata su sqlite3.Row
        (accesso alle colonne per nome) e foreign key abilitate.
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    if "password" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password TEXT NOT NULL DEFAULT ''")
        conn.execute("UPDATE users SET password = username")
        conn.commit()
    return conn


def add_message(user_id: int, role: str, content: str, tool_used: str | None = None) -> None:
    """Salva un singolo messaggio nella cronologia di un utente.

    Args:
        user_id: Identificativo dell'utente proprietario del messaggio.
        role: Ruolo del messaggio, tipicamente "user" o "assistant".
        content: Testo del messaggio da memorizzare.
        tool_used: Nome del comando che ha generato il messaggio (es.
            "summarize"), oppure None se non applicabile.

    Returns:
        None.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO memory (user_id, role, content, tool_used) VALUES (?, ?, ?, ?)",
            (user_id, role, content, tool_used),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(user_id: int, n: int = 10) -> list[dict]:
    """Recupera gli ultimi N messaggi di un utente in ordine cronologico.

    Internamente ordina per id decrescente (per prendere i piu' recenti) e poi
    inverte il risultato, cosi' da restituirli dal piu' vecchio al piu' nuovo.

    Args:
        user_id: Identificativo dell'utente di cui leggere la cronologia.
        n: Numero massimo di messaggi da restituire.

    Returns:
        Una lista di dizionari con le chiavi 'role', 'content', 'tool_used' e
        'timestamp', in ordine di lettura naturale (dal piu' vecchio al piu' recente).
    """
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
