---
name: ffpa-analyzer
description: "Analisi Function Point con metodologia FFPA (Fast Function Points Analysis - Gartner). Usa questa skill ogni volta che l'utente vuole misurare, stimare o contare i Function Point di un'applicazione o di un requisito. Si attiva quando l'utente menziona: function point, FP, FFP, FFPA, FPA, misura funzionale, sizing funzionale, dimensionamento software, conteggio FP, analisi funzionale ai fini della misura. Funziona con qualsiasi tipo di input: codice sorgente, specifiche tecniche/funzionali, requisiti utente, user story, documenti di analisi, descrizioni testuali. Produce sempre una tabella strutturata degli oggetti logici con classe, codice, complessità e FFP, compatibile con il template Excel (Calcolatrice FFP) ufficiale per contratti in FP/UdA."
---

# FFPA Analyzer — Analisi Function Point (Metodologia FFPA)

## Contesto

Questa skill applica la metodologia **Fast Function Points Analysis (FFPA)** come descritta nel *Manuale Misura Software per Unità di Prodotto (IT) v5.0* — il riferimento normativo ufficiale.

FFPA **amplia la metodologia tradizionale IFPUG** (Function Point Analysis) integrandola con due modelli aggiuntivi:
- un modello per valutare le **Regole di Business** implementate negli algoritmi (Classe D)
- un modello per le funzionalità realizzate tramite **configurazione di package**

L'unità di misura è il **FFP (Fast Function Point)**, sempre di tipo Unadjusted (UFP) nel senso IFPUG: non si applica mai un fattore di aggiustamento (Value Adjustment Factor).

Il conteggio si esegue su **oggetti logici** riconoscibili dall'utente — non su oggetti fisici o tecnici — ed è indipendente dalla tecnologia di implementazione. È applicabile sia al codice sorgente che alle specifiche, in tutte le fasi del ciclo di vita.

Leggi **`references/ffpa-weights-v2.md`** per la tabella completa dei pesi, le soglie di complessità, le regole su cosa si conta, e la mappatura delle colonne del template Excel. Quello è il tuo riferimento normativo operativo.

---

## Tipi di input accettati

- **Codice sorgente**: entità/modelli → A, controller/API/form → B/C, algoritmi/logiche → D
- **Specifiche o documenti funzionali**: identifica le funzionalità dal punto di vista dell'utente
- **Requisiti utente / User Story**: ogni story descrive 1-N processi funzionali
- **Descrizione testuale**: estrai solo ciò che è percepibile e richiesto dall'utente

---

## Processo di analisi

### Step 1 — Raccolta del contesto

Prima di procedere, identifica:
- **Cosa fa l'applicazione?** (processo di business supportato)
- **Chi sono gli utenti?** (umani, altre applicazioni, o entrambi — includono tutti i soggetti che interagiscono con il confine funzionale)
- **Confine funzionale**: cosa è dentro e cosa è fuori. Le comunicazioni tra sotto-componenti dello stesso confine **non si contano** come flussi I/O.
- **Tipo di conteggio**: New Development, Enhancement (ADD/CHG/DEL), o Application totale
- **Tipo di contratto**: in FP o in UdA (determina il template Excel da usare)

Se questi elementi non sono espliciti, deducili dal contesto e documenta le assunzioni.

### Step 2 — Livello di astrazione

Individua il corretto livello di astrazione analizzando il contesto: processo di business, informazioni trattate, utilizzatori. Un requisito può essere funzionale per un'applicazione e tecnico per un'altra, in base allo scopo dell'applicazione.

### Step 3 — Identificazione dei requisiti funzionali

Mantieni solo i **requisiti funzionali**: cosa deve fare il software per soddisfare le esigenze dell'utente. Scarta:
- Requisiti tecnici (performance, protocolli, infrastruttura, sicurezza tecnica)
- Requisiti di qualità (disponibilità, scalabilità, SLA)
- Requisiti di usabilità pura (layout, aspetto grafico)

I requisiti tecnici/non funzionali esclusi dai FFP possono rientrare nelle **Prestazioni Non Funzionali** (Step 10).

### Step 4 — Identificazione dei Processi Funzionali e degli Oggetti Logici

Un **Processo Funzionale** è la più piccola unità di attività che: (1) è significativa per l'utente, (2) è autonoma, (3) lascia l'applicazione in uno stato di coerenza funzionale.

#### Intento Primario — Regola fondamentale

Determina l'intento primario di ogni processo per capire cosa contare:

- **Elaborazione di input** → aggiornare dati o ricevere informazioni da trattare; l'output fornisce solo feedback. Conta: **1 oggetto B.1 o B.2** + eventuali D.
- **Produzione di output** → produrre informazioni per l'utente/altra app; l'input indica solo cosa/come produrre. Conta: **1 oggetto B.3, B.4, C.1 o C.2** + eventuali D.
- **Input E output entrambi indipendenti** → entrambe le componenti sono importanti per l'utente. Conta: **1 B.1/B.2 per l'input + 1 B.3/B.4/C.1/C.2 per l'output** + eventuali D.
- **Elaborazioni interne** → nessun flusso I/O, attivato da schedulatore/trigger. Conta: **1 B.5** + eventuali D.

#### Classificazione degli oggetti logici

**Classe A — Entità Logiche** (dati conservati):
- **A.1** Strutture logiche **interne**: dati creati, modificati o cancellati entro il confine funzionale
- **A.2** Strutture logiche **esterne**: dati referenziati in sola lettura, mantenuti da un'altra applicazione

**Classe B — Input** (dati che entrano):
- **B.1** Form per **aggiornare la base dati** (inserimento/modifica/cancellazione da utente umano). Insert + Modify + Delete sulla stessa entità = **1 solo B.1**. Workflow wizard step-by-step sulla stessa transazione = **1 solo B.1**.
- **B.2** **Input da altre applicazioni** (flussi batch o on-line, interfacce, API in ingresso)
- **B.3** **Liste predefinite** (dropdown, lookup, combo, pick list da DB). Peso fisso. Se i valori dipendono dal contesto → B.3 + D.2.
- **B.4** **Visualizzazione informazioni / interrogazioni** (read-only, ricerche, dettaglio, pop-up informativi). Per la complessità: campi di filtro + campi mostrati in output.
- **B.5** **Elaborazioni interne** (batch, scheduler, senza I/O diretto). Peso fisso. Può includere maschera di lancio con soli dati di controllo.

**Classe C — Output** (dati che escono):
- **C.1** **Report** (stampa, PDF, CSV, export verso utente). Aspetto predefinito/statico. Export da B.4 con stessi dati/subset → C.1 fascia bassa. Invio e-mail → C.1 (campi: destinatario variabile, oggetto variabile, corpo, allegati); allegato autonomo con contenuto logico distinto = C.1 aggiuntivo.
- **C.2** **Output verso altre applicazioni** (flussi in uscita, interfacce, API call)

**Classe D — Regole di Business** (logica interna):
- **D.1** **Calcoli interni** (formule, algoritmi, aggregazioni, conversioni, indicatori). Le transcodifiche NON sono D.1.
- **D.2** **Inferenze interne** (logica decisionale, regole condizionali, validazioni business, mapping, selezione dati per l'utente)

Per D.1 e D.2: peso fisso, 1 requisito funzionale = 1 oggetto D. Aggiungere D solo per logiche aggiuntive di business NON comprese nell'intento primario del processo. NON aggiungere D per: selezione/filtro dati, controlli formali/sintattici, transcodifiche, join semplici, ordinamento standard.

### Step 5 — Regole di esclusione

#### NON sono Entità Logiche A:
- **Dati di decodifica**: codice + descrizione, valori statici, liste geografiche, codici abbreviativi, valori di default. Regola: se puoi sostituire il codice con la descrizione senza perdere significato di business → è decodifica. Eccezione: tabelle dinamiche con attività dedicate di mantenimento (es. tassi di cambio, range reddito/imposta).
- **Tabelle tecniche**: sole FK, tabelle associative, tabelle a una sola occorrenza costante, tabelle di appoggio, file di properties/risorse.

#### Trattamenti INCLUSI nel peso degli oggetti B/C (NON contare come D aggiuntivi):
Controlli formali/obbligatorietà/sintassi, controlli di natura tecnica, controllo dominio ammesso, transcodifiche, mantenimento base dati, reperimento dati dalle entità logiche, controlli di esistenza nel DB, controlli di buona programmazione (data inizio < data fine), join/relazioni padre-figlio, ordinamento e formattazione standard.

### Step 6 — Riuso Funzionale

La stessa funzionalità con stesse modalità logico-funzionali (stessi campi, stessi trattamenti) si conta **UNA SOLA VOLTA**. Si conta come oggetto distinto solo se opera su dati semanticamente distinti o ha trattamento logico diverso.

Esempi: lista B.3 usata in più form → 1 sola volta. Tracciatura log C.1 con stesso tracciato applicata a N processi → 1 C.1 + (N-1) D.2.

### Step 7 — Determinazione della complessità

Per A.1/A.2: conta i **campi logici** (attributi significativi per l'utente, non le FK).
Per B/C: conta gli **elementi distinti** (campi di filtro + campi di output, non tecnici, non pulsanti/tasti).
B.3, B.5, D.1, D.2: nessuna fascia — peso fisso.

Vedi `references/ffpa-weights-v2.md` per le soglie esatte. Quando il numero non è determinabile, usa la fascia più probabile e documentalo.

### Step 8 — Enhancement (ADD/CHG/DEL) — solo se applicabile

Per conteggi di tipo Enhancement, classifica ogni oggetto come ADD / CHG / DEL.

- **ADD**: oggetto non esiste già. Complessità = tutti i campi dell'oggetto aggiunto.
- **DEL**: oggetto non esisterà più. Complessità = campi PRIMA della cancellazione.
- **CHG**: oggetto esiste e verrà modificato. Complessità = **TUTTI i campi dopo la modifica** (non solo quelli impattati).

**4 casistiche per modifica di oggetti B/C:**
1. **Impatto strutturale, nessuna nuova regola**: conta l'oggetto modificato (es. aggiunta campo a B.1). Modifiche ai trattamenti dei campi non impattati sono assorbite.
2. **Nessun impatto strutturale, nuove logiche di business**: conta solo i D.2 per le nuove verifiche (es. disabilitare un tasto per condizione di business).
3. **Impatto strutturale E nuove logiche**: conta sia l'oggetto modificato sia i D.2.
4. **Nessun impatto strutturale, modifica trattamento logico esistente**: conta 1 D.2 convenzionale.

NON sono modifiche conteggiabili: variazioni grafiche, porting tecnologico, modifica tipo/lunghezza campo, variazione protocolli.

### Step 9 — Configurazioni (Package) — solo se applicabile

Per applicazioni configurabili (ERP, CRM, package con parametri), le funzionalità realizzate tramite inserimento dati in strutture predefinite si contano come **Configuration Points**:

```
FP(Configurazione) = 0,2 × num.dati + 0,5 × num.liste + num.regole
```

- **Liste** = Oggetti Logici di Business da configurare (elemento aggregatore di livello più alto)
- **Dati** = attributi significativi per l'utente, statici all'interno della lista, indipendenti tra liste
- **Regole** = informazioni che mettono in relazione oggetti tra loro. Tipi:
  - Monodirezionale → 1 regola per oggetto, indipendentemente da quanti oggetti si relaziona
  - Bidirezionale → n regole (nuovi oggetti) + m regole (oggetti preesistenti da ridefinire)
  - Workflow → 1 regola per ogni relazione uscente da ciascun nodo
  - Macchina a stati → 1 regola per ogni stato da cui è possibile il passaggio, indipendentemente dal numero di stati destinazione

**Operazioni di configurazione:**
- **Aggiunta**: nuove liste + tutti i dati valorizzati + eventuali regole
- **Modifica**: solo liste impattate + soli dati modificati + regole nuove/modificate (NON si riconteggia l'intero oggetto)
- **Cancellazione con evidenza parametri**: liste impattate + dati valorizzati
- **Cancellazione senza evidenza**: convenzionalmente 1 lista + 1 dato per oggetto; non si contano regole associative rimosse automaticamente

### Step 10 — Prestazioni Non Funzionali — solo se applicabile

I requisiti non funzionali esclusi dal conteggio FFP si riportano nelle colonne NF del template:

| Codice | Descrizione |
|--------|-------------|
| **ND.1** | Estrazione ad hoc (query/estrazioni one-shot) |
| **ND.2** | Popolamento di dati (caricamento iniziale, migrazione) |
| **ND.3** | Bonifica di dati (pulizia, normalizzazione) |
| **NI.1** | Modifiche estetiche o di usabilità interfacce |
| **NI.2** | Search Engine Optimization (SEO) |
| **NT.1** | Adozione requisiti di sicurezza |
| **NT.2** | Modifica requisiti prestazionali |
| **NT.3** | Technical re-engineering |
| **NA.1** | Modifiche architetturali |

### Step 11 — Condivisione dati tra applicazioni — solo se applicabile

| Scenario | App che accede | App sorgente |
|----------|----------------|--------------|
| Accesso diretto ai dati (query su DB altrui) | A.2 | nessun FFP |
| Tabella di scambio | B.2 | C.2 |
| Replica strutture dati (CDC, Golden Gate) | A.2 | nessun FFP |
| Servizio in lettura (API per leggere) | B.2 + A.1 se non già contata | C.2 |
| Servizio in scrittura (API per scrivere) | C.2 | B.2 + A.1 se non già contata |
| Duplicazione dati in lettura (copia locale) | B.2 + A.1 (copia locale) | C.2 |
| Duplicazione bidirezionale | A.1 + C.2 + B.2 | speculare |

Per la complessità di B.2/C.2 nei servizi: contare ogni campo di richiesta logicamente distinto + tutti i campi ricevuti/forniti (non già contati come richiesta).

### Step 12 — Calcolo FFP

Moltiplica il numero di oggetti per tipo e fascia per i rispettivi pesi (da `references/ffpa-weights-v2.md`).

---

## Formato di output

### Tabella degli oggetti logici

La tabella deve includere obbligatoriamente la **Classe** (categoria FFPA):

```
| # | Processo Funzionale | Classe           | Cod. | Complessità        | FFP  | Rif./Note |
|---|---------------------|------------------|------|--------------------|------|-----------|
| 1 | Gestione Anagrafica | Entità Logiche   | A.1  | (a) 1-50 campi     | 7    | ...       |
| 2 | Inserimento Ordine  | Input            | B.1  | (b) 5-15 elementi  | 12   | ...       |
| 3 | Report Vendite      | Output           | C.1  | (b) 6-20 elementi  | 4,5  | ...       |
| 4 | Calcolo Provvigioni | Regole Business  | D.1  | (fisso)            | 3    | ...       |
...
| **TOTALE** | | | | | **XX FFP** | |
```

Le classi sono: **Entità Logiche** (A.1, A.2) · **Input** (B.1–B.5) · **Output** (C.1, C.2) · **Regole di Business** (D.1, D.2)

**Regola**: non accorpare in una stessa riga oggetti diversi di funzionalità diverse — mantenere il dettaglio per garantire la tracciabilità.

### Riepilogo per categoria

```
| Classe                  | Codici       | N. oggetti | FFP totali |
|-------------------------|--------------|------------|------------|
| A — Entità Logiche      | A.1, A.2     | ...        | ...        |
| B — Input               | B.1–B.5      | ...        | ...        |
| C — Output              | C.1, C.2     | ...        | ...        |
| D — Regole di Business  | D.1, D.2     | ...        | ...        |
| Configurazione          |              | ...        | ... CP     |
| **TOTALE SVILUPPO**     |              | **...**    | **... FFP**|
| Prest. Non Funzionali   |              | ...        | ... UDA    |
```

### Sezione finale obbligatoria

1. **Tipo di conteggio**: New Development / Enhancement (ADD X FFP + CHG Y FFP + DEL Z FFP) / Application
2. **Confine funzionale**: cosa è stato incluso/escluso e perché
3. **Assunzioni rilevanti**: scelte fatte dove l'input era ambiguo
4. **Elementi NON conteggiati come FFP**: motivazione + eventuale categoria NF
5. **Dati di decodifica esclusi**: elenco con motivazione
6. **Riuso funzionale applicato**: oggetti contati una sola volta, documentati

### Dati per Cover Sheet (se disponibili)

Se l'utente fornisce informazioni contrattuali, indicarle nell'output: Autore Report FP, Fornitore, Applicazione/Sistema, Codice contratto, Tariffa UDA, Produttività FP.

---

## Linee guida per input da codice sorgente

- **Classi/modelli/entità di dominio** → A.1 (interne) o A.2 (esterne/in sola lettura)
- **Controller, endpoint con scrittura** (POST/PUT/DELETE) → B.1 o B.2
- **Endpoint di ricezione dati da altri sistemi** → B.2
- **Endpoint di sola lettura** (GET), query, filtri → B.4
- **Job/batch/scheduler** → B.5
- **Service con logica algoritmica** → D.1 o D.2
- **Export/download/report endpoint** → C.1
- **Client HTTP verso altri sistemi** (chiamate in uscita) → C.2
- **Dropdown/lookup/select da DB** → B.3

Lavora a livello logico, non fisico: più endpoint che implementano la stessa funzionalità logica = 1 oggetto.

Escludi da A: tabelle codice+descrizione (decodifica), tabelle associative con sole FK, tabelle tecniche (log, sessioni, config infrastrutturale), file properties.

---

## Linee guida per input da user story

Schema tipico: "Come [utente], voglio [azione] per [obiettivo]"

- "Gestire X" implica tipicamente: 1 B.1 (ins+mod+del) + B.4 (lista) + B.4 (dettaglio) → 3 oggetti, non 5
- Sii conservativo: non moltiplicare se la story non esplicita operazioni distinte
- Applica il riuso funzionale: se la stessa lista/query appare in più story, contala una volta

---

## Linee guida per ambienti DWH / BI / DataMart

- **ETL da flussi sorgente o tabella di scambio** → 1 B.2 per flusso logico distinto
- **ETL da query diretta su entità sorgente** → 1 A.2 + 1 B.5
- **Repliche intere tabelle** (CDC, Golden Gate) → A.2 (nessun FFP per l'app sorgente)
- **Staging Area**: tabelle NON conteggiate (tecniche), salvo nuove informazioni usate direttamente
- **ODS**: 1 A.1 per entità logica + 1 B.5 per processo di elaborazione/mantenimento
- **Tabelle dei Fatti**: 1 A.1 (complessità = tutti i campi, inclusi quelli referenziati sulle dimensioni)
- **Tabelle delle Dimensioni**: 1 A.1 ciascuna
- **Processi di aggregazione**: 1 B.5 + eventuali D per logiche aggiuntive
- **Normalizzazione, integrazione, storicizzazione**: nessun FFP
- **Report/cruscotti** → C.1 · **Query/interrogazioni** → B.4 · **Flussi verso altre app** → C.2
- **Report configurati in package BI** (Business Objects, Microstrategy, ecc.) → trattare come Configurazione

---

## Note importanti

- Il sizing è **indipendente dalla tecnologia**: stesso requisito = stessi FFP in Java, Python, low-code o COBOL
- **B.4 vs C.1**: output a video interattivo → B.4; output scaricabile/stampabile predefinito → C.1
- **Autenticazione/login**: tecnico, NON si conta (salvo sia la funzione principale dell'applicazione)
- **Configurazioni di sistema**: si contano solo se fruibili dall'utente funzionale come funzionalità
- **Dati di decodifica** (codice+descrizione, valori statici, liste geografiche): NON sono entità logiche A
- **Tabelle tecniche** (sole FK, appoggio, properties): NON sono entità logiche A
- **Message box** (popup di conferma, avviso, errore): NON si contano separatamente — incluse nella D.2 che le genera
- **Tasti/pulsanti/bottoni** (Salva, Annulla, Conferma): NON sono elementi distinti ai fini della complessità
- **B.1 insert+modify+delete** sulla stessa entità = 1 solo B.1, indipendentemente dal numero di form fisici
- **Workflow guidati** (wizard step-by-step) che raccolgono dati in un'unica transazione = 1 solo B.1
