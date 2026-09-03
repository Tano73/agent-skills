---
name: mineru-pdf-to-md
description: >
  Converte PDF e immagini in Markdown ad alta fedeltà usando MinerU con il modello VLM
  MinerU2.5-Pro (opendatalab/MinerU2.5-Pro-2604-1.2B), preservando layout, tabelle, formule
  ed estraendo le immagini. Usa SEMPRE questa skill quando l'utente vuole "convertire un PDF
  in Markdown", "estrarre il testo da un PDF", "parsare/leggere un PDF", "pdf to md",
  "OCR di un documento scansionato", "trasformare una scansione in testo", oppure quando
  nomina esplicitamente "MinerU", "MinerU2.5", "magic-pdf" o "mineru". Attiva anche quando
  l'utente chiede di rendere un PDF (paper, manuale, capitolato, bilancio, contratto)
  processabile da un LLM, indicizzabile per RAG o leggibile come testo, anche senza dire
  "Markdown". NON usare per: convertire DOCX/HTML/EPUB tra formati testuali (usa
  pandoc-convert), generare un PDF a partire da Markdown, compilare o unire PDF, o
  spezzare un Markdown già esistente in capitoli (usa markdown-chapter-splitter).
---

# MinerU PDF → Markdown

MinerU converte documenti a layout complesso in Markdown pulito. Il suo modello di punta è
**MinerU2.5-Pro-2604-1.2B**, un VLM che legge la pagina come immagine e ne ricostruisce la
struttura: ordine di lettura, tabelle in HTML, formule in LaTeX, figure ritagliate su file.

Questo lo rende adatto dove un estrattore di testo tradizionale fallisce — PDF a due colonne,
scansioni, paper scientifici, capitolati con tabelle annidate — ma comporta un vincolo
concreto: **il VLM ha bisogno di una GPU o di un server remoto**. Il primo compito della
skill è quindi capire dove può girare, non lanciare subito la conversione.

**Script:**
- `$HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_env.py` — diagnosi ambiente e installazione
- `$HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_convert.py` — conversione, normalizzazione output, report qualità

---

## Fase 0 — Diagnosi dell'ambiente

Esegui sempre questo comando prima di qualsiasi conversione. È veloce e determina tutto il resto:

```bash
python3 $HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_env.py check
```

Lo script rileva GPU CUDA, Apple Silicon, un eventuale server VLM (variabili d'ambiente
`MINERU_SERVER_URL` o `MINERU_VLM_SERVER_URL`) e la presenza di `mineru`, poi raccomanda un backend.

| Situazione rilevata | Backend scelto | Usa MinerU2.5-Pro? |
|---|---|---|
| Server OpenAI-compatibile raggiungibile | `vlm-http-client` | Sì, in remoto |
| GPU CUDA ≥ 8 GB VRAM o Apple Silicon | `hybrid-auto-engine` | Sì, in locale |
| Solo CPU, nessun server | `pipeline` | **No** |

### Il caso CPU va dichiarato all'utente

Se la raccomandazione è `pipeline`, la conversione funzionerà comunque — MinerU ha una pipeline
classica (layout detection + OCR) che gira bene su CPU — ma **MinerU2.5-Pro non viene usato**, e
tabelle e formule risultano sensibilmente più deboli. Siccome l'utente ha probabilmente chiesto
proprio quel modello, non silenziare la differenza: spiega il fallback e presenta le alternative
reali (procedere con `pipeline`, puntare a un server remoto con `--server-url`, oppure forzare
`vlm-auto-engine` su CPU, che usa davvero MinerU2.5-Pro ma impiega diversi minuti a pagina).

---

## Fase 1 — Installazione, se serve

Se `mineru_env.py check` riporta `mineru: not installed`, **chiedi conferma prima di installare**:
l'installazione crea un virtualenv in `~/.mineru-venv` e scarica pacchetti che nel profilo GPU
pesano diversi GB.

Mostra all'utente cosa verrà fatto:

```bash
python3 $HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_env.py install --profile auto --dry-run
```

Poi, dopo l'ok, esegui senza `--dry-run`. I profili corrispondono ai backend:

| Profilo | Pacchetti | Peso indicativo | Per |
|---|---|---|---|
| `client` | `mineru` | pochi MB | `vlm-http-client` verso un server remoto |
| `pipeline` | `mineru[pipeline]` | ~2 GB | CPU locale, backend `pipeline` |
| `gpu` | `mineru[core,vllm]` | diversi GB | VLM locale con GPU |

Al primo avvio MinerU scarica anche i pesi del modello da Hugging Face. Se la rete blocca HF,
imposta `MINERU_MODEL_SOURCE=modelscope`.

---

## Fase 2 — Conversione

Un solo comando per il caso normale:

```bash
python3 $HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_convert.py "<input.pdf>"
```

Lo script sceglie il backend (`--backend auto`), lancia `mineru`, appiattisce l'output e
produce il report qualità. Stampa sempre il comando `mineru` che sta eseguendo, così l'utente
vede cosa succede davvero.

### Layout dell'output

MinerU scrive un albero annidato con parecchi artefatti di debug. Lo script normalizza a:

```
<cartella-del-pdf>/<nome>-md/
├── <nome>.md
└── images/          # figure e tabelle ritagliate, referenziate dal Markdown
```

Il Markdown referenzia le immagini con path relativi `images/…`, quindi la cartella va spostata
insieme al `.md`. Usa `-o <dir>` per una destinazione diversa e `--keep-raw` se servono anche
`middle.json`, `content_list.json` e i PDF di visualizzazione layout.

### Opzioni utili

| Opzione | Quando |
|---|---|
| `-o <dir>` | destinazione diversa dal default accanto al sorgente |
| `-b <backend>` | forzare un backend contro la raccomandazione automatica |
| `--server-url http://host:30000` | server VLM non esposto via variabile d'ambiente |
| `-s N -e M` | solo le pagine da N a M (0-based) — utile per provare un documento lungo |
| `--lang <script>` | solo per script non latini, e solo con backend `pipeline` |
| `--keep-raw` | conservare JSON intermedi per elaborazioni successive |
| `--json` | output strutturato, utile se devi incatenare altri passi |

### Lingua e OCR

Italiano e inglese **non richiedono `--lang`**: lo script latino è il default. Il flag serve solo
per cinese, coreano, arabo, cirillico, greco, thai, devanagari e simili, ed è ignorato dai backend
`vlm-*` (il VLM riconosce la lingua da solo). Se l'utente chiede "OCR in italiano", rassicuralo:
non serve nessuna opzione.

### Documenti lunghi

Prima di lanciare un PDF da centinaia di pagine, converti un campione con `-s 0 -e 4` e mostra
il risultato. Se il campione è buono si prosegue; se no si è risparmiato molto tempo. Su CPU con
backend `pipeline` conta indicativamente qualche secondo a pagina, con `vlm-auto-engine` minuti.

---

## Fase 3 — Verifica e consegna

Il report qualità viene stampato automaticamente. Non limitarti a incollarlo: **interpretalo**.

```
=== MinerU quality report ===
Characters:     23,926
Pages:          84 with content / 85 requested (source has 85)
Text coverage:  14% of the source text layer
Tables:         17 HTML + 0 Markdown
Formula blocks: 12
Images:         14 referenced, 0 missing
  ! CONTENT LOST on 1 page(s): [3] — the source has text there but the parse produced nothing
  ! only 14% of the text in the source's own text layer made it into the Markdown
```

Il controllo più importante è **Text coverage**: se il PDF ha un proprio layer di testo, lo script
lo estrae e lo usa come metro di paragone. Una copertura del 14% significa che sei sesti del
documento non sono arrivati nel Markdown, e nulla nell'exit status di `mineru` lo direbbe. Il dato
compare solo quando esiste un riferimento: per una scansione (layer di testo vuoto) non ha senso e
viene omesso, quindi la sua assenza non è una promozione. Serve `pypdf` importabile dal `python3`
di sistema; se manca, il controllo si disattiva in silenzio e resta solo la densità di testo.

Cosa fare per ciascun segnale:

- **`CONTENT LOST`** — pagine che nel sorgente contengono testo ma nel Markdown no. È il segnale
  più grave: c'è perdita reale. Se sono poche, riconvertile da sole (`-s 17 -e 17`) e reinseriscile
  al posto giusto: spesso al secondo tentativo escono, e consegnare un documento completo vale la
  spesa di un comando in più. Se non escono nemmeno così, dillo invece di consegnare in silenzio.
- **Copertura < 60%** — stesso discorso su scala di documento. Il file non è affidabile per RAG.
  Attenzione a non liquidarlo come "è il backend `pipeline`, si sa che è più debole": `pipeline`
  perde qualità su tabelle e formule, non i cinque sesti del testo. Una copertura del 15% significa
  che qualcosa è rotto — installazione incompleta, PDF protetto, pagine renderizzate come immagini
  — e indicare la causa sbagliata manda l'utente a comprare una GPU per un problema che non è quello.
- **Pagine vuote anche nel sorgente** — frontespizi e separatori: rumore, non problema. Lo script
  lo distingue da solo, non serve che tu riapra il PDF.
- **Markdown quasi vuoto** (< 200 caratteri) — quasi sempre una scansione che il backend non ha
  letto: con `pipeline` verifica che l'OCR sia attivo, meglio ancora passa a un backend VLM.
- **Immagini mancanti** — la cartella `images/` non è stata copiata o è stata spostata senza il
  `.md`. Verifica il percorso.
- **Densità di testo bassa** — segnalata solo quando manca un riferimento di copertura. Apri il
  Markdown e confronta una pagina con l'originale.
- **Avviso backend `pipeline`** — ricordalo nel messaggio finale, così l'utente sa che la qualità
  su tabelle e formule non è quella di MinerU2.5-Pro.

Prima di attribuire un difetto alla conversione, controlla il sorgente. È facile scambiare per
errore di parsing qualcosa che era già così nell'originale — una parola senza accento, una tabella
storta, una sigla strana — e segnalare difetti inesistenti erode la fiducia nel report tanto
quanto tacere quelli veri.

Confronta anche il profilo del documento con come l'utente te l'ha descritto. Se ha parlato di un
capitolato pieno di tabelle e il report ne conta due, o se il titolo estratto non c'entra con
quello che si aspettava, quasi sempre ha indicato il file sbagliato — una copia vecchia, un
download interrotto, un omonimo nella cartella. Dirglielo prima che costruisca qualcosa sopra il
file sbagliato vale molto più che consegnare in silenzio.

Per rifare solo il controllo su un output già prodotto:

```bash
python3 $HOME/.agents/skills/mineru-pdf-to-md/scripts/mineru_convert.py \
  --check-only "<dir>-md" --source "<input.pdf>"
```

Chiudi comunicando: percorso del `.md`, backend usato, se MinerU2.5-Pro è stato coinvolto, e le
eventuali anomalie con la tua interpretazione.

---

## Errori frequenti

| Sintomo | Causa e rimedio |
|---|---|
| `mineru not found` | Non installato o venv diverso: Fase 1, oppure `--venv <path>` |
| `backend … needs a server URL` | Backend http-client senza endpoint: passa `--server-url` |
| `mineru produced no Markdown` | Parsing fallito a monte: rilancia con `--keep-raw` e leggi l'output di `mineru` |
| Download modello lentissimo o in errore | `export MINERU_MODEL_SOURCE=modelscope` |
| OOM / processo killato su CPU | `vlm-auto-engine` non sta nella RAM: usa `pipeline` o un server remoto |
| PDF protetto da password | MinerU non lo apre: chiedi all'utente una copia senza protezione |

---

## Confini con le altre skill

- **pandoc-convert** — conversioni tra formati testuali strutturati (DOCX, HTML, EPUB, MD). Un
  DOCX ha già la struttura: non serve un VLM.
- **markdown-chapter-splitter** — parte da un Markdown esistente. Se l'utente vuole convertire
  *e poi* spezzare in capitoli, questa skill produce il `.md` e l'altra lo divide.
- **docling** — parser alternativo. Se MinerU non è installabile nell'ambiente e l'utente ha
  fretta, docling è un ripiego ragionevole: dillo invece di insistere.
