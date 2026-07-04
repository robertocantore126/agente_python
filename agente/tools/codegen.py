"""Funzione 4: generazione di codice (con Chain-of-Thought opzionale)."""

import re
from datetime import datetime
from pathlib import Path

import llm_client
import memory

LANG_EXTENSIONS = {"python": "py", "javascript": "js", "bash": "sh", "java": "java", "c": "c"}


def _extract_code_block(text: str, lang: str) -> str:
    """Estrae il codice da un blocco ```lang ... ``` nella risposta del modello.

    Args:
        text: Testo completo restituito dal modello.
        lang: Linguaggio atteso, usato per riconoscere il blocco.

    Returns:
        Il codice contenuto nel blocco; se il modello non usa un blocco,
        viene restituito l'intero testo come fallback.
    """
    match = re.search(rf"```(?:{lang})?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


SYSTEM_PROMPT = (
    "Sei un assistente esperto di programmazione. Restituisci solo codice valido "
    "in un blocco ```lang ... ```, senza spiegazioni fuori dal blocco."
)


def generate(prompt: str, user_id: int, lang: str = "python", cot: bool = False) -> str:
    """Genera codice a partire da una descrizione in linguaggio naturale.

    Args:
        prompt: Descrizione testuale del codice da generare.
        user_id: Identificativo dell'utente attivo, per la cronologia.
        lang: Linguaggio di programmazione desiderato (default "python").
        cot: Se True, chiede al modello di ragionare passo passo
            (Chain-of-Thought) prima di produrre il codice.

    Returns:
        Il codice generato, gia' estratto dal blocco della risposta.

    Raises:
        llm_client.LLMError: Se la chiamata al modello fallisce.
    """
    context = [{"role": "system", "content": SYSTEM_PROMPT}]

    if cot:
        user_prompt = (
            f"Ragiona passo per passo su come implementare questo task in {lang}, "
            f"poi scrivi il codice finale in un blocco ```{lang} ... ```.\n\nTask: {prompt}"
        )
    else:
        user_prompt = f"Scrivi codice {lang} per questo task, in un blocco ```{lang} ... ```.\n\nTask: {prompt}"
    response = llm_client.chat(context + [{"role": "user", "content": user_prompt}])

    code = _extract_code_block(response, lang)

    memory.add_message(user_id, "user", f"[codegen] {prompt}", tool_used="codegen")
    memory.add_message(user_id, "assistant", response, tool_used="codegen")
    return code


def save_to_file(code: str, output: str | None, lang: str = "python") -> Path:
    """Salva il codice generato su file.

    Args:
        code: Il codice da scrivere su disco.
        output: Percorso del file di destinazione; se None, viene generato un
            nome con timestamp (es. "generated_20260704_120000.py").
        lang: Linguaggio, usato per scegliere l'estensione quando output e' None.

    Returns:
        Il percorso del file effettivamente scritto.
    """
    if output:
        output_path = Path(output)
    else:
        ext = LANG_EXTENSIONS.get(lang, "txt")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"generated_{timestamp}.{ext}")
    output_path.write_text(code, encoding="utf-8")
    return output_path
