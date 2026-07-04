"""Wrapper verso il modello testuale/vision.

Due backend selezionabili con la variabile d'ambiente AGENTE_BACKEND:
  - "api" (default): endpoint OpenAI-compatible (default Groq, gratuito e veloce).
  - "local": modello via Ollama in locale.

Tutti i tool passano da qui: cambiando backend non serve modificare il resto
del codice. Utile all'esame quando la macchina non ha hardware adatto a Ollama.
"""

import base64
import os

# --- Scelta del backend ---
# Default "api" per partire subito senza configurare nulla (vedi API_KEY sotto).
# Per usare il locale: AGENTE_BACKEND=local (la variabile d'ambiente vince sul default).
BACKEND = os.environ.get("AGENTE_BACKEND", "api").lower()

# --- Config backend locale (Ollama) ---
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TEXT_MODEL = os.environ.get("AGENTE_TEXT_MODEL", "mistral:7b-instruct")
VISION_MODEL = os.environ.get("AGENTE_VISION_MODEL", "llava")

# --- Config backend API (OpenAI-compatible). Default: Groq / Llama 4 Scout ---
API_BASE_URL = os.environ.get("AGENTE_API_BASE_URL", "https://api.groq.com/openai/v1")
# ATTENZIONE: chiave scritta in chiaro per comodita' (da rigenerare dopo l'uso).
API_KEY = os.environ.get("AGENTE_API_KEY", "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")
API_MODEL = os.environ.get("AGENTE_API_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
API_VISION_MODEL = os.environ.get("AGENTE_API_VISION_MODEL", API_MODEL)


class LLMError(RuntimeError):
    """Errore di comunicazione con il modello (Ollama locale o API)."""


def _api_client():
    """Crea il client per il backend API (OpenAI-compatible).

    L'import di 'openai' e' pigro: chi usa solo il backend locale non ha bisogno
    di avere la libreria installata, e viceversa.

    Returns:
        Un'istanza del client OpenAI configurata con base URL e chiave.

    Raises:
        LLMError: Se la chiave API (AGENTE_API_KEY) non e' impostata.
    """
    if not API_KEY:
        raise LLMError("AGENTE_API_KEY non impostata: serve una chiave per il backend API.")
    from openai import OpenAI

    return OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


def chat(messages: list[dict], model: str | None = None, temperature: float = 0.2, **options) -> str:
    """Invia una conversazione al modello testuale e restituisce la risposta.

    Instrada la richiesta al backend attivo (Ollama locale o API) in base alla
    variabile d'ambiente AGENTE_BACKEND.

    Args:
        messages: Lista di messaggi nel formato {"role": ..., "content": ...}.
        model: Nome del modello; se None si usa il default del backend attivo.
        temperature: Grado di casualita' della generazione (0 = deterministico).
        **options: Opzioni aggiuntive passate al backend locale (es. num_predict).

    Returns:
        Il contenuto testuale della risposta del modello.

    Raises:
        LLMError: Se il backend non e' raggiungibile o restituisce un errore.
    """
    if BACKEND == "api":
        return _api_chat(messages, model or API_MODEL, temperature)
    return _ollama_chat(messages, model or TEXT_MODEL, temperature, **options)


def _ollama_chat(messages: list[dict], model: str, temperature: float, **options) -> str:
    """Esegue la chat sul modello locale via Ollama.

    Args:
        messages: Lista di messaggi {role, content}.
        model: Nome del modello Ollama da usare.
        temperature: Grado di casualita' della generazione.
        **options: Opzioni aggiuntive per Ollama (es. num_predict, stop).

    Returns:
        Il contenuto testuale della risposta.

    Raises:
        LLMError: Se Ollama non e' raggiungibile o il modello restituisce errore.
    """
    import ollama

    try:
        response = ollama.Client(host=OLLAMA_HOST).chat(
            model=model, messages=messages, options={"temperature": temperature, **options}
        )
    except ollama.ResponseError as exc:
        raise LLMError(f"Errore dal modello '{model}': {exc}") from exc
    except Exception as exc:
        raise LLMError(
            f"Impossibile contattare Ollama su {OLLAMA_HOST}. "
            "Assicurati che Ollama sia avviato ('ollama serve')."
        ) from exc
    return response["message"]["content"]


def _api_chat(messages: list[dict], model: str, temperature: float) -> str:
    """Esegue la chat su un endpoint API OpenAI-compatible.

    I messaggi {role, content} sono gia' nel formato dell'API, quindi non serve
    alcuna conversione.

    Args:
        messages: Lista di messaggi {role, content}.
        model: Nome del modello remoto da usare.
        temperature: Grado di casualita' della generazione.

    Returns:
        Il contenuto testuale della risposta.

    Raises:
        LLMError: Se la chiave manca o la chiamata all'API fallisce.
    """
    try:
        response = _api_client().chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"Errore dall'API ({API_BASE_URL}, modello '{model}'): {exc}") from exc
    return response.choices[0].message.content


def describe_image(image_path: str, prompt: str = "Descrivi questa immagine in dettaglio.") -> str:
    """Descrive un'immagine tramite il modello vision del backend attivo.

    Args:
        image_path: Percorso dell'immagine da analizzare.
        prompt: Istruzione testuale che accompagna l'immagine.

    Returns:
        La descrizione testuale prodotta dal modello.

    Raises:
        LLMError: Se il backend non e' raggiungibile o restituisce un errore.
    """
    if BACKEND == "api":
        return _api_describe(image_path, prompt)
    return _ollama_describe(image_path, prompt)


def _ollama_describe(image_path: str, prompt: str) -> str:
    """Descrive un'immagine usando il modello vision locale (Ollama).

    Args:
        image_path: Percorso dell'immagine; viene passato a Ollama tramite il
            parametro nativo 'images'.
        prompt: Istruzione testuale che accompagna l'immagine.

    Returns:
        La descrizione testuale prodotta dal modello.

    Raises:
        LLMError: Se Ollama non e' raggiungibile o il modello restituisce errore.
    """
    import ollama

    try:
        response = ollama.Client(host=OLLAMA_HOST).chat(
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


def _api_describe(image_path: str, prompt: str) -> str:
    """Descrive un'immagine tramite un modello multimodale via API.

    L'immagine viene letta e inviata inline come data URI codificato in base64.

    Args:
        image_path: Percorso dell'immagine da analizzare.
        prompt: Istruzione testuale che accompagna l'immagine.

    Returns:
        La descrizione testuale prodotta dal modello.

    Raises:
        LLMError: Se la chiave manca o la chiamata all'API fallisce.
    """
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else (ext or "png")
    try:
        response = _api_client().chat.completions.create(
            model=API_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                    ],
                }
            ],
        )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"Errore dall'API vision (modello '{API_VISION_MODEL}'): {exc}") from exc
    return response.choices[0].message.content
