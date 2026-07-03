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

## Modelli usati

- **Testo** (riassunto, traduzione, codegen): `mistral:7b-instruct` — configurabile con la variabile d'ambiente `AGENTE_TEXT_MODEL` (es. `phi3:mini` per risposte più veloci).
- **Vision** (descrizione immagini): `llava` — configurabile con `AGENTE_VISION_MODEL`.
- Host Ollama configurabile con `OLLAMA_HOST` (default `http://localhost:11434`).

## Utenti e memoria

Non è richiesta password: `agente login <username>` crea l'utente se non esiste e lo imposta come attivo per i comandi successivi (sessione salvata in `db/.session.json`). Ogni utente ha la propria cronologia in `db/database.db`, iniettata come contesto nelle chiamate successive al modello.

## Comandi

```bash
python main.py login alice
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
