---
name: todo-manager
description: >
  Gestione di todo personali su file system (directory .todos/): creazione, aggiornamento, completamento.
  Usa questa skill per: (1) CREARE un todo ("add todo", "nuovo todo", "crea todo", "aggiungi todo",
  "I need to remember to...", "ho bisogno di ricordarmi di...", "add to my todo list"),
  (2) AGGIORNARE un todo ("update todo", "update the priority of", "modifica il todo",
  "cambia priorità/scadenza del todo"), (3) COMPLETARE un todo ("mark as done", "complete todo",
  "segna come fatto", "ho finito il todo", "close that todo", "chiudi il todo").
  Attiva anche su promemoria personali impliciti ("I need to remember to X", "ho bisogno di
  ricordarmi di X"). NON usare per: listare todo, creare issue GitHub/Jira, note in documenti,
  reminder su calendario, task di progetto senza "todo" esplicito, o domande sulla skill stessa.
---

# Todo Manager

Gestione del ciclo di vita dei todo personali. L'agent propone i contenuti semantici; tutte le operazioni sul filesystem sono delegate a `todo.py`.

**Script:** `$HOME/.agents/skills/todo-manager/scripts/todo.py`

---

## Operazioni disponibili

| Trigger | Operazione |
|---|---|
| "add todo", "nuovo todo", "create todo", "I need to remember..." | **CREATE** |
| "update todo", "modifica", "cambia priorità/scadenza", "aggiorna" | **UPDATE** |
| "complete todo", "done", "segna come fatto", "chiudi task" | **COMPLETE** |

---

## Fase 0 — Localizza `.todos/`

Prima di qualsiasi operazione, cerca `.todos/` in:
1. Directory di lavoro corrente
2. Cartelle parent (fino a 3 livelli)
3. Percorsi comuni: `~/kb/`, `~/notes/`, `~/Documents/`

**CREATE** — se `.todos/` non esiste, chiedi conferma e inizializza:

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py init --dir "<path>/.todos"
```

**UPDATE / COMPLETE** — se `.todos/` non esiste → errore: "No .todos directory found."

---

## CREATE — Aggiungi un nuovo todo

### Fase A — Proposta (agent)

Dal prompt dell'utente, estrai o inferisci:
- **Titolo** (obbligatorio)
- **Descrizione** (Task Details): proposta contestuale basata sul titolo e sul contesto conversazionale
- **Checklist**: almeno uno step concreto e pertinente
- **Priorità**: `high` / `medium` / `low` — proposta in base all'urgenza percepita
- **Scadenza**: data `YYYY-MM-DD` o `none` — proposta in base al contesto

> **Importante:** i suggerimenti li genera l'agent, non uno script. Non inventare default silenziosi per priorità o scadenza se il contesto non è sufficiente.

### Fase B — Validazione e conferma obbligatoria (agent + utente)

**Non procedere mai alla Fase C senza conferma esplicita dell'utente.**

Presenta un riepilogo completo con `ask_user`:

```
📋 Riepilogo todo proposto:

  Titolo:      [titolo]
  Priorità:    [high|medium|low]
  Scadenza:    [YYYY-MM-DD oppure "nessuna"]
  Descrizione: [testo proposto]
  Checklist:
    - [ ] step 1
    - [ ] step 2
    ...

Confermi o vuoi modificare qualcosa?
- ✅ Conferma tutto
- ✏️ Modifica titolo
- ✏️ Modifica descrizione
- ✏️ Modifica checklist
- ✏️ Modifica priorità
- ✏️ Modifica scadenza
- ❌ Annulla
```

Regole obbligatorie:
- Se **priorità** manca o è ambigua → **devi chiedere** prima di procedere
- Se **scadenza** manca o è ambigua → **devi chiedere** prima di procedere
- Se **descrizione** o **checklist** sono vuote → **devi proporre e chiedere conferma**
- Se l'utente annulla → nessun file creato

Ripeti la conferma finché tutti i campi obbligatori sono esplicitamente approvati.

### Fase C — Creazione deterministica (script)

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py create \
  --dir "<path>/.todos" \
  --title "Titolo confermato" \
  --priority high|medium|low \
  --due YYYY-MM-DD|none \
  --details "Descrizione confermata" \
  --check "Step 1" \
  --check "Step 2"
```

**Gestione duplicati:** se lo script risponde con `"error": "duplicate_found"`:

```
Un todo simile esiste già: [titolo].
- Crea comunque (usa --force)
- Apri quello esistente
- Annulla
```

Per creare comunque, aggiungi `--force` al comando `create`.

**Risposta attesa (successo):**

```json
{
  "success": true,
  "operation": "create",
  "title": "...",
  "priority": "...",
  "due_date": "...",
  "filename": "YYYY-MM-DD_slug.md",
  "path": ".../.todos/active/...",
  "valid": true
}
```

Mostra all'utente:

```
✅ Todo creato!

  Titolo:     [title]
  Priorità:   [priority]
  Scadenza:   [due_date o 'Nessuna']
  Percorso:   .todos/active/[filename]
```

---

## UPDATE — Modifica un todo esistente

### Step 1: Trova il todo

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py find \
  --dir "<path>/.todos" \
  --query "fragmento titolo o slug"
```

- **0 risultati** → avvisa l'utente
- **1 risultato** → usa lo `slug` restituito
- **N risultati** → mostra la lista e chiedi quale modificare

### Step 2: Conferma le modifiche

Riassumi le modifiche richieste e chiedi conferma con `ask_user` prima di applicarle.

### Step 3: Applica con lo script

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py update \
  --dir "<path>/.todos" \
  --slug "<slug>" \
  [--title "Nuovo titolo"] \
  [--priority high|medium|low] \
  [--due YYYY-MM-DD] \
  [--remove-due] \
  [--status pending|in_progress] \
  [--add-tag "tag"] \
  [--remove-tag "tag"]
```

Lo script aggiorna frontmatter, execution log, filename (se cambia il titolo) e README di governance.

Mostra il riepilogo JSON delle modifiche applicate.

---

## COMPLETE — Segna un todo come completato

### Step 1: Trova il todo

Come per UPDATE, usa `find` e disambigua se necessario.

### Step 2: Conferma

Chiedi conferma con `ask_user` se non è esplicita nel prompt.

### Step 3: Completa con lo script

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py complete \
  --dir "<path>/.todos" \
  --slug "<slug>"
```

Lo script imposta `status: done`, aggiunge `completed_at`, aggiorna l'execution log, sposta il file in `.todos/completed/` e aggiorna i README.

Mostra:

```
✅ Todo completato!

  Titolo:      [title]
  Completato:  [completed_at]
  Archiviato:  .todos/completed/[filename]
```

---

## Validazione

Lo script valida automaticamente dopo `create` e `update`. Per validazione manuale:

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/todo.py validate \
  --file "<path/to/todo.md>"
```

Verifica:
- Frontmatter YAML corretto
- Campi obbligatori: `title`, `status`, `priority`, `created_at`
- Valori validi per `status` e `priority`
- Date in formato `YYYY-MM-DD`
- Sezioni obbligatorie: `## Task Details`, `## Checklist`, `## Execution Log`
- Almeno un item in `## Checklist`

---

## Gestione errori

| Situazione | Azione |
|---|---|
| `.todos/` non trovata (CREATE) | Proponi `todo.py init` |
| `.todos/` non trovata (UPDATE/COMPLETE) | Errore: "No .todos directory found." |
| Todo non trovato | Messaggio chiaro + suggerisci `find` |
| Duplicato (CREATE) | Mostra opzioni; usa `--force` se confermato |
| Utente annulla in Fase B | Nessun file creato |
| `valid: false` nel JSON | Mostra `validation_errors` e non dichiarare successo |

---

## Ruoli: agent vs script

| Responsabilità | Chi |
|---|---|
| Proporre descrizione, checklist, priorità, scadenza | **Agent** |
| Confermare con l'utente tutti i campi obbligatori | **Agent** |
| Scrivere file `.md`, slug, frontmatter, execution log | **Script** |
| Aggiornare README di governance | **Script** |
| Spostare `active/` → `completed/` | **Script** |
| Inizializzare struttura `.todos/` | **Script** |
| Validare formato file | **Script** |

**Non scrivere mai manualmente file todo o README di governance.** Usa sempre `todo.py`.
