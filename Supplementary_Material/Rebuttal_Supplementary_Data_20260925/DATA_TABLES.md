# Supplementary data tables

Source: `Rebuttle reply-version20260925 (2).md`, appendix Data one–four (lines 151–245). Non-breaking spaces are normalized to ordinary spaces; all table values, method labels, run labels, and score expressions are retained. These are reported data, not newly executed experiments.

For CSV schemas and provenance, see [README.md](README.md). For derived results and discrepancies with narrative claims, see [STATISTICAL_NOTES.md](STATISTICAL_NOTES.md).

## Data one: Paired 2×2 Contingency Table for McNemar’s Test (SWE-bench Verified)

|  | ACoder Solved | ACoder Unsolved |
| --- | --- | --- |
| **DeepDiscovery Solved** | 350 | 43 |
| **DeepDiscovery Unsolved** | 2 | 105 |

## Data two: Raw FRR Data from Three Independent Runs on 27 Tasks

|  | run 1（mix） | run 2（medium） | run 3（max） |
| --- | --- | --- | --- |
| Claude Code(Native) | 23 | 24 | 25 |
| DeepWiki | 22+1/4+1/6+1/10 | 24 | 25+6/10 |
| CodeWiki | 22+1/6+5/10 | 24+4/10 | 24+1/4+1/10 |
| RAG | 22 | 22+1/7+1/9+1/10 | 24 |
| GraphRAG | 23+2/6 | 24+1/3+4/10 | 25 |
| AST+GraphRAG | 23+4/9+1/10 | 22+7/8+7/9+5/10 | 25+3/8+1/10 |
| **DEEPDISCOVERY** | **23+1/2+5/10** | **24+4/8+5/10** | **26** |

## Data three: Task-Level Statistics for the Medium-Scale Benchmark

| Task ID | Files | Core Files | Input Token | Output Token |
| --- | --- | --- | --- | --- |
| 1 | 2 | 1 | 6142 | 2066 |
| 2 | 2 | 1 | 6114 | 2788 |
| 3 | 3 | 1 | 6212 | 2232 |
| 4 | 3 | 1 | 6262 | 2474 |
| 5 | 3 | 1 | 6025 | 2236 |
| 6 | 3 | 1 | 6128 | 2521 |
| 7 | 4 | 1 | 6142 | 2302 |
| 8 | 4 | 1 | 6098 | 2325 |
| 9 | 4 | 1 | 6112 | 2428 |
| 10 | 4 | 1 | 6248 | 2491 |
| 11 | 4 | 1 | 6029 | 2677 |
| 12 | 4 | 1 | 6103 | 2427 |
| 13 | 5 | 1 | 6088 | 2288 |
| 14 | 5 | 1 | 6122 | 2442 |
| 15 | 5 | 1 | 6049 | 2556 |
| 16 | 5 | 1 | 6077 | 2875 |
| 17 | 5 | 1 | 6122 | 2531 |
| 18 | 5 | 1 | 6088 | 2388 |
| 19 | 6 | 1 | 6102 | 2740 |
| 20 | 6 | 2 | 6211 | 3022 |
| 21 | 6 | 1 | 6118 | 2894 |
| 22 | 6 | 1 | 6032 | 3321 |
| 23 | 7 | 1 | 6121 | 3420 |
| 24 | 7 | 1 | 6023 | 3338 |
| 25 | 8 | 1 | 6113 | 3012 |
| 26 | 9 | 1 | 6032 | 3527 |
| 27 | 10 | 1 | 6248 | 3823 |

## Data four: Task-Level Statistics for the Large-Scale Benchmark

| Task ID | Files | Core Files | Input Token | Output Token |
| --- | --- | --- | --- | --- |
| 1 | 2 | 1 | 6124 | 2112 |
| 2 | 2 | 2 | 6202 | 2082 |
| 3 | 2 | 1 | 6109 | 2022 |
| 4 | 2 | 1 | 6011 | 2063 |
| 5 | 3 | 1 | 6107 | 2146 |
| 6 | 3 | 1 | 6088 | 2203 |
| 7 | 3 | 1 | 6042 | 2412 |
| 8 | 3 | 1 | 6152 | 2114 |
| 9 | 3 | 1 | 6092 | 2270 |
| 10 | 4 | 1 | 6132 | 2321 |
| 11 | 4 | 1 | 6087 | 2292 |
| 12 | 4 | 1 | 6183 | 2421 |
| 13 | 4 | 1 | 6023 | 2166 |
| 14 | 4 | 1 | 6143 | 2218 |
| 15 | 5 | 1 | 6136 | 2428 |
| 16 | 5 | 2 | 6148 | 2477 |
| 17 | 5 | 1 | 6076 | 2372 |
| 18 | 5 | 1 | 6148 | 2630 |
| 19 | 5 | 1 | 6177 | 2524 |
| 20 | 5 | 1 | 6204 | 2322 |
| 21 | 6 | 1 | 6092 | 2803 |
| 22 | 6 | 1 | 6146 | 2744 |
| 23 | 6 | 1 | 6117 | 2865 |
| 24 | 6 | 1 | 6102 | 2921 |
| 25 | 6 | 1 | 6183 | 2718 |
| 26 | 7 | 1 | 6155 | 2831 |
| 27 | 7 | 1 | 6089 | 2926 |
| 28 | 7 | 1 | 6042 | 2722 |
| 29 | 7 | 1 | 6144 | 3213 |
| 30 | 8 | 1 | 6058 | 2742 |
| 31 | 8 | 1 | 6174 | 2932 |
| 32 | 8 | 1 | 6213 | 3025 |
| 33 | 8 | 1 | 6111 | 3228 |
| 34 | 8 | 1 | 6104 | 3542 |
| 35 | 9 | 3 | 6066 | 3370 |
| 36 | 9 | 1 | 6127 | 3128 |
| 37 | 10 | 1 | 6059 | 3027 |
| 38 | 12 | 1 | 6145 | 3361 |
| 39 | 13 | 1 | 6186 | 3525 |
| 40 | 16 | 1 | 6134 | 3277 |
