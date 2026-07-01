/**
 * Project file-structure rendering with blacklist / .gitignore-aligned filtering.
 * Ported and de-coupled from ACoder's `utils/codeAnalyzer.ts`
 * (Alibaba `bundle.json` / `ajx_modules` specifics removed; `.gitignore` support kept).
 */
import * as fs from "fs"
import ignore, { Ignore } from "ignore"
import * as path from "path"
import { Logger } from "../logger"

/** Default directories that are never worth traversing for repository understanding. */
export const DEFAULT_IGNORE_DIRECTORIES = [
	"node_modules",
	"__pycache__",
	"env",
	"venv",
	".venv",
	"target/dependency",
	"build/dependencies",
	"dist",
	"out",
	"bundle",
	"vendor",
	"tmp",
	"temp",
	"deps",
	"Pods",
	".git",
]

interface BuildIgnoreOptions {
	/** Repository root, used to read a `.gitignore` when present. */
	rootPath: string
	/** Extra gitignore-format patterns. */
	extraPatterns?: string[]
	/** Whether to honor the repo's `.gitignore` (default true). */
	useGitignore?: boolean
}

function buildIgnore(options: BuildIgnoreOptions): Ignore {
	const ig = ignore()
	ig.add(DEFAULT_IGNORE_DIRECTORIES)
	if (options.extraPatterns && options.extraPatterns.length > 0) {
		ig.add(options.extraPatterns)
	}
	if (options.useGitignore !== false) {
		const gitignorePath = path.join(options.rootPath, ".gitignore")
		try {
			if (fs.existsSync(gitignorePath)) {
				ig.add(fs.readFileSync(gitignorePath, "utf-8"))
				Logger.log(`Loaded .gitignore from ${gitignorePath}`)
			}
		} catch (e) {
			Logger.warn(`Failed to read .gitignore: ${e instanceof Error ? e.message : String(e)}`)
		}
	}
	return ig
}

export interface FileStructureOptions {
	extraIgnorePatterns?: string[]
	useGitignore?: boolean
}

/**
 * Render the repository's directory tree as an indented text block, filtering
 * out ignored directories/files. Mirrors the compressed structural view used as
 * a Location-stage input.
 */
export function getProjectFileStructure(rootPath: string, options: FileStructureOptions = {}): string {
	const absRoot = path.resolve(rootPath)
	Logger.log(`Building file structure for ${absRoot}`)

	const ig = buildIgnore({
		rootPath: absRoot,
		extraPatterns: options.extraIgnorePatterns,
		useGitignore: options.useGitignore,
	})

	let fileStructure = `Repository path: ${absRoot}\n\n`

	function isIgnored(relPath: string, isDirectory: boolean): boolean {
		if (!relPath) {
			return false
		}
		const normalized = relPath.split(path.sep).join("/")
		const candidate = isDirectory ? `${normalized}/` : normalized
		try {
			return ig.ignores(candidate) || ig.ignores(normalized)
		} catch {
			return false
		}
	}

	function traverse(dirPath: string, prefix: string): string {
		let result = ""
		let items: string[]
		try {
			items = fs.readdirSync(dirPath)
		} catch (error) {
			return `${prefix}[access error: ${error instanceof Error ? error.message : String(error)}]\n`
		}

		const directories: string[] = []
		const files: string[] = []

		for (const item of items) {
			const itemPath = path.join(dirPath, item)
			let isDirectory = false
			try {
				isDirectory = fs.statSync(itemPath).isDirectory()
			} catch {
				continue
			}
			const relPath = path.relative(absRoot, itemPath)
			if (isIgnored(relPath, isDirectory)) {
				continue
			}
			if (isDirectory) {
				directories.push(item)
			} else {
				files.push(item)
			}
		}

		directories.sort()
		files.sort()

		for (const dir of directories) {
			result += `${prefix}    ${dir}/\n`
			result += traverse(path.join(dirPath, dir), prefix + "    ")
		}
		for (const file of files) {
			result += `${prefix}    ${file}\n`
		}
		return result
	}

	fileStructure += traverse(absRoot, "")
	return fileStructure
}
