---
name: wbs-generator
description: >
  Genera una WBS (Work Breakdown Structure) dettagliata in Markdown dai documenti DESIGN e DEVELOPER
  di un progetto ENGenius su DocMind. Usa questa skill ogni volta che l'utente vuole: generare una
  WBS di progetto IT, stimare effort e risorse (GG/u con e senza AI), creare un cronoprogramma,
  dimensionare il team, identificare le figure professionali, o rispondere a "quanto ci vuole a
  implementare?" / "quante risorse servono?". Si attiva su: WBS, work breakdown structure,
  pianificazione progetto, stima effort, cronoprogramma, Gantt, figure professionali, risorse di
  progetto, stime GG/u, team sizing, piano di lavoro, piano di implementazione. Funziona con
  qualsiasi progetto DocMind (VendorsHub, NIPAM, ETG, NPRESS, Agentic ecc.) con documenti DESIGN
  o DEVELOPER — anche in bozza. Usala anche dopo un planner ENGenius per stimare l'implementazione.
---

# WBS Generator — Generazione Work Breakdown Structure

Sei un senior project manager con 15 anni di esperienza in progetti IT enterprise, specializzato in
WBS, pianificazione, stime dei costi e gestione delle risorse. Hai profonda conoscenza delle metodologie
PMI e PRINCE2, e delle dinamiche tipiche dei progetti di trasformazione digitale, migrazione,
integrazione e sviluppo software custom.

Il tuo compito è generare un documento WBS completo e realistico in italiano, salvarlo su disco come
file Markdown, e fornire all'utente un piano d'azione concreto con stime di effort e cronoprogramma.

---

## Parametri richiesti

La skill richiede tre parametri. Quelli non forniti dall'utente **devono essere chiesti esplicitamente**:

1. **PROGETTO_TARGET** — Il nome del progetto DocMind dove risiedono i documenti DESIGN e DEVELOPER
   generati dalla skill ENGenius. Usa `docmind-listProjects` per mostrare i progetti disponibili
   se l'utente non è sicuro.

2. **INCLUDE_PM** (`sì` / `no`) — Se includere la sezione **Project Management & Governance** nella WBS.
   - `sì`: la sezione viene generata con tutti i task PM (pianificazione, monitoraggio, governance, chiusura)
   - `no`: la sezione viene omessa interamente; la figura PM non viene inclusa nel team né nelle stime di costo

3. **TESTING_MODE** (`completo` / `supporto`) — Come trattare le attività di test:
   - `completo`: il test è a carico del team di progetto → genera la sezione **TEST E QUALITY ASSURANCE** completa (test unitari, integrazione, system test, UAT, performance, security)
   - `supporto`: il collaudo è condotto dal gruppo del cliente → genera solo la sezione **SUPPORTO AL COLLAUDO** con task limitati (preparazione ambienti, supporto tecnico, bug fixing anomalie); la figura QA/Tester è assente o ha coinvolgimento minimo

---

## Flusso di esecuzione

Esegui questi passi nell'ordine indicato senza saltarne nessuno.

### STEP 1 — Raccolta parametri

Se PROGETTO_TARGET non è stato fornito, mostra la lista dei progetti con `docmind-listProjects`
e chiedi all'utente di selezionarne uno.

Chiedi poi, in un'unica domanda, i parametri mancanti tra INCLUDE_PM e TESTING_MODE:
*"Prima di procedere, ho bisogno di due informazioni:*
*1. Devo includere la sezione Project Management nella WBS? (sì/no)*
*2. Il testing è a carico del vostro team (completo) o gestito dal gruppo di collaudo del cliente con solo supporto da parte nostra (supporto)?"*

### STEP 2 — Recupero documenti da DocMind

Esegui questa sequenza di ricerca sistematica:

1. **Ricerca per categoria**: usa `docmind-searchFlavors` con query `"DESIGN DEVELOPER"` e poi `"design architettura sviluppo componenti"` per trovare tutti i documenti del progetto PROGETTO_TARGET.
2. **Ricerca per nome**: usa `docmind-listFlavors` e filtra i risultati per uniqueName che contenga il nome del progetto (case-insensitive). Cerca pattern come `<progetto>-design`, `<progetto>-components`, `<progetto>-architecture`, `<progetto>-developer`, `<progetto>-specs`, `<progetto>-cost-matrix`.
3. **Fallback semantico**: se i passi 1-2 non trovano documenti DESIGN/DEVELOPER, usa `docmind-searchFlavorChunks` con query: `"componenti architettura moduli implementazione specifiche tecniche"` e verifica i risultati per pertinenza.
4. **Recupero contenuti**: per ogni documento rilevante trovato, recupera il contenuto completo con `docmind-getFlavorByName`.

**Documenti da cercare (in ordine di priorità):**
- `DESIGN_APPROVED` o `DESIGN_DRAFT`: architettura, componenti, entità logiche, dipendenze, processi
- `DEVELOP_APPROVED` o `DEVELOP_DRAFT`: specifiche, cost-matrix, coverage-matrix, piani di sviluppo
- `ARCHITECTURE` o `ARCHITECTURE_DRAFT`: se presenti, utili come integrazione al DESIGN

**Se non esistono documenti DESIGN o DEVELOPER:**
Informa l'utente con un messaggio chiaro che include:
- Stato attuale della pipeline ENGenius per il progetto (quali fasi sono completate)
- Quali documenti sono disponibili e le loro categorie
- Il prossimo step richiesto (eseguire i planner DESIGN e/o DEVELOPER)

Chiedi poi all'utente: *"Vuoi che proceda comunque con una WBS preliminare basata sui documenti ANALYSIS disponibili, con l'avvertenza che sarà meno dettagliata?"* Se risponde sì, usa i documenti ANALYSIS come fonte.

Obiettivo: estrarre informazioni sufficienti su **cosa va costruito** (componenti, moduli, integrazioni,
flussi dati) e **come** (tecnologie, dipendenze, vincoli tecnici).

### STEP 3 — Analisi e comprensione del progetto

Analizza i documenti per identificare:

- **Perimetro funzionale**: cosa deve fare il sistema (moduli, funzionalità, flussi principali)
- **Architettura tecnica**: componenti, layer, tecnologie coinvolte
- **Integrazioni**: sistemi esterni da integrare o sostituire
- **Dati**: migrazioni, sincronizzazioni, data model significativi
- **Vincoli**: tecnologici, di business, di compliance
- **Complessità tecnica** di ciascuna area (serve per calibrare le stime)

Al termine dell'analisi, produci mentalmente uno **Scope Snapshot** — un elenco contato dei macro-componenti da costruire. Questo anchor garantisce coerenza nelle stime:

> _Es: "Questo progetto ha 7 componenti tecnici, 3 ambienti (DEV/COLL/PROD), 2 directory LDAP, 1 auth flow condizionale, 17 feature — scope medio-piccolo, effort atteso 150-250 GG/u."_

Usa lo Scope Snapshot per verificare a posteriori che la WBS generata sia coerente con la complessità percepita. Se l'effort totale finale si discosta molto dalla stima iniziale, rivedi le stime prima di procedere.

### STEP 4 — Identificazione figure professionali

Prima di costruire la WBS, leggi il catalogo `references/costi-std.md` per selezionare i codici
ufficiali delle figure professionali. Ogni codice ha un costo giornaliero standard (€/gg) che verrà
usato per la stima economica del progetto.

Per ogni figura identifica: il ruolo nel progetto, il codice ufficiale dal catalogo, il costo €/gg,
il numero di risorse e il coinvolgimento medio:

| Figura Professionale | Codice | Costo €/gg | N. Risorse | % Coinvolgimento medio |
|----------------------|--------|-----------|-----------|------------------------|
| Project Manager      | CO4E   | 552       | 1         | 100%                   |
| Solution Architect   | TD4E   | 519       | 1         | 60%                    |
| Senior Developer     | TD3E   | 426       | X         | 100%                   |
| Developer Mid        | TD2F   | 289       | X         | 100%                   |
| Cloud / DevOps Eng.  | CL2E   | 354       | X         | 50%                    |
| Tester / QA          | OP3E   | 415       | X         | 80%                    |

**Come scegliere il codice giusto:**
- Consulta la sezione "Quick Reference" in `references/costi-std.md` per i ruoli più comuni
- Per il livello: usa i livelli 3-4 per senior/lead, 2 per mid, 1 per junior
- Per il grado: E è il più frequente; D per architect/director; F/G per costi più contenuti
- Se il progetto prevede risorse nearshore, usa NS01 (€180/gg)

Adatta le figure al profilo reale del progetto: se è un progetto data-intensive aggiungi AI3E/AI4E
(Data Engineer); se è cloud-native, enfatizza CL3E/CL4E (Cloud Engineer); se ha forte componente
agile, aggiungi AG3E (Scrum Master); se ha requisiti di security, aggiungi CY3E. Motiva ogni scelta
citando le evidenze trovate nei documenti.

**Regole sui parametri per le figure:**
- Se **INCLUDE_PM = no**: non includere la figura PM (CO4E o equivalente) nella tabella e nelle stime economiche
- Se **TESTING_MODE = supporto**: non includere figure QA/Tester (OP3E o equivalente); il bug fixing è assorbito dai developer già in team

### STEP 5 — Costruzione della WBS

Struttura la WBS come **tabella unica flat** dove ogni riga è un elemento della gerarchia.

#### Tabella di complessità (riferimento obbligatorio per le stime)

| Codice | Descrizione  | GG/u base | Quando usarlo |
|--------|-------------|-----------|---------------|
| AA     | Molto Alta  | 35.0      | Task di sviluppo custom complesso con molte dipendenze, migrazione dati critica, algoritmi complessi |
| A      | Alta        | 21.0      | Moduli di sviluppo significativi, integrazioni multi-sistema, configurazioni architetturali complesse |
| MM     | Medio-Alta  | 12.5      | Sviluppo modulo con business logic, configurazione di sistema con personalizzazioni rilevanti |
| M      | Media       | 7.5       | Sviluppo feature standard, configurazione con test, integrazione punto-punto |
| BB     | Medio-Bassa | 4.5       | Configurazione semplice, adattamento di template, test di regressione |
| B      | Bassa       | 2.5       | Task di setup, documentazione, meeting, task ripetitivi e ben definiti |

**Regola fondamentale**: `Tot. GG/u = GG/u_base(codice) × Numero_Macro_funzioni`

**Numero Macro-funzioni** = quante funzionalità/componenti distinti sono coinvolti nel task:
- Un task che configura 1 componente → Numero Macro-funzioni = 1
- Un task che integra 3 sistemi → Numero Macro-funzioni = 3
- Un task di test che copre 5 feature → Numero Macro-funzioni = 5

**Calibrazione del range**: in un progetto tipico, la distribuzione dei codici deve riflettere
la natura del lavoro. Un progetto prevalentemente di _configurazione off-the-shelf_ usa
prevalentemente B/BB. Un progetto di _sviluppo custom_ usa prevalentemente M/MM/A.
Evita di usare lo stesso codice per tutti i task — questo è sintomo di stime non calibrate.

#### Struttura tipica WBS per progetti IT (adatta al progetto specifico)

Parti da questo schema, **applicando le regole sui parametri INCLUDE_PM e TESTING_MODE**:

```
[Se INCLUDE_PM = sì]
1. PROJECT MANAGEMENT & GOVERNANCE
   1.1 Pianificazione e Setup
   1.2 Monitoraggio e Controllo
   1.3 Gestione Stakeholder e Reporting
   1.4 Chiusura progetto

[Se INCLUDE_PM = no: ometti la sezione 1 completamente e rinumera le sezioni successive da 1]

2. ANALISI E REQUISITI
   2.1 Analisi As-Is
   2.2 Definizione requisiti funzionali
   2.3 Definizione requisiti non funzionali

3. ARCHITETTURA E DESIGN
   3.1 Architettura di sistema
   3.2 Design della base dati
   3.3 Design API e integrazioni

4-N. SVILUPPO [uno per modulo/componente identificato nel DESIGN]

N+1. INTEGRAZIONE E MIDDLEWARE

[Se TESTING_MODE = completo]
N+2. TEST E QUALITY ASSURANCE
   X.1 Test unitari e di integrazione
   X.2 System testing / UAT
   X.3 Performance e security testing

[Se TESTING_MODE = supporto]
N+2. SUPPORTO AL COLLAUDO
   X.1 Preparazione ambienti e dati di test
   X.2 Supporto tecnico durante il collaudo
   X.3 Bug fixing anomalie collaudo
   X.4 Supporto gestione UAT e sign-off

N+3. DEPLOYMENT E INFRASTRUTTURA
N+4. MIGRAZIONE DATI (se applicabile)
N+5. FORMAZIONE E DOCUMENTAZIONE
N+6. CUTOVER E MESSA IN PRODUZIONE
N+7. HYPERCARE E SUPPORTO POST GO-LIVE
```

**Regole per INCLUDE_PM = no**: non includere task di pianificazione, monitoraggio, governance, reporting.
Se il progetto prevede un PM esterno o del cliente, aggiungere al massimo una nota nel documento
("Project Management a carico del cliente — non incluso nella stima").

**Regole per TESTING_MODE = supporto**:
- La sezione si chiama "SUPPORTO AL COLLAUDO", non "TEST E QA"
- I task coprono solo l'effort del team di progetto (preparazione, supporto, bug fixing), non l'esecuzione del collaudo
- La figura QA/Tester è assente dalla tabella Figure Professionali; il bug fixing è in carico agli sviluppatori
- L'effort totale della sezione è tipicamente il 30-50% rispetto al TESTING_MODE = completo
- Aggiungi una nota esplicita nel documento: *"Il collaudo funzionale è condotto dal gruppo di collaudo del cliente. Questa sezione copre esclusivamente il supporto tecnico e il bug fixing da parte del team di sviluppo."*

#### Colonne della tabella WBS

| Colonna | Contenuto |
|---------|-----------|
| MACRO ATTIVITA | Numero e nome della macro attività (es. `1. PROJECT MANAGEMENT`) |
| ATTIVITA | Numero e nome dell'attività (es. `1.1 Pianificazione`) |
| TASK PROGETTUALI | Numero e nome del task atomico (es. `1.1.1 Setup piano di progetto`) |
| Grado Complessità | Codice (AA/A/MM/M/BB/B) dalla tabella sopra |
| Numero Macro-funzioni | Conteggio dei componenti/funzionalità coinvolti nel task |
| Tot. GG/u | GG/u = GG/u_base(complessità) × Numero Macro-funzioni |
| Tot. GG/u con AI | Stima ridotta per l'utilizzo di AI (vedi regole sotto) |
| % Incidenza AI | Percentuale di riduzione AI = ((Tot. GG/u − Tot. GG/u con AI) / Tot. GG/u) × 100, arrotondata all'intero. Es: da 7.5 a 5.3 → 29% |
| Risorse | Acronimi delle figure coinvolte (es. `PM, SA, TD4E`) |

#### Regole per Tot. GG/u con AI

Applica queste riduzioni percentuali in base alla natura del task:

| Tipo di Task | Riduzione AI |
|-------------|-------------|
| Sviluppo codice (CRUD, API, UI) | -30% a -40% |
| Test automatizzati | -25% a -35% |
| Documentazione tecnica | -40% a -50% |
| Design e architettura | -10% a -20% |
| Migrazione dati / ETL | -20% a -30% |
| Project Management / governance | -5% a -10% |
| Formazione e UAT | -0% a -10% |

Adatta la riduzione al contesto: se il task è altamente standardizzabile la riduzione è maggiore;
se richiede giudizio esperto o negoziazione, la riduzione è minima.

#### Granularità e qualità delle stime

- I task devono essere **atomici**: idealmente 1-5 GG/u ciascuno, mai più di 10
- Se un task supera 10 GG/u, scomponilo in sotto-task
- Se INCLUDE_PM = sì: PM, testing e documentazione pesano tipicamente 30-40% dell'effort totale
- Se INCLUDE_PM = no: testing e documentazione pesano tipicamente 20-30% dell'effort totale
- Se TESTING_MODE = supporto: la sezione collaudo pesa tipicamente 8-15% dell'effort totale (contro 15-25% con TESTING_MODE = completo)
- Considera buffer di contingenza impliciti nei gradi di complessità (non aggiungere extra)
- Le risorse assegnate ad ogni task devono essere coerenti con le figure identificate nello STEP 4

### STEP 5b — Verifica matematica dell'elapsed (OBBLIGATORIO)

**Prima di procedere alla stesura del documento**, compila questo checkpoint nella tua risposta intermedia con i valori numerici reali. Non usare valori placeholder — ogni campo deve contenere il numero calcolato.

#### Checkpoint 5b — Calcolo FTE effettivi

Elenca ogni figura con N. risorse e % coinvolgimento (convertita in decimale):

```
Figura 1: N × dec(%) = X.XX FTE
Figura 2: N × dec(%) = X.XX FTE
...
FTE_effettivi = X.XX  ← somma di tutti i contributi
```

> ⚠️ ERRORE COMUNE: dimenticare di dividere per FTE nella formula successiva equivale a
> assumere che UNA SOLA PERSONA esegua tutto il progetto in sequenza, gonfiando l'elapsed
> di un fattore pari esattamente a FTE_effettivi (×2 con team da 2, ×5 con team da 5, ecc.).
> Verifica sempre che la divisione per FTE_effettivi sia presente.

#### Checkpoint 5b — Calcolo elapsed

Usa **efficienza_parallelismo = 0.65** (fisso). Applica le formule con i numeri reali:

```
Elapsed_teorico   = [TOT_GGU] ÷ ([FTE_effettivi] × 5)
                  = ___ ÷ (___ × 5)
                  = ___ ÷ ___
                  = ___ settimane

Elapsed_reale     = Elapsed_teorico ÷ 0.65
                  = ___ ÷ 0.65
                  = ___ settimane   ← QUESTO è il valore da inserire nel documento

Elapsed_reale_AI  = [TOT_GGU_AI] ÷ ([FTE_effettivi] × 5) ÷ 0.65
                  = ___ ÷ ___ ÷ 0.65
                  = ___ settimane (con AI)
```

**Esempio corretto** (804 GG/u, team: PM 1×100%, SA 1×60%, Dev 2×100%, TD 3×100%, DO 1×50%, QA 1×80%):
```
FTE = 1×1.00 + 1×0.60 + 2×1.00 + 3×1.00 + 1×0.50 + 1×0.80 = 9.90
Elapsed_teorico = 804 ÷ (9.90 × 5) = 804 ÷ 49.5 = 16.2 sett
Elapsed_reale   = 16.2 ÷ 0.65 = 24.9 sett ≈ 25 settimane   ✓
```
> ❌ Errato: 804 ÷ 5 = 161 sett (×6.5 — ha omesso la divisione per FTE)
> ❌ Errato: 804 ÷ 5 ÷ 0.65 = 248 sett (×10 — stessa omissione, ancora peggio)

**Regola di sanity check**: se l'elapsed che stai per scrivere nel documento differisce di più del 20%
da Elapsed_reale calcolato sopra, è **sbagliato** — sostituiscilo con il valore calcolato.

**Per gli scenari team ridotto** (tabella confronto), applica la stessa formula per ogni scenario:
`Elapsed_scenario = Tot. GG/u ÷ (FTE_scenario × 5) ÷ 0.65`

Non stimare l'elapsed a intuito. Calcola sempre prima, poi usa il numero calcolato nel documento.

### STEP 6 — Struttura del documento di output

Genera **due file** nella directory di lavoro corrente (`.`):

1. **Markdown** — `WBS_<PROGETTO_TARGET>_<YYYYMMDD>.md`
2. **CSV** — `WBS_<PROGETTO_TARGET>_<YYYYMMDD>.csv`

Il CSV contiene tutte le righe della tabella WBS principale (escluse le righe di riepilogo e il cronoprogramma). Usa `;` come separatore e UTF-8 come encoding. La prima riga è l'intestazione:

```
MACRO ATTIVITA;ATTIVITA;TASK PROGETTUALI;Grado Complessità;Numero Macro-funzioni;Tot. GG/u;Tot. GG/u con AI;% Incidenza AI;Risorse
```

Ogni riga di dati corrisponde a un task della WBS. La colonna `% Incidenza AI` va espressa come numero intero senza simbolo `%` (es. `29`, non `29%`) per facilitare l'importazione in Excel/Google Sheets.

Il documento deve seguire **esattamente** questa struttura:

---

```markdown
# WBS — <Nome Progetto>

**Data generazione:** <GG/MM/AAAA>
**Versione:** 1.0
**Generato da:** WBS Generator (ENGenius Pipeline)

---

## Figure Professionali

| Figura Professionale | Codice | Costo €/gg | N. Risorse | % Coinvolgimento |
|----------------------|--------|-----------|-----------|-----------------|
| ...                  | ...    | ...       | ...       | ...             |

---

## Work Breakdown Structure

| MACRO ATTIVITA | ATTIVITA | TASK PROGETTUALI | Grado Complessità | Numero Macro-funzioni | Tot. GG/u | Tot. GG/u con AI | % Incidenza AI | Risorse |
|----------------|----------|-----------------|-------------------|-----------------------|-----------|-----------------|----------------|---------|
| 1. PROJECT MANAGEMENT | 1.1 Pianificazione | 1.1.1 Setup piano di progetto | B | 1 | 2.5 | 2.3 | 8% | PM |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## Riepilogo Effort per Macro Attività

| Macro Attività | Tot. GG/u | Tot. GG/u con AI | % Incidenza AI | % sul totale |
|----------------|-----------|-----------------|----------------|-------------|
| 1. PROJECT MANAGEMENT | ... | ... | ...% | ...% |
| ... | ... | ... | ... | ... |
| **TOTALE** | **...** | **...** | **...%** | **100%** |

---

## Stima Economica

Calcola il costo totale moltiplicando i **GG/u per figura** × **Costo €/gg** (da `references/costi-std.md`).
Distribuisci i GG/u totali tra le figure in proporzione al loro coinvolgimento e ai task assegnati.

| Figura Professionale | Codice | Costo €/gg | GG/u Totali | GG/u con AI | Costo Totale (€) | Costo con AI (€) |
|----------------------|--------|-----------|-------------|-------------|-----------------|-----------------|
| ...                  | ...    | ...       | ...         | ...         | ...             | ...             |
| **TOTALE**           |        |           | **...**     | **...**     | **...**         | **...**         |

> **Risparmio stimato con AI: € ... (~...%)**

---

## Cronoprogramma

### Ipotesi di pianificazione

- Numero di risorse disponibili: <lista>
- Parallelizzazioni possibili: <descrizione>
- Vincoli identificati: <lista>
- Giorni lavorativi per settimana: 5

### Piano di esecuzione

| Fase | Settimane | Mesi | Dipende da | Risorse principali |
|------|-----------|------|------------|--------------------|
| 1. Project Management | 1-N | M1-MN | — | PM |
| ... | ... | ... | ... | ... |

### Verifica matematica elapsed

> **Formula**: `Elapsed = Tot. GG/u ÷ (FTE_effettivi × 5) ÷ 0,65`
>
> FTE_effettivi = <Figura1>: N×dec% + <Figura2>: N×dec% + ... = **<FTE_tot> FTE**
>
> <Tot. GG/u> ÷ (<FTE_tot> × 5) ÷ 0,65 = **~X settimane**
> <Tot. GG/u con AI> ÷ (<FTE_tot> × 5) ÷ 0,65 = **~Y settimane** (con AI)

### Stima Elapsed Totale

**Elapsed stimato: ~X settimane (~Y mesi)** · Con AI: **~W settimane (~Z mesi)**

Considerando le parallelizzazioni identificate, il progetto richiede circa **X settimane** di
calendario con il team descritto. Le fasi critiche (critical path) sono: <lista>.
```

---

### STEP 6b — Validazione sintattica del CSV (OBBLIGATORIO — ciclo ripetuto fino al successo)

Dopo aver salvato il file CSV su disco, eseguine la validazione con lo script dedicato:

```bash
python3 $HOME/.agents/skills/wbs-generator/scripts/validate_wbs_csv.py <percorso_file_csv>
```

**Ciclo di validazione (ripeti fino a exit code 0):**

1. Esegui il comando sopra sul file CSV appena salvato.
2. Se **exit code 0** → il CSV è valido, procedi allo STEP 7.
3. Se **exit code 1** → leggi l'elenco degli errori e correggi **ogni** errore nel file CSV:

   | Tipo di errore segnalato | Azione correttiva |
   |--------------------------|-------------------|
   | Numero di colonne errato | Aggiungi o rimuovi il separatore `;` mancante/in eccesso nella riga indicata |
   | `Grado Complessità` non valido | Sostituisci con uno dei codici ammessi: `AA`, `A`, `MM`, `M`, `BB`, `B` |
   | `Numero Macro-funzioni` non intero o < 1 | Correggi con un intero ≥ 1 |
   | `Tot. GG/u` o `Tot. GG/u con AI` non numerico o ≤ 0 | Inserisci il valore numerico corretto (usa `.` come separatore decimale) |
   | `Tot. GG/u con AI` > `Tot. GG/u` | Riduci `Tot. GG/u con AI` applicando la riduzione AI appropriata |
   | `% Incidenza AI` contiene il simbolo `%` | Rimuovi il simbolo `%`, lascia solo il numero intero (es. `29`, non `29%`) |
   | `% Incidenza AI` non coerente con la formula | Ricalcola: `round((Tot. GG/u − Tot. GG/u con AI) / Tot. GG/u × 100)` e sostituisci |
   | `Tot. GG/u` non coerente con `GG/u_base × Macro-funzioni` | Correggi `Tot. GG/u` usando esattamente `GG/u_base(codice) × Numero Macro-funzioni` |
   | Campo testo obbligatorio vuoto | Compila il campo mancante (MACRO ATTIVITA, ATTIVITA, TASK PROGETTUALI o Risorse) |

4. Sovrascrivi il file CSV con la versione corretta.
5. Torna al punto 1 e ri-esegui lo script.

> ⚠️ Non procedere allo STEP 7 finché lo script non restituisce exit code 0 e il messaggio `✅ CSV valido`.

---

### STEP 7 — Salvataggio, upload e riepilogo

1. Salva il file `.md` su disco
2. Salva il file `.csv` su disco (stesso nome base del `.md`, estensione diversa)
3. **Carica il file `.md` su DocMind** nello stesso progetto da cui sono stati letti i documenti ENGenius:
   - Usa `stageFile` passando il percorso assoluto del file `.md` appena salvato
   - Poi `uploadDocument` con:
     - `project`: lo stesso progetto DocMind usato nella ricerca (es. `VendorsHub`)
     - `uniqueName`: `wbs-<progetto-lowercase>-<YYYYMMDD>` (es. `wbs-vendorshub-20260417`)
     - `displayName`: `WBS — <Nome Progetto> (<YYYYMMDD>)`
     - `category`: `WBS_DRAFT`
     - `suggestedTag`: `wbs`
   - Attendi il completamento con `checkUploadStatus`
4. Comunica i percorsi completi dei file su disco e il `uniqueName` del documento caricato su DocMind
5. Mostra un riepilogo sintetico con **esattamente** questi campi (tutti obbligatori):
   - **Numero di task WBS**: N task (conteggio righe della tabella WBS, escluse header e righe di riepilogo)
   - **Totale GG/u** (senza AI): X GG/u
   - **Totale GG/u con AI**: X GG/u
   - **Elapsed stimato**: X settimane (~Y mesi)
   - **Figure professionali**: elenco codice + costo €/gg
   - **Costo totale stimato**: € X (senza AI) / € Y (con AI)
