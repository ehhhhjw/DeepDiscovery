# Statistical notes and source consistency

The original values remain in [DATA_TABLES.md](DATA_TABLES.md) and the CSV files. The calculations below are **derived from those supplied tables**, not new experimental observations. Reported claims are quoted separately so readers can distinguish source statements from arithmetic checks.

## 1. SWE-bench Verified: paired results

Source: Data one, lines 153–156; Reviewer-A-Q1/W4, lines 11–13 and 99.

| Derived quantity | Value |
| --- | ---: |
| Paired instances | 500 |
| Both systems solved | 350 |
| DeepDiscovery-enhanced system only solved | 43 |
| ACoder baseline only solved | 2 |
| Neither system solved | 105 |
| ACoder baseline solved | 352 / 500 = 70.4% |
| DeepDiscovery-enhanced system solved | 393 / 500 = 78.6% |
| Net additional solved instances | 41 |
| Absolute solve-rate improvement | 8.2 percentage points |
| Relative solve-rate improvement over ACoder | 11.647727% |

For the 45 discordant pairs, the two-sided **exact McNemar test**, using the binomial null with success probability 0.5, gives:

```text
p = 2 × [C(45, 0) + C(45, 1) + C(45, 2)] / 2^45
  = 5.88897819397971 × 10^-11
```

This p-value is calculated here; the rebuttal supplies the contingency table but does not state this numeric p-value. The existing [result summary](../SWE-Bench-Verified_logs_trajs/ACoder.20250901_final.json) reports 500 total and 393 resolved instances, matching the enhanced-system marginal. The source does not provide baseline/enhanced outcomes joined by instance ID, so the four paired cells cannot be independently reconstructed from this supplement alone.

## 2. Three-run FRR results

Source: Data two, lines 160–168. Expressions are evaluated as exact rational numbers before normalization by 27. Displayed percentages below are rounded to six decimal places.

| Method | Run 1 FRR (%) | Run 2 FRR (%) | Run 3 FRR (%) | Mean FRR (%) |
| --- | ---: | ---: | ---: | ---: |
| Claude Code(Native) | 85.185185 | 88.888889 | 92.592593 | 88.888889 |
| DeepWiki | 83.395062 | 88.888889 | 94.814815 | 89.032922 |
| CodeWiki | 83.950617 | 90.370370 | 90.185185 | 88.168724 |
| RAG | 81.481481 | 82.792475 | 88.888889 | 84.387615 |
| GraphRAG | 86.419753 | 91.604938 | 92.592593 | 90.205761 |
| AST+GraphRAG | 87.201646 | 89.454733 | 94.351852 | 90.336077 |
| DEEPDISCOVERY | 88.888889 | 92.592593 | 96.296296 | 92.592593 |

The reported aggregate FRR values of 84.4% for RAG and 92.6% for DeepDiscovery (Reviewer-C-Q2/C-W3) agree with these means when rounded to one decimal place.

### Paired check: DeepDiscovery versus AST+GraphRAG

| Derived quantity | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| AST+GraphRAG score | 23.5444444444 | 24.1527777778 | 25.4750000000 |
| DeepDiscovery score | 24 | 25 | 26 |
| Paired score difference | 0.4555555556 | 0.8472222222 | 0.5250000000 |

Using the three runs as paired observations (`n = 3`, `df = 2`), a two-sided paired t-test and a Student-t confidence interval for the mean difference give:

| Derived statistic | Value |
| --- | ---: |
| Mean score difference | 0.6092592593 task-score units |
| 95% CI for mean score difference | [0.0901076904, 1.1284108281] task-score units |
| Mean FRR difference | 2.2565157750 percentage points |
| 95% CI for mean FRR difference | [0.3337321867, 4.1792993634] percentage points |
| t statistic | 5.0494521682 |
| Degrees of freedom | 2 |
| Two-sided p-value | 0.0370541522 |
| Relative gain over AST+GraphRAG's mean | 2.4979120796% |
| Run-level win / tie / loss | 3 / 0 / 0 |

Reproduction formulas, with `d` denoting the three paired score differences:

```text
mean_difference = mean(d)
standard_error = sample_standard_deviation(d) / sqrt(3)
t = mean_difference / standard_error
95% CI = mean_difference ± 4.302652729749464 × standard_error
two-sided p (df = 2) = 1 − |t| / sqrt(t² + 2)
FRR difference in percentage points = score_difference × 100 / 27
relative gain (%) = mean_difference / mean(AST+GraphRAG scores) × 100
```

The t-test calculation assumes the three paired run differences are suitable independent observations for this model. With only three runs, it provides a limited run-level check; it does not establish task-level significance or validate the separate claim about 81 task/run pairs.

### Reported claims and discrepancies

| Source | Claim as reported | Check against supplied data |
| --- | --- | --- |
| Reviewer-A-Q2, line 23 | Average gain 0.61 points; “2.26% relative” | 0.61 agrees after rounding in task-score units. 2.26 is the rounded FRR **percentage-point** gain; relative gain over the baseline mean is about 2.50%. |
| Reviewer-A-Q2, line 23 | `t(2) ≈ 5.16`, `p < 0.05`, 95% CI `[+0.10, +1.12]` | Exact table arithmetic yields `t ≈ 5.05`, `p ≈ 0.03705`, and score CI `[+0.09, +1.13]` at two decimals. The reported `p < 0.05` threshold agrees; the stated statistic and endpoints do not reproduce exactly. |
| Reviewer-A-Q2, line 23 | Analysis over 81 task/run pairs: `p < 0.01`; independent RQ2 experiments support stability | Per-task/run outcomes, the task-level test specification, and numeric RQ2 results are not supplied here. These claims cannot be checked from the aggregate run table. |
| Reviewer-A-W2, line 83 | AST+GraphRAG scores `23.54, 24.19, 25.48` | Run 2's expression in Data two is `22+7/8+7/9+5/10 = 24.1527777778`, which rounds to 24.15, not 24.19. |
| Reviewer-A-W2, line 83 | Average improvement `2.21%`, 95% CI `[+0.54%, +3.88%]` | The mean 2.21 is reproducible in percentage points from that paragraph's rounded scores, but not from the exact Data two values. Even using the paragraph's scores, the same three-run paired t procedure gives a CI of approximately `[+0.4878, +3.9320]` percentage points; the stated CI is not reproduced. |
| Reviewer-A-W3 heading, line 87 | Micro precision of `9%–11%` | Retained as a reviewer-framed range; the source supplies no method/run precision table or prediction counts from which to verify it. |

No original score expression or reported comparison is replaced by these calculations. Task-level win/tie/loss counts cannot be inferred from three method/run aggregates.

## 3. Task-level benchmark summaries

Source: Data three (27 rows, lines 174–200) and Data four (40 rows, lines 206–245).

| Derived quantity | Medium-scale benchmark | Large-scale benchmark |
| --- | ---: | ---: |
| Tasks | 27 | 40 |
| Sum of relevant-file counts | 135 | 240 |
| Sum of core-file counts | 28 | 44 |
| Relevant files per task, min–max | 2–10 | 2–16 |
| Core files per task, min–max | 1–2 | 1–3 |
| Input tokens, total | 165,161 | 244,831 |
| Output tokens, total | 73,144 | 106,495 |
| Input + output tokens, total | 238,305 | 351,326 |
| Input tokens per task, mean | 6,117.074074 | 6,120.775000 |
| Output tokens per task, mean | 2,709.037037 | 2,662.375000 |
| Input + output tokens per task, mean | 8,826.111111 | 8,783.150000 |
| Input tokens per task, min–max | 6,023–6,262 | 6,011–6,213 |
| Output tokens per task, min–max | 2,066–3,823 | 2,022–3,542 |

The medium-scale relevant-file sum matches the reported 135 files (Reviewer-A-Q2, line 19). This is a sum over task rows, not a verified count of unique repository files. Its mean input-plus-output tokens rounds to the reported 8,826 (lines 63, 91, 143).

The source's approximate input/output ranges (lines 31, 93) are consistent with these rows at their stated rough precision. The tables do not identify the run or establish whether a row is an average over runs. No per-task timing, tokenization configuration, returned-file counts, or full-text promotion counts are supplied.

## 4. Reported comparison metrics and illustrative values

[reported_comparisons.csv](reported_comparisons.csv) transcribes FRR, MR, execution time, execution tokens, and preprocessing costs. It preserves missing numeric values for DeepDiscovery's “no offline preprocessing required” statement rather than treating it as a measured zero. Runtime, MR, and baseline token values cannot be independently recomputed from the supplied four tables.

The [budget example](METHODS_AND_EXAMPLE.md) is illustrative and is excluded from benchmark totals. Its local arithmetic for the budget split and action priorities is consistent. However, if the example's 8,000-token stopping point and approximately 4,000-token promotion cost belong to the same execution, their total is 12,000, exceeding the stated 10,000-token budget. The source leaves that continuity unresolved.
