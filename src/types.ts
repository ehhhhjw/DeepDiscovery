/**
 * Core data model for DeepDiscovery, aligned with the paper's
 * Location–Inference framework (see paper §III).
 */

/** A relation edge in the multi-relational repository graph G = (V, A). */
export type RelationType =
	| "import"
	| "require"
	| "include"
	| "export"
	| "organizational" // folder containment / module proximity
	| "implicit" // config / registration / DI / event-mediated links

export interface Relation {
	source: string
	target: string
	type: RelationType
}

/** How an entity's contextual representation z_e is materialized. */
export type EntityView = "metadata" | "fulltext"

/**
 * A selected repository entity in the task context B(q) = {(e_i, z_i, ρ_i)}.
 * - `path`     -> e_i (the entity)
 * - `view`/`content` -> z_i (metadata view m(e) or FullText(e))
 * - `rationale`-> ρ_i (structural rationale for inclusion)
 */
export interface ContextEntity {
	path: string
	view: EntityView
	content: string
	rationale: string
}

export interface Usage {
	inputTokens: number
	outputTokens: number
	cacheWriteTokens: number
	cacheReadTokens: number
	cost: number
}

/**
 * The structured task-level context package produced by DeepDiscovery.
 * This is what is handed to a downstream model, rather than a flat file list.
 */
export interface ContextPackage {
	/** Selected entities with metadata-first views and inclusion rationales. */
	entities: ContextEntity[]
	/** Structural relations among the selected entities. */
	relations: Relation[]
	/** Predicted task-relevant file set Ŷ(q) (used for FRR / MR / MP). */
	relatedFiles: string[]
	/** Human-/model-readable serialization of the package. */
	serialized: string
	/** Aggregated token usage and estimated cost across all LLM calls. */
	usage: Usage
}

/** Result of the Location stage. */
export interface LocationResult {
	/** Inferred environment context c_q (tech stack, scope, role priors). */
	environment: EnvironmentContext
	/** High-confidence task anchors Ĥ (file names / paths). */
	anchors: string[]
	/** Raw LLM localization text (for debugging / rationale). */
	rawLocalization: string
}

/** Environment-aware analysis output c_q (paper §III, Location). */
export interface EnvironmentContext {
	/** Likely technology stack, e.g. ["typescript", "react"]. */
	techStack: string[]
	/** Likely module scope / directories to focus on. */
	moduleScope: string[]
	/** Artifact-role priors, e.g. { config: 0.8, test: 0.4 }. */
	rolePriors: Record<string, number>
	/** Explicit task constraints extracted from the description. */
	constraints: string[]
}

/** Public entry options for a single repository-understanding run. */
export interface DeepDiscoveryOptions {
	/** Absolute or relative path to the repository to analyze. */
	repoPath: string
	/** Natural-language software engineering task q. */
	task: string
	/** B_max: exploration budget (approx. token cap). */
	budget?: number
	/** κ: metadata -> full-text promotion threshold in [0,1]. */
	kappa?: number
	/** τ_stop: expansion stop threshold in [0,1]. */
	tauStop?: number
	/** Model id override. */
	model?: string
	/** Stable task id used as the cache key; derived from repoPath+task if omitted. */
	taskId?: string
	/** Enable result caching (default true). */
	useCache?: boolean
	/** Progress callback for long-running steps. */
	onProgress?: (message: string) => void
}
