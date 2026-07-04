"""Funzione 2: traduzione di file."""

from pathlib import Path

import llm_client
import memory
from tools.summarize import extract_text


SYSTEM_PROMPT = "Sei un assistente che traduce testi in modo fedele e naturale."


def translate_file(path: str, target_lang: str, user_id: int) -> tuple[str, Path]:
    """Traduce un file nella lingua richiesta e salva il risultato su disco.

    Il file tradotto viene creato accanto all'originale, con la lingua nel nome
    (es. "documento.txt" -> "documento.english.txt"). La cronologia non viene
    inserita nel contesto: e' un'operazione stateless, lo storico rischierebbe
    solo di sviare il modello.

    Args:
        path: Percorso del file di origine (.txt o .pdf).
        target_lang: Lingua di destinazione (es. "english", "spagnolo").
        user_id: Identificativo dell'utente attivo, per la cronologia.

    Returns:
        Una tupla (testo_tradotto, percorso_file_salvato).

    Raises:
        FileNotFoundError: Se il file di origine non esiste.
        ValueError: Se il formato del file non e' supportato.
        llm_client.LLMError: Se la chiamata al modello fallisce.
    """
    text = extract_text(path)
    context = [{"role": "system", "content": SYSTEM_PROMPT}]

    prompt = (
        f"Traduci il seguente testo in {target_lang}. "
        "Restituisci solo il testo tradotto, senza commenti aggiuntivi:\n\n" + text
    )
    translated = llm_client.chat(context + [{"role": "user", "content": prompt}])

    source_path = Path(path)
    output_path = source_path.with_name(f"{source_path.stem}.{target_lang}.txt")
    output_path.write_text(translated, encoding="utf-8")

    memory.add_message(
        user_id, "user", f"[translate] {path} -> {target_lang}", tool_used="translate"
    )
    memory.add_message(user_id, "assistant", translated, tool_used="translate")
    return translated, output_path
