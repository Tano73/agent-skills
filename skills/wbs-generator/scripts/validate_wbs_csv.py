#!/usr/bin/env python3
"""validate_wbs_csv.py — Valida la correttezza sintattica di un file CSV WBS.

Controlla:
  - Encoding UTF-8 e separatore `;`
  - Header esatto a 9 colonne
  - Numero corretto di colonne per ogni riga dati
  - Campi testo obbligatori non vuoti (MACRO ATTIVITA, ATTIVITA, TASK PROGETTUALI, Risorse)
  - Grado Complessità: uno dei codici validi (AA / A / MM / M / BB / B)
  - Numero Macro-funzioni: intero ≥ 1
  - Tot. GG/u: numero positivo
  - Tot. GG/u con AI: numero positivo ≤ Tot. GG/u
  - % Incidenza AI: intero 0-100 senza simbolo '%'
  - Consistenza % Incidenza AI rispetto alla formula (tolleranza ±2)
  - Consistenza Tot. GG/u rispetto a GG/u_base × Numero Macro-funzioni (tolleranza ±0.5)

Uso:
    python3 validate_wbs_csv.py <percorso_file_csv>

Exit code:
    0 — CSV valido
    1 — Uno o più errori trovati
    2 — Errore di utilizzo (argomenti mancanti)
"""

import csv
import sys
from pathlib import Path

EXPECTED_HEADER = [
    "MACRO ATTIVITA",
    "ATTIVITA",
    "TASK PROGETTUALI",
    "Grado Complessità",
    "Numero Macro-funzioni",
    "Tot. GG/u",
    "Tot. GG/u con AI",
    "% Incidenza AI",
    "Risorse",
]

VALID_COMPLEXITY_CODES = {"AA", "A", "MM", "M", "BB", "B"}

COMPLEXITY_BASE = {
    "AA": 35.0,
    "A": 21.0,
    "MM": 12.5,
    "M": 7.5,
    "BB": 4.5,
    "B": 2.5,
}

EXPECTED_COL_COUNT = len(EXPECTED_HEADER)

# Tolerances
PCT_TOLERANCE = 2      # ±2 percentage points for % Incidenza AI formula check
GGU_TOLERANCE = 0.5    # ±0.5 GG/u for Tot. GG/u formula check


def validate(csv_path: str) -> list:
    errors = []
    path = Path(csv_path)

    if not path.exists():
        return [f"ERRORE: file non trovato: {csv_path}"]
    if not path.is_file():
        return [f"ERRORE: il percorso non è un file regolare: {csv_path}"]

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"ERRORE: il file non è codificato in UTF-8: {exc}"]

    lines = content.splitlines()
    if not lines:
        return ["ERRORE: file vuoto"]

    reader = csv.reader(lines, delimiter=";")
    rows = list(reader)

    if not rows:
        return ["ERRORE: nessuna riga trovata nel CSV"]

    # --- Header validation ---
    header = rows[0]
    if header != EXPECTED_HEADER:
        if len(header) != EXPECTED_COL_COUNT:
            errors.append(
                f"ERRORE riga 1 (header): {len(header)} colonne invece di "
                f"{EXPECTED_COL_COUNT}. "
                f"Atteso: {';'.join(EXPECTED_HEADER)} | "
                f"Trovato: {';'.join(header)}"
            )
            return errors  # cannot reliably validate data rows
        else:
            errors.append(
                f"ERRORE riga 1 (header): nomi di colonna errati.\n"
                f"  Atteso:  {';'.join(EXPECTED_HEADER)}\n"
                f"  Trovato: {';'.join(header)}"
            )

    data_rows = rows[1:]
    if not data_rows:
        errors.append("ERRORE: nessuna riga dati trovata dopo l'header")
        return errors

    # --- Data row validation ---
    for i, row in enumerate(data_rows, start=2):  # row 1 = header
        # Skip completely blank lines
        if all(cell.strip() == "" for cell in row):
            continue

        line_prefix = f"ERRORE riga {i}"

        # Column count
        if len(row) != EXPECTED_COL_COUNT:
            errors.append(
                f"{line_prefix}: {len(row)} colonne invece di {EXPECTED_COL_COUNT} "
                f"(separatore ';' mancante o in eccesso)"
            )
            continue  # further checks are unreliable on malformed rows

        macro, attivita, task, complessita, n_macro_str, ggu_str, ggu_ai_str, pct_str, risorse = row

        # --- Mandatory text fields ---
        if not macro.strip():
            errors.append(f"{line_prefix}: 'MACRO ATTIVITA' è vuoto")
        if not attivita.strip():
            errors.append(f"{line_prefix}: 'ATTIVITA' è vuota")
        if not task.strip():
            errors.append(f"{line_prefix}: 'TASK PROGETTUALI' è vuoto")
        if not risorse.strip():
            errors.append(f"{line_prefix}: 'Risorse' è vuoto")

        # --- Grado Complessità ---
        complessita_clean = complessita.strip()
        if complessita_clean not in VALID_COMPLEXITY_CODES:
            errors.append(
                f"{line_prefix}: 'Grado Complessità' = '{complessita_clean}' non valido. "
                f"Valori ammessi: {', '.join(sorted(VALID_COMPLEXITY_CODES))}"
            )

        # --- Numero Macro-funzioni (positive integer) ---
        n_macro_clean = n_macro_str.strip()
        n_macro = None
        try:
            n_macro = int(n_macro_clean)
            if n_macro < 1:
                errors.append(
                    f"{line_prefix}: 'Numero Macro-funzioni' = {n_macro} deve essere ≥ 1"
                )
                n_macro = None
        except ValueError:
            errors.append(
                f"{line_prefix}: 'Numero Macro-funzioni' = '{n_macro_clean}' "
                "non è un intero valido"
            )

        # --- Tot. GG/u (positive float) ---
        ggu_clean = ggu_str.strip().replace(",", ".")
        ggu = None
        try:
            ggu = float(ggu_clean)
            if ggu <= 0:
                errors.append(
                    f"{line_prefix}: 'Tot. GG/u' = {ggu} deve essere > 0"
                )
                ggu = None
        except ValueError:
            errors.append(
                f"{line_prefix}: 'Tot. GG/u' = '{ggu_clean}' non è un numero valido"
            )

        # --- Tot. GG/u con AI (positive float ≤ Tot. GG/u) ---
        ggu_ai_clean = ggu_ai_str.strip().replace(",", ".")
        ggu_ai = None
        try:
            ggu_ai = float(ggu_ai_clean)
            if ggu_ai <= 0:
                errors.append(
                    f"{line_prefix}: 'Tot. GG/u con AI' = {ggu_ai} deve essere > 0"
                )
                ggu_ai = None
            elif ggu is not None and ggu_ai > ggu:
                errors.append(
                    f"{line_prefix}: 'Tot. GG/u con AI' ({ggu_ai}) > 'Tot. GG/u' ({ggu}) — "
                    "l'AI non può aumentare l'effort"
                )
        except ValueError:
            errors.append(
                f"{line_prefix}: 'Tot. GG/u con AI' = '{ggu_ai_clean}' "
                "non è un numero valido"
            )

        # --- % Incidenza AI (integer 0-100, no '%' symbol) ---
        pct_clean = pct_str.strip()
        if "%" in pct_clean:
            errors.append(
                f"{line_prefix}: '% Incidenza AI' = '{pct_clean}' contiene il simbolo '%' — "
                "deve essere un intero senza simbolo (es. 29, non 29%)"
            )
            pct_clean = pct_clean.replace("%", "").strip()

        pct = None
        try:
            pct = int(pct_clean)
            if not 0 <= pct <= 100:
                errors.append(
                    f"{line_prefix}: '% Incidenza AI' = {pct} fuori range [0, 100]"
                )
            # Consistency with formula: % = round((ggu - ggu_ai) / ggu * 100)
            if ggu is not None and ggu_ai is not None and ggu > 0:
                expected_pct = round((ggu - ggu_ai) / ggu * 100)
                if abs(pct - expected_pct) > PCT_TOLERANCE:
                    errors.append(
                        f"{line_prefix}: '% Incidenza AI' = {pct} non coerente con la formula "
                        f"((GG/u - GG/u AI) / GG/u × 100) = {expected_pct} "
                        f"(tolleranza ±{PCT_TOLERANCE}). "
                        f"Correggilo a {expected_pct}"
                    )
        except ValueError:
            errors.append(
                f"{line_prefix}: '% Incidenza AI' = '{pct_clean}' non è un intero valido"
            )

        # --- Consistency: Tot. GG/u = GG/u_base × Numero Macro-funzioni ---
        if (
            complessita_clean in COMPLEXITY_BASE
            and n_macro is not None
            and ggu is not None
        ):
            base = COMPLEXITY_BASE[complessita_clean]
            expected_ggu = base * n_macro
            if abs(ggu - expected_ggu) > GGU_TOLERANCE:
                errors.append(
                    f"{line_prefix}: 'Tot. GG/u' = {ggu} non corrisponde a "
                    f"GG/u_base({complessita_clean})={base} × Macro-funzioni={n_macro} "
                    f"= {expected_ggu} (tolleranza ±{GGU_TOLERANCE}). "
                    f"Correggilo a {expected_ggu}"
                )

    return errors


def count_data_rows(csv_path: str) -> int:
    path = Path(csv_path)
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    reader = csv.reader(lines, delimiter=";")
    rows = list(reader)
    return sum(1 for r in rows[1:] if not all(c.strip() == "" for c in r))


def main():
    if len(sys.argv) != 2:
        print(
            "Uso: python3 validate_wbs_csv.py <percorso_file_csv>",
            file=sys.stderr,
        )
        sys.exit(2)

    csv_path = sys.argv[1]
    errors = validate(csv_path)

    if errors:
        print(
            f"❌ CSV non valido: {len(errors)} errore/i trovato/i in '{csv_path}':"
        )
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        n = count_data_rows(csv_path)
        print(f"✅ CSV valido: {n} righe dati verificate con successo in '{csv_path}'")
        sys.exit(0)


if __name__ == "__main__":
    main()
