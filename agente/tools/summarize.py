"""Funzione 1: riassunto di file PDF/TXT."""

from pathlib import Path

import llm_client
import memory


def extract_text(path: str) -> str:
    """Estrae il testo grezzo da un file di testo o PDF.

    Args:
        path: Percorso del file da leggere. Sono supportati i formati .txt e .pdf.

    Returns:
        Il testo contenuto nel file come singola stringa.

    Raises:
        FileNotFoundError: Se il file indicato non esiste.
        ValueError: Se l'estensione del file non e' .txt ne' .pdf.
    """
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


SYSTEM_PROMPT = "Sei un assistente che riassume documenti in modo chiaro e conciso."


def summarize_file(path: str, user_id: int, max_length: int | None = None) -> str:
    """Riassume il contenuto di un file e registra l'operazione nella cronologia.

    Args:
        path: Percorso del file (.txt o .pdf) da riassumere.
        user_id: Identificativo dell'utente attivo, usato per salvare la cronologia.
        max_length: Lunghezza massima (in caratteri) del riassunto; se superata,
            il testo viene troncato. Se None, nessun limite.

    Returns:
        Il riassunto prodotto dal modello.

    Raises:
        FileNotFoundError: Se il file non esiste.
        ValueError: Se il formato del file non e' supportato.
        llm_client.LLMError: Se la chiamata al modello fallisce.
    """
    text = extract_text(path)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Riassumi il seguente testo:\n\n{text}"},
    ]
    summary = llm_client.chat(messages).strip()

    if max_length and len(summary) > max_length:
        summary = summary[:max_length].rstrip() + "…"

    memory.add_message(user_id, "user", f"[summarize] {path}", tool_used="summarize")
    memory.add_message(user_id, "assistant", summary, tool_used="summarize")
    return summary
