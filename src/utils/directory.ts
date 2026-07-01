/**
 * Enhanced path resolution + directory-structure rendering.
 * Ported from ACoder's `utils/processPathsGenrateDirectory.ts`
 * (only the local `fileExistsAtPath` dependency was inlined).
 */
import * as fs from "fs/promises"
import * as path from "path"

async function fileExistsAtPath(filePath: string): Promise<boolean> {
	try {
		await fs.access(filePath)
		return true
	} catch {
		return false
	}
}

export interface PathInfo {
	originalPath: string
	absolutePath: string
	exists: boolean
	isDirectory: boolean
}

export interface DirectoryStructure {
	[key: string]: DirectoryStructure | string[]
}

/** Resolves loosely-specified paths (by name or partial path) to concrete files. */
export class EnhancedPathResolver {
	private fileNameMap: Map<string, string[]> = new Map()
	private isMapInitialized = false

	private async initializeFileNameMap(searchDirectory: string): Promise<void> {
		if (this.isMapInitialized) {
			return
		}
		this.fileNameMap.clear()
		await this.scanDirectoryForFiles(searchDirectory, 15)
		this.isMapInitialized = true
	}

	private async scanDirectoryForFiles(dirPath: string, maxDepth: number, currentDepth = 0): Promise<void> {
		if (currentDepth >= maxDepth) {
			return
		}
		try {
			const entries = await fs.readdir(dirPath, { withFileTypes: true })
			for (const entry of entries) {
				if (entry.name.startsWith(".") || entry.name === "node_modules") {
					continue
				}
				const fullPath = path.join(dirPath, entry.name)
				if (entry.isFile()) {
					const absolutePath = path.resolve(fullPath)
					if (!this.fileNameMap.has(entry.name)) {
						this.fileNameMap.set(entry.name, [])
					}
					this.fileNameMap.get(entry.name)!.push(absolutePath)
				}
				if (entry.isDirectory()) {
					await this.scanDirectoryForFiles(fullPath, maxDepth, currentDepth + 1)
				}
			}
		} catch {
			// ignore inaccessible directories
		}
	}

	private findFilesByName(fileName: string): PathInfo[] {
		const absolutePaths = this.fileNameMap.get(fileName) || []
		return absolutePaths.map((absolutePath) => ({
			originalPath: fileName,
			absolutePath,
			exists: true,
			isDirectory: false,
		}))
	}

	async resolvePathsEnhanced(inputPaths: string[], searchDirectory: string = process.cwd()): Promise<PathInfo[]> {
		await this.initializeFileNameMap(searchDirectory)
		const results: PathInfo[] = []
		for (const inputPath of inputPaths) {
			if (path.isAbsolute(inputPath)) {
				const isDirectory = await this.checkIsDirectory(inputPath)
				results.push({
					originalPath: inputPath,
					absolutePath: path.resolve(inputPath),
					exists: await fileExistsAtPath(inputPath),
					isDirectory,
				})
			} else {
				results.push(...(await this.resolveRelativePath(inputPath, searchDirectory)))
			}
		}
		return results
	}

	private async resolveRelativePath(inputPath: string, searchDirectory: string): Promise<PathInfo[]> {
		const normalizedPath = inputPath.replace(/\\/g, "/")
		const fullPath = path.join(searchDirectory, normalizedPath)
		if (await fileExistsAtPath(fullPath)) {
			const isDirectory = await this.checkIsDirectory(fullPath)
			return [{ originalPath: inputPath, absolutePath: path.resolve(fullPath), exists: true, isDirectory }]
		}
		if (!normalizedPath.includes("/")) {
			const found = await this.findFileByName(normalizedPath, searchDirectory)
			if (found.length > 0) {
				return found
			}
		} else {
			const found = await this.findFileByPartialPath(normalizedPath, searchDirectory)
			if (found.length > 0) {
				return found
			}
		}
		return [{ originalPath: inputPath, absolutePath: path.resolve(searchDirectory, inputPath), exists: false, isDirectory: false }]
	}

	private async findFileByName(fileName: string, searchDirectory: string): Promise<PathInfo[]> {
		await this.initializeFileNameMap(searchDirectory)
		return this.findFilesByName(fileName)
	}

	private async findFileByPartialPath(partialPath: string, searchDirectory: string): Promise<PathInfo[]> {
		const pathParts = partialPath.split("/")
		const fileName = pathParts[pathParts.length - 1]
		const pathSegments = pathParts.slice(0, -1)
		await this.initializeFileNameMap(searchDirectory)
		const allMatchingFiles = this.findFilesByName(fileName)
		return allMatchingFiles.filter((fileInfo) => this.pathContainsSegments(fileInfo.absolutePath, pathSegments))
	}

	private pathContainsSegments(filePath: string, segments: string[]): boolean {
		if (segments.length === 0) {
			return true
		}
		const normalizedPath = filePath.replace(/\\/g, "/").toLowerCase()
		const pathParts = normalizedPath.split("/").filter((part) => part !== "")
		let segmentIndex = 0
		for (const part of pathParts) {
			if (segmentIndex < segments.length && part === segments[segmentIndex].toLowerCase()) {
				segmentIndex++
			}
		}
		return segmentIndex === segments.length
	}

	resetFileNameMap(): void {
		this.fileNameMap.clear()
		this.isMapInitialized = false
	}

	async checkIsDirectory(filePath: string): Promise<boolean> {
		try {
			const stats = await fs.stat(filePath)
			return stats.isDirectory()
		} catch {
			return false
		}
	}
}

function buildDirectoryStructure(pathInfos: PathInfo[], baseDir?: string): DirectoryStructure {
	const structure: DirectoryStructure = {}
	const existingPaths = pathInfos.filter((info) => info.exists && !info.isDirectory)
	for (const pathInfo of existingPaths) {
		let relativePath = baseDir ? path.relative(baseDir, pathInfo.absolutePath) : pathInfo.absolutePath
		relativePath = relativePath.replace(/\\/g, "/")
		const pathParts = relativePath.split("/").filter((part) => part !== "")
		const fileName = pathParts.pop()!
		let current = structure
		for (const part of pathParts) {
			if (!current[part]) {
				current[part] = {}
			}
			current = current[part] as DirectoryStructure
		}
		if (!current["__files__"]) {
			current["__files__"] = []
		}
		;(current["__files__"] as string[]).push(fileName)
	}
	return structure
}

function formatDirectoryStructure(structure: DirectoryStructure, indent = "", maxDepth = 10, currentDepth = 0): string {
	if (currentDepth >= maxDepth) {
		return `${indent}... (more files)\n`
	}
	let result = ""
	const directories = Object.entries(structure).filter(([key]) => key !== "__files__")
	for (const [key, value] of directories) {
		result += `${indent}${key}/\n`
		result += formatDirectoryStructure(value as DirectoryStructure, indent + "  ", maxDepth, currentDepth + 1)
	}
	if (structure["__files__"]) {
		const files = (structure["__files__"] as string[]).sort()
		for (const file of files) {
			result += `${indent}${file}\n`
		}
	}
	return result
}

let globalResolver: EnhancedPathResolver | null = null

function getGlobalResolver(): EnhancedPathResolver {
	if (!globalResolver) {
		globalResolver = new EnhancedPathResolver()
	}
	return globalResolver
}

/**
 * Resolve a set of loosely-specified file references and render them as an
 * indented directory tree (used by the Location fallback path).
 */
export async function processPathsGenerateDirectory(
	inputPaths: string[],
	options: { workdir?: string; maxResults?: number; forceRescan?: boolean } = {},
): Promise<string> {
	const workdir = options.workdir
	const { maxResults = 100, forceRescan = false } = options
	const resolver = getGlobalResolver()
	if (forceRescan) {
		resolver.resetFileNameMap()
	}
	let pathInfos = await resolver.resolvePathsEnhanced(inputPaths, options.workdir)
	if (pathInfos.length > maxResults) {
		pathInfos = pathInfos.slice(0, maxResults)
	}
	const directoryStructure = buildDirectoryStructure(pathInfos, workdir)
	return formatDirectoryStructure(directoryStructure)
}

export function resetGlobalFileNameMap(): void {
	globalResolver?.resetFileNameMap()
}
