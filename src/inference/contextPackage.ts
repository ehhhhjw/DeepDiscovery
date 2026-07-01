/**
 * Metadata-first context construction & serialization (Inference stage, paper §III).
 *
 * For each selected entity, choose a metadata view m(e) or full-text FullText(e)
 * based on a promotion score u(e|q,B) vs the fixed threshold κ, then serialize the
 * recovered evidence into a structured task-level context package (not a flat list).
 */
import * as fs from "fs"
import * as path from "path"
import { Logger } from "../logger"
import { parseAndGenerateRepoMapXML, XMLParser } from "../repomap/xmlParser"
import type { ContextEntity, ContextPackage, EnvironmentContext, Relation } from "../types"
import { EMPTY_USAGE } from "../llm/client"

/** Cap on full-text bytes promoted per entity, to keep the package bounded. */
const MAX_FULLTEXT_BYTES = 24000

export interface BuildContextOptions {
	repoPath: string
	cacheDir: string
	task: string
	files: string[]
	anchors: string[]
	relations: Relation[]
	kappa: number
	environment?: EnvironmentContext
	rawLocalization?: string
}

/**
 * Promotion score u(e | q, B) in [0,1]: likelihood that full-text inspection is
 * needed. Higher when the entity is an anchor, is supported by multiple relations,
 * or lies on a high-confidence path.
 */
function promotionScore(fileName: string, anchors: string[], relations: Relation[]): number {
	let score = 0.3
	if (anchors.includes(fileName)) {
		score += 0.4 // anchors are likely to be directly modified
	}
	const relationDegree = relations.filter((r) => r.source === fileName || r.target === fileName).length
	if (relationDegree >= 1) {
		score += 0.15
	}
	if (relationDegree >= 3) {
		score += 0.15 // multi-supported -> on a high-confidence path
	}
	return Math.min(score, 1)
}

/** Resolve a repo-relative path (from the repomap XML) to an absolute path. */
function resolveFromRepo(repoPath: string, relPath: string): string {
	return path.isAbsolute(relPath) ? relPath : path.join(repoPath, relPath)
}

function readFullText(absPath: string): string | null {
	try {
		if (!fs.existsSync(absPath) || !fs.statSync(absPath).isFile()) {
			return null
		}
		const buf = fs.readFileSync(absPath, "utf-8")
		return buf.length > MAX_FULLTEXT_BYTES ? buf.slice(0, MAX_FULLTEXT_BYTES) + "\n... [truncated]" : buf
	} catch {
		return null
	}
}

function rationaleFor(fileName: string, anchors: string[], relations: Relation[]): string {
	if (anchors.includes(fileName)) {
		return "task anchor (high-confidence entry point)"
	}
	const via = relations.find((r) => r.source === fileName || r.target === fileName)
	if (via) {
		const other = via.source === fileName ? via.target : via.source
		return `recovered via ${via.type} relation with ${other}`
	}
	return "included as task-relevant candidate"
}

/**
 * Build the structured context package. `usage` is set to empty here and filled
 * in by the orchestrator, which aggregates all LLM calls.
 */
export async function buildContextPackage(options: BuildContextOptions): Promise<ContextPackage> {
	const { repoPath, cacheDir, files, anchors, relations, kappa, environment } = options

	// Produce a filtered repomap XML scoped to the selected files, then parse it
	// to obtain metadata (compressed) views + directory structure.
	let metadataByBasename = new Map<string, { path: string; content: string }>()
	let directoryStructure = ""
	try {
		const filteredPath = await parseAndGenerateRepoMapXML(cacheDir, files)
		if (filteredPath && fs.existsSync(filteredPath)) {
			const parsed = await XMLParser.parseXMLFile(filteredPath, files)
			directoryStructure = parsed.relatedDirectoryStructure
			for (const item of parsed.relatedFileContents) {
				metadataByBasename.set(path.basename(item.path), item)
			}
		}
	} catch (e) {
		Logger.warn(`Context construction: filtered repomap unavailable (${e instanceof Error ? e.message : String(e)}).`)
	}

	const entities: ContextEntity[] = []
	for (const fileName of files) {
		const meta = metadataByBasename.get(fileName)
		const u = promotionScore(fileName, anchors, relations)
		const rationale = rationaleFor(fileName, anchors, relations)

		if (u >= kappa) {
			// Promote to full text when available; otherwise fall back to metadata.
			const relPath = meta?.path ?? fileName
			const fullText = readFullText(resolveFromRepo(repoPath, relPath))
			if (fullText !== null) {
				entities.push({ path: relPath, view: "fulltext", content: fullText, rationale })
				continue
			}
		}
		// Metadata view.
		entities.push({
			path: meta?.path ?? fileName,
			view: "metadata",
			content: meta?.content ?? "(metadata unavailable)",
			rationale,
		})
	}

	const serialized = serializePackage(options, entities, directoryStructure)

	return {
		entities,
		relations,
		relatedFiles: files,
		serialized,
		usage: { ...EMPTY_USAGE },
	}
}

/** Serialize the package into a compact, downstream-consumable text block. */
function serializePackage(options: BuildContextOptions, entities: ContextEntity[], directoryStructure: string): string {
	const { task, anchors, relations, environment } = options
	const lines: string[] = []
	lines.push("# DeepDiscovery Task-Level Context Package\n")
	lines.push(`## Task\n${task}\n`)

	if (environment) {
		lines.push("## Environment")
		lines.push(`- Tech stack: ${environment.techStack.join(", ") || "(unknown)"}`)
		lines.push(`- Module scope: ${environment.moduleScope.join(", ") || "(unknown)"}`)
		if (environment.constraints.length) {
			lines.push(`- Constraints: ${environment.constraints.join("; ")}`)
		}
		lines.push("")
	}

	lines.push(`## Task anchors\n${anchors.length ? anchors.map((a) => `- ${a}`).join("\n") : "(none)"}\n`)

	if (directoryStructure) {
		lines.push("## Relevant directory structure")
		lines.push("```")
		lines.push(directoryStructure)
		lines.push("```\n")
	}

	if (relations.length) {
		lines.push("## Structural relations")
		for (const r of relations) {
			lines.push(`- ${r.source} --${r.type}--> ${r.target}`)
		}
		lines.push("")
	}

	lines.push("## Entities")
	for (const e of entities) {
		lines.push(`\n### ${e.path}  [${e.view}]`)
		lines.push(`_rationale: ${e.rationale}_`)
		lines.push("```")
		lines.push(e.content)
		lines.push("```")
	}

	return lines.join("\n")
}

export const _internal = { promotionScore, rationaleFor }
