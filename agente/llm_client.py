"""Wrapper verso Ollama (libreria nativa `ollama`)."""

import os

import ollama

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TEXT_MODEL = os.environ.get("AGENTE_TEXT_MODEL", "mistral:7b-instruct")
VISION_MODEL = os.environ.get("AGENTE_VISION_MODEL", "llava")

_client = ollama.Client(host=OLLAMA_HOST)


class LLMError(RuntimeError):
    """Errore di comunicazione con il server Ollama locale."""


# Invia una lista di messaggi (system/user/assistant) al modello testuale locale
# e ne restituisce solo il contenuto della risposta.
def chat(messages: list[dict], model: str = TEXT_MODEL) -> str:
    try:
        response = _client.chat(model=model, messages=messages)
    except ollama.ResponseError as exc:
        raise LLMError(f"Errore dal modello '{model}': {exc}") from exc
    except Exception as exc:
        raise LLMError(
            f"Impossibile contattare Ollama su {OLLAMA_HOST}. "
            "Assicurati che Ollama sia avviato ('ollama serve')."
        ) from exc
    return response["message"]["content"]


# Invia un'immagine al modello vision (llava) insieme a un prompt testuale.
def describe_image(image_path: str, prompt: str = "Descrivi questa immagine in dettaglio.") -> str:
    try:
        response = _client.chat(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": prompt, "images": [image_path]}],
        )
    except ollama.ResponseError as exc:
        raise LLMError(f"Errore dal modello vision '{VISION_MODEL}': {exc}") from exc
    except Exception as exc:
        raise LLMError(
            f"Impossibile contattare Ollama su {OLLAMA_HOST}. "
            "Assicurati che Ollama sia avviato ('ollama serve')."
        ) from exc
    return response["message"]["content"]
