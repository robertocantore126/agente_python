"""Funzione 3: descrizione di immagini caricate."""

from pathlib import Path

import llm_client
import memory

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# Descrive un'immagine tramite il modello vision. A differenza degli altri tool,
# non usa memory.build_context_messages: il modello vision riceve solo prompt + immagine.
def describe(image_path: str, user_id: int) -> str:
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
