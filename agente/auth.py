"""Selezione utente e sessione locale (nessuna password: multi-utente semplificato)."""

import json
from pathlib import Path

from memory import get_connection, DB_DIR

SESSION_PATH = DB_DIR / ".session.json"


# Recupera l'id utente esistente o ne crea uno nuovo se lo username non e' mai stato visto.
def get_or_create_user(username: str) -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is not None:
            return row["id"]
        cursor = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# La "sessione" e' solo un file JSON locale: nessuna password, basta indicare
# quale utente e' attivo per associare correttamente cronologia e memoria.
def login(username: str) -> int:
    user_id = get_or_create_user(username)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(
        json.dumps({"user_id": user_id, "username": username}), encoding="utf-8"
    )
    return user_id


def logout() -> None:
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()


def current_user() -> dict | None:
    if not SESSION_PATH.exists():
        return None
    try:
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
