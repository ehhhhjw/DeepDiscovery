/**
 * Reproducibility artifacts (paper §V.E): rule-template families used by the
 * rule signal s_rule, and artifact-role priors π_L. These are injected into the
 * Location prompts so heuristic cues guide the LLM rather than acting as hard filters.
 *
 * They are intentionally language/framework-agnostic defaults; downstream users
 * may extend them for a specific stack.
 */

/** Rule-template families: naming / directory / keyword heuristics for s_rule. */
export const RULE_TEMPLATES: string[] = [
	"Files whose names or directories match task keywords (e.g. a 'payment' task favors */payment/*, *Payment*, pay_*).",
	"Interface/implementation pairs: an interface or abstract type and its concrete implementation are usually both relevant.",
	"Bridge/adapter files that connect a caller module to a service module (names like *Bridge*, *Adapter*, *Client*, *Gateway*).",
	"Configuration & registration files that wire a feature into the app (e.g. *.config.*, routes, DI containers, *Registry*, *Provider*).",
	"Test files that exercise the target behavior (e.g. *.test.*, *.spec.*, __tests__/*) when reasoning or modification requires them.",
	"Entry points and index/barrel files that re-export the target symbols.",
]

/**
 * Artifact-role priors π_L(type(v) | q): task-conditioned weights over artifact
 * roles. Defaults below are a reasonable starting point; the value is a prior
 * salience in [0,1], not a hard threshold.
 */
export const ARTIFACT_ROLE_PRIORS: Record<string, number> = {
	implementation: 1.0,
	interface: 0.9,
	bridge: 0.8,
	configuration: 0.75,
	registration: 0.7,
	test: 0.5,
	documentation: 0.3,
}

/**
 * Prompt fragment that asks the model to assign the fusion weights
 * (α_q, β_q, γ_q, δ_q) for Score_loc, conditioned on the repository profile.
 * Kept as a shared artifact so the weighting behavior is reproducible.
 */
export const FUSION_WEIGHT_GUIDANCE = `When judging relevance, balance four kinds of evidence:
- semantic similarity between the task and a file's content/metadata (weight α),
- alignment between the task and the compressed structural summary (weight β),
- rule/heuristic cues such as naming, directory, and framework keywords (weight γ),
- artifact-role priors for the file type given the task (weight δ).
Rely more on structural/LLM alignment (α, β) for semantically complex domains, and
more on rule cues (γ) for repositories with strong naming/directory conventions.`
