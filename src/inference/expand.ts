/**
 * Budget-aware multi-relational implementation-path recovery (Inference stage, paper §III).
 *
 * Given task anchors and the reference graph, greedily expands relation edges by
 * Priority(d) = Gain(d) / Cost(d), stopping when the budget is exhausted or the
 * best remaining priority falls below τ_stop. This makes explicit the expansion
 * that ACoder's `locationComponent` performed as a single reference sweep.
 */
import * as path from "path"
import type { AnalysisReference } from "./projectGraph"
import type { EnvironmentContext, Relation, RelationType } from "../types"
import { Logger } from "../logger"

/** File extensions we consider worth pulling into the context (task-relevant artifacts). */
const TARGET_EXT = /\.(md|mdx|js|jsx|ts|tsx|vue|svelte|py|java|go|rs|rb|php|json|ya?ml|xml|toml|txt)$/i

function isTargetFile(name: string): boolean {
	return TARGET_EXT.test(name)
}

/** Approximate tokens consumed per included file (used to translate budget -> file count). */
const APPROX_TOKENS_PER_FILE = 1200

export interface ExpandOptions {
	budget: number
	tauStop: number
	environment?: EnvironmentContext
}

export interface ExpandResult {
	/** Expanded set of file basenames (anchors ∪ recovered path). */
	files: string[]
	/** Relations traversed during expansion, for the context package. */
	relations: Relation[]
}

/** Map a reference type to the paper's relation taxonomy. */
function toRelationType(referenceType: string): RelationType {
	switch (referenceType) {
		case "import":
			return "import"
		case "require":
			return "require"
		case "export":
			return "export"
		case "include":
			return "include"
		default:
			return "import"
	}
}

/** Gain heuristic: how much an edge improves task-relevance / path completeness. */
function edgeGain(newName: string, connectsAnchor: boolean, environment?: EnvironmentContext): number {
	let gain = 0.5
	if (connectsAnchor) {
		gain += 0.3 // bridges toward the anchor set
	}
	// Role prior boost from environment (config/registration/test/etc.).
	if (environment) {
		const lower = newName.toLowerCase()
		if (/(config|registr|provider|module|route)/.test(lower)) {
			gain += (environment.rolePriors.configuration ?? 0) * 0.2
		}
		if (/(test|spec)/.test(lower)) {
			gain += (environment.rolePriors.test ?? 0) * 0.1
		}
		if (/(bridge|adapter|client|gateway|service)/.test(lower)) {
			gain += (environment.rolePriors.bridge ?? 0) * 0.2
		}
	}
	return Math.min(gain, 1)
}

/**
 * Greedily expand from anchors over the reference edges.
 * Deterministic and offline (no LLM), consistent with the reference expansion in
 * the original implementation but exposing budget and τ_stop controls.
 */
export function expandAnchors(anchors: string[], references: AnalysisReference[], options: ExpandOptions): ExpandResult {
	const maxFiles = Math.max(anchors.length, Math.floor(options.budget / APPROX_TOKENS_PER_FILE))
	const selected = new Set<string>(anchors)
	const relations: Relation[] = []
	const relationKey = new Set<string>()

	// Candidate edges are references where either endpoint is already selected.
	// We loop until no candidate exceeds τ_stop or the budget cap is reached.
	let progress = true
	while (progress && selected.size < maxFiles) {
		progress = false

		// Score all candidate edges from the current frontier.
		let best: { ref: AnalysisReference; newName: string; priority: number } | null = null
		for (const ref of references) {
			const src = ref.sourceFileName
			const tgt = ref.targetFileName
			if (!src || !tgt) {
				continue
			}
			const srcIn = selected.has(src)
			const tgtIn = selected.has(tgt)
			if (srcIn === tgtIn) {
				continue // both in or both out -> not a frontier edge
			}
			const newName = srcIn ? tgt : src
			if (!isTargetFile(newName) || selected.has(newName)) {
				continue
			}
			const connectsAnchor = anchors.includes(src) || anchors.includes(tgt)
			const gain = edgeGain(newName, connectsAnchor, options.environment)
			const cost = 1 // uniform per-edge cost; kept explicit to mirror Priority = Gain/Cost
			const priority = gain / cost
			if (!best || priority > best.priority) {
				best = { ref, newName, priority }
			}
		}

		if (best && best.priority >= options.tauStop) {
			selected.add(best.newName)
			const key = `${best.ref.sourceFileName}->${best.ref.targetFileName}:${best.ref.referenceType}`
			if (!relationKey.has(key)) {
				relationKey.add(key)
				relations.push({
					source: best.ref.sourceFileName,
					target: best.ref.targetFileName,
					type: toRelationType(best.ref.referenceType),
				})
			}
			progress = true
		}
	}

	Logger.log(`Expansion: ${anchors.length} anchors -> ${selected.size} files (cap ${maxFiles}, τ_stop ${options.tauStop}).`)
	return { files: Array.from(selected), relations }
}

export { isTargetFile }
export const _internal = { edgeGain, APPROX_TOKENS_PER_FILE, basename: path.basename }
