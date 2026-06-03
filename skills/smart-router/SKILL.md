---
name: smart-router
description: 'Routes a task to the most cost-effective model by first scoring its complexity with a cheap analyzer model, then executing with the best-fit tier. Trigger this skill ONLY when the user explicitly invokes it in the prompt with an unambiguous routing phrase. Italian triggers — "smart router", "usa lo smart router", "instrada con lo smart router", "scegli tu il modello", "scegli il modello giusto", "ottimizza il costo del modello", "esegui con lo smart router". English triggers — "smart router", "use the smart router", "route this with the smart router", "smart execute", "pick the right model", "use the best model", "optimize the model cost". Also handles router configuration verbs (init / show / use / reset / detect / status / list-clients / help). Do NOT trigger on the bare words "route"/"routing"/"instrada" used in their networking or web-framework sense (e.g. "add a route", "fix the routing table"). This skill does NOT auto-intercept tasks and has no enable/disable session state: the user must invoke it explicitly every time.'
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
│   └── router.py             ← config CLI (verbs: init/show/use/reset/status/…)
└── evals/
    ├── evals.json            ← test prompts + expected routing
    └── scripts/
        └── route.py          ← offline routing-decision validator
```

The skill's runtime model selection is **runtime-agnostic**: it operates on abstract *tiers* (`cheap`, `balanced`, `heavy`, `frontier`, `code-mid`, `code-heavy`, `analyzer`). Tier → real slug resolution is delegated to `models.json`, organized **per client** (Cursor, Claude Code, Codex CLI, …). The same skill installation can therefore be shared across multiple CLI clients.

## How the user invokes this skill

This skill has **no session toggle**. It runs only when the user explicitly invokes it in the prompt — either to **route a task** (e.g. "usa lo smart router per…", "route this with the smart router", "scegli tu il modello per…") or to **manage the model configuration** via one of the verbs below. There is no "always on" mode and no `~/.smart-router.state` file: each routing request must be explicit. Do not self-trigger on the bare words "route"/"routing"/"instrada" when they refer to networking or web routes.

## Router configuration commands (verbs)

The user can manage the tier→slug configuration by name. Each verb maps 1:1 to a sub-command of `router.py`. When the user says any of the trigger phrases below, run the corresponding command and surface its output to the user.

> **Path convention**: the agent's working directory is usually the user's project, **not** the skill folder. Always invoke the scripts with their full path:
>
> - `python3 ~/.agents/skills/smart-router/bin/router.py <verb>`
> - `python3 ~/.agents/skills/smart-router/evals/scripts/route.py <args>`
>
> The short `bin/router.py` / `evals/scripts/route.py` forms used below are shorthand for these full paths.

| Verb (it/en)                                  | CLI sub-command                             | What it does                                                  |
|-----------------------------------------------|---------------------------------------------|---------------------------------------------------------------|
| `stato` / `status`                            | `bin/router.py status`                      | Show active client + tier mapping                             |
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
python3 ~/.agents/skills/smart-router/bin/router.py init

python3 ~/.agents/skills/smart-router/bin/router.py init --client claude-code -y

python3 ~/.agents/skills/smart-router/bin/router.py init --client generic --slugs "model-a,model-b" -y
```

## When to run the routing workflow

Run the workflow below **only for the task the user explicitly asked to route**. There is no session state and no auto-interception: if the user did not invoke a routing trigger (see the skill description), do not route — just answer normally. When the user does invoke it, route the single task they provided.

## Workflow

### Step 0 — Resolve the active client

```bash
python3 ~/.agents/skills/smart-router/bin/router.py show   # prints the active client's mapping
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
echo "$ANALYZER_OUTPUT" | python3 ~/.agents/skills/smart-router/evals/scripts/route.py --eval 1
```

### Step 2 — Select the tier

Evaluation order (this matches `evals/scripts/route.py` exactly):

1. **Rule A — Code-override**: if it fires, return immediately.
2. **Rule B — Multi-peak override**: else, if it fires, return immediately.
3. **Rule D — Base table**: else, pick the base tier from `overall`.
4. **Rule C — Context-size guard**: finally, apply this *post-adjustment* to the base-table result.

So A and B are early-exit overrides (first match wins); C is **not** an early-exit rule — it only nudges the base-table outcome. All ranges are semi-open: `[a, b)`.

#### Rule A — Code-override (global, early exit)

Applies regardless of `overall`:

- `code >= 4` AND `overall >= 3.5` → **`code-heavy`**
- `code >= 4` AND `overall <  3.5` → **`code-mid`**

#### Rule B — Multi-peak override (early exit)

Applies when ≥3 of the 6 dimensions are `>= 4`:

- → **`heavy`** (or **`frontier`** if also `overall >= 4.0`)

> Rationale: the weighted-overall formula can under-rate tasks where several non-code dimensions are high but one or two are very low (e.g. a long analytical essay scores `code=1` which drags the mean down). The multi-peak override fixes this.

#### Rule D — Base table by `overall`

Reached only when neither A nor B fired:

| `overall`        | Tier        |
|------------------|-------------|
| `[1.0, 1.8)`     | `cheap`     |
| `[1.8, 3.0)`     | `balanced`  |
| `[3.0, 4.2)`     | `heavy`     |
| `[4.2, 5.0]`     | `frontier`  |

#### Rule C — Context-size guard (post-adjustment, defensive)

Applied **after** the base table, never as an early exit:

- if `context_size == 5` AND the base tier is `cheap` → escalate to **`balanced`**.

> **Note**: with the current weighted formula, `context_size == 5` alone forces `overall ≥ 1.857`, which already maps to `balanced` (or higher). So this guard is **defensive** — it documents the invariant "never `cheap` for a huge context" and protects against future formula/threshold changes, but in practice it does not fire. If you lower the `cheap` threshold or change the formula, re-check this rule.

### Step 3 — Resolve tier → slug and announce

1. Read the active client's tier mapping from `models.json` (via `python3 ~/.agents/skills/smart-router/bin/router.py show` or by parsing the JSON directly).
2. Resolve the chosen tier to a concrete slug.
3. Show the user a one-line summary (skip if `overall <= 1.5` and tier `cheap` — silent fast path):

```text
🔍 Complexity: 3.2/5 (dominant: code, reasoning) → tier code-mid → gpt-5.3-codex  [client: copilot]
```

### Step 4 — Execute with the selected model

Spawn a second subagent pinned to the resolved slug, with the original task as the prompt. Pass along all files, attachments, and context the user provided. How you pin the model depends on the runtime:

- **Cursor**: use the `Task` tool with `model: "<resolved-slug>"`.
- **GitHub Copilot CLI**: launch the subagent with the model forced, e.g. `copilot --model <resolved-slug> -p "<task>"` (or set `COPILOT_MODEL=<resolved-slug>` for that invocation).
- **Other clients**: use the client's native "spawn subagent / sub-task with a chosen model" mechanism.

The same applies to the **Step 1** analyzer subagent (pin it to `tiers.analyzer`). Save outputs where appropriate (files to the current directory, or wherever the user expects them).

## Edge cases

- **Task is already trivial and the user is in a hurry**: if `overall <= 1.5` and tier `cheap`, skip the announcement banner and just execute silently.
- **User specifies a model explicitly**: respect the user's choice — don't override it. This skill is for when the user hasn't specified a preference.
- **JSON-fallback strategy** (analyzer fails / returns malformed JSON / scores out of range):
  1. Try once more with a stricter prompt: `RESPOND WITH JSON ONLY. NO PROSE.`
  2. If it still fails, fall back to the active client's `fallback` slug.
  3. Inform the user: `⚠️ Routing analysis failed; falling back to <slug>.`
- **Very long context (`context_size == 5`)**: see rule **C** above — never use `cheap` for a 5.
- **No client configured / `models.json` missing**: prompt the user to run `python3 ~/.agents/skills/smart-router/bin/router.py init` and stop. Do not guess slugs.
- **User runs the skill from a different CLI than configured**: `status` shows the active client. Suggest `python3 ~/.agents/skills/smart-router/bin/router.py detect` and `use` to switch.
- **Legacy state file**: earlier versions wrote `~/.smart-router.state` for a session toggle. That mechanism is gone; the file (if present) is ignored and can be safely deleted.

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
2. Pipe it into the validator: `python3 ~/.agents/skills/smart-router/evals/scripts/route.py --eval <id>`
3. Compare against `expected_routing` in `evals/evals.json`.
4. (Optional) Run **Step 4** on the resolved slug and inspect the output.

Quick selfcheck of the routing table:

```bash
python3 ~/.agents/skills/smart-router/evals/scripts/route.py --selfcheck
```

When you change the formula or the routing table, rerun the suite and update the expected outcomes if they drift.
