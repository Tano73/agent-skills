---
title: "LLM Wiki Manager — Guida all'utilizzo"
category: concept
tags: [meta, skill, workflow, guida]
sources: []
created: 2026-05-11
updated: 2026-05-11
---

# LLM Wiki Manager — Guida all'utilizzo

Lo skill `llm-wiki-manager` trasforma l'assistente AI in un **wiki maintainer disciplinato**: crea, aggiorna e mantiene una knowledge base personale in Markdown, accumulando conoscenza sessione dopo sessione.

Ogni fonte ingerita, ogni domanda a cui risponde, arricchisce il wiki per le sessioni future.

---

## Concetti chiave

| Termine | Significato |
|---------|-------------|
| **SETUP** | Inizializza la struttura del wiki da zero |
| **INGEST** | Trasforma un documento/articolo in pagine wiki strutturate |
| **QUERY** | Risponde a domande usando le pagine wiki come base di conoscenza |
| **LINT** | Audit del wiki: trova contraddizioni, pagine orfane, gap di contenuto |
| `wiki/index.md` | Catalogo completo di tutte le pagine — la "mappa" del wiki → vedi [Index-File Discovery](index-file-discovery.md) |
| `wiki/log.md` | Registro cronologico append-only di tutte le operazioni → vedi [Append-Only Log](append-only-log.md) |
| `raw/` | Cartella per documenti sorgente originali — **mai modificare** |

---

## Struttura directory

```
<wiki-root>/
├── AGENTS.md               ← manuale operativo dello skill (generato da SETUP)
├── raw/                    ← documenti sorgente originali (immutabili)
│   └── assets/             ← immagini e allegati
└── wiki/
    ├── index.md            ← catalogo di tutte le pagine
    ├── log.md              ← storico delle operazioni
    ├── overview.md         ← sintesi evolutiva della conoscenza
    ├── entities/           ← progetti, sistemi, tecnologie, API
    ├── concepts/           ← pattern, decisioni architetturali, best practice
    └── sources/            ← una pagina per ogni documento ingerito
```

---

## Operazione 1: SETUP

### Quando usarla

Quando si inizia un nuovo wiki da zero, su un nuovo dominio o progetto.

### Come invocarla

```
setup
crea wiki
inizializza una wiki per il dominio [nome dominio]
crea una nuova wiki per il progetto [nome progetto]
```

### Cosa fa l'assistente AI

1. Chiede conferma della directory root del wiki
2. Crea l'intera struttura di directory (`wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `raw/`, `raw/assets/`)
3. Crea `wiki/index.md` con tabelle vuote
4. Crea `wiki/log.md` con la prima entry di setup
5. Crea `wiki/overview.md` con un'introduzione al dominio
6. Crea `AGENTS.md` con le convenzioni del wiki adattate al dominio
7. Esegue `git init && git add . && git commit -m "chore: initialize llm-wiki"`
8. Suggerisce il primo documento da ingerire

### Esempio pratico

**Prompt utente:**
```
setup — voglio una wiki per il nostro progetto microservices in Go
usiamo Kubernetes, gRPC, PostgreSQL e Kafka
```

**Output atteso:**
```
✅ Struttura wiki creata in ./

File creati:
- AGENTS.md (manuale operativo)
- wiki/index.md (catalogo vuoto)
- wiki/log.md (primo entry: setup 2026-05-11)
- wiki/overview.md (dominio: microservices Go)
- raw/, raw/assets/
- wiki/entities/, wiki/concepts/, wiki/sources/

📌 Git: commit iniziale eseguito.

Suggerimento: hai già un documento su gRPC o sull'architettura generale?
Posso ingestionarlo subito con: ingest raw/architettura.md
```

---

## Operazione 2: INGEST

### Quando usarla

Dopo aver letto un articolo, un ADR, una RFC, dei meeting notes, documentazione tecnica — qualunque fonte di conoscenza che vuoi rendere ricercabile e persistente.

### Come invocarla

```
ingest raw/kubernetes-operators.md
processa questo articolo: [incolla testo]
aggiungi questo al wiki: raw/design/service-mesh-adr.md
leggi questo e mettilo nella wiki
```

### Cosa fa l'assistente AI

1. Legge il documento sorgente (da `raw/`, testo incollato, o DocMind)
2. Discute con te: 3–5 takeaway chiave, entità e concetti coinvolti, eventuali contraddizioni
3. Crea `wiki/sources/<slug>.md` con summary, key takeaways, entità e concetti referenziati
4. Crea/aggiorna le pagine `wiki/entities/` coinvolte (con backlink alla fonte)
5. Crea/aggiorna le pagine `wiki/concepts/` coinvolte
6. Aggiorna `wiki/overview.md` con le nuove conoscenze
7. Aggiorna `wiki/index.md` con le nuove righe
8. Appende entry in `wiki/log.md`
9. Riporta l'elenco di tutte le pagine create o modificate (tipicamente 5–15 per fonte)

### Esempio pratico

**Prompt utente:**
```
ingest — ho letto questo articolo su Kubernetes Operators:

[testo incollato dell'articolo]
```

**Output atteso:**
```
📥 INGEST: Kubernetes Operators

Takeaway chiave:
1. Gli Operators estendono l'API di Kubernetes con CRD
2. Il controller loop riconcilia lo stato desiderato con quello corrente
3. KubeBuilder è il framework raccomandato per sviluppare Operators
4. Day-2 operations (backup, upgrade, scaling) sono il principale use case

Pagine create:
- wiki/sources/kubernetes-operators-article.md
- wiki/entities/kubernetes-operator.md (nuovo)
- wiki/entities/kubebuilder.md (nuovo)
- wiki/concepts/controller-loop.md (nuovo)
- wiki/concepts/custom-resource-definition.md (nuovo)
- wiki/concepts/day-2-operations.md (nuovo)

Pagine aggiornate:
- wiki/index.md (+5 righe)
- wiki/overview.md (paragrafo Kubernetes esteso)
- wiki/log.md (entry ingest)

✅ 8 pagine create/modificate.
```

---

## Operazione 3: QUERY

### Quando usarla

Quando vuoi una risposta sintetizzata usando le conoscenze accumulate nel wiki, con citazioni alle pagine rilevanti.

### Come invocarla

```
cosa sai di Kubernetes Operators?
dimmi come funziona il controller loop
qual è la differenza tra un Operator e un Deployment?
come funziona gRPC nel nostro sistema?
query: pattern CQRS — dove lo usiamo?
```

### Cosa fa l'assistente AI

1. Legge `wiki/index.md` per identificare le pagine più rilevanti
2. Legge le pagine entity, concept e source rilevanti
3. Sintetizza la risposta con citazioni (link Markdown relativi alle pagine wiki)
4. Sceglie il formato migliore:
   - **Domanda fattuale** → testo conciso con link
   - **Confronto** → tabella Markdown
   - **Architettura/design** → sezioni strutturate
   - **Processo/flusso** → passi numerati o diagramma Mermaid
5. Chiede: *"Vuoi che salvi questa risposta come pagina wiki?"*

### Esempio pratico

**Prompt utente:**
```
qual è la differenza tra un Kubernetes Operator e un normale Deployment?
```

**Output atteso:**
```markdown
## Operator vs Deployment

| Dimensione | Deployment | Operator |
|------------|-----------|---------|
| Tipo di app | Stateless | Stateful / complessa |
| Logica operativa | Nessuna | Customizzata nel controller |
| API extension | No | Sì (CRD) |
| Day-2 operations | Manuale | Automatizzata |
| Complessità impl. | Bassa | Alta |

**Fonti**: 
- [Controller Loop](../concepts/controller-loop.md)
- [Custom Resource Definition](../concepts/custom-resource-definition.md)
- [Kubernetes Operators — articolo](../sources/kubernetes-operators-article.md)

Vuoi che salvi questa risposta come pagina wiki?
Proposta: wiki/concepts/operator-vs-deployment.md
```

---

## Operazione 4: LINT

### Quando usarla

Periodicamente (ogni 10–20 ingest) per fare un audit del wiki, trovare inconsistenze e migliorare la qualità.

### Come invocarla

```
lint
controlla il wiki
fai un audit
health check
verifica il wiki, ci sono contraddizioni?
```

### Cosa fa l'assistente AI

Analizza tutte le pagine wiki e produce un report prioritizzato:

```markdown
# Wiki Lint Report — 2026-05-11

## 🔴 Contraddizioni
- wiki/concepts/caching.md e wiki/sources/redis-article.md hanno versioni diverse per TTL default

## 🟠 Pagine Orfane
- wiki/concepts/sidecar-proxy.md — nessun link in entrata

## 🟠 Pagine Mancanti
- "Service Mesh" citata in 3 pagine ma manca una pagina dedicata

## 🟡 Contenuto Stale
- wiki/entities/api-gateway.md — aggiornata 6 mesi fa, potrebbero esserci novità

## 🟡 Cross-Reference Mancanti
- wiki/entities/kafka.md e wiki/concepts/event-sourcing.md dovrebbero linkarsi

## 🟢 Gap di Dati
- gRPC streaming documentato superficialmente — ci sono fonti disponibili?

## 🟢 Domande Suggerite
- Come si integra il nostro service mesh con il rate limiting dell'API gateway?
```

Poi chiede quali item risolvere subito.

---

## Session Start (automatico)

Ogni volta che lo skill è attivo, l'assistente AI **prima di fare qualsiasi cosa**:

1. Verifica che `wiki/index.md` esista (se no → propone SETUP)
2. Legge `wiki/index.md` (catalogo completo)
3. Legge le ultime 5 entry di `wiki/log.md` (attività recente)
4. Riassume brevemente lo stato:

```
Il wiki contiene 24 entity pages, 31 concept pages, 8 sources.
Ultima attività: ingest "gRPC best practices" (2026-05-10) — 7 pagine modificate.

Cosa vuoi fare? SETUP · INGEST · QUERY · LINT
```

---

## Scenari di utilizzo tipici

### Scenario A: Onboarding su un nuovo progetto

```
# Giorno 1
setup — wiki per il progetto PaymentService (Java, Spring Boot, Postgres, Kafka)

# Giorno 2
ingest raw/architecture-overview.pdf

# Giorno 3
ingest raw/adr-001-event-sourcing.md
ingest raw/adr-002-saga-pattern.md

# Dopo 1 settimana
query: come gestiamo i pagamenti falliti? qual è il pattern di retry?
```

### Scenario B: Studio personale

```
# Leggi un libro/corso
ingest — [incolla capitolo sul DDD]

# Ogni settimana
ingest raw/notes-week-3.md

# Prima di un colloquio
query: dimmi i concetti chiave di Domain-Driven Design che conosco
lint — ci sono argomenti che ho coperto superficialmente?
```

### Scenario C: Team knowledge base (con DocMind)

```
# Condivisione via DocMind
ingest docmind://project-xyz/post-mortem-2026-04

# Query con semantic search
query: abbiamo mai avuto problemi simili con il database connection pool?
```

### Scenario D: Review periodica

```
# Ogni mese
lint

# Basandoti sul report:
# - Risolvi contraddizioni
# - Crea le pagine mancanti
# - Aggiorna contenuto stale
```

---

## Convenzioni delle pagine

### Naming

- Sempre `kebab-case.md`: `kubernetes-operator.md`, `circuit-breaker.md`
- Cross-reference: **solo link Markdown relativi** — `[Title](../entities/foo.md)`
- **Mai** Obsidian wikilinks `[[foo]]`

### Frontmatter (tutte le pagine)

```yaml
---
title: "Titolo pagina"
category: entity | concept | source | overview
tags: [tag1, tag2]
sources: [source-slug]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Dove mettere cosa

| Tipo di contenuto | Directory |
|---|---|
| Tecnologia, libreria, sistema, API, progetto | `entities/` |
| Pattern, principio, concetto astratto, decisione | `concepts/` |
| Documento sorgente processato | `sources/` |

---

## Integrazione DocMind (opzionale)

Se DocMind MCP è disponibile nell'ambiente:

| Layer | Funzionalità |
|-------|-------------|
| **Layer 1** — Ingest | Accetta `uniqueName` DocMind o query di ricerca come input per INGEST |
| **Layer 2** — Query | Usa `searchFlavorChunks` per trovare pagine rilevanti in aggiunta a `index.md` |
| **Layer 3** — Mirror | Sincronizza le pagine wiki su DocMind per condivisione e ricerca cross-wiki |

In modalità **local-only** (senza DocMind), lo skill funziona identicamente.

---

## Installazione

### Prerequisiti

- Un agent AI che supporta il sistema di skill (Copilot CLI, Cursor, Claude Code)
- Python 3 (solo se vuoi ripackagizzare lo skill)

### Metodo 1 — File `.skill` (raccomandato)

```bash
# Copia il file pacchettizzato nella directory degli skill utente
cp llm-wiki-manager.skill ~/.agents/skills/
```

Poi riavvia la sessione o ricarica gli skill. Lo skill comparirà automaticamente nell'elenco disponibile.

### Metodo 2 — Directory SKILL.md

```bash
# Copia la cartella skill nella directory degli skill utente
cp -r llm-wiki-manager/ ~/.agents/skills/
```

Il contenuto minimo necessario è:
```
~/.agents/skills/llm-wiki-manager/
└── SKILL.md
```

### Compatibilità

| Tool | Compatibile | Note |
|------|-------------|------|
| **Copilot CLI** | ✅ | Directory: `~/.agents/skills/` |
| **Cursor** | ✅ | Verifica il path di configurazione degli skill |
| **Claude Code** | ✅ | Stesso meccanismo di Copilot CLI |

### Verifica installazione

Dopo l'installazione, nella sessione puoi scrivere:
```
setup — inizializza wiki per il mio progetto
```
Se lo skill è attivo, l'assistente seguirà il workflow strutturato descritto in questa guida.

---

## Relazioni con altri concetti del wiki

Questa guida descrive il workflow operativo dello skill. I concetti fondamentali del wiki sono documentati separatamente:

- [Persistent Compounding Wiki](persistent-compounding-wiki.md) — perché un wiki LLM è diverso dal RAG tradizionale
- [Index-File Discovery](index-file-discovery.md) — come `index.md` funziona da catalogo senza database
- [Append-Only Log](append-only-log.md) — perché `log.md` è append-only e come si usa

---

## Regole fondamentali

1. **Mai scrivere in `raw/`** — è la fonte di verità immutabile
2. **Aggiorna sempre `index.md` e `log.md`** dopo ogni operazione
3. **Ogni pagina deve linkare almeno un'altra pagina** wiki
4. **Ogni pagina deve avere una entry in `index.md`**
5. **Flagga sempre le contraddizioni** con il notice standard

```markdown
> ⚠️ **Contraddizione** [YYYY-MM-DD]: [fonte-a](../sources/a.md) afferma X,
> ma [fonte-b](../sources/b.md) afferma Y. Da risolvere.
```
