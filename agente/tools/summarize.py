"""Funzione 1: riassunto di file PDF/TXT."""

from pathlib import Path

import llm_client
import memory

CHUNK_CHAR_LIMIT = 6000


# Estrae il testo grezzo da un file .txt o .pdf; altri formati non sono supportati.
def extract_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")

    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError(f"Formato non supportato: '{suffix}'. Usa .txt o .pdf")


# Divide un testo lungo in blocchi di al piu' `limit` caratteri, cosi' ogni chunk
# rientra nella finestra di contesto del modello quando il documento e' troppo grande.
def _chunk_text(text: str, limit: int = CHUNK_CHAR_LIMIT) -> list[str]:
    return [text[i : i + limit] for i in range(0, len(text), limit)] or [""]


SYSTEM_PROMPT = "Sei un assistente che riassume documenti in modo chiaro e conciso."


def summarize_file(path: str, user_id: int, max_length: int | None = None) -> str:
    text = extract_text(path)
    context = memory.build_context_messages(user_id, SYSTEM_PROMPT)

    if len(text) <= CHUNK_CHAR_LIMIT:
        prompt = f"Riassumi il seguente testo in modo chiaro e conciso:\n\n{text}"
        summary = llm_client.chat(context + [{"role": "user", "content": prompt}])
    else:
        # Documento troppo lungo per un'unica chiamata: riassume ogni chunk
        # separatamente (senza contesto storico, per non sforare la finestra)
        # e poi fonde i riassunti parziali in uno unico coerente.
        chunks = _chunk_text(text)
        partial_summaries = []
        for chunk in chunks:
            prompt = f"Riassumi il seguente estratto di testo:\n\n{chunk}"
            partial_summaries.append(llm_client.chat([{"role": "user", "content": prompt}]))
        combined = "\n\n".join(partial_summaries)
        final_prompt = f"Riassumi in un unico testo coerente questi riassunti parziali:\n\n{combined}"
        summary = llm_client.chat(context + [{"role": "user", "content": final_prompt}])

    if max_length and len(summary) > max_length:
        summary = summary[:max_length].rstrip() + "…"

    # Registra sia la richiesta che la risposta, cosi' i comandi successivi
    # dello stesso utente potranno vederle come contesto.
    memory.add_message(user_id, "user", f"[summarize] {path}", tool_used="summarize")
    memory.add_message(user_id, "assistant", summary, tool_used="summarize")
    return summary
