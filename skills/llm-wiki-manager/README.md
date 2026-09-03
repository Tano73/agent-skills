# llm-wiki-manager — Guida Utente

Una skill per Cursor/Claude che mantiene una **knowledge base markdown locale, persistente e in continua crescita**, e si integra con il MCP **DocMind** per ricerca semantica cross-progetto, workflow di spec e condivisione di team.

> **Per gli agenti**: il manuale operativo (cosa fa l'agente passo-passo) è in `SKILL.md`. Questo README è invece per te, l'utente umano: cosa puoi chiedere, come usarla, esempi pratici.

---

## Indice

1. [A cosa serve](#a-cosa-serve)
2. [Setup in 3 minuti](#setup-in-3-minuti)
3. [Wiki dentro un progetto esistente](#wiki-dentro-un-progetto-esistente)
4. [Le 7 operazioni che puoi chiedere](#le-7-operazioni-che-puoi-chiedere)
5. [Integrazione DocMind](#integrazione-docmind)
6. [Convenzioni di base](#convenzioni-di-base)
7. [Esempio: una settimana di sviluppo](#esempio-una-settimana-di-sviluppo)
8. [FAQ](#faq)
9. [Troubleshooting](#troubleshooting)
10. [Approfondimenti](#approfondimenti)

---

## A cosa serve

### Il problema

Quando lavori su un progetto software accumuli sapere prezioso che oggi si perde:

- Leggi un doc, capisci come funziona una libreria, ma fra 3 mesi te lo dimentichi.
- Risolvi un bug "strano", e fra un mese qualcuno (o tu stesso) lo rincontra da zero.
- Prendi una decisione architetturale importante, ma la motivazione resta solo nella tua testa.
- Conosci la knowledge del team ma è frammentata: docs, chat, email, slide.

### Il pattern

Questa skill implementa il pattern **"LLM wiki"** descritto originalmente da Andrej Karpathy: una knowledge base personale composta da:

```
<wiki-root>/
├── AGENTS.md          ← operating manual specifico di questa wiki
├── raw/               ← documenti sorgente IMMUTABILI (i tuoi materiali grezzi)
│   └── assets/        ← immagini e allegati
└── wiki/
    ├── index.md       ← catalogo di tutto
    ├── log.md         ← diario cronologico append-only
    ├── overview.md    ← sintesi evolutiva del sapere
    ├── entities/      ← cose concrete (progetti, sistemi, tool, API, team)
    ├── concepts/      ← idee astratte (pattern, principi, protocolli)
    └── sources/       ← una pagina di sintesi per ogni documento ingerito
```

Ogni volta che l'agente impara qualcosa di nuovo (ingerendo un documento, rispondendo a una domanda, risolvendo un bug), aggiorna **15+ file in un colpo solo**: la source page, le entity correlate, i concept toccati, l'index, il log, l'overview. Le pagine si linkano tra loro come un grafo navigabile.

### A chi serve

- Sviluppatori che lavorano in domini complessi (autenticazione, sistemi distribuiti, integrazioni).
- Tech lead che vogliono memoria storica delle decisioni architetturali.
- Chiunque legga molta documentazione tecnica e voglia che ogni lettura "compongi" sapere riutilizzabile.

### Cosa NON è

- **Non è un wiki di team**: per quello c'è DocMind (vedi sezione [Integrazione DocMind](#integrazione-docmind)).
- **Non è un tool di project management**: per status, AC, e workflow di feature usa le `spec_*` di DocMind, non la wiki.
- **Non è autosufficiente**: ha bisogno di te per decidere cosa è importante. L'agente propone, tu confermi.

---

## Setup in 3 minuti

### Prerequisiti

- Cursor o Claude Code con questa skill installata in `~/.agents/skills/llm-wiki-manager/` o `~/.claude/skills/llm-wiki-manager/`.
- (Opzionale ma consigliato) MCP DocMind configurato.
- (Opzionale) Git installato — la skill committa per te ad ogni setup.

### Passi

1. **Scegli dove vivrà la wiki**. Due scenari tipici:

   **Scenario A — Wiki standalone** (cartella dedicata, senza altri progetti dentro):

   ```bash
   mkdir ~/wiki-keycloak  # esempio: knowledge su Keycloak/SAML/OIDC
   cd ~/wiki-keycloak
   ```

   **Scenario B — Wiki dentro un progetto esistente** (il progetto ha già il suo `AGENTS.md`):

   ```bash
   cd ~/projects/myapp  # progetto già con AGENTS.md e .git/
   # NON serve creare la cartella a mano: lo fa lo skill
   ```

   In entrambi i casi, lo skill rileva il contesto automaticamente:
   - Se la cwd ha già un `AGENTS.md` → propone `./knowledge/` come wiki root (sub-directory dedicata).
   - Se la cwd è pulita → propone la cwd stessa come wiki root.
   - Conferma sempre con te prima di procedere; puoi sovrascrivere il default proponendo un path diverso (es. `docs/wiki/`, `kb/`).

2. **Apri Cursor** nella cartella e dì all'agente:

   > *"crea una nuova wiki per il dominio Java/Spring Boot/Keycloak/OIDC"*

   (Trigger riconosciuti: `setup`, `inizializza`, `crea wiki`, `crea una nuova wiki`.)

3. L'agente esegue **SETUP**:
   - Cerca prima una wiki esistente (cwd, parent, path comuni come `./knowledge/`, `~/kb/`); se non la trova, conferma con te il wiki root proposto.
   - Ti fa un'intervista breve sul dominio (quali sono le entity principali, i concept chiave).
   - Se DocMind è disponibile, fa un pre-scan dei progetti DocMind per trovare documenti rilevanti e li ingerisce automaticamente.
   - Crea la struttura completa con pagine seed già linkate tra loro.
   - Esegue un lint meccanico locale (`scripts/wiki_lint.py`).
   - **Git smart, con conferma**: se la cartella è già in un repo git, propone un commit nel repo padre; altrimenti propone `git init` + commit. **Non esegue `git commit` senza un sì esplicito.**

4. **Aggiungi il binding DocMind** all'`AGENTS.md` generato (sezione `## DocMind Binding`):

   ```markdown
   ## DocMind Binding

   - **Project DocMind associato**: `<nome-progetto-docmind>`
   - **PROMOTE target project**: `org-patterns`
   - **Hybrid search default mode**: `hybrid`
   ```

   Se non usi DocMind, lascia stare: tutte le operations funzionano comunque in *local-only mode*.

5. **Fatto.** Inizia a interrogare e ingerire.

---

## Wiki dentro un progetto esistente

Lo scenario più comune nei progetti software reali: hai già un repo con il suo `AGENTS.md` (build, lint, test, convenzioni) e vuoi aggiungere la wiki come **componente del progetto stesso**, non come repo separato.

### Layout standard

Lo skill propone di default `./knowledge/` come sub-directory:

```
myapp/
├── AGENTS.md              ← progetto: build, test, lint, convenzioni codice
├── .git/                   ← repo già esistente
├── src/
├── tests/
└── knowledge/             ← wiki root (creata dallo skill in SETUP)
    ├── AGENTS.md          ← convenzioni della wiki (NON collide con quello del progetto)
    ├── raw/
    │   └── assets/
    └── wiki/
        ├── index.md
        ├── log.md
        ├── overview.md
        ├── entities/
        ├── concepts/
        └── sources/
```

Puoi sovrascrivere il nome (`docs/wiki/`, `kb/`, `wiki-acme/`, ecc.) confermandolo all'agente in fase di SETUP.

### Come funziona la risoluzione di `AGENTS.md` (è un vantaggio, non un problema)

Cursor risolve `AGENTS.md` **gerarchicamente verso l'alto** dalla cwd. Quando l'agente lavora con cwd in `myapp/knowledge/`, vede DUE `AGENTS.md`:

- `myapp/knowledge/AGENTS.md` → convenzioni della wiki (più specifico, prevale).
- `myapp/AGENTS.md` → convenzioni del progetto (contesto generale).

Quando invece l'agente lavora con cwd in `myapp/src/` (codice), vede solo `myapp/AGENTS.md`: la wiki non interferisce.

**Questa è la separazione di responsabilità che vuoi**: il progetto sa di sé stesso, la wiki sa di sé stessa, l'agente nella wiki conosce entrambe.

### Git smart: niente sub-repo

In Scenario B (progetto già git), lo skill rileva il repo padre con `git rev-parse --is-inside-work-tree` e **salta `git init`**: i file della wiki vengono committati direttamente nel repo del progetto, senza creare una pericolosa cartella `knowledge/.git/` nested.

Risultato: `git log` mostra commit di codice e wiki nella stessa history.

### Vantaggi di tenere la wiki dentro il progetto

| Beneficio | Spiegazione |
|---|---|
| **History unificata** | `git log` vede commit di codice e wiki insieme |
| **Branch coerenti** | Una feature branch può includere sia codice che evoluzione della wiki ("aggiungo handler + documento il flusso") |
| **CI/CD può linkarli** | Pipeline che esegue `lint completo` sulla wiki quando cambia il codice rilevante |
| **Onboarding** | Un nuovo dev clona il progetto e ha subito sia il codice sia la knowledge accumulata |
| **PR ricche** | Un PR può includere "+ documento questa decisione in `knowledge/wiki/concepts/...`" |

### Quando preferire invece una wiki standalone

| Caso | Perché |
|---|---|
| Knowledge attraversa più progetti | Es. una wiki "Java auth" che copre N applicazioni del team |
| Non vuoi che la wiki finisca nei build artifact / docker image | Una sub-directory richiede `.dockerignore` esplicito |
| Il progetto è open source ma le tue note no | La tua wiki personale resta privata |
| Vuoi sperimentare senza inquinare la history del progetto | I commit "chore: ingest doc X" sarebbero rumore nei log del repo principale |

In questi casi, mantieni la wiki in una cartella separata (`~/wiki-<dominio>/`) — lo skill la rileva come Scenario A e inizializza un suo repo dedicato.

### Cosa cambia per le altre operations

Niente. INGEST, QUERY, LINT, SPEC-DRAFT, SPEC-COMPOUND, PROMOTE funzionano identici, indipendentemente dal fatto che la wiki sia in `./knowledge/` di un progetto o in una cartella standalone. I path delle source page e dei raw file restano relativi alla wiki root.

---

## Le 7 operazioni che puoi chiedere

L'agente sceglie automaticamente l'operazione giusta in base a cosa dici. Ecco la tabella di riferimento.

| Operazione | Cosa fa | Frasi che la attivano |
|---|---|---|
| **SETUP** | Inizializza la wiki da zero | "setup", "crea wiki", "inizializza" |
| **INGEST** | Aggiunge un documento alla knowledge base | path di file in `raw/`, "ingerisci", "aggiungi", "processa", "leggi questo" |
| **QUERY** | Risponde a una domanda usando la wiki | "dimmi cosa sai di X", "come funziona Y", "cerca X" |
| **LINT** | Audit della wiki (link rotti, pagine orfane, drift) | "lint", "controlla", "audit", "verifica il wiki" |
| **SPEC-DRAFT** | Crea una spec DocMind attingendo dalla wiki | "crea una spec per X", "nuova feature", "draft a spec" |
| **SPEC-COMPOUND** | Quando una spec DocMind va in DONE, porta il sapere maturato nella wiki | automatico su `spec_transition → SPEC_DONE`, oppure "esegui spec-compound per X" |
| **PROMOTE** | Pubblica una pagina wiki matura su DocMind | "promuovi", "pubblica su DocMind", "promote X" |

### SETUP

**Quando**: una sola volta, quando crei una nuova wiki per un nuovo dominio.

**Cosa devi sapere**:
- Scegli bene il **dominio**: una wiki per progetto/area tematica, non una wiki "tuttofare".
- Se hai DocMind, attiva il pre-scan: parti già con knowledge esistente importata.
- L'`AGENTS.md` generato è personalizzabile dopo (vedi *Schema Evolution* nello SKILL.md).

**Esempio**:

> *"crea una nuova wiki per il dominio backend Spring Boot + Keycloak + PostgreSQL. Le entity principali sono Keycloak, Spring Boot, PostgreSQL. I concept sono OIDC, OAuth2, JWT, Spring Security."*

### INGEST

**Quando**: hai un documento nuovo (PDF, markdown, articolo, doc DocMind) che vuoi distillare nella wiki.

**Modi per ingerirlo**:

```
1. File già in raw/        → "ingerisci raw/saml-config.md"
2. File esterno            → "ingerisci /tmp/articolo.md"  (l'agente ti chiede di copiarlo in raw/ prima)
3. Contenuto pastato       → incolla nel prompt + "ingerisci questo"
4. Documento DocMind       → "ingerisci da DocMind kc-saml-bindings"
5. Ricerca DocMind         → "cerca su DocMind 'SAML NameID' e ingerisci il più rilevante"
```

**Cosa succede**:
1. L'agente verifica/salva il file in `raw/<slug>.md` (immutabile da qui in poi).
2. Ti chiede i 3-5 takeaway principali, quali entity/concept tocca, eventuali contraddizioni con quello che è già nella wiki.
3. Crea/aggiorna `wiki/sources/<slug>.md` + entity + concept correlati.
4. Aggiorna `index.md`, `log.md`, `overview.md`.

**Output tipico**: 5-15 file wiki toccati in un colpo solo.

**Versioning**: se ingerisci due volte lo stesso documento e il contenuto è cambiato, l'agente ti propone di salvarlo come `raw/<slug>-v2.md`. La versione originale resta immutabile.

### QUERY

**Quando**: hai una domanda. Tutto. Quasi sempre.

**Forme**:

| Tipo domanda | Esempio | Output atteso |
|---|---|---|
| Definizione | *"cosa è SAML?"* | Risposta sintetica + link a concept page |
| Comparison | *"differenza tra OIDC e SAML?"* | Tabella markdown |
| Architecture | *"come è configurato il login con Keycloak qui?"* | Markdown strutturato con sezioni |
| Process | *"come si testa una migrazione DB?"* | Lista numerata o diagramma Mermaid |
| Summary | *"prepara una presentazione su Spring Security"* | Slide deck Marp |

**Dopo la risposta**, l'agente ti chiede: *"vuoi salvare come pagina wiki?"*. Se sì:
- Crea la pagina nella cartella più appropriata.
- Aggiorna entity/concept correlati con riferimenti incrociati.
- Aggiorna `index.md`, `log.md`, `overview.md`.

Le risposte salvate **compongono come quelle ingerite**: niente differenza tra "ho letto un articolo" e "ho ragionato a partire dalla wiki".

**Con DocMind**: se la wiki non basta, l'agente fa `searchFlavorChunks` automaticamente, e ti propone di ingerire la fonte trovata.

### LINT

**Quando**: ogni tanto (settimanalmente / dopo molte ingest). Fa pulizia.

I check meccanici (link rotti, source dangling, `source_file` mancanti, pagine fuori da `index.md`, orphan, pagine senza link in uscita) sono eseguiti dallo script bundled:

```bash
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_lint.py "<wiki-root>"
```

L'agente interpreta l'output, aggiunge i check semantici e produce il report unificato.

**Cosa controlla**:

| Severity | Categoria | Cosa cattura |
|---|---|---|
| 🔴 | Contradictions | Notice `⚠️ Contradiction` non ancora risolti |
| 🔴 | Dangling Source References | Slug citati ma source page mancante *(script)* |
| 🟠 | Missing Provenance | Source page con `source_file` rotto *(script)* |
| 🟠 | Orphan Pages | Pagine senza link in entrata *(script)* |
| 🟠 | Missing Pages | Termini citati 2+ volte ma senza pagina dedicata |
| 🟡 | Stale Content | Pagine probabilmente obsolete |
| 🟡 | Missing Cross-References | Link ovvi non ancora fatti |
| 🟢 | Data Gaps | Aree thinly coperte |
| 🟢 | Suggested Questions | Domande che la wiki può quasi rispondere |
| 🟡 | Stale Schema | `AGENTS.md` non riflette più la pratica |
| **DocMind-aware** | (vedi sotto) |

**Due modalità**:
- **Veloce** (default): `wiki_lint.py` + check semantici locali. Nessuna chiamata DocMind.
- **Completo**: include 6 check DocMind-aware (vedi [Integrazione DocMind](#integrazione-docmind)). Trigger esplicito: *"lint completo"* / *"audit"*.

**Cosa fai dopo**: l'agente ti chiede quali issue risolvere. Puoi anche dire *"correggi tutti i 🔴 e 🟠"*.

### SPEC-DRAFT *(richiede DocMind)*

**Quando**: stai per iniziare una feature/task formale e vuoi tracciarla con la spec workflow di DocMind.

**Cosa serve**: che la wiki abbia già contesto sull'area (altrimenti la spec partirebbe nuda).

**Esempio**:

> *"crea una spec DocMind per integrare il login SAML SP-Initiated col partner X"*

**Cosa succede**:
1. L'agente identifica entity/concept rilevanti nella wiki.
2. Compone una bozza di spec markdown attingendo da quelle pagine.
3. Ti chiede di concordare gli AC iniziali (3-7 criteri).
4. Chiama `stageDraft` + `spec_create` su DocMind.
5. Aggiunge `## Related Specs` su ogni entity/concept toccato nella wiki (backlink).
6. Aggiorna `log.md`.

**Regola d'oro**: la spec contiene **il cosa**. La wiki contiene **il perché e il come**. Le decisioni architetturali emerse durante la review della spec → vanno nelle `## Key Decisions` dell'entity, NON nel body della spec.

### SPEC-COMPOUND *(richiede DocMind)*

**Quando**: quando una spec DocMind raggiunge `SPEC_DONE`. L'agente lo propone automaticamente alla transizione di stato, ma **non scrive nulla senza la tua conferma esplicita**.

**Cosa succede dopo conferma**:
1. Fetch del contenuto finale della spec da DocMind.
2. Snapshot in `raw/spec-<uniqueName>.md` (immutabile).
3. Crea `wiki/sources/spec-<uniqueName>.md`.
4. Aggiorna le entity correlate (`## Related Specs` → `SPEC_DONE`, `## Tech Stack` se sono emerse novità).
5. Aggiorna concept se sono emersi pattern.
6. Aggiorna `index.md` + `log.md`.
7. Ti propone PROMOTE se la knowledge è chiaramente trans-progetto.

**Spec re-aperta dopo DONE**: la source page wiki originale resta immutabile; viene creato uno snapshot versionato `raw/spec-<uniqueName>-v2.md`, e la source page riceve un notice `⚠️ Spec re-opened`.

**Manual fallback**: se vuoi forzare il compounding di una spec già DONE, dì *"esegui spec-compound per <uniqueName>"*.

### PROMOTE *(richiede DocMind)*

**Quando**: una pagina wiki è diventata stabile, validata, e ha valore anche per altri progetti del team.

**Promotion threshold** (almeno una condizione):
- Pagina stabile da **≥2 settimane** (nessuna modifica sostanziale).
- Citata da **≥2 spec DONE** distinte.
- Contenuto chiaramente **trans-progetto** (pattern generale, linea guida).

**Esempio**:

> *"promuovi `wiki/concepts/multi-realm-partner-isolation.md` su DocMind"*

**Cosa succede**:
1. L'agente compone una versione "team-grade" della pagina (rimozione di riferimenti specifici al progetto, generalizzazione).
2. Ti mostra la preview e chiede conferma.
3. `stageFile` + `uploadDocument` su DocMind nel `promote_target` project.
4. Aggiunge `docmind_mirror` al frontmatter della pagina wiki.
5. Aggiorna `log.md`.

**Manutenzione**: quando modifichi una pagina con `docmind_mirror`, l'agente ti propone `updateDocument` per rinfrescare il mirror.

---

## Integrazione DocMind

DocMind è un MCP RAG con:
- **Flavors** (documenti) organizzati per **project** e taggati.
- **Search** semantico ibrido (`searchFlavorChunks`).
- **Spec workflow** formale (DRAFT → REVIEW → APPROVED → IMPLEMENTING → DONE con AC enforcement).

La skill si integra a **5 layer**, accendibili indipendentemente:

| Layer | Cosa fa | Direzione |
|---|---|---|
| 1 | Ingest da DocMind: `getFlavorByName`, `searchFlavorChunks` come fonte di INGEST | DocMind → wiki |
| 2 | Query con semantic search: fallback DocMind se la wiki non basta | DocMind → wiki |
| 3 | Mirror to DocMind: pagine wiki sync via `uploadDocument` | wiki → DocMind |
| 4 | Spec Workflow Integration: SPEC-DRAFT + SPEC-COMPOUND | bidirezionale, asimmetrico |
| 5 | Promotion to DocMind: PROMOTE con threshold e mirror maintenance | wiki → DocMind |

### Modello mentale: Hub-and-spoke

```
        ┌─────────────────────────────┐
        │       DocMind (hub)         │
        │  Flavors  •  Specs  •  Tags │
        └─────┬────────────────▲──────┘
              │ INGEST/QUERY   │ PROMOTE
              │                │ (mature pages)
              ▼                │
        ┌─────────────────────────────┐
        │     llm-wiki (spoke)        │
        │  per-progetto, locale, git  │
        └─────────────────────────────┘
```

- **DocMind = hub di team**: knowledge condivisa, cercabile, autoritativa. Lì vivono le spec ufficiali.
- **wiki = spoke personale**: distillazione veloce, navigabilità ad alta velocità con link diretti, compounding locale.

### Regola decisionale in una riga

| Domanda | Risposta → Strumento |
|---|---|
| "Ha senso anche fra 6 mesi quando il task sarà chiuso?" | Sì → wiki / No → DocMind spec |
| "È specifica del progetto o trans-progetto?" | Specifica → wiki / Trans → DocMind flavor |
| "È stato volatile (status, AC progress, assignee)?" | Sempre e solo DocMind |

### LINT DocMind-aware

Quando lanci *"lint completo"*, la skill aggiunge 6 check:

| Severity | Check | Cosa cattura |
|---|---|---|
| 🔴 | Invalid Spec Backlinks | `uniqueName` in `## Related Specs` che non esiste più su DocMind |
| 🟠 | Spec Status Drift | Stato locale ≠ stato DocMind |
| 🟠 | Missing SPEC_DONE Compounding | Spec DONE su DocMind ma snapshot wiki assente |
| 🟡 | Stale Spec Snapshot | Snapshot `raw/` ≠ flavor DocMind cambiata dopo DONE |
| 🟡 | Promotion Candidates | Pagine che soddisfano il threshold ma non promosse |
| 🟡 | Mirror Drift | Pagine con `docmind_mirror` modificate dopo `lastPushedAt` |

### DocMind offline?

Tutto funziona in **local-only mode**. SETUP/INGEST/QUERY/LINT (parte locale)/SPEC-COMPOUND restano operative. L'agente ti avvisa una volta per sessione che DocMind non risponde, e prosegue.

---

## Convenzioni di base

### Tre tipi di pagina

| Tipo | Cartella | Risponde a |
|---|---|---|
| **Entity** | `wiki/entities/` | *Cosa è? Cosa fa? Come si relaziona?* |
| **Concept** | `wiki/concepts/` | *Cosa è questa idea? Perché conta? Dove si applica?* |
| **Source** | `wiki/sources/` | *Cosa diceva questo documento? Cosa ne abbiamo imparato?* |

**Regola pratica**: concetti astratti vanno in `concepts/`, sistemi/tool/API concrete in `entities/`.

### Esempi reali

- **Entity**: Keycloak, Spring Boot, PostgreSQL, "Servizio Pagamenti V2"
- **Concept**: OIDC, JWT, "SAML SP-Initiated SSO", "Multi-tenancy"
- **Source**: ogni doc tecnico che hai ingerito, ogni spec DocMind DONE, ogni risposta salvata

### File naming

- Tutti i file: `kebab-case.md` (minuscolo, parole separate da trattini).
- Cross-references: **link markdown relativi**: `[Keycloak](../entities/keycloak.md)`.
- **Mai** wikilink Obsidian (`[[foo]]`): rovinano la portabilità.

### Frontmatter (tutte le pagine wiki)

```yaml
---
title: "Page Title"
category: entity | concept | source | overview
tags: [tag1, tag2]
sources: [source-slug-1]
created: YYYY-MM-DD
updated: YYYY-MM-DD
# Opzionale, solo se la pagina è stata promossa su DocMind:
docmind_mirror:
  project: <docmind-project>
  uniqueName: <docmind-flavor-unique-name>
  lastPushedAt: YYYY-MM-DD
---
```

### Cosa NON modificare a mano

- **`raw/`**: tutto immutabile. Le source originali non si toccano mai. Se serve una versione nuova, la skill crea `<slug>-v2.md` accanto all'originale.
- **`raw/spec-<uniqueName>.md`**: anche gli snapshot di spec DONE sono immutabili.

### Cosa puoi tranquillamente modificare a mano

- Tutte le pagine in `wiki/entities/`, `wiki/concepts/`: vivono e crescono.
- `wiki/index.md`, `wiki/log.md`, `wiki/overview.md`: puoi correggere refusi.
- `AGENTS.md`: è il manuale di questa wiki specifica, va aggiornato quando le convenzioni evolvono.

### Promotion threshold (per pagine entity/concept ↔ DocMind)

Una pagina si "promuove" a DocMind quando soddisfa almeno una di:
- Stabile da ≥2 settimane.
- Citata da ≥2 spec DONE.
- Contenuto trans-progetto evidente.

---

## Esempio: una settimana di sviluppo

Scenario: devo integrare il login SAML SP-Initiated con un partner esterno.

### Lunedì mattina — Esplorazione

> *"dimmi cosa sai di Keycloak SAML"*

La skill legge la wiki, trova `wiki/concepts/saml.md`, `wiki/entities/keycloak.md`, le 3 source page sui doc Keycloak SAML già ingeriti. Risposta in 30 secondi.

### Lunedì pomeriggio — Manca un pezzo

La wiki non copre la modalità "SP-Initiated con NameID Format = persistent".

> *"cerca su DocMind 'SAML NameID persistent'"*

DocMind trova `kc-saml-nameid-formats`. La skill mi chiede se ingerirlo: sì.

Risultato: `raw/kc-saml-nameid-formats.md` (immutabile), `wiki/sources/kc-saml-nameid-formats.md`, aggiornamento di `wiki/concepts/saml.md` con la nuova sezione.

### Martedì — Creo la spec su DocMind

> *"crea una spec DocMind per l'integrazione SAML SP-Initiated col partner X"*

La skill compone la spec attingendo dalla wiki, mi fa concordare 4 AC, chiama `spec_create`. Aggiunge `## Related Specs` a `keycloak.md` e `saml.md`.

### Mercoledì — Review architetturale

Decisione: separare il realm Keycloak per il partner. È una **decisione architetturale di lungo periodo**, quindi:
- Va in `wiki/entities/keycloak.md` sotto `## Key Decisions`.
- **NON** va nel body della spec DocMind (che linka la decisione).
- Spec transition: DRAFT → REVIEW → APPROVED.
- `spec_update_plan` per scrivere l'implementation plan.

### Giovedì — Implementazione

Spec a `SPEC_IMPLEMENTING`. Mentre programmo, scopro un bug: il `KeycloakSpringBootConfigResolver` confligge con `OAuth2ClientAutoConfiguration` di Spring Boot.

> *"salva questo bug nella wiki"*

La skill aggiorna `wiki/entities/spring-boot.md` sotto `## Problems & Solutions`, con sintomo, root cause, fix, e link alla spec come "discovered while".

Questa knowledge resta utile anche tra 6 mesi, ben dopo che la spec sarà chiusa.

### Venerdì — Done

Tutti gli AC verdi. `spec_transition` → `SPEC_DONE`. La skill propone automaticamente SPEC-COMPOUND. Confermo.

- Snapshot in `raw/spec-pw-saml-partner-x.md`.
- Source page `wiki/sources/spec-pw-saml-partner-x.md` con takeaway.
- Update di `keycloak.md` (tech stack + `## Related Specs` → `SPEC_DONE`).
- Update di `saml.md` (`## Where Applied`).
- Log entry.

Poi: *"la decisione multi-realm è un pattern che può servire ad altri progetti, vuoi promuoverla?"*. Sì → PROMOTE → `uploadDocument(project=org-patterns, ...)` → `docmind_mirror` nel frontmatter.

**Fine settimana, knowledge consolidata, niente perso.**

---

## FAQ

### Posso avere più wiki contemporaneamente?

Sì, una per progetto/dominio. Ognuna ha il suo `AGENTS.md` con il proprio `## DocMind Binding`. Le wiki sono autonome e indipendenti.

### Posso usare la skill senza DocMind?

Sì. Layer 1-5 sono **opzionali**. Le operations SETUP, INGEST, QUERY, LINT (parte locale) funzionano in *local-only mode* senza degradazione. Perdi solo le operations SPEC-DRAFT, SPEC-COMPOUND, PROMOTE e le 6 LINT check DocMind-aware.

### La skill cancella file?

**Mai** in `raw/`. Le source sono immutabili per principio. In `wiki/` può eliminare pagine solo su tua conferma esplicita (es. LINT che propone di rimuovere un'orphan page).

### Cosa succede se cambio idea su una source ingerita?

Niente: l'ingest non è distruttivo. Puoi ri-ingerirla con discussione diversa, oppure modificare le pagine wiki a mano. La source originale in `raw/` resta come traccia storica.

### Posso usare git per fare branch / merge?

Sì. La wiki è solo file markdown in una cartella git. Tutti i workflow git standard funzionano. SETUP fa il primo commit per te.

### Cosa significa "promozione" di una pagina?

Significa pubblicarla su DocMind come flavor (documento ufficiale). Da quel momento è cercabile via `searchFlavorChunks` da chiunque nel team. Il frontmatter `docmind_mirror` traccia il legame e LINT segnala se la pagina locale ha drift rispetto al mirror.

### Le spec DocMind sono come issue di Jira/Linear?

Concettualmente simili (lifecycle, AC, plan, dipendenze, assignee). DocMind però ha contenuto markdown ricco e si integra nativamente col grafo flavors, quindi è più "Notion + Linear" che "Jira puro".

### Quando una decisione va in wiki vs in spec?

Regola: **knowledge persistente → wiki, work item con lifecycle → spec**.
- "Abbiamo scelto SAML perché..." → wiki `## Key Decisions` (vivrà per sempre).
- "Implementare login SAML, AC: [...], status: APPROVED" → DocMind spec (vita = durata del task).

### Posso modificare l'`AGENTS.md` della mia wiki?

Sì, è incoraggiato. La sezione "Schema Evolution" dello SKILL.md dice esplicitamente che `AGENTS.md` deve crescere con la wiki: quando le convenzioni cambiano (nuovi page type, naming rules, workflow), aggiornalo. LINT 🟡 Stale Schema segnala drift.

### Quante pagine può raggiungere una wiki?

Nessun limite hard. Karpathy nel doc originale parla di wiki personali con centinaia di pagine, perfettamente funzionanti. Una wiki cresce bene se ogni ingest tocca **molte** pagine (5-15 per source): questo crea il grafo. Se ogni source resta isolata, hai solo un archivio piatto, non una wiki.

---

## Troubleshooting

### "L'agente non riconosce il trigger"

Verifica di aver detto qualcosa di abbastanza vicino ai trigger noti (vedi tabella in [Le 7 operazioni](#le-7-operazioni-che-puoi-chiedere)). Se sei in dubbio, dì esplicitamente *"esegui INGEST"* / *"esegui QUERY"* / ecc.

### "L'agente sta per scrivere troppi file"

Buon segno: significa che la source ha molto contenuto rilevante. Ogni ingest può legittimamente toccare 5-15 file. Se 30+ qualcosa è strano: rivedi se hai chiesto un INGEST quando in realtà ti serviva QUERY.

### "L'agente vuole modificare un file in `raw/`"

Non glielo lasciar fare. È una violazione del principio di immutabilità. Se vuoi davvero salvare una versione nuova del documento, fai un nuovo INGEST: il versioning check creerà `<slug>-v2.md` automaticamente.

### "DocMind risponde lentamente / non risponde"

L'agente dovrebbe avvisarti una volta per sessione e proseguire in local-only mode. Se non lo fa, dì esplicitamente *"procedi in local-only mode"*.

### "LINT è lentissimo"

Stai probabilmente in modalità completo. Per check rapidi quotidiani usa il default (*"lint"* normale). Riserva *"lint completo"* per audit periodici (es. settimanali).

### "Ho fatto SPEC-COMPOUND ma vedo una source page strana"

SPEC-COMPOUND crea `wiki/sources/spec-<uniqueName>.md` con tag `[spec, ...]` e frontmatter `docmind_spec`. È una variante normale della source page standard, non un bug. Vedi sezione "Variant: Spec source page" nello SKILL.md.

### "Una spec è tornata in REVIEW dopo essere stata DONE"

Lo SKILL.md gestisce questo caso: la source page wiki resta immutabile, e al prossimo DONE viene creato `raw/spec-<x>-v2.md` con una nuova source page versionata. La source originale riceve un notice `⚠️ Spec re-opened`.

### "Voglio un rollback completo della skill"

I file `.bak-YYYYMMDD-HHMMSS` accanto a `SKILL.md` sono backup automatici creati ad ogni modifica strutturale. Per rollback:

```bash
cd ~/.agents/skills/llm-wiki-manager
ls SKILL.md.bak-*           # lista backup
cp SKILL.md.bak-<scegli> SKILL.md
```

---

## Approfondimenti

- **Manuale operativo per l'agente**: [`SKILL.md`](SKILL.md) — leggilo se vuoi capire **esattamente** cosa fa l'agente in ogni step.
- **Background concettuale**: [`references/llm-wiki-karpathy.md`](references/llm-wiki-karpathy.md) — il post originale di Andrej Karpathy sul pattern LLM wiki: i tre layer (raw / wiki / schema), le operazioni, la filosofia.
- **Esempio di wiki reale**: una wiki ben tenuta vive in qualche progetto privato; chiedi all'agente *"mostrami un esempio di entity page ben strutturata"* per vedere il template applicato.

---

## Cheat sheet (stampa e tieni accanto al monitor)

```
SETUP            "crea una wiki per <dominio>"
INGEST           "ingerisci <file/path/DocMind name>"
QUERY            "dimmi cosa sai di <X>"
LINT             "lint" (veloce) / "lint completo" (con DocMind)
SPEC-DRAFT       "crea una spec per <task>"
SPEC-COMPOUND    automatico su SPEC_DONE; manual: "esegui spec-compound per <uniqueName>"
PROMOTE          "promuovi <pagina>"

REGOLE D'ORO:
- 6 mesi rule: ha senso fra 6 mesi? → wiki, no? → spec
- Trans-progetto? → DocMind, project? → wiki
- Stato volatile? → solo DocMind
- raw/ è IMMUTABILE — non si tocca mai

PAGE TYPES:
- entities/   → sistemi, tool, API, progetti (concreti)
- concepts/   → pattern, principi, protocolli (astratti)
- sources/    → sintesi di ogni documento ingerito
```
