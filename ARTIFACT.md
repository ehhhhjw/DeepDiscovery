# Artifact — DeepDiscovery

**Anonymous, publicly accessible repository:**
<https://anonymous.4open.science/r/DeepDiscovery-4A4F>

This artifact supports the verifiability of the main claims in the paper
*"DeepDiscovery: A Location–Inference Framework for Task-Level Repository
Understanding in Industrial Codebases."* All materials are anonymized and do not
reveal the authors' identities or organization. No login is required to browse or
download the repository.

---

## 1. What the artifact contains

The artifact has **four** parts: a runnable reference implementation of the
method, two supplementary evidence folders described in the paper, and a
supplement organizing the numerical evidence from the 2026-09-25 rebuttal.

### (A) Runnable DeepDiscovery reference implementation — `src/`, `vendor/`, `tests/`
A self-contained TypeScript implementation of the paper's two-stage
**Location–Inference** framework, extracted and de-coupled from the internal
production system so it can be run and inspected independently:

- `src/location/` — environment-aware analysis, adaptive repository compression,
  rule-guided anchor localization (`Score_loc`).
- `src/inference/` — multi-relational reference graph (tree-sitter), budget-aware
  expansion (`Priority = Gain/Cost`, `τ_stop`), second-round refinement, and
  metadata-first context construction (`κ` promotion).
- `src/core/deepDiscovery.ts` — the Algorithm 1 orchestrator.
- `vendor/repoamap/` — the actual repository-compression engine used by the
  method (bundled; built locally, no private registry).
- `tests/` — unit + mocked end-to-end tests (XML parser, reference graph,
  compression engine, full pipeline, result cache).

This part lets a reviewer inspect and execute the **method itself** (scoring,
expansion, stopping, metadata-first context construction), independently of the
proprietary industrial data.

### (B) `Supplementary_Material/SWE-Bench-Verified_logs_trajs/` — end-to-end evidence
Execution trajectories and logs of the DeepDiscovery-equipped system on the
public **SWE-bench Verified** benchmark (the publicly reproducible portion of the
evaluation):

- `ACoder.20250901_final.json` — official SWE-bench result summary.
- `acoder_trajs/` — 500 per-instance execution trajectories (`.md`).
- `acoder_logs/` — 500 per-instance run directories (`eval.sh`, `patch.diff`,
  `report.json`, `run_instance.log`, `test_output.txt`).
- `acoder_diff.jsonl` — predicted patch per instance (500 lines).

### (C) `Supplementary_Material/AST+Graph_RAG_PROJECT/` — baseline code (desensitized)
Desensitized experimental code for the controlled method-level comparison
baselines **RAG**, **GraphRAG**, and **AST+GraphRAG** (paper RQ1), with three
subprojects (`AST_Tree_Graph/`, `rag-python-tools/`, `graph_search_demo/`) and
its own `README.md`. Sample data, keys, internal domains, and business
identifiers are replaced with placeholders.

### (D) `Supplementary_Material/Rebuttal_Supplementary_Data_20260925/` — rebuttal data

[Tables, CSV files, and statistical notes](Supplementary_Material/Rebuttal_Supplementary_Data_20260925/README.md)
organized from the 2026-09-25 rebuttal: a paired SWE-bench contingency table,
21 method/run FRR records, 27 medium-scale and 40 large-scale task-statistic
records, and reported baseline comparisons. Source values are retained alongside
clearly labeled derived checks and unresolved statistical discrepancies. The
package also records annotation context and a separate illustrative budget
example; it does not add industrial source code or per-task/run retrieval outputs.

---

## 2. How to independently verify

### (A) Run the reference implementation
Requirements: Node.js ≥ 18.

```bash
npm install        # also builds the bundled repomap engine (postinstall)
npm run build      # compile the TypeScript sources
npm test           # vitest: 9 tests across 4 files should pass
```

`npm test` exercises the compression engine, the tree-sitter reference graph, the
result cache, and a mocked end-to-end Location→Inference run (no API key needed).
To run the method against a real repository, set an Anthropic-compatible key and
use the CLI:

```bash
export ANTHROPIC_API_KEY=...        # or ANTHROPIC_BASE_URL for a compatible gateway
npx deepdiscovery --repo <path> --task "<task description>" --verbose
```

Without an API key, the Location file-structure/compression stages still run and
the LLM stage fails with a clear message (graceful degradation).

### (B) Inspect the SWE-bench Verified evidence
The result summary can be recomputed directly from the provided files:

```bash
cd Supplementary_Material/SWE-Bench-Verified_logs_trajs
# resolved / total from the official summary
node -e "const d=require('./ACoder.20250901_final.json'); \
  console.log('resolved', d.resolved_instances, '/', d.total_instances)"
```

| Metric | Value |
|---|---|
| Total instances | 500 |
| Resolved | **393** |
| **Solve Rate** | **78.6%** |

This matches the 78.6% Solve Rate reported for the DeepDiscovery-enhanced system.
Individual runs can be inspected under `acoder_trajs/` and `acoder_logs/`, and the
predicted patches in `acoder_diff.jsonl`.

### (C) Inspect the baselines
See `Supplementary_Material/AST+Graph_RAG_PROJECT/README.md` for the data flow and
per-subproject setup of the RAG / GraphRAG / AST+GraphRAG baselines.

### (D) Inspect the rebuttal data

Start with the supplement's [README](Supplementary_Material/Rebuttal_Supplementary_Data_20260925/README.md)
for source provenance and CSV definitions, then use its
[statistical notes](Supplementary_Material/Rebuttal_Supplementary_Data_20260925/STATISTICAL_NOTES.md)
for arithmetic checks and the distinction between run-level and task-level
evidence. Reproducing the industrial experiments still requires data absent
from this artifact.

---

## 3. Mapping to paper claims

| Paper claim | Supporting material |
|---|---|
| Method design (Location–Inference, Algorithm 1) | Part (A): `src/` + `vendor/` + `tests/` |
| RQ3 — end-to-end Solve Rate on SWE-bench Verified (78.6%) | Part (B): logs/trajectories + `ACoder.20250901_final.json` |
| RQ1 — controlled method-level comparison (RAG / GraphRAG / AST+GraphRAG) | Part (C): desensitized baseline code |
| Rebuttal numerical evidence: paired outcomes, FRR runs, task/file/token statistics | Part (D): source tables, CSVs, and statistical consistency notes |

---

## 4. Scope, limitations, and justification

The **SWE-bench Verified** evaluation is publicly reproducible: it uses the public
benchmark under its official execution and verification protocol, and this
artifact provides the full run logs, trajectories, patches, and result summary.

The **industrial repository-understanding evaluation** (RQ2/RQ4) should be
interpreted as **organization-internal deployment evidence**. Due to proprietary
source code, compliance restrictions, and confidential deployment assets, the
artifact does **not** include: the full industrial production system integration,
the industrial codebase, internal task descriptions, gold relevant-file
annotations, the relation-extraction specifications, or the full
system-integration details used in that internal evaluation. The reference
implementation in Part (A) reproduces the **method** (scoring, expansion,
stopping, and metadata-first context construction) so that the approach can be
inspected and executed without access to the proprietary data.

After data disclosure is approved, we plan to desensitize the complete
experimental and project data and release the desensitized version publicly.

---

## 5. Anonymity

All provided materials have been anonymized and do not reveal the authors'
identities or organization. Commit history uses an anonymized author identity,
and the repository is served without requiring any account.
