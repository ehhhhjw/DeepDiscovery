/**
 * Second-round anchor refinement (Inference stage).
 *
 * Faithful migration of the second half of ACoder's
 * `locationComponent.performCombinedFileLocation`:
 *  1. Build a filtered, compressed repomap view scoped to the expanded candidate
 *     files (`parseAndGenerateRepoMapXML`) and ask the LLM to re-localize on it
 *     ("tiny repomap ajx" round).
 *  2. If that view is unavailable/empty, fall back to a rendered directory tree
 *     of the candidate files (`processPathsGenerateDirectory`) and re-localize
 *     ("project structure ajx" round).
 */
import * as fs from "fs"
import { localizeAnchors } from "../location/anchorLocalize"
import type { LLMClient, LLMUsage } from "../llm/client"
import { addUsage, EMPTY_USAGE } from "../llm/client"
import { Logger } from "../logger"
import { parseAndGenerateRepoMapXML } from "../repomap/xmlParser"
import type { EnvironmentContext } from "../types"
import { processPathsGenerateDirectory } from "../utils/directory"

export interface RefineOptions {
	repoPath: string
	cacheDir: string
	task: string
	/** Expanded candidate files from graph expansion. */
	candidateFiles: string[]
	environment?: EnvironmentContext
}

export interface RefineResult {
	/** Anchors localized in the refinement round (file basenames). */
	anchors: string[]
	/** Raw LLM answer from the round that produced results. */
	rawText: string
	/** Which round produced the result: "repomap" | "structure" | "none". */
	round: "repomap" | "structure" | "none"
	usage: LLMUsage
}

/**
 * Refine anchors using the expanded candidate set, mirroring the original
 * two-round-then-fallback behavior.
 */
export async function refineAnchors(llm: LLMClient, options: RefineOptions): Promise<RefineResult> {
	let usage: LLMUsage = { ...EMPTY_USAGE }

	// Round 2: filtered compressed repomap view of the candidate files.
	const filteredPath = await parseAndGenerateRepoMapXML(options.cacheDir, options.candidateFiles)
	if (filteredPath && fs.existsSync(filteredPath)) {
		const tinyView = fs.readFileSync(filteredPath, "utf-8")
		if (tinyView.trim()) {
			Logger.log("Refinement round 2: localizing on filtered compressed repomap view.")
			const res = await localizeAnchors(llm, options.task, tinyView, options.environment)
			usage = addUsage(usage, res.usage)
			if (res.ran && res.anchors.length > 0) {
				return { anchors: res.anchors, rawText: res.rawText, round: "repomap", usage }
			}
		}
	}

	// Fallback round: rendered directory tree of the candidate files.
	Logger.log("Refinement fallback: localizing on candidate directory structure.")
	const dirView = await processPathsGenerateDirectory(options.candidateFiles, { workdir: options.repoPath })
	if (dirView.trim()) {
		const res = await localizeAnchors(llm, options.task, dirView, options.environment)
		usage = addUsage(usage, res.usage)
		if (res.ran && res.anchors.length > 0) {
			return { anchors: res.anchors, rawText: res.rawText, round: "structure", usage }
		}
	}

	return { anchors: [], rawText: "", round: "none", usage }
}
