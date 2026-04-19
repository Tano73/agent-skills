# Tabella Pesi FFPA (Fast Function Points Analysis - Gartner) — v2

## Tabella 2 – Complessità degli Oggetti Logici

| Categoria | Codice | Classificazione | Complessità | FFP | Col. Excel |
|-----------|--------|-----------------|-------------|-----|------------|
| **Entità Logiche** | A.1 | Strutture logiche **interne** (dati gestiti entro il confine funzionale) | (a) da 1 a 50 campi | 7 | F |
| | | | (b) più di 50 campi | 10 | G |
| | A.2 | Strutture logiche **esterne** (referenziate, mantenute da altra app) | (a) da 1 a 50 campi | 5 | H |
| | | | (b) più di 50 campi | 7 | I |
| **Oggetti Logici di Input** | B.1 | Form per **aggiornare la base dati** (inserimento/modifica/cancellazione da utente umano) | (a) da 1 a 4 elementi distinti | 9 | J |
| | | | (b) da 5 a 15 elementi distinti | 12 | K |
| | | | (c) più di 15 elementi distinti | 18 | L |
| | B.2 | **Input da altre applicazioni** (flussi in ingresso, interfacce B2B) | (a) da 1 a 4 elementi distinti | 3 | M |
| | | | (b) da 5 a 15 elementi distinti | 4 | N |
| | | | (c) più di 15 elementi distinti | 6 | O |
| | B.3 | **Liste predefinite** (dropdown, lookup, combo, pick list da DB) | nessuna fascia — peso fisso | 3,5 | P (contare # liste) |
| | B.4 | **Visualizzazione informazioni / interrogazioni** (read-only, inquiry, display, pop-up) | (a) da 1 a 5 elementi distinti | 3,5 | Q |
| | | | (b) da 6 a 20 elementi distinti | 4,5 | R |
| | | | (c) più di 20 elementi distinti | 6,5 | S |
| | B.5 | **Elaborazioni interne** (processi batch, scheduler, elaborazioni senza I/O diretto) | nessuna fascia — peso fisso | 3 | T (contare # processi) |
| **Oggetti Logici di Output** | C.1 | **Report** (stampa, PDF, CSV, export verso utente) | (a) da 1 a 5 elementi distinti | 3,5 | U |
| | | | (b) da 6 a 20 elementi distinti | 4,5 | V |
| | | | (c) più di 20 elementi distinti | 6,5 | W |
| | C.2 | **Output verso altre applicazioni** (flussi in uscita, interfacce B2B, API call) | (a) da 1 a 5 elementi distinti | 3,5 | X |
| | | | (b) da 6 a 20 elementi distinti | 4,5 | Y |
| | | | (c) più di 20 elementi distinti | 6,5 | Z |
| **Regole di Business** | D.1 | **Calcoli interni** (algoritmi, formule, aggregazioni, conversioni, indicatori) | nessuna fascia — peso fisso | 3 | AA |
| | D.2 | **Inferenze interne** (logica decisionale, regole condizionali, criteri di validazione, mapping, selezione) | nessuna fascia — peso fisso | 3 | AB |

### Configurazione (colonne AC-AE del template Excel)

| Oggetto | Peso unitario | Col. Excel |
|---------|--------------|------------|
| Dati | 0,2 CP per dato | AC |
| Liste | 0,5 CP per lista | AD |
| Regole | 1,0 CP per regola | AE |

**Formula**: `FP(Conf) = 0,2 × dati + 0,5 × liste + regole`

### Prestazioni Non Funzionali (colonne AF-AO del template Excel)

| Codice | Descrizione | Col. Excel |
|--------|-------------|------------|
| ND.1 | Estrazione ad hoc | AF |
| ND.2 | Popolamento di dati | AG |
| ND.3 | Bonifica di dati | AH |
| NI.1 | Modifiche estetiche o di usabilità delle interfacce | AI |
| NI.2 | Search Engine Optimization (SEO) e Search | AJ |
| NT.1 | Adozione di requisiti di sicurezza | AK |
| NT.2 | Modifica di requisiti prestazionali | AL |
| NT.3 | Technical re-engineering | AM |
| NA.1 | Modifiche architetturali | AN |
| Altre | Altre prestazioni fuori dal ciclo di vita del software | AO |

Le Prestazioni Non Funzionali sono misurate in **UDA effettivi**, non in FFP.

---

## Mappatura colonne Template Excel "Report FP Fornitore"

| Colonna | Campo | Note |
|---------|-------|------|
| A | ID Rilascio | Identificativo del rilascio |
| B | ID Requisito | Identificativo del requisito/bug/story |
| C | Processo Funzionale | Nome del processo funzionale |
| D | Descrizione Impatto | Cosa cambia — fondamentale per tracciabilità |
| E | Tipo di attività | "Sviluppo" o "Configurazione" |
| F | A.1 (a) 0-50 | Numero di entità logiche interne ≤50 campi |
| G | A.1 (b) >50 | Numero di entità logiche interne >50 campi |
| H | A.2 (a) 0-50 | Numero di entità logiche esterne ≤50 campi |
| I | A.2 (b) >50 | Numero di entità logiche esterne >50 campi |
| J | B.1 (a) <5 | Numero di form update con 1-4 elementi |
| K | B.1 (b) 5-15 | Numero di form update con 5-15 elementi |
| L | B.1 (c) >15 | Numero di form update con >15 elementi |
| M | B.2 (a) <5 | Numero di input da altre app con 1-4 elementi |
| N | B.2 (b) 5-15 | Numero di input da altre app con 5-15 elementi |
| O | B.2 (c) >15 | Numero di input da altre app con >15 elementi |
| P | B.3 # liste | Numero di liste predefinite |
| Q | B.4 (a) <6 | Numero di inquiry/display con 1-5 elementi |
| R | B.4 (b) 6-20 | Numero di inquiry/display con 6-20 elementi |
| S | B.4 (c) >20 | Numero di inquiry/display con >20 elementi |
| T | B.5 # processi | Numero di elaborazioni interne |
| U | C.1 (a) <6 | Numero di report con 1-5 elementi |
| V | C.1 (b) 6-20 | Numero di report con 6-20 elementi |
| W | C.1 (c) >20 | Numero di report con >20 elementi |
| X | C.2 (a) <6 | Numero di output verso altre app con 1-5 elementi |
| Y | C.2 (b) 6-20 | Numero di output verso altre app con 6-20 elementi |
| Z | C.2 (c) >20 | Numero di output verso altre app con >20 elementi |
| AA | D1 Calcoli interni | Numero di calcoli interni |
| AB | D2 Inferenze interne | Numero di inferenze interne |
| AC | Conf. Dati | Numero di dati di configurazione |
| AD | Conf. Liste | Numero di liste di configurazione |
| AE | Conf. Regole | Numero di regole di configurazione |
| AF | ND.1 | UDA per estrazioni ad hoc |
| AG | ND.2 | UDA per popolamento dati |
| AH | ND.3 | UDA per bonifica dati |
| AI | NI.1 | UDA per modifiche estetiche/usabilità |
| AJ | NI.2 | UDA per SEO/Search |
| AK | NT.1 | UDA per requisiti di sicurezza |
| AL | NT.2 | UDA per requisiti prestazionali |
| AM | NT.3 | UDA per technical re-engineering |
| AN | NA.1 | UDA per modifiche architetturali |
| AO | Altre | UDA per altre prestazioni |
| AP | Rif. Documentale/Note | Riferimenti a specifiche, paragrafi, note |

---

## Regole chiave per determinare la complessità

### "Elementi distinti" per oggetti B/C
- Un **elemento distinto** = un campo logico, attributo, dato significativo per l'utente
- Se lo stesso campo appare più volte nella stessa schermata (es. array/lista), si conta **una volta sola**
- Non contare i campi tecnici (ID interni, timestamp di sistema, chiavi surrogate, Foreign Key)
- I pulsanti di azione (Salva, Annulla, Conferma) **non** si contano come elementi
- Per B.4: contare campi di filtro + campi mostrati in output (non già contati come filtro)
- Per C.1: contare campi di filtro + elementi distinti del report
- Per B.2/C.2 nei servizi: contare campi di richiesta + campi ricevuti/forniti (non già contati come richiesta)

### "Campi" per entità logiche A.1 / A.2
- Si contano gli **attributi logici** dell'entità, non le colonne fisiche del DB
- Attributi ripetuti in tabelle correlate si sommano all'entità principale se concettualmente parte di essa
- NON contare le Foreign Key (chiavi esterne)
- Raggruppare tabelle/entità che contribuiscono a definire un solo oggetto significativo per l'utente

---

## Cosa si conta e cosa NON si conta

### SI CONTA (Requisiti Funzionali)
- Funzionalità percepibili dall'utente (umano o altra applicazione)
- Gestione dati: inserimento, modifica, cancellazione, visualizzazione, ricerca
- Interfacce di scambio dati con altri sistemi
- Report e output informativi
- Regole di business che implementano calcoli o logica decisionale
- Funzionalità di configurazione (liste di valori, parametri, regole configurabili)
- Audit log funzionale (richiesto come requisito funzionale)
- Invio e-mail con allegati (come C.1)

### NON SI CONTA (Requisiti Tecnici / Non Funzionali)
- Requisiti di performance, scalabilità, disponibilità (SLA)
- Sicurezza tecnica: autenticazione, autorizzazione, cifratura (se non richiesta funzionalmente)
- Infrastruttura: backup, deploy, monitoraggio
- Log tecnici (log di debug, log applicativo non richiesto dall'utente)
- Migrazioni dati "one-shot" non ripetibili (possono rientrare in ND.2)
- Refactoring, ottimizzazioni tecniche senza impatto funzionale
- Protocolli di comunicazione (es. uso di REST vs SOAP: tecnico)
- Variazioni dell'aspetto grafico/layout senza impatto funzionale (possono rientrare in NI.1)
- Porting su nuove piattaforme/tecnologie (possono rientrare in NT.3)
- Message box di conferma/avviso/errore (incluse nei D.2)
- Funzionalità "out of the box" fornite dal framework/piattaforma senza sviluppo

### NON SONO ENTITÀ LOGICHE (da escludere dal conteggio A)
- **Dati di decodifica**: codice + descrizione, valori statici, liste geografiche, tabelle tipologiche, codici abbreviativi, valori di default. Regola: se puoi sostituire il codice con la descrizione senza cambiare il significato di business → decodifica.
  - **Eccezione**: dati per regole di business, se dinamici e mantenuti con attività dedicate (tassi di cambio, range reddito/imposta, dati di controllo mantenuti dall'utente)
- **Tabelle tecniche**: tabelle associative con sole FK, tabelle con una sola occorrenza costante, tabelle con info tecniche, tabelle di appoggio, file di properties/risorse

### TRATTAMENTI INCLUSI nel peso degli oggetti B/C (NON contare come D)
- Selezione dati logici dal dataset fisico
- Controlli formali, obbligatorietà, sintassi campi
- Controlli tecnici
- Controllo valore campo / dominio ammesso (salvo logiche business aggiuntive)
- Transcodifica dati (NON è D.1)
- Mantenimento base dati
- Reperimento dati dalle entità logiche
- Controlli di esistenza nel DB
- Controlli di buona programmazione (data inizio < data fine)
- Join/relazioni semplici padre-figlio o tramite FK
- Ordinamento e formattazione standard

---

## Processo Funzionale: definizione e rilevanza

Un **Processo Funzionale** è la più piccola unità di attività che:
1. È **significativa per l'utente** (l'utente la riconosce e la richiede)
2. È **autonoma** (eseguibile indipendentemente)
3. **Lascia l'applicazione in uno stato di coerenza funzionale**

Un oggetto logico corrisponde sempre a un Processo Funzionale. Non si contano sotto-funzionalità tecniche.

### Intento Primario

Per ogni processo funzionale, identificare l'intento primario:
- **Elaborazione di input** → contare B.1/B.2 + eventuali D
- **Produzione di output** → contare B.3/B.4/C.1/C.2 + eventuali D
- **Entrambi (input e output indipendenti)** → contare sia B che C + eventuali D
- **Elaborazioni interne** → contare B.5 + eventuali D

### Riuso Funzionale

Stessa funzionalità usata in più parti con stessi campi e stessi trattamenti = **conta 1 sola volta**.

Si conta come distinto solo se: opera su dati semanticamente distinti OPPURE ha trattamento logico diverso.

---

## Tipi di conteggio FFPA

| Tipo | Quando si usa |
|------|--------------|
| **New Development (ND)** | Nuovo sviluppo da zero |
| **Enhancement (E)** | Modifica/evolutiva su applicazione esistente — si contano solo gli oggetti aggiunti (ADD), modificati (CHG) o eliminati (DEL) |
| **Application (A)** | Misura della dimensione totale dell'applicazione installata |

Per i conteggi Enhancement:
- Ogni oggetto va classificato come ADD / CHG / DEL
- Per CHG: complessità = TUTTI i campi dopo la modifica (non solo quelli impattati)
- Per DEL: complessità = campi prima della cancellazione

---

## Regole speciali B.1

- Insert + Modify + Delete sulla stessa entità = **1 solo B.1**, indipendentemente dal numero di form fisici o pulsanti
- Workflow guidati step-by-step che raccolgono dati in un'unica transazione = **1 solo B.1**
- Più form fisici per usabilità → non influenzano il conteggio
- Più form logici su una singola schermata fisica → contare separatamente

---

## Regole speciali B.3

- Peso fisso 3,5 FFP, nessuna fascia di complessità
- Se usata in più form → contare 1 sola volta (riuso funzionale)
- Se i valori dipendono dal contesto (es. province filtrate per regione) → B.3 + D.2
- Modifica di B.3: contare come CHG solo se mostra campi semanticamente diversi (non semplice aggiunta valori). Se cambia solo il filtro sulla stessa fonte → D.2.
- Aggiunta nuovi valori a B.3 esistente (configurazione) → 1 lista + 1 dato per valore

---

## Regole speciali B.4 vs C.1

| Caratteristica | B.4 | C.1 |
|---------------|-----|-----|
| Tipo output | Dinamico, interattivo, a video | Predefinito, statico, stampabile/scaricabile |
| Manipolazione | L'utente può navigare, filtrare, ordinare | Output fisso, non manipolabile |
| Esempio | Schermata di ricerca impiegati | Report PDF lista impiegati per centro |
| Complessità | filtri + campi output | filtri + elementi distinti report |

Caso speciale: export/download da B.4 con stessi dati o subset (anche con layout diverso) → **C.1 fascia bassa** (1 dato). Se arricchiti con dati aggiuntivi → **C.1 con complessità normale**.

---

## Regole speciali C.1 — Tracciatura log

Funzionalità di tracciatura log con stesso tracciato e stessi trattamenti = riuso funzionale:
- **1 C.1** per la prima istanza
- **1 D.2** per ogni ulteriore processo funzionale distinto che richiede la tracciatura

---

## Regole speciali per invio e-mail

L'invio e-mail si conta come **C.1**. Elementi distinti:
- Destinatario (solo se variabile)
- Oggetto/Subject (solo se variabile)
- Corpo del messaggio (per testo statico)
- Campi variabili nel corpo
- Allegato (1 campo per allegato)

Allegato autonomo (contenuto logico distinto, indipendente dalla mail, consultabile anche altrimenti) = **C.1 aggiuntivo** (se non già contato).

---

## Condivisione dati tra applicazioni — Scenari di riferimento

| # | Scenario | App che accede ai dati | App sorgente dei dati |
|---|----------|----------------------|----------------------|
| 1 | Accesso diretto ai dati (query su DB altrui) | A.2 | nessun FFP |
| 2 | Tabella di scambio (struttura dedicata) | B.2 | C.2 |
| 3 | Replica strutture dati (CDC, Golden Gate, ecc.) | A.2 | nessun FFP |
| 4 | Servizio in lettura (API per leggere) | B.2 | C.2 + A.1 |
| 5 | Servizio in scrittura (API per scrivere) | C.2 | B.2 + A.1 |
| 6 | Duplicazione dati lettura (copia locale periodica) | B.2 + A.1 | C.2 |
| 7 | Duplicazione dati scrittura (sync bidirezionale) | A.1 + C.2 + B.2 | speculare |

Complessità B.2/C.2 nei servizi: campi di richiesta + campi ricevuti/forniti (non già contati come richiesta).

---

## Output atteso dall'analisi FFPA

La lista degli oggetti logici deve essere prodotta come tabella compatibile con le colonne del template Excel "Report FP Fornitore", con:

| Col | Campo |
|-----|-------|
| A | ID Rilascio |
| B | ID Requisito |
| C | Processo Funzionale |
| D | Descrizione Impatto |
| E | Tipo di attività (Sviluppo / Configurazione) |
| F-AB | Conteggio oggetti per tipo e fascia (numeri, non FFP) |
| AC-AE | Configurazione: Dati, Liste, Regole |
| AF-AO | Prestazioni Non Funzionali (UDA effettivi) |
| AP | Rif. Documentale / Note |

Seguita da:
- **Riepilogo per categoria** (A, B, C, D, Configurazione, Prest. Non Funzionali)
- **Tipo di conteggio** (ND / Enhancement ADD+CHG+DEL / Application)
- **Eventuali assunzioni** fatte durante l'analisi
- **Elementi NON conteggiati** con motivazione e eventuale categoria NF
- **Riuso funzionale applicato**
