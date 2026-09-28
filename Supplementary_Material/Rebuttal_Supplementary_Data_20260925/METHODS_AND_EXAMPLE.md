# Budget procedure and illustrative example

Source: appendix Algorithm one and Example one (lines 247–310). The following is a source excerpt with non-breaking spaces normalized. It is explanatory material, not an experimental trace or additional benchmark observations.

**Arithmetic caveat:** Example one permits stopping at 8,000 consumed tokens, then describes about 4,000 additional full-text tokens under a 10,000-token total budget. If these numbers describe the same execution, their sum is 12,000 tokens. The source does not reconcile them. The figures below are preserved as reported and must not be used as measured evidence of budget compliance. The numeric priority threshold, promotion threshold, and gain weights are not specified in this excerpt.

The source describes two consecutive expansions without a new role or bridging relation as the stagnation limit. Its reported gain definition (Reviewer-B-Q2, lines 43–51) is:

```text
Gain(d | C, q) = w1 * R_rel(d, q) + w2 * B_bridge(d, C) + w3 * A_role(d, C, q)
Priority(d | C, q) = Gain(d | C, q) / Cost(d)
```

The three terms represent task relevance, bridging disconnected path fragments or task anchors, and recovering missing artifact roles. Reviewer-C-Q1 (line 57) states that thresholds and coefficients were fixed on a held-out development set before evaluation; its size and parameter values are not given.

## Algorithm one: Budget Enforcement during Execution

```text
Input: Task query q, Repository graph G, Total budget Γ_max
Output: Structured context package C

1: // Phase 1: Budget Splitting
2: Allocate localization budget Γ_loc and inference budget Γ_inf = Γ_max - Γ_loc
3: Initialize current cost c_curr = 0, context C = ∅, stagnation counter k = 0

4: // Phase 2: Location under Γ_loc
5: H = Locate(q, G, Γ_loc)
6: c_curr = c_curr + Cost(H)
7: Add anchors H to C as metadata views m(e)

8: // Phase 3: Inference under Γ_inf with Early Stopping
9: While c_curr < Γ_max:
10:    Generate candidate actions D from current anchors in C
11:    For each d in D:
12:        Compute Priority(d) = Gain(d | C, q) / Cost(d)   // Eq. (7)
13:
14:    Select d* = argmax Priority(d)
15:    If Priority(d*) < Threshold OR k >= 2:
16:        Break  // Explicit early stopping
17:
18:    Execute d*, add new entities to C as metadata views m(e)
19:    c_curr = c_curr + Cost(d*)
20:    If d* introduces no new artifact role or bridge relation:
21:        k = k + 1
22:    Else:
23:        k = 0

24: // Phase 4: Metadata-First Promotion Control
25: For each entity e in C:
26:    Compute promotion score u(e | q, C)
27:    If u(e | q, C) >= κ:
28:        Replace m(e) with FullText(e)   // Eq. (8), consumes remaining budget
29:    Else:
30:        Keep m(e)                       // Saves budget

31: Return C

```

## Example one: illustrative budget accounting

Scenario: “fix the permission validation failure.” These values are reported in source lines 293–308 and describe an example, not measurements from the benchmark tasks.

| Budget or stage | Reported value | Interpretation |
| --- | ---: | --- |
| Total budget | 10,000 tokens | Overall limit |
| Localization allocation | 3,000 tokens | First stage |
| Inference allocation | 7,000 tokens | Remaining allocation |
| Environment sensing and compression | 1,500 tokens | Localization cost |
| Anchor localization | 1,500 tokens | Localization cost; cumulative cost reaches 3,000 |
| `auth_service.py` metadata view | ~200 tokens | Anchor representation; do not add again to the stated localization total without a cost breakdown |
| `auth_service.py` full text | ~3,000 tokens | Alternative representation, not loaded at localization |

The candidate actions are:

| Action | Target | Cost (tokens) | Gain | Priority = Gain / Cost | Reported decision |
| --- | --- | ---: | ---: | ---: | --- |
| d1 | `security_config.yaml` | 500 | 0.94 | 0.00188 | Selected; a new artifact role is recovered |
| d2 | `string_utils.py` | 400 | 0.06 | 0.00015 | Not selected in this comparison |

Selecting d1 raises cumulative cost from 3,000 to 3,500 tokens and resets the stagnation counter. Two consecutive expansions without a new role or bridging relation trigger early stopping; the source illustrates this with a possible cumulative cost of 8,000 tokens.

After expansion, the example describes 15 metadata cards. Two files containing bug-fix logic exceed the promotion threshold and are promoted to full text at about 4,000 additional tokens. The other 13 bridge or configuration files retain metadata views of about 150 tokens each. The source does not give the actual promotion scores or threshold.

The individual split, priority, and entity-count calculations are consistent (`3,000 + 7,000 = 10,000`, `1,500 + 1,500 = 3,000`, `2 + 13 = 15`). The conditional 8,000-token stopping point followed by about 4,000 additional tokens needs clarification before this can be read as a single execution within the 10,000-token limit. The source's concluding assertion of budget compliance is therefore a methodological claim, not verified by the illustrative accounting.
