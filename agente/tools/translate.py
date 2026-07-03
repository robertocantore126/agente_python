"""Funzione 2: traduzione di file."""

from pathlib import Path

import llm_client
import memory
from tools.summarize import extract_text


SYSTEM_PROMPT = "Sei un assistente che traduce testi in modo fedele e naturale."


# Traduce un file di testo nella lingua target e salva il risultato accanto all'originale
# (es. "documento.txt" -> "documento.en.txt").
def translate_file(path: str, target_lang: str, user_id: int) -> tuple[str, Path]:
    text = extract_text(path)
    context = memory.build_context_messages(user_id, SYSTEM_PROMPT)

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
