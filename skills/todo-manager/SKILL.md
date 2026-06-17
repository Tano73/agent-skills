---
name: todo-manager
description: >
  Gestione di todo personali su file system (directory Todos/): creazione, aggiornamento, completamento.
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

Gestione completa del ciclo di vita dei todo: creazione, aggiornamento e completamento.

---

## Operazioni disponibili

| Trigger | Operazione |
|---|---|
| "add todo", "nuovo todo", "create todo", "I need to remember..." | **CREATE** |
| "update todo", "modifica", "cambia priorità/scadenza", "aggiorna" | **UPDATE** |
| "complete todo", "done", "segna come fatto", "chiudi task" | **COMPLETE** |

---

## Fase 0 — Localizza la directory Todos

Prima di qualsiasi operazione, cerca `Todos/` in:
1. Directory di lavoro corrente
2. Cartelle parent (fino a 3 livelli)
3. Percorsi comuni: `~/kb/`, `~/notes/`, `~/Documents/`

Se non trovata (solo per CREATE): offri di creare la struttura:
> "No Todos directory found. Would you like me to create one?"
> - Yes, create in `[path suggerito]`
> - Yes, in a different location
> - No, cancel

Se l'utente conferma, crea con il **Default RULE.md** (vedi in fondo).

Per UPDATE e COMPLETE, se non esiste `Todos/` → messaggio di errore chiaro.

---

## CREATE — Aggiungi un nuovo todo

### Step 1: Raccolta informazioni

Raccogli dal prompt dell'utente (o chiedi con `ask_user` se mancanti):

- **Titolo** (obbligatorio): breve descrizione del task
- **Priorità**: `high` / `medium` (default) / `low`
- **Scadenza** (opzionale): `today` / `tomorrow` / `this week` / data specifica / nessuna

### Step 2: Controlla duplicati

Scansiona `Todos/active/` per titoli simili (case-insensitive). Se esiste già:
> "A similar todo already exists: *[title]*."
> - Create anyway (append counter: `_2`, `_3`…)
> - Open existing
> - Cancel

### Step 3: Genera il file

**Formato filename:** `YYYY-MM-DD_[slug].md`
- Slug: titolo lowercase, spazi → trattini, solo alfanumerici + trattini, max 50 char
- Esempio: `2025-01-13_reply-to-client-email.md`

**Crea `Todos/active/[filename]`** con questo template esatto:

```markdown
---
title: [Titolo fornito dall'utente]
status: pending
priority: [high|medium|low]
created_at: [YYYY-MM-DD]
due_date: [YYYY-MM-DD se fornita, altrimenti ometti questo campo]
source_file: null
source_type: manual
tags: []
dependencies: []
related_files: []
---

# [Title]

## Task Details

[Breve placeholder: "_Fill in task details here._"]

## Checklist

- [ ] [Primo step — l'utente può modificare]

## Execution Log

### [Data odierna YYYY-MM-DD]
- Todo created manually
- Status: pending
- Priority: [priority]
```

> **Nota sul `due_date`:** includi il campo solo se l'utente ha fornito una scadenza. Se non specificata, ometti completamente il campo dal frontmatter.

### Step 4: Aggiorna governance

**`Todos/active/README.md`** — aggiungi entry:
```
- [filename](filename) — [title] (Priority: [priority], Due: [date o 'none'])
```
Aggiorna "Last updated: YYYY-MM-DD".

**`Todos/README.md`** — aggiorna conteggio attivi e sezione "Recent Changes":
```
- YYYY-MM-DD: Added "[title]"
```
Mantieni max 10 voci in "Recent Changes".

### Step 5: Valida e conferma

Esegui lo script di validazione (vedi sezione Script) sul file appena creato, poi mostra:

```
✅ Todo created successfully!

  Title:     [title]
  Priority:  [priority]
  Due Date:  [date o 'No deadline']
  Location:  Todos/active/[filename]
```

---

## UPDATE — Modifica un todo esistente

### Step 1: Individua il todo

Cerca in `Todos/active/` il file il cui titolo o slug corrisponde a quanto indicato dall'utente.
Se più file corrispondono, mostra la lista e chiedi quale.
Se non trovato, avvisa l'utente.

### Step 2: Determina cosa cambiare

Campi aggiornabili:
- `title` — aggiorna anche il filename e le entry nei README
- `priority` — `high` / `medium` / `low`
- `due_date` — nuova data o rimozione
- `status` — `pending` / `in_progress`
- `tags` — aggiungi/rimuovi tag
- `dependencies` / `related_files`

### Step 3: Applica le modifiche

1. Aggiorna il frontmatter YAML
2. Aggiungi entry in `## Execution Log`:
   ```
   ### [Data odierna]
   - Updated: [campo] → [nuovo valore]
   ```
3. Se il titolo è cambiato: rinomina il file e aggiorna `Todos/active/README.md`

### Step 4: Valida e conferma

Esegui lo script di validazione, poi mostra un riepilogo delle modifiche applicate.

---

## COMPLETE — Segna un todo come completato

### Step 1: Individua il todo

Cerca in `Todos/active/` (come per UPDATE).

### Step 2: Aggiorna il file

1. Cambia `status: pending` → `status: done` nel frontmatter
2. Aggiungi entry in `## Execution Log`:
   ```
   ### [Data odierna]
   - Todo completed
   - Status: done
   ```
3. Aggiungi campo `completed_at: [YYYY-MM-DD]` al frontmatter

### Step 3: Sposta il file

```
Todos/active/[filename]  →  Todos/completed/[filename]
```

### Step 4: Aggiorna governance

- Rimuovi entry da `Todos/active/README.md`
- Aggiorna "Last updated"
- Aggiorna `Todos/README.md`: decrementa active, incrementa completed
- Aggiungi a "Recent Changes": `- YYYY-MM-DD: Completed "[title]"`

### Step 5: Conferma

```
✅ Todo completed!

  Title:     [title]
  Completed: [date]
  Archived:  Todos/completed/[filename]
```

---

## Script di validazione

Usa lo script `$HOME/.agents/skills/todo-manager/scripts/validate_todo.py` per verificare che un file todo rispetti il formato.

**Quando eseguirlo:** dopo CREATE e UPDATE.

```bash
python3 $HOME/.agents/skills/todo-manager/scripts/validate_todo.py <path/to/todo.md>
```

Lo script verifica:
- Presenza e correttezza del frontmatter YAML
- Campi obbligatori: `title`, `status`, `priority`, `created_at`
- Valori validi: `status` ∈ {pending, in_progress, done}, `priority` ∈ {high, medium, low}
- Formato date: `YYYY-MM-DD`
- Sezioni obbligatorie: `## Task Details`, `## Checklist`, `## Execution Log`
- Almeno un item in `## Checklist`

Se la validazione fallisce, mostra gli errori e chiedi all'utente se vuole procedere comunque.

---

## Gestione errori

| Situazione | Azione |
|---|---|
| `Todos/` non trovata (CREATE) | Offri di creare la struttura |
| `Todos/` non trovata (UPDATE/COMPLETE) | Errore: "No Todos directory found." |
| Todo non trovato (UPDATE/COMPLETE) | Messaggio chiaro + suggerisci ricerca |
| Titolo duplicato (CREATE) | Avvisa, offri opzioni |
| Utente cancella a metà | Nessun file creato/modificato |
| `Todos/active/` mancante | Creala prima di scrivere |

---

## Default RULE.md Template

```markdown
# Todos — Personal Task Management

## Purpose

Centralized management of all todo items.

## Todo Tracking

enabled: true
todos_directory: [percorso assoluto di questa Todos/]

## Structure

Todos/
├── active/     # Todo attivi
└── completed/  # Todo completati

## Naming Convention

YYYY-MM-DD_todo-title-slug.md

## Allowed Operations

- Create: Allowed
- Update: Allowed (must update execution log)
- Delete: Not allowed (archive to completed/ instead)
- Move: Only between active/ and completed/
```
