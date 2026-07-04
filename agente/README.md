# Assistente AI Locale CLI Multi-Utente

CLI Python che usa un LLM locale via [Ollama](https://ollama.com) per riassumere file, tradurre testi, descrivere immagini e generare/eseguire codice, con memoria conversazionale persistente per utente su SQLite.

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

ollama pull mistral:7b-instruct   # modello testuale di default
ollama pull llava                 # modello vision per describe
ollama serve                      # se non già in esecuzione come servizio
```

## Backend: modello locale o API

Il programma può usare due backend, scelti con `AGENTE_BACKEND`:

- `local` (default): modello via **Ollama** in locale.
- `api`: endpoint **OpenAI-compatible** (default [Groq](https://console.groq.com), gratuito e veloce). Utile quando la macchina non ha hardware adatto a Ollama.

### Backend locale (Ollama)

- **Testo**: `mistral:7b-instruct` — configurabile con `AGENTE_TEXT_MODEL` (es. `phi3:mini` per risposte più veloci, o un modello più piccolo se la GPU ha poca VRAM).
- **Vision**: `llava` — configurabile con `AGENTE_VISION_MODEL`.
- Host Ollama configurabile con `OLLAMA_HOST` (default `http://localhost:11434`).

### Backend API (es. Groq)

```bash
set AGENTE_BACKEND=api
set AGENTE_API_KEY=gsk_...          # chiave da console.groq.com (gratuita)
# opzionali (hanno gia' un default sensato):
set AGENTE_API_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
set AGENTE_API_BASE_URL=https://api.groq.com/openai/v1
```

Il modello di default (`Llama 4 Scout`) è multimodale, quindi gestisce sia i comandi testuali sia `describe`. Per usare un altro provider (OpenAI, OpenRouter…) basta cambiare `AGENTE_API_BASE_URL`, `AGENTE_API_KEY` e `AGENTE_API_MODEL`. La lista dei modelli Groq attivi è su `https://api.groq.com/openai/v1/models`.

## Utenti e memoria

`agente login <username> [password]` accede all'utente: al primo accesso lo crea con la password scelta, altrimenti verifica che la password combaci. Se ometti la password, la CLI la chiede a schermo (`Password: `). L'utente attivo è salvato in `db/.session.json` per i comandi successivi. Ogni utente ha la propria cronologia in `db/database.db`, consultabile con il comando `history`.

> Nota: la password è salvata **in chiaro** nella tabella `users`. È una semplificazione didattica; in produzione si salverebbe un hash con salt (es. `hashlib.pbkdf2_hmac`).

## Comandi

```bash
python main.py login alice segreta123
python main.py login alice            # chiede la password a schermo
python main.py whoami
python main.py logout

python main.py summarize report.pdf [--max-length 500]
python main.py translate note.txt --to inglese
python main.py describe foto.png
python main.py codegen "funzione che calcola i numeri di Fibonacci" [--lang python] [--output fib.py] [--cot]
python main.py run fib.py
```

## Nota Windows (caratteri accentati)

Se sul terminale vedi caratteri accentati mostrati male (es. `capacit�`), esegui `chcp 65001` prima di lanciare la CLI per impostare la code page del terminale su UTF-8.

## Limitazioni note

- **Nessuna autenticazione reale**: `login` seleziona/crea un utente solo in base allo username, senza password. Scelta di scope ridotto per un progetto didattico.
- **Sandbox esecuzione codice**: `run` esegue il file con `python -I`, timeout (default 8s) e variabili d'ambiente ridotte a quelle strettamente necessarie. È un isolamento a livello di processo, non un vero sandbox filesystem/rete (richiederebbe container Docker o una VM), sufficiente per lo scopo didattico ma da non usare con codice non fidato in produzione.
- **Descrizione immagini** richiede un modello separato multimodale (`llava`), dato che i modelli testuali da 1.5B–7B non processano immagini.

## Test manuali

1. `python main.py login alice` → verificare la creazione di `db/database.db` con una riga in `users`.
2. `python main.py summarize <file.txt>` → verificare l'output e una nuova coppia di righe in `memory`.
3. `python main.py translate <file.txt> --to inglese` → verificare il file `<file>.inglese.txt` generato.
4. `python main.py describe <immagine.png>` → verificare che `llava` sia stato scaricato (`ollama list`).
5. `python main.py codegen "somma di due numeri" --output somma.py` poi `python main.py run somma.py` → verificare stdout e codice di uscita.
6. `python main.py logout` seguito da un comando funzionale → verificare che venga richiesto il login.
