"""Entry point: parsing comandi CLI dell'assistente AI locale."""

import argparse
import sys

# Forza UTF-8 su stdout/stderr: sul terminale Windows di default e' spesso cp1252/cp850
# e romperebbe la stampa di accenti e caratteri non ASCII.
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import auth
import llm_client
import memory
from tools import code_exec, codegen, describe_image, summarize, translate


# Tutti i comandi tranne login/logout/whoami richiedono un utente loggato,
# perche' devono sapere a chi associare cronologia e nuova memoria nel DB.
def require_session() -> dict:
    user = auth.current_user()
    if user is None:
        print("Nessuna sessione attiva. Esegui prima 'login <username>'.")
        sys.exit(1)
    return user


def cmd_login(args: argparse.Namespace) -> None:
    auth.login(args.username)
    print(f"Login effettuato come '{args.username}'.")


def cmd_logout(_: argparse.Namespace) -> None:
    auth.logout()
    print("Logout effettuato.")


def cmd_whoami(_: argparse.Namespace) -> None:
    user = auth.current_user()
    if user is None:
        print("Nessun utente loggato.")
    else:
        print(f"Utente attivo: {user['username']}")


# Riassume un file PDF/TXT passandolo all'LLM insieme allo storico dell'utente.
def cmd_summarize(args: argparse.Namespace) -> None:
    user = require_session()
    summary = summarize.summarize_file(args.file, user["user_id"], max_length=args.max_length)
    print("--- Riassunto ---")
    print(summary)


# Traduce un file di testo nella lingua richiesta e salva il risultato su disco.
def cmd_translate(args: argparse.Namespace) -> None:
    user = require_session()
    translated, output_path = translate.translate_file(args.file, args.to, user["user_id"])
    print(f"--- Traduzione ({args.to}) ---")
    print(translated)
    print(f"Salvato in: {output_path}")


# Descrive un'immagine usando il modello vision configurato in llm_client.
def cmd_describe(args: argparse.Namespace) -> None:
    user = require_session()
    description = describe_image.describe(args.image, user["user_id"])
    print("--- Descrizione immagine ---")
    print(description)


# Genera codice a partire da una descrizione testuale e lo salva su file.
def cmd_codegen(args: argparse.Namespace) -> None:
    user = require_session()
    code = codegen.generate(args.description, user["user_id"], lang=args.lang, cot=args.cot)
    output_path = codegen.save_to_file(code, args.output, lang=args.lang)
    print(f"--- Codice generato ({args.lang}) ---")
    print(code)
    print(f"Salvato in: {output_path}")


# Mostra le ultime N interazioni salvate nel DB per l'utente attivo.
def cmd_history(args: argparse.Namespace) -> None:
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


# Esegue un file .py in un sottoprocesso isolato (vedi tools/code_exec.py) e ne registra l'esito.
def cmd_run(args: argparse.Namespace) -> None:
    user = require_session()
    stdout, stderr, returncode = code_exec.run_and_record(args.file, user["user_id"])
    if stdout:
        print("--- stdout ---")
        print(stdout)
    if stderr:
        print("--- stderr ---")
        print(stderr)
    print(f"Codice di uscita: {returncode}")


# Costruisce il parser argparse con un subcommand per ogni funzionalita' dell'agente.
# Ogni subparser lega gli argomenti CLI alla relativa funzione cmd_* via set_defaults(func=...).
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agente", description="Assistente AI locale multi-utente")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_login = subparsers.add_parser("login", help="Seleziona o crea un utente")
    p_login.add_argument("username")
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
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except llm_client.LLMError as exc:
        # Ollama non raggiungibile o errore del modello: messaggio pulito invece di traceback.
        print(exc)
        sys.exit(1)
    except (FileNotFoundError, ValueError) as exc:
        # Input utente non valido (file mancante, formato non supportato, ecc.).
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
