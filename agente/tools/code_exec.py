"""Funzione 4.1: esecuzione del codice generato in un sottoprocesso isolato.

Isolamento a livello di processo (subprocess con `-I`, timeout, ambiente ridotto),
non un sandbox filesystem/rete completo: sufficiente per uno scopo didattico.
"""

import os
import subprocess
import sys
from pathlib import Path

import memory

DEFAULT_TIMEOUT = 8

# Variabili minime da passare al sottoprocesso, diverse per sistema operativo:
# su Windows servono SystemRoot/TEMP/ecc., su Linux/macOS HOME/TMPDIR/LANG.
if os.name == "nt":
    _SAFE_ENV_KEYS = ("SystemRoot", "PATH", "TEMP", "TMP", "windir", "PATHEXT")
else:
    _SAFE_ENV_KEYS = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")


def _restricted_env() -> dict:
    """Costruisce l'ambiente minimo da passare al sottoprocesso.

    Include solo le variabili indispensabili a eseguire Python sul sistema
    operativo corrente, per non esporre il resto dell'ambiente dell'utente.

    Returns:
        Un dizionario {nome_variabile: valore} con le sole chiavi consentite
        effettivamente presenti nell'ambiente.
    """
    return {key: os.environ[key] for key in _SAFE_ENV_KEYS if key in os.environ}


def run_file(path: str, timeout: int = DEFAULT_TIMEOUT, input_text: str | None = None) -> tuple[str, str, int]:
    """Esegue un file Python in un sottoprocesso isolato.

    Il processo viene avviato con il flag `-I` (isolated mode), un timeout e un
    ambiente ridotto, per contenere gli effetti di codice non fidato.

    Args:
        path: Percorso del file .py da eseguire.
        timeout: Secondi massimi di esecuzione prima dell'interruzione.
        input_text: Se fornito, viene inviato sullo stdin del processo
            (utile per testare codice che usa input()).

    Returns:
        Una tupla (stdout, stderr, returncode). In caso di timeout, returncode
        vale -1 e stderr contiene il messaggio di interruzione.

    Raises:
        FileNotFoundError: Se il file non esiste.
        ValueError: Se il file non ha estensione .py.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    if file_path.suffix.lower() != ".py":
        raise ValueError(f"Posso eseguire solo file .py, ricevuto: '{file_path.suffix}'")

    try:
        result = subprocess.run(
            [sys.executable, "-I", str(file_path)],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(file_path.parent),
            env=_restricted_env(),
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Esecuzione interrotta per timeout ({timeout}s).", -1


def run_and_record(path: str, user_id: int, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str, int]:
    """Esegue un file Python e registra l'esito nella cronologia dell'utente.

    Args:
        path: Percorso del file .py da eseguire.
        user_id: Identificativo dell'utente attivo, per la cronologia.
        timeout: Secondi massimi di esecuzione.

    Returns:
        Una tupla (stdout, stderr, returncode) come restituita da run_file.

    Raises:
        FileNotFoundError: Se il file non esiste.
        ValueError: Se il file non ha estensione .py.
    """
    stdout, stderr, returncode = run_file(path, timeout=timeout)

    memory.add_message(user_id, "user", f"[run] {path}", tool_used="code_exec")
    memory.add_message(
        user_id,
        "assistant",
        f"stdout:\n{stdout}\nstderr:\n{stderr}\nreturncode: {returncode}",
        tool_used="code_exec",
    )
    return stdout, stderr, returncode
