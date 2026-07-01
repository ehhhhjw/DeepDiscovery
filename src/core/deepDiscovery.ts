/**
 * DeepDiscovery orchestrator — Algorithm 1 (Location–Inference Context Recovery).
 *
 *   ĉ_q   <- EnvAnalyze(q, R)
 *   S     <- AdaptiveCompress(R, B_max)
 *   Ĥ     <- top anchors by Score_loc                 (Location)
 *   B     <- greedy expand by Priority=Gain/Cost      (Inference)
 *          + second-round LLM refinement over the expanded set (repomap / dir view)
 *   z_e   <- metadata-first rule with threshold κ
 *   return Serialize(B)                               (structured context package)
 *
 * This faithfully preserves ACoder's `findRelatedFilesWithRepomap` pipeline:
 * cache check -> first-round localization on the directory tree -> reference-graph
 * expansion -> second-round localization on the filtered compressed repomap (with
 * a directory-view fallback) -> metadata-first context construction -> cache write.
 */
import * as crypto from "crypto"
import * as path from "path"
import { analyzeEnvironment } from "../location/envAnalyze"
import { localizeAnchors } from "../location/anchorLocalize"
import { compressRepository } from "../location/compress"
import { getProjectFileStructure } from "../location/fileStructure"
import { buildContextPackage } from "../inference/contextPackage"
import { expandAnchors } from "../inference/expand"
import { ProjectGraph } from "../inference/projectGraph"
import { refineAnchors } from "../inference/refine"
import { addUsage, EMPTY_USAGE, type LLMClient, type LLMUsage } from "../llm/client"
import { AnthropicLLMClient } from "../llm/client"
import { loadConfig, type ResolvedConfig } from "../config"
import { Logger, setVerbose } from "../logger"
import { findCacheInfo, saveCacheInfo } from "../utils/cache"
import { getProjectCacheDir } from "../utils/paths"
import type { ContextPackage, DeepDiscoveryOptions } from "../types"

export interface RunDeps {
	/** Inject a custom LLM client (tests / alternative providers). */
	llm?: LLMClient
	/** Pre-resolved config; otherwise derived from options + env. */
	config?: ResolvedConfig
}

/** Derive a stable cache key from the repository path and task, unless one is given. */
function resolveCacheKey(options: DeepDiscoveryOptions): string {
	if (options.taskId && options.taskId.trim()) {
		return options.taskId.trim()
	}
	return crypto
		.createHash("sha1")
		.update(`${path.resolve(options.repoPath)}\n${options.task}`)
		.digest("hex")
		.slice(0, 16)
}

/** Merge two file-basename lists, de-duplicated, preserving order (a first). */
function mergeFiles(a: string[], b: string[]): string[] {
	const seen = new Set<string>()
	const out: string[] = []
	for (const f of [...a, ...b]) {
		if (f && !seen.has(f)) {
			seen.add(f)
			out.push(f)
		}
	}
	return out
}

/**
 * Execute the full Location–Inference pipeline for a single task and return the
 * structured task-level context package.
 */
export async function runDeepDiscovery(options: DeepDiscoveryOptions, deps: RunDeps = {}): Promise<ContextPackage> {
	const config =
		deps.config ??
		loadConfig({
			model: options.model,
			budget: options.budget,
			kappa: options.kappa,
			tauStop: options.tauStop,
		})
	setVerbose(config.verbose)

	const progress = options.onProgress ?? (() => {})
	const cacheDir = getProjectCacheDir(options.repoPath, config.cacheDir) || options.repoPath
	const useCache = options.useCache !== false
	const cacheKey = resolveCacheKey(options)
	const cacheFilePath = path.join(cacheDir, "repomapCache", `${cacheKey}.json`)
	let usage: LLMUsage = { ...EMPTY_USAGE }

	// --- Cache check (mirrors the original short-circuit on a warm cache) ---
	if (useCache) {
		const cached = await findCacheInfo(cacheFilePath, cacheKey)
		if (cached) {
			try {
				const pkg = JSON.parse(cached) as ContextPackage
				Logger.log("Returning cached context package.")
				progress("Loaded from cache")
				return pkg
			} catch {
				Logger.warn("Cached context package was invalid; recomputing.")
			}
		}
	}

	// --- Location: environment-aware analysis + adaptive compression (no LLM key needed yet) ---
	progress("Location: reading repository structure")
	const fileStructure = getProjectFileStructure(options.repoPath)

	progress("Location: compressing repository (repomap engine)")
	const compressed = compressRepository({ repoPath: options.repoPath, cacheDir })

	// LLM client is required from here on.
	const llm =
		deps.llm ??
		new AnthropicLLMClient({
			apiKey: config.apiKey ?? "",
			baseURL: config.baseURL,
			model: config.model,
		})

	progress("Location: environment-aware analysis")
	const env = await analyzeEnvironment(llm, options.task, fileStructure)
	usage = addUsage(usage, env.usage)

	// First-round localization over the directory tree (matches the original
	// "project structure" round). Compression runs in parallel and is consumed
	// by the second round below.
	progress("Location: rule-guided anchor localization (round 1)")
	const firstRound = await localizeAnchors(llm, options.task, fileStructure, env.environment)
	usage = addUsage(usage, firstRound.usage)
	const anchors = firstRound.anchors
	Logger.log(`Round-1 anchors: ${anchors.join(", ") || "(none)"}`)

	// --- Inference: build reference graph, expand, refine, construct context ---
	progress("Inference: building multi-relational reference graph")
	const graph = new ProjectGraph(options.repoPath)
	await graph.analyzeProject()
	const { references } = graph.getAnalysisResult()

	progress("Inference: budget-aware implementation-path recovery")
	const expansion = expandAnchors(anchors, references, {
		budget: config.budget,
		tauStop: config.tauStop,
		environment: env.environment,
	})

	// Second-round refinement over the expanded candidate set: filtered compressed
	// repomap view, with a directory-tree fallback (both migrated from the original).
	progress("Inference: second-round localization on expanded set")
	const refined = await refineAnchors(llm, {
		repoPath: options.repoPath,
		cacheDir,
		task: options.task,
		candidateFiles: expansion.files,
		environment: env.environment,
	})
	usage = addUsage(usage, refined.usage)
	Logger.log(`Refinement (${refined.round}) anchors: ${refined.anchors.join(", ") || "(none)"}`)

	// Final task-relevant set: refinement result unioned with expanded candidates,
	// so graph-recovered bridge/config files are not dropped.
	const finalFiles = mergeFiles(refined.anchors, expansion.files)

	progress("Inference: metadata-first context construction")
	const contextPackage = await buildContextPackage({
		repoPath: options.repoPath,
		cacheDir,
		task: options.task,
		files: finalFiles,
		anchors,
		relations: expansion.relations,
		kappa: config.kappa,
		environment: env.environment,
		rawLocalization: refined.rawText || firstRound.rawText,
	})

	contextPackage.usage = usage

	// --- Cache write ---
	if (useCache) {
		await saveCacheInfo(cacheFilePath, cacheKey, JSON.stringify(contextPackage))
	}

	progress("Done")
	return contextPackage
}
