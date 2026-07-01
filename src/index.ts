/**
 * DeepDiscovery — public library API.
 *
 * A Location–Inference framework for task-level repository understanding.
 * See the paper: "DeepDiscovery: A Location–Inference Framework for Task-Level
 * Repository Understanding in Industrial Codebases".
 */
export { runDeepDiscovery, type RunDeps } from "./core/deepDiscovery"
export { loadConfig, DEFAULTS, type ResolvedConfig } from "./config"
export {
	AnthropicLLMClient,
	addUsage,
	EMPTY_USAGE,
	type LLMClient,
	type LLMResult,
	type LLMUsage,
} from "./llm/client"
export type {
	DeepDiscoveryOptions,
	ContextPackage,
	ContextEntity,
	EntityView,
	Relation,
	RelationType,
	EnvironmentContext,
	LocationResult,
	Usage,
} from "./types"

import { runDeepDiscovery } from "./core/deepDiscovery"
import type { ContextPackage, DeepDiscoveryOptions } from "./types"

/**
 * Convenience wrapper: run the pipeline with the given options and default deps.
 *
 * @example
 * import { run } from "deepdiscovery"
 * const pkg = await run({ repoPath: "./my-repo", task: "add retry to payment" })
 * console.log(pkg.relatedFiles)
 */
export function run(options: DeepDiscoveryOptions): Promise<ContextPackage> {
	return runDeepDiscovery(options)
}
