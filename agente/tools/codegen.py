"""Funzione 4: generazione di codice (con Chain-of-Thought opzionale)."""

import re
from datetime import datetime
from pathlib import Path

import llm_client
import memory

LANG_EXTENSIONS = {"python": "py", "javascript": "js", "bash": "sh", "java": "java", "c": "c"}


# Estrae il codice da un blocco ```lang ... ``` nella risposta del modello;
# se il modello non lo racchiude in un blocco, usa l'intera risposta come fallback.
def _extract_code_block(text: str, lang: str) -> str:
    match = re.search(rf"```(?:{lang})?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


SYSTEM_PROMPT = "Sei un assistente esperto di programmazione."


# Genera codice da una descrizione in linguaggio naturale.
# Con cot=True chiede al modello di ragionare passo passo prima di scrivere il codice
# (Chain-of-Thought), utile per task piu' complessi a scapito di una risposta piu' lunga.
def generate(prompt: str, user_id: int, lang: str = "python", cot: bool = False) -> str:
    context = memory.build_context_messages(user_id, SYSTEM_PROMPT)

    if cot:
        thought_prompt = (
            f"Ragiona passo per passo (Thought) su come implementare questo task in {lang}, "
            f"poi scrivi il codice finale in un blocco ```{lang} ... ```.\n\nTask: {prompt}"
        )
        response = llm_client.chat(context + [{"role": "user", "content": thought_prompt}])
    else:
        code_prompt = (
            f"Scrivi codice {lang} per il seguente task. "
            f"Restituisci solo il codice in un blocco ```{lang} ... ```, senza spiegazioni.\n\n"
            f"Task: {prompt}"
        )
        response = llm_client.chat(context + [{"role": "user", "content": code_prompt}])

    code = _extract_code_block(response, lang)

    memory.add_message(user_id, "user", f"[codegen] {prompt}", tool_used="codegen")
    memory.add_message(user_id, "assistant", response, tool_used="codegen")
    return code


# Salva il codice generato su file, usando un nome con timestamp se l'utente
# non ne specifica uno esplicito con --output.
def save_to_file(code: str, output: str | None, lang: str = "python") -> Path:
    if output:
        output_path = Path(output)
    else:
        ext = LANG_EXTENSIONS.get(lang, "txt")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"generated_{timestamp}.{ext}")
    output_path.write_text(code, encoding="utf-8")
    return output_path
