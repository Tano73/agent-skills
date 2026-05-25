---
name: smart-router
description: Routes tasks to the most cost-effective model by first scoring complexity with a cheap analyzer model, then executing with the best-fit tier. ALWAYS trigger this skill when the user invokes a router verb — "attiva smart router", "abilita routing", "disattiva routing", "stato router", "smart router on/off/status/init/show/use/reset", "configura smart router", "inizializza router" — or any variant asking to enable/disable/configure automatic routing. Also trigger when the user says "route this", "smart execute", "usa il modello giusto", "ottimizza il costo", "scegli tu il modello". When session routing is ENABLED (check state file ~/.smart-router.state), intercept ALL user tasks automatically — even if the user did not explicitly ask for routing — and route them through this skill before executing.
---

# Smart Router

Route tasks to the most appropriate AI model by spending a tiny amount of cheap-model time upfront to score the task's complexity, then executing with the model best suited to that complexity.

## Why this matters

Running every task on the most powerful model wastes money and time. Running everything on cheap models degrades quality. This skill finds the right balance: a small analysis cost buys a much better routing decision.

## Architecture (file map)

```text
~/.agents/skills/smart-router/
├── SKILL.md                  ← this file (the workflow)
├── models.json               ← multi-client tier→slug mapping (schema v2)
├── bin/
│   └── router.py             ← control CLI (verbs: enable/disable/status/init/…)
└── evals/
    ├── evals.json            ← test prompts + expected routing
    └── scripts/
        └── route.py          ← offline routing-decision validator
```

The skill's runtime model selection is **runtime-agnostic**: it operates on abstract *tiers* (`cheap`, `balanced`, `heavy`, `frontier`, `code-mid`, `code-heavy`, `analyzer`). Tier → real slug resolution is delegated to `models.json`, organized **per client** (Cursor, Claude Code, Codex CLI, …). The same skill installation can therefore be shared across multiple CLI clients.

## Router commands (verbs)

The user can invoke router commands by name. Each verb maps 1:1 to a sub-command of `bin/router.py`. When the user says any of the trigger phrases below, run the corresponding command and surface its output to the user.

| Verb (it/en)                                  | CLI sub-command                             | What it does                                                  |
|-----------------------------------------------|---------------------------------------------|---------------------------------------------------------------|
| `attiva` / `abilita` / `enable` / `on`        | `bin/router.py enable`                      | Turn on session routing                                       |
| `disattiva` / `disabilita` / `disable` / `off`| `bin/router.py disable`                     | Turn off session routing                                      |
| `stato` / `status`                            | `bin/router.py status`                      | Show state + active client + tier mapping                     |
| `rileva` / `detect`                           | `bin/router.py detect`                      | Detect which CLI client is currently running                  |
| `inizializza` / `init` / `setup` / `configura`| `bin/router.py init [--client X]`           | Interactive wizard: configure tier→slug mapping for a client  |
| `mostra` / `show`                             | `bin/router.py show [--client X]`           | Print the client's current mapping                            |
| `usa` / `use` / `switch`                      | `bin/router.py use <client>`                | Switch the active client                                      |
| `reset` / `rimuovi config`                    | `bin/router.py reset [--client X]`          | Delete a client's configuration                               |
| `lista client` / `list-clients`               | `bin/router.py list-clients`                | List configured clients and known templates                   |
| `?` / `help` / `aiuto`                        | `bin/router.py help`                        | Show all available commands                                   |

### `init` — interactive setup wizard

When the user asks to initialize/setup the router, run `bin/router.py init` and present its prompts to the user. The wizard:

1. **Detects the current client** automatically by inspecting environment variables (`CURSOR_AGENT`, `CLAUDECODE`, `CODEX_CLI`, `AIDER_MODEL`, …) and the `PATH`.
2. Asks the user to **confirm or override** the detected client.
3. Proposes the **default slug list** for that client (from `known_clients` in `models.json`). The user can accept or paste their own comma-separated list.
4. For **each tier** (`analyzer`, `cheap`, `balanced`, `heavy`, `frontier`, `code-mid`, `code-heavy`), the wizard proposes a default slug and lets the user override.
5. Asks for a **fallback** slug (used when routing analysis fails).
6. Saves the config under `clients.<client>` in `models.json` and sets `active_client` to this client if none was active.

For non-interactive use (e.g. CI or scripted setup), pass `-y` to accept all defaults and optionally `--slugs "a,b,c"` to pre-supply the list.

**Examples**:

```bash
bin/router.py init

bin/router.py init --client claude-code -y

bin/router.py init --client generic --slugs "model-a,model-b" -y
```

## Session State (Toggle)

The skill is enabled or disabled session-wide via `~/.smart-router.state` (literal text `enabled` or `disabled`). Manage it through `bin/router.py enable|disable|status`. The Python script is the source of truth — do not write the file by hand from the agent. Status distinguishes four cases: `enabled`, `disabled`, `missing` (treated as disabled), `corrupt` (treated as disabled with a warning).

### Checking state before every task

**At the start of every invocation** (even when the user didn't explicitly ask for routing), check the state:

```bash
bin/router.py status >/dev/null && state=$(cat ~/.smart-router.state 2>/dev/null | tr -d '[:space:]')
case "${state:-disabled}" in
  enabled)  do_routing="yes" ;;
  *)        do_routing="no"  ;;   # disabled, missing, or corrupt → safe default
esac
```

- If `enabled`: proceed with the full routing workflow below for the current task.
- If `disabled`: only run the routing workflow if the user explicitly asked for it (e.g. "route this", "smart execute").

When routing is enabled, **every task the user asks goes through the router**, even simple ones like "rename this variable".

## Workflow

### Step 0 — Resolve the active client

```bash
bin/router.py show          # prints the active client's mapping
```

If no client is configured (fresh install), prompt the user to run `init` and stop. Do not invent slugs.

### Step 1 — Analyze complexity (cheap model)

Resolve `tiers.analyzer` from the active client's config and spawn a subagent with that slug. The analyzer scores the task on six dimensions (1–5 each) and returns a JSON object.

> **Context-size hint for the analyzer**: do NOT paste entire attached files into the analyzer prompt. Pass only the user's task text plus a short summary: file names, sizes, and the first ~40 lines of each. The analyzer needs to *gauge* the work, not perform it. If the user attached N files, append `[attached: N files, total ≈XXX KB, names: …]` to the task.

**Subagent prompt template** (copy verbatim, replacing `<TASK_TEXT>` and `<ATTACHMENTS_SUMMARY>`):

```text
Analyze the complexity of the following task and return ONLY a JSON object with no extra text, no markdown fences, no commentary.

Task:
<TASK_TEXT>

Attachments (summary only, do not analyze content deeply):
<ATTACHMENTS_SUMMARY>

Score each dimension from 1 to 5 using the rubrics below. Be precise — do not default to 3 when unsure.

---

DIMENSION RUBRICS:

**reasoning** — logical steps, inference chains, multi-hop dependencies
  1 = single lookup or mechanical operation (e.g. "what is 2+2", "convert this date format")
  2 = 2-3 sequential steps, no branching (e.g. "summarize this paragraph")
  3 = multi-step process with some conditional logic (e.g. "analyze this dataset and identify trends")
  4 = complex reasoning with interdependencies, trade-offs, or synthesis across domains
  5 = frontier reasoning: novel proofs, complex system design, research-level analysis

**code** — code generation, refactoring, debugging, architecture
  1 = trivial: rename a variable, fix a typo, convert data format
  2 = simple function or script, one concept
  3 = moderate: multiple functions, a class, or use of a library API
  4 = significant: async/concurrent patterns, API client with error handling, framework migration, design patterns, test suites
  5 = complex architecture: distributed systems, compilers, OS-level code, complex algorithms, large-scale refactoring

**creativity** — originality, writing quality, novel synthesis
  1 = no creativity needed (format conversion, data extraction)
  2 = minimal: follow a clear template
  3 = moderate: structured writing with some original content
  4 = substantial: long-form original content, persuasive writing, nuanced analysis (e.g. 1000-word essay, brand voice)
  5 = high creativity: fiction, poetry, highly original research, cross-domain synthesis

**context_size** — volume of input/output to process
  1 = tiny: a few lines or a short paragraph
  2 = small: up to ~500 words or a single short file
  3 = medium: 1–5 pages or multiple small files
  4 = large: 5–20 pages, many files, or structured datasets
  5 = very large: entire codebases, books, large datasets

**domain_expertise** — specialized knowledge required beyond general programming/writing
  1 = general knowledge only
  2 = basic technical knowledge
  3 = intermediate domain knowledge (e.g. refactor Python code, SQL joins)
  4 = advanced specialized knowledge (e.g. GDPR compliance, healthcare AI pipeline, PostgreSQL query plan)
  5 = expert-level: frontier ML research, medical diagnosis, legal analysis

**ambiguity** — how underspecified or contradictory the requirements are
  1 = crystal clear: exact input/output specified
  2 = mostly clear: minor gaps but intent is obvious
  3 = some ambiguity: missing edge cases or implicit assumptions
  4 = significant ambiguity: multiple valid interpretations, conflicting requirements
  5 = highly ambiguous: vague goal, no success criteria

---

IMPORTANT CALIBRATION NOTES:
- A task involving async/await refactoring, aiohttp, asyncio.gather, and type hints is code=4.
- A task asking for a 1000+ word analytical essay on a specialized topic (healthcare, ethics, law) is creativity=4 AND domain_expertise=4 AND context_size>=3.
- "Well-known patterns" does not make a task simpler — score what the task demands, not how familiar the pattern is.
- Avoid anchoring on 3.

Compute `overall` as: (sum_of_all_scores + 0.5 * max_score + 0.5 * second_max_score) / 7.0
This gives extra weight to the two highest-scoring dimensions.

Return JSON only, no other text:
{
  "scores": { "reasoning": N, "code": N, "creativity": N, "context_size": N, "domain_expertise": N, "ambiguity": N },
  "overall": <float>,
  "dominant_factors": ["<top 1-2 dimension names>"],
  "rationale": "<one sentence>"
}
```

### Step 1.5 — Parse the analyzer output (robust)

The analyzer subagent should return pure JSON, but sometimes it wraps the output in prose or ```json fences. Always strip first:

1. Find the **first `{`** and the **last matching `}`** in the response.
2. Parse the slice as JSON.
3. Validate that all 6 scores are integers in `[1, 5]` and `overall` is a float in `[1.0, 5.0]`.
4. If any step fails, apply the **JSON-fallback strategy** in Edge cases.

You can also pipe the analyzer's raw output into the offline validator:

```bash
echo "$ANALYZER_OUTPUT" | python3 evals/scripts/route.py --eval 1
```

### Step 2 — Select the tier

Apply the rules **in this order** (first match wins). All ranges are semi-open: `[a, b)`.

#### Rule A — Code-override (global)

Applies regardless of `overall`:

- `code >= 4` AND `overall >= 3.5` → **`code-heavy`**
- `code >= 4` AND `overall <  3.5` → **`code-mid`**

#### Rule B — Multi-peak override

Applies when ≥3 of the 6 dimensions are `>= 4`:

- → **`heavy`** (or **`frontier`** if also `overall >= 4.0`)

> Rationale: the weighted-overall formula can under-rate tasks where several non-code dimensions are high but one or two are very low (e.g. a long analytical essay scores `code=1` which drags the mean down). The multi-peak override fixes this.

#### Rule C — Context-size guard

- `context_size == 5` → at minimum **`balanced`** (never `cheap`).

#### Rule D — Base table by `overall`

| `overall`        | Tier        |
|------------------|-------------|
| `[1.0, 1.8)`     | `cheap`     |
| `[1.8, 3.0)`     | `balanced`  |
| `[3.0, 4.2)`     | `heavy`     |
| `[4.2, 5.0]`     | `frontier`  |

### Step 3 — Resolve tier → slug and announce

1. Read the active client's tier mapping from `models.json` (via `bin/router.py show` or by parsing the JSON directly).
2. Resolve the chosen tier to a concrete slug.
3. Show the user a one-line summary (skip if `overall <= 1.5` and tier `cheap` — silent fast path):

```text
🔍 Complexity: 3.2/5 (dominant: code, reasoning) → tier code-mid → gpt-5.3-codex  [client: cursor]
```

### Step 4 — Execute with the selected model

Spawn a second subagent using `model: "<resolved-slug>"` with the original task as the prompt. Pass along all files, attachments, and context the user provided.

Save outputs where appropriate (files to current directory, or wherever the user expects them).

## Edge cases

- **Task is already trivial and the user is in a hurry**: if `overall <= 1.5` and tier `cheap`, skip the announcement banner and just execute silently.
- **User specifies a model explicitly**: respect the user's choice — don't override it. This skill is for when the user hasn't specified a preference.
- **JSON-fallback strategy** (analyzer fails / returns malformed JSON / scores out of range):
  1. Try once more with a stricter prompt: `RESPOND WITH JSON ONLY. NO PROSE.`
  2. If it still fails, fall back to the active client's `fallback` slug.
  3. Inform the user: `⚠️ Routing analysis failed; falling back to <slug>.`
- **Very long context (`context_size == 5`)**: see rule **C** above — never use `cheap` for a 5.
- **User asks to toggle AND run a task in the same message** (e.g. "attiva il router e poi scrivi..."): handle the toggle first, confirm it, then immediately apply routing to the task in the same turn.
- **State file missing or corrupt**: treat as `disabled` and inform the user they can enable with "attiva smart router".
- **No client configured / `models.json` missing**: prompt the user to run `bin/router.py init` and stop. Do not guess slugs.
- **User runs the skill from a different CLI than configured**: `status` shows the active client. Suggest `bin/router.py detect` and `use` to switch.

## Example routing decisions (fully ricalcolabili)

> Formula: `overall = (sum + 0.5*max + 0.5*second_max) / 7.0`

| Task                                                      | Scores (r,c,cr,ctx,d,a) | overall | Tier         | Trigger       |
|-----------------------------------------------------------|-------------------------|---------|--------------|---------------|
| "What's 42 × 7?"                                          | 1,1,1,1,1,1             | 1.00    | `cheap`      | base table    |
| "Convert this CSV to JSON" (3 rows)                       | 1,1,1,1,1,1             | 1.00    | `cheap`      | base table    |
| "Refactor 200-line Python class to async/await + aiohttp" | 3,4,2,1,3,2             | 2.64    | `code-mid`   | code-override |
| "1200-word essay on AI ethics in healthcare"              | 4,1,4,3,4,2             | 3.14    | `heavy`      | multi-peak    |
| "Design distributed cache + write Go implementation"      | 5,5,3,3,4,3             | 4.00    | `code-heavy` | code-override |
| "3000-word short story in the style of Borges"            | 4,1,5,4,3,3             | 3.50    | `heavy`      | multi-peak    |

## Validation suite

`evals/` contains test prompts. To validate the skill end-to-end:

1. For each eval, run the **Step 1** analyzer subagent and capture the JSON.
2. Pipe it into the validator: `python3 evals/scripts/route.py --eval <id>`
3. Compare against `expected_routing` in `evals/evals.json`.
4. (Optional) Run **Step 4** on the resolved slug and inspect the output.

Quick selfcheck of the routing table:

```bash
python3 evals/scripts/route.py --selfcheck
```

When you change the formula or the routing table, rerun the suite and update the expected outcomes if they drift.
