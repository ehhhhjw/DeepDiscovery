/**
 * Rule-guided anchor-localization prompt (Location stage, paper §III).
 *
 * Extends ACoder's `locate_path_by_repomap.ts` by injecting the rule-template
 * families, artifact-role priors, and fusion-weight guidance so the LLM performs
 * an implicit Score_loc = α·sem + β·sum + γ·rule + δ·prior fusion.
 */
import type { EnvironmentContext } from "../types"
import { FUSION_WEIGHT_GUIDANCE, RULE_TEMPLATES } from "./artifacts"

/**
 * Build the localization prompt.
 * @param task            the natural-language task q
 * @param repoView        a compressed repo view or file structure (S / structure)
 * @param environment     optional inferred environment context c_q
 */
export function anchorLocalizePrompt(task: string, repoView: string, environment?: EnvironmentContext): string {
	const envBlock = environment
		? `\n## Environment context\n- Tech stack: ${environment.techStack.join(", ") || "(unknown)"}\n- Module scope: ${environment.moduleScope.join(", ") || "(unknown)"}\n- Constraints: ${environment.constraints.join("; ") || "(none)"}\n`
		: ""

	const ruleBlock = RULE_TEMPLATES.map((r, i) => `${i + 1}. ${r}`).join("\n")

	return `## Goal
Using the "Task" and the "Repository view" below, find ALL file paths relevant to the task.

## Weighting guidance
${FUSION_WEIGHT_GUIDANCE}

## Rule cues (heuristics, not hard filters)
${ruleBlock}
${envBlock}
## Steps
1. Understand the task's concrete intent.
2. Using the repository view, decide which files are likely relevant (implementation, interface, bridge, configuration/registration, and tests when needed).
3. Output the relevant file paths separated by ',' (comma). Prefer complete task-relevant sets over minimal ones.
4. If no relevant files are found, output exactly "No relevant files found".

====

## Task
${task}

## Repository view
${repoView}
`
}
