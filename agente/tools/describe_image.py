"""Funzione 3: descrizione di immagini caricate."""

from pathlib import Path

import llm_client
import memory

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def describe(image_path: str, user_id: int) -> str:
    """Descrive un'immagine tramite il modello vision e registra l'operazione.

    A differenza degli altri tool riceve solo prompt + immagine, senza cronologia
    (operazione stateless).

    Args:
        image_path: Percorso dell'immagine (.jpg, .jpeg o .png).
        user_id: Identificativo dell'utente attivo, per la cronologia.

    Returns:
        La descrizione testuale dell'immagine prodotta dal modello.

    Raises:
        FileNotFoundError: Se l'immagine non esiste.
        ValueError: Se il formato dell'immagine non e' supportato.
        llm_client.LLMError: Se la chiamata al modello fallisce.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Immagine non trovata: {image_path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato immagine non supportato: '{path.suffix}'. Usa .jpg, .jpeg o .png"
        )

    description = llm_client.describe_image(str(path))

    memory.add_message(user_id, "user", f"[describe] {image_path}", tool_used="describe_image")
    memory.add_message(user_id, "assistant", description, tool_used="describe_image")
    return description
