"""Login utente con password e gestione della sessione locale."""

import json
from pathlib import Path

from memory import get_connection, DB_DIR

SESSION_PATH = DB_DIR / ".session.json"


def login(username: str, password: str) -> int:
    """Effettua il login di un utente, registrandolo al primo accesso.

    Se lo username non esiste, l'utente viene creato con la password fornita;
    altrimenti la password deve coincidere con quella salvata. In caso di
    successo, l'utente attivo viene memorizzato nel file di sessione locale.

    Nota: la password e' salvata in chiaro (scelta didattica); in produzione si
    userebbe un hash con salt (es. hashlib.pbkdf2_hmac).

    Args:
        username: Nome utente con cui accedere o registrarsi.
        password: Password scelta (primo accesso) o da verificare.

    Returns:
        L'identificativo numerico dell'utente autenticato.

    Raises:
        ValueError: Se l'utente esiste ma la password non corrisponde.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, password FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None:
            cursor = conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)", (username, password)
            )
            conn.commit()
            user_id = cursor.lastrowid
        elif password == row["password"]:
            user_id = row["id"]
        else:
            raise ValueError("Password errata.")
    finally:
        conn.close()

    DB_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(
        json.dumps({"user_id": user_id, "username": username}), encoding="utf-8"
    )
    return user_id


def logout() -> None:
    """Termina la sessione attiva eliminando il file di sessione.

    Returns:
        None. Se non c'e' alcuna sessione attiva, non fa nulla.
    """
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()


def current_user() -> dict | None:
    """Restituisce l'utente attualmente loggato leggendo il file di sessione.

    Returns:
        Un dizionario con le chiavi 'user_id' e 'username' se una sessione e'
        attiva; None se non c'e' alcuna sessione o il file e' illeggibile.
    """
    if not SESSION_PATH.exists():
        return None
    try:
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
