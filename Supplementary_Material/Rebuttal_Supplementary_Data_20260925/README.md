# Rebuttal supplementary data — 2026-09-25

This supplement organizes the numerical evidence in `Rebuttle reply-version20260925 (2).md`: the SWE-bench Verified paired outcomes, three-run FRR scores, task-level industrial benchmark statistics, and reported baseline comparisons. It also includes the annotation context and an illustrative budget example needed to interpret those numbers.

Values transcribed from the source and values calculated from its tables are explicitly distinguished. No experiments were rerun. Statistical discrepancies in the source are documented in [STATISTICAL_NOTES.md](STATISTICAL_NOTES.md), without changing the reported data.

## Contents

| File | Contents | Source location |
| --- | --- | --- |
| [DATA_TABLES.md](DATA_TABLES.md) | Readable versions of all four original tables | Data one–four, lines 151–245 |
| [data_one_swe_bench_contingency.csv](data_one_swe_bench_contingency.csv) | Paired 2×2 outcomes for 500 SWE-bench Verified instances | Data one, lines 153–156 |
| [data_two_frr_runs.csv](data_two_frr_runs.csv) | 21 method/run records: original expressions, exact sums, decimal sums, and normalized FRR | Data two, lines 160–168 |
| [data_three_medium_tasks.csv](data_three_medium_tasks.csv) | File counts and input/output tokens for 27 medium-scale tasks | Data three, lines 172–200 |
| [data_four_large_tasks.csv](data_four_large_tasks.csv) | File counts and input/output tokens for 40 large-scale tasks | Data four, lines 204–245 |
| [reported_comparisons.csv](reported_comparisons.csv) | 14 reported metric records for RAG, AST+GraphRAG, and DeepDiscovery | Reviewer-C-Q2, Reviewer-A-W3, Reviewer-C-W3; lines 63, 91, 143 |
| [STATISTICAL_NOTES.md](STATISTICAL_NOTES.md) | Derived summaries, statistical checks, reported claims, and limitations | Reviewer-A-Q1/Q2/W2 plus Data one–four |
| [METHODS_AND_EXAMPLE.md](METHODS_AND_EXAMPLE.md) | Budget procedure and illustrative numeric example, with an arithmetic caveat | Reviewer-B-Q2/C-Q1 and Algorithm one / Example one |

## Data definitions

All CSV files use UTF-8, a header row, and comma-separated fields. Empty metric cells mean that no numeric value is supplied or the field is not applicable; they do not mean zero. Decimal results are rounded to 12 places in `data_two_frr_runs.csv`; its expressions and exact fractions retain the full precision of the source.

| File | Fields and interpretation |
| --- | --- |
| `data_one_swe_bench_contingency.csv` | `deepdiscovery_outcome` is the row outcome for the DeepDiscovery-enhanced ACoder system; `acoder_solved` and `acoder_unsolved` are paired baseline counts. |
| `data_two_frr_runs.csv` | `method` retains the source label; `run_id` is 1–3; `run_label` retains `mix`, `medium`, and `max` exactly; `task_count` is 27; `score_expression` is the reported expression; `score_exact_fraction`, `score_decimal`, and `frr_percent` are derived. The meanings of the run labels are not specified in the source. |
| `data_three_medium_tasks.csv`, `data_four_large_tasks.csv` | `task_id` is local to its benchmark; `files` and `core_files` are task-level relevant-file and core-file counts; `input_tokens` and `output_tokens` are reported token counts. Task IDs must not be joined across benchmarks. |
| `reported_comparisons.csv` | `method`, `metric`, and `unit` identify the measurement; `value` holds a scalar, or `lower`/`upper` hold reported endpoints; `approximate` records source approximation; `source_section`, `source_lines`, and `notes` retain context. MR endpoints are not labeled as confidence intervals because the source does not define their interval type. |

### FRR score versus FRR percentage

Reviewer-A-Q2 (line 21) defines FRR with a task denominator of **T = 27**, not the sum of 135 relevant-file counts. A task contributes 1 when all files are recovered, or the recovered-file fraction when all core files are recovered but some other files are missing. The excerpt does not explicitly state the contribution when core-file recovery fails; this supplement does not reconstruct missing task-level scores.

Data two contains sums of task contributions, rather than percentages:

```text
score = sum of the terms in score_expression
FRR (%) = 100 × score / 27
FRR difference (percentage points) = 100 × (score_A − score_B) / 27
```

For example, DeepDiscovery run 1 is `23+1/2+5/10 = 24`, corresponding to `88.888889%` FRR. The same 27 tasks are described as evaluated in three independent runs. The source supplies method/run aggregates, not the 81 individual task/run outcomes for each method.

### Annotation and experiment context

Reviewer-A-Q3 (lines 29–31) reports that the gold relevant-file sets were defined before DeepDiscovery development by **six domain experts: four technical experts and two senior experts**, from different business scenarios. They identified the minimal file set needed for task understanding and completion and resolved ambiguous cases through joint review. No numerical agreement statistic, individual annotator labels, or detailed agreement counts are supplied.

The source associates the task-level token statistics with DeepDiscovery in Reviewer-A-W3 (lines 91–93), but Data three/four do not identify a specific run, tokenizer, or aggregation across runs. File-count sums count task/file occurrences; the tables do not identify files well enough to establish distinct-file totals across tasks.

Reviewer-A-Q1/W4 (lines 11, 99) identifies **ACoder** as the SWE-bench baseline, reports a reproduced solve rate of **70.4%**, and describes it as ranked second on the August 2025 SWE-bench Verified leaderboard. The source states that the enhanced system uses the same model, prompts, tools, retries, and budget. Exact model/version identifiers and numeric budgets are not supplied in this document. These are source statements, not independently verified configuration matches.

## Provenance and available evidence

- Source document: `Rebuttle reply-version20260925 (2).md` (document version 2026-09-25).
- Source SHA-256: `be4021706318442a669daeb4aa9cea1a5eaab08899853203436534099ba4af1d`.
- Extracted on 2026-09-28. Source references use 1-based lines, including blank lines, in that exact file.
- Non-breaking spaces are normalized for readability. CSV table labels omit presentation-only bold markup. Source method labels and fractional expressions are otherwise retained.
- Existing public evidence: [SWE-bench result summary](../SWE-Bench-Verified_logs_trajs/ACoder.20250901_final.json), [execution trajectories](../SWE-Bench-Verified_logs_trajs/acoder_trajs/), and [baseline code](../AST+Graph_RAG_PROJECT/README.md).

The existing SWE-bench summary independently agrees with Data one's enhanced-system marginal: **393 resolved out of 500**. That agreement does not validate the baseline outcome of every paired instance; the rebuttal's 2×2 table does not include the paired instance IDs.

Reviewer-A-W1 (lines 75–79) states that the industrial repositories cannot be fully released. This supplement contains the aggregate and task-level statistics already present in the supplied document. It does not contain industrial source code, task descriptions, gold-file identities, per-task retrieval outputs, or new disclosure approvals. Future-release promises in the rebuttal are not treated as available data.
