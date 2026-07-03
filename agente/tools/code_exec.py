"""Funzione 4.1: esecuzione sandboxata del codice generato.

Isolamento a livello di processo/timeout (subprocess con `-I` e ambiente ridotto),
non un sandbox filesystem/rete completo: su Windows senza container Docker questo
e' il livello di restrizione praticabile per uno scopo didattico.
"""

import os
import subprocess
import sys
from pathlib import Path

import memory

DEFAULT_TIMEOUT = 8

_SAFE_ENV_KEYS = ("SystemRoot", "PATH", "TEMP", "TMP", "windir")


# Ambiente minimo passato al sottoprocesso: solo le variabili indispensabili
# per eseguire Python su Windows, per non esporre il resto dell'ambiente dell'utente.
def _restricted_env() -> dict:
    return {key: os.environ[key] for key in _SAFE_ENV_KEYS if key in os.environ}


# Esegue un file .py in un sottoprocesso isolato (`-I` disabilita site-packages utente
# e variabili PYTHON*) con timeout ed environment ristretto.
def run_file(path: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str, int]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    if file_path.suffix.lower() != ".py":
        raise ValueError(f"Posso eseguire solo file .py, ricevuto: '{file_path.suffix}'")

    try:
        result = subprocess.run(
            [sys.executable, "-I", str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(file_path.parent),
            env=_restricted_env(),
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Esecuzione interrotta per timeout ({timeout}s).", -1


# Esegue il file e registra l'esito (stdout/stderr/returncode) nella memoria dell'utente.
def run_and_record(path: str, user_id: int, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str, int]:
    stdout, stderr, returncode = run_file(path, timeout=timeout)

    memory.add_message(user_id, "user", f"[run] {path}", tool_used="code_exec")
    memory.add_message(
        user_id,
        "assistant",
        f"stdout:\n{stdout}\nstderr:\n{stderr}\nreturncode: {returncode}",
        tool_used="code_exec",
    )
    return stdout, stderr, returncode
