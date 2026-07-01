/**
 * Adaptive repository compression (Location stage, paper §III).
 *
 * Produces a compressed structural view of the repository (tree-sitter signature
 * extraction). The primary engine is the vendored `@ali/repoamap` bundled under
 * `vendor/repoamap` — the same repomap engine used by the original system. If the
 * vendored engine is not built, it falls back to a locally installed `repomix`,
 * then to `npx repomix`. Output is an XML file consumed by anchor localization
 * and the inference stage.
 */
import { execFileSync } from "child_process"
import * as fs from "fs"
import * as path from "path"
import { Logger } from "../logger"

export interface CompressOptions {
	/** Repository root to compress. */
	repoPath: string
	/** Directory where the compressed XML is written. */
	cacheDir: string
	/** Extra gitignore-format ignore patterns (comma-joined for the engine). */
	ignorePatterns?: string[]
	/** Timeout in ms for the compression subprocess. */
	timeoutMs?: number
}

export interface CompressResult {
	/** Path to the generated repomap XML, or "" on failure. */
	outputPath: string
	/** The XML content (empty string on failure). */
	content: string
	/** Which engine produced the output ("repoamap" | "repomix" | "npx" | ""). */
	engine: string
}

interface Engine {
	name: string
	cmd: string
	baseArgs: string[]
}

/**
 * Resolve the compression engine, preferring the vendored `@ali/repoamap`.
 * Order: vendored repoamap (built) -> local repomix -> local repoamap -> npx repomix.
 */
function resolveEngine(repoPath: string): Engine {
	const binExt = process.platform === "win32" ? ".cmd" : ""

	// 1) Vendored @ali/repoamap (bundled with DeepDiscovery). Run via Node against its bin.
	const vendoredBin = path.join(__dirname, "..", "..", "vendor", "repoamap", "bin", "repoamap.cjs")
	const vendoredLib = path.join(__dirname, "..", "..", "vendor", "repoamap", "lib", "cli", "cliRun.js")
	if (fs.existsSync(vendoredBin) && fs.existsSync(vendoredLib)) {
		return { name: "repoamap", cmd: process.execPath, baseArgs: [vendoredBin] }
	}
	if (fs.existsSync(vendoredBin) && !fs.existsSync(vendoredLib)) {
		Logger.warn("Vendored repoamap is present but not built. Run `npm run build:engine`. Falling back to repomix.")
	}

	// 2) Locally installed repomix / repoamap binaries.
	const localBins: Array<{ name: string; p: string }> = [
		{ name: "repomix", p: path.join(__dirname, "..", "..", "node_modules", ".bin", `repomix${binExt}`) },
		{ name: "repomix", p: path.join(repoPath, "node_modules", ".bin", `repomix${binExt}`) },
		{ name: "repoamap", p: path.join(repoPath, "node_modules", ".bin", `repoamap${binExt}`) },
	]
	for (const b of localBins) {
		if (fs.existsSync(b.p)) {
			return { name: b.name, cmd: b.p, baseArgs: [] }
		}
	}

	// 3) Fall back to npx repomix.
	return { name: "npx", cmd: process.platform === "win32" ? "npx.cmd" : "npx", baseArgs: ["--yes", "repomix"] }
}

/**
 * Run the compression engine to produce a compressed repository view.
 * Never throws for tool/output errors: returns an empty result and logs instead,
 * so the pipeline can gracefully degrade to plain file-structure input.
 */
export function compressRepository(options: CompressOptions): CompressResult {
	const { cacheDir } = options
	// Resolve to an absolute path so the positional target arg and cwd don't
	// double-resolve when a relative repoPath is passed.
	const repoPath = path.resolve(options.repoPath)
	const outputPath = path.join(cacheDir, "repomap-output-all.xml")
	const engine = resolveEngine(repoPath)

	const args = [...engine.baseArgs, "--compress", "--style", "xml", "--output", outputPath]
	if (options.ignorePatterns && options.ignorePatterns.length > 0) {
		args.push("--ignore", options.ignorePatterns.join(","))
	}
	// The target directory is the last positional argument (absolute).
	args.push(repoPath)

	try {
		Logger.log(`Running compression (${engine.name}): ${engine.cmd} ${args.join(" ")}`)
		execFileSync(engine.cmd, args, {
			cwd: repoPath,
			timeout: options.timeoutMs ?? 120000,
			encoding: "utf8",
			stdio: ["ignore", "pipe", "pipe"],
		})
		const content = fs.existsSync(outputPath) ? fs.readFileSync(outputPath, "utf-8") : ""
		if (!content) {
			Logger.warn("Compression produced no output.")
			return { outputPath: "", content: "", engine: "" }
		}
		Logger.log(`Compression complete via ${engine.name}: ${outputPath} (${content.length} chars)`)
		return { outputPath, content, engine: engine.name }
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err)
		Logger.warn(`Repository compression failed (${engine.name}): ${msg}`)
		return { outputPath: "", content: "", engine: "" }
	}
}
