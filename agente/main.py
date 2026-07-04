"""Entry point: parsing comandi CLI dell'assistente AI locale."""

import argparse
import sys

# Forza UTF-8 su stdout/stderr: il terminale Windows usa spesso cp1252/cp850 e
# romperebbe la stampa di accenti e caratteri non ASCII.
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import auth
import llm_client
import memory
from tools import code_exec, codegen, describe_image, summarize, translate


def require_session() -> dict:
    """Restituisce l'utente loggato o termina il programma se non c'e'.

    Tutti i comandi tranne login/logout/whoami richiedono un utente attivo, per
    sapere a chi associare cronologia e memoria nel database.

    Returns:
        Il dizionario dell'utente attivo (con 'user_id' e 'username').

    Raises:
        SystemExit: Se non c'e' alcuna sessione attiva (esce con codice 1).
    """
    user = auth.current_user()
    if user is None:
        print("Nessuna sessione attiva. Esegui prima 'login <username>'.")
        sys.exit(1)
    return user


def cmd_login(args: argparse.Namespace) -> None:
    """Gestisce il comando 'login': accede o registra un utente.

    Se la password non e' passata come argomento, viene chiesta a schermo.

    Args:
        args: Argomenti del comando; usa 'username' e 'password'.

    Returns:
        None.
    """
    password = args.password if args.password is not None else input("Password: ")
    auth.login(args.username, password)
    print(f"Login effettuato come '{args.username}'.")


def cmd_logout(_: argparse.Namespace) -> None:
    """Gestisce il comando 'logout': termina la sessione attiva.

    Args:
        _: Argomenti del comando (non usati).

    Returns:
        None.
    """
    auth.logout()
    print("Logout effettuato.")


def cmd_whoami(_: argparse.Namespace) -> None:
    """Gestisce il comando 'whoami': stampa l'utente attualmente loggato.

    Args:
        _: Argomenti del comando (non usati).

    Returns:
        None.
    """
    user = auth.current_user()
    if user is None:
        print("Nessun utente loggato.")
    else:
        print(f"Utente attivo: {user['username']}")


def cmd_summarize(args: argparse.Namespace) -> None:
    """Gestisce il comando 'summarize': riassume un file e stampa il risultato.

    Args:
        args: Argomenti del comando; usa 'file' e 'max_length'.

    Returns:
        None.
    """
    user = require_session()
    summary = summarize.summarize_file(args.file, user["user_id"], max_length=args.max_length)
    print("--- Riassunto ---")
    print(summary)


def cmd_translate(args: argparse.Namespace) -> None:
    """Gestisce il comando 'translate': traduce un file e salva il risultato.

    Args:
        args: Argomenti del comando; usa 'file' e 'to' (lingua di destinazione).

    Returns:
        None.
    """
    user = require_session()
    translated, output_path = translate.translate_file(args.file, args.to, user["user_id"])
    print(f"--- Traduzione ({args.to}) ---")
    print(translated)
    print(f"Salvato in: {output_path}")


def cmd_describe(args: argparse.Namespace) -> None:
    """Gestisce il comando 'describe': descrive un'immagine.

    Args:
        args: Argomenti del comando; usa 'image'.

    Returns:
        None.
    """
    user = require_session()
    description = describe_image.describe(args.image, user["user_id"])
    print("--- Descrizione immagine ---")
    print(description)


def cmd_codegen(args: argparse.Namespace) -> None:
    """Gestisce il comando 'codegen': genera codice e lo salva su file.

    Args:
        args: Argomenti del comando; usa 'description', 'lang', 'output' e 'cot'.

    Returns:
        None.
    """
    user = require_session()
    code = codegen.generate(args.description, user["user_id"], lang=args.lang, cot=args.cot)
    output_path = codegen.save_to_file(code, args.output, lang=args.lang)
    print(f"--- Codice generato ({args.lang}) ---")
    print(code)
    print(f"Salvato in: {output_path}")


def cmd_history(args: argparse.Namespace) -> None:
    """Gestisce il comando 'history': mostra le ultime interazioni dell'utente.

    Args:
        args: Argomenti del comando; usa 'n' (numero di messaggi da mostrare).

    Returns:
        None.
    """
    user = require_session()
    entries = memory.get_recent(user["user_id"], n=args.n)
    if not entries:
        print("Nessuno storico salvato per questo utente.")
        return
    for entry in entries:
        tool = f" [{entry['tool_used']}]" if entry["tool_used"] else ""
        print(f"--- {entry['timestamp']} | {entry['role']}{tool} ---")
        print(entry["content"])
        print()


def cmd_run(args: argparse.Namespace) -> None:
    """Gestisce il comando 'run': esegue un file .py in un sottoprocesso isolato.

    Args:
        args: Argomenti del comando; usa 'file'.

    Returns:
        None.
    """
    user = require_session()
    stdout, stderr, returncode = code_exec.run_and_record(args.file, user["user_id"])
    if stdout:
        print("--- stdout ---")
        print(stdout)
    if stderr:
        print("--- stderr ---")
        print(stderr)
    print(f"Codice di uscita: {returncode}")


def build_parser() -> argparse.ArgumentParser:
    """Costruisce il parser degli argomenti con un sotto-comando per funzionalita'.

    Ogni subparser lega i propri argomenti alla relativa funzione cmd_* tramite
    set_defaults(func=...), cosi' main() puo' invocare direttamente la funzione
    del comando scelto.

    Returns:
        Il parser argparse configurato con tutti i sotto-comandi.
    """
    parser = argparse.ArgumentParser(prog="agente", description="Assistente AI locale multi-utente")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_login = subparsers.add_parser("login", help="Accedi (crea l'utente al primo accesso)")
    p_login.add_argument("username")
    p_login.add_argument("password", nargs="?", default=None, help="Se omessa, viene chiesta a schermo")
    p_login.set_defaults(func=cmd_login)

    p_logout = subparsers.add_parser("logout", help="Termina la sessione attiva")
    p_logout.set_defaults(func=cmd_logout)

    p_whoami = subparsers.add_parser("whoami", help="Mostra l'utente attivo")
    p_whoami.set_defaults(func=cmd_whoami)

    p_summarize = subparsers.add_parser("summarize", help="Riassumi un file PDF/TXT")
    p_summarize.add_argument("file")
    p_summarize.add_argument("--max-length", type=int, default=None)
    p_summarize.set_defaults(func=cmd_summarize)

    p_translate = subparsers.add_parser("translate", help="Traduci un file")
    p_translate.add_argument("file")
    p_translate.add_argument("--to", required=True, help="Lingua di destinazione")
    p_translate.set_defaults(func=cmd_translate)

    p_describe = subparsers.add_parser("describe", help="Descrivi un'immagine")
    p_describe.add_argument("image")
    p_describe.set_defaults(func=cmd_describe)

    p_codegen = subparsers.add_parser("codegen", help="Genera codice da una descrizione")
    p_codegen.add_argument("description")
    p_codegen.add_argument("--lang", default="python")
    p_codegen.add_argument("--output", default=None)
    p_codegen.add_argument("--cot", action="store_true", help="Abilita il ragionamento Chain-of-Thought")
    p_codegen.set_defaults(func=cmd_codegen)

    p_history = subparsers.add_parser("history", help="Mostra lo storico delle interazioni")
    p_history.add_argument("--n", type=int, default=10, help="Numero di messaggi da mostrare")
    p_history.set_defaults(func=cmd_history)

    p_run = subparsers.add_parser("run", help="Esegui un file .py in sandbox")
    p_run.add_argument("file")
    p_run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    """Punto d'ingresso: analizza gli argomenti ed esegue il comando richiesto.

    Gli errori previsti (modello non raggiungibile, input non valido) vengono
    intercettati e stampati come messaggio pulito, uscendo con codice 1 invece
    di mostrare un traceback.

    Returns:
        None.
    """
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except llm_client.LLMError as exc:
        print(exc)
        sys.exit(1)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
