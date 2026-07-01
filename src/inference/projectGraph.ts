/**
 * Multi-relational repository graph G = (V, A) (Inference stage, paper §III).
 *
 * Ported from ACoder's `utils/projectAnalyzer.ts`. Extracts explicit dependency
 * edges (import / require / export) via tree-sitter, with a regex fallback.
 * The wasm files are resolved from the `tree-sitter-wasms` package so the code
 * works both from `src` (tsx) and `dist` (compiled).
 */
import * as fs from "fs"
import { Graph } from "graphlib"
import * as path from "path"
import Parser from "web-tree-sitter"
import { Logger } from "../logger"

const SUPPORTED_LANGUAGES: Record<string, string> = {
	".js": "javascript",
	".jsx": "javascript",
	".ts": "typescript",
	".tsx": "tsx",
	".py": "python",
	".java": "java",
	".cpp": "cpp",
	".c": "c",
	".cs": "c_sharp",
	".go": "go",
	".rs": "rust",
	".php": "php",
	".rb": "ruby",
}

export interface FileReference {
	sourceFile: string
	targetFile: string
	referenceType: "import" | "require" | "include" | "export"
	line: number
	column: number
	importPath?: string
	targetFileName?: string
}

export interface AnalysisReference {
	sourceFile: string
	targetFile: string
	referenceType: string
	line: number
	column: number
	importPath?: string
	sourceFileName: string
	targetFileName: string
}

/** Per-file node metadata (dependencies/dependents, size, mtime). */
export interface FileNode {
	label: string
	type: "file"
	path: string
	dependencies: string[]
	dependents: string[]
	lastModified: number
	size: number
}

/** Resolve the directory that holds the tree-sitter `.wasm` grammars. */
function resolveWasmDir(): string | null {
	try {
		const pkgJson = require.resolve("tree-sitter-wasms/package.json")
		return path.join(path.dirname(pkgJson), "out")
	} catch {
		// Fallback to a relative guess (project-root/node_modules).
		const guess = path.join(__dirname, "..", "..", "node_modules", "tree-sitter-wasms", "out")
		return fs.existsSync(guess) ? guess : null
	}
}

/** Locate the core `tree-sitter.wasm` shipped with web-tree-sitter (for Parser.init). */
function resolveCoreWasm(): string | null {
	try {
		const pkgJson = require.resolve("web-tree-sitter/package.json")
		const candidate = path.join(path.dirname(pkgJson), "tree-sitter.wasm")
		return fs.existsSync(candidate) ? candidate : null
	} catch {
		return null
	}
}

export class ProjectGraph {
	private graph: Graph
	private parsers: Map<string, Parser> = new Map()
	private workspacePath: string
	private fileReferences: FileReference[] = []
	private fileNodes: Map<string, FileNode> = new Map()
	private initialized = false

	constructor(workspacePath: string) {
		this.graph = new Graph({ directed: true })
		this.workspacePath = path.resolve(workspacePath)
	}

	private async initializeParsers(): Promise<void> {
		if (this.initialized) {
			return
		}
		const coreWasm = resolveCoreWasm()
		try {
			await Parser.init(coreWasm ? { locateFile: () => coreWasm } : undefined)
		} catch (e) {
			Logger.warn(`tree-sitter init failed, will use regex fallback: ${e instanceof Error ? e.message : String(e)}`)
			this.initialized = true
			return
		}

		const wasmDir = resolveWasmDir()
		if (!wasmDir) {
			Logger.warn("tree-sitter wasm directory not found; using regex fallback for reference parsing.")
			this.initialized = true
			return
		}

		const uniqueLanguages = new Set(Object.values(SUPPORTED_LANGUAGES))
		for (const language of uniqueLanguages) {
			try {
				const wasmPath = path.join(wasmDir, `tree-sitter-${language}.wasm`)
				if (fs.existsSync(wasmPath)) {
					const parser = new Parser()
					const Language = await Parser.Language.load(wasmPath)
					parser.setLanguage(Language)
					this.parsers.set(language, parser)
				}
			} catch (error) {
				Logger.log(`Failed to load parser for ${language}: ${error instanceof Error ? error.message : String(error)}`)
			}
		}
		this.initialized = true
	}

	private getLanguageFromFile(filePath: string): string | null {
		return SUPPORTED_LANGUAGES[path.extname(filePath).toLowerCase()] || null
	}

	private parseFileReferences(filePath: string, content: string): FileReference[] {
		const language = this.getLanguageFromFile(filePath)
		if (!language) {
			return []
		}
		const parser = this.parsers.get(language)
		let references: FileReference[] = []

		if (parser) {
			try {
				const tree = parser.parse(content)
				const traverse = (node: Parser.SyntaxNode) => {
					if (node.type === "import_statement" || node.type === "import_declaration") {
						const sourceNode = node.children.find((c) => c.type === "string" || c.type === "string_literal")
						if (sourceNode) {
							this.pushRef(references, filePath, sourceNode, "import")
						}
					}
					if (node.type === "call_expression") {
						const functionNode = node.children[0]
						if (functionNode && functionNode.text === "require") {
							const argumentNode = node.children
								.find((c) => c.type === "arguments")
								?.children.find((c) => c.type === "string" || c.type === "string_literal")
							if (argumentNode) {
								this.pushRef(references, filePath, argumentNode, "require")
							}
						}
					}
					if (node.type === "export_statement" || node.type === "export_declaration") {
						const sourceNode = node.children.find((c) => c.type === "string" || c.type === "string_literal")
						if (sourceNode) {
							this.pushRef(references, filePath, sourceNode, "export")
						}
					}
					for (const child of node.children) {
						traverse(child)
					}
				}
				traverse(tree.rootNode)
			} catch (error) {
				Logger.log(`tree-sitter parse error for ${filePath}: ${error instanceof Error ? error.message : String(error)}`)
				references = []
			}
		}

		if (references.length === 0) {
			references = this.parseFileReferencesWithRegex(filePath, content)
		}
		return references
	}

	private pushRef(
		references: FileReference[],
		filePath: string,
		node: Parser.SyntaxNode,
		type: "import" | "require" | "export",
	): void {
		const importPath = node.text.replace(/['"]/g, "")
		const resolvedPath = this.resolveImportPath(filePath, importPath)
		references.push({
			sourceFile: filePath,
			targetFile: resolvedPath || "",
			referenceType: type,
			line: node.startPosition.row,
			column: node.startPosition.column,
			importPath,
			targetFileName: this.extractFileNameFromImportPath(importPath),
		})
	}

	private parseFileReferencesWithRegex(filePath: string, content: string): FileReference[] {
		const references: FileReference[] = []
		const lines = content.split("\n")
		const patterns: Array<{ regex: RegExp; type: "import" | "require" | "export" }> = [
			{ regex: /import\s+.*?\s+from\s+['"`]([^'"`]+)['"`]/g, type: "import" },
			{ regex: /require\s*\(\s*['"`]([^'"`]+)['"`]\s*\)/g, type: "require" },
			{ regex: /export\s+.*?\s+from\s+['"`]([^'"`]+)['"`]/g, type: "export" },
			{ regex: /import\s*\(\s*['"`]([^'"`]+)['"`]\s*\)/g, type: "import" },
		]
		lines.forEach((line, lineIndex) => {
			patterns.forEach(({ regex, type }) => {
				let match
				regex.lastIndex = 0
				while ((match = regex.exec(line)) !== null) {
					const importPath = match[1]
					const resolvedPath = this.resolveImportPath(filePath, importPath)
					references.push({
						sourceFile: filePath,
						targetFile: resolvedPath || "",
						referenceType: type,
						line: lineIndex,
						column: match.index || 0,
						importPath,
						targetFileName: this.extractFileNameFromImportPath(importPath),
					})
				}
			})
		})
		return references
	}

	private extractFileNameFromImportPath(importPath: string): string {
		const parts = importPath.split("/")
		let fileName = parts[parts.length - 1]
		if (!path.extname(fileName)) {
			fileName += ".js"
		}
		return fileName
	}

	private resolveImportPath(sourceFile: string, importPath: string): string | null {
		try {
			if (!importPath.startsWith(".") && !importPath.startsWith("/")) {
				return null
			}
			const sourceDir = path.dirname(sourceFile)
			let resolvedPath: string
			if (importPath.startsWith(".")) {
				resolvedPath = path.resolve(sourceDir, importPath)
			} else {
				resolvedPath = path.resolve(this.workspacePath, importPath.substring(1))
			}
			const extensions = [".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]
			if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isFile()) {
				return resolvedPath
			}
			for (const ext of extensions) {
				const pathWithExt = resolvedPath + ext
				if (fs.existsSync(pathWithExt)) {
					return pathWithExt
				}
			}
			if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isDirectory()) {
				for (const ext of extensions) {
					const indexPath = path.join(resolvedPath, `index${ext}`)
					if (fs.existsSync(indexPath)) {
						return indexPath
					}
				}
			}
			return null
		} catch {
			return null
		}
	}

	private getAllFiles(): string[] {
		const files: string[] = []
		const extensions = Object.keys(SUPPORTED_LANGUAGES)
		const ignoreDirs = new Set(["node_modules", ".git", "dist", "build", ".next", ".nuxt", "out", "vendor"])
		const traverse = (dir: string) => {
			let items: string[]
			try {
				items = fs.readdirSync(dir)
			} catch {
				return
			}
			for (const item of items) {
				const fullPath = path.join(dir, item)
				let stat: fs.Stats
				try {
					stat = fs.statSync(fullPath)
				} catch {
					continue
				}
				if (stat.isDirectory()) {
					if (!ignoreDirs.has(item) && !item.startsWith(".")) {
						traverse(fullPath)
					}
				} else if (stat.isFile() && extensions.includes(path.extname(item).toLowerCase())) {
					files.push(fullPath)
				}
			}
		}
		traverse(this.workspacePath)
		return files
	}

	async analyzeProject(): Promise<void> {
		await this.initializeParsers()
		const files = this.getAllFiles()
		Logger.log(`Analyzing ${files.length} source files for references.`)
		for (const filePath of files) {
			try {
				const content = fs.readFileSync(filePath, "utf-8")
				const references = this.parseFileReferences(filePath, content)
				this.fileReferences.push(...references)
				if (!this.graph.hasNode(filePath)) {
					this.graph.setNode(filePath, { label: path.basename(filePath), path: filePath })
				}
			} catch (error) {
				Logger.log(`Failed to read ${filePath}: ${error instanceof Error ? error.message : String(error)}`)
			}
		}
		for (const ref of this.fileReferences) {
			if (ref.targetFile) {
				this.graph.setEdge(ref.sourceFile, ref.targetFile, { type: ref.referenceType })
			}
		}
		this.buildReferenceGraph()
		Logger.log(`Reference analysis complete: ${this.fileReferences.length} references.`)
	}

	/** Populate per-file node metadata (dependencies/dependents/size/mtime). */
	private ensureFileNode(filePath: string): FileNode {
		let node = this.fileNodes.get(filePath)
		if (node) {
			return node
		}
		let lastModified = 0
		let size = 0
		try {
			const stat = fs.statSync(filePath)
			lastModified = stat.mtime.getTime()
			size = stat.size
		} catch {
			// file may be a resolved-but-missing target; keep defaults
		}
		node = { label: path.basename(filePath), type: "file", path: filePath, dependencies: [], dependents: [], lastModified, size }
		this.fileNodes.set(filePath, node)
		return node
	}

	private buildReferenceGraph(): void {
		for (const nodeId of this.graph.nodes()) {
			this.ensureFileNode(nodeId)
		}
		for (const reference of this.fileReferences) {
			if (!reference.targetFile) {
				continue
			}
			const sourceNode = this.ensureFileNode(reference.sourceFile)
			const targetNode = this.ensureFileNode(reference.targetFile)
			if (!sourceNode.dependencies.includes(reference.targetFile)) {
				sourceNode.dependencies.push(reference.targetFile)
			}
			if (!targetNode.dependents.includes(reference.sourceFile)) {
				targetNode.dependents.push(reference.sourceFile)
			}
		}
	}

	getAnalysisResult(): { references: AnalysisReference[] } {
		return {
			references: this.fileReferences.map((ref) => ({
				sourceFile: ref.sourceFile,
				targetFile: ref.targetFile,
				referenceType: ref.referenceType,
				line: ref.line,
				column: ref.column,
				importPath: ref.importPath,
				sourceFileName: path.basename(ref.sourceFile),
				targetFileName: ref.targetFile ? path.basename(ref.targetFile) : ref.targetFileName || "",
			})),
		}
	}

	getGraph(): Graph {
		return this.graph
	}

	getAllFileReferences(): FileReference[] {
		return this.fileReferences
	}

	/** Direct dependencies (files this one imports) and dependents (importers). */
	getFileReferences(filePath: string): { dependencies: string[]; dependents: string[] } {
		const node = this.fileNodes.get(filePath)
		if (node) {
			return { dependencies: [...node.dependencies], dependents: [...node.dependents] }
		}
		const dependencies = (this.graph.outEdges(filePath) || []).map((e) => e.w)
		const dependents = (this.graph.inEdges(filePath) || []).map((e) => e.v)
		return { dependencies, dependents }
	}

	/** Node metadata for a file, or null if unknown. */
	getFileInfo(filePath: string): FileNode | null {
		return this.fileNodes.get(filePath) || null
	}

	/** All file nodes (copy). */
	getAllFileNodes(): Map<string, FileNode> {
		return new Map(this.fileNodes)
	}

	/** Dependencies/dependents with the underlying reference records. */
	getFileReferencesWithDetails(filePath: string): {
		dependencies: Array<{ file: string; references: FileReference[] }>
		dependents: Array<{ file: string; references: FileReference[] }>
	} {
		const dependencies = new Map<string, FileReference[]>()
		const dependents = new Map<string, FileReference[]>()
		for (const reference of this.fileReferences) {
			if (reference.sourceFile === filePath) {
				if (!dependencies.has(reference.targetFile)) {
					dependencies.set(reference.targetFile, [])
				}
				dependencies.get(reference.targetFile)!.push(reference)
			}
			if (reference.targetFile === filePath) {
				if (!dependents.has(reference.sourceFile)) {
					dependents.set(reference.sourceFile, [])
				}
				dependents.get(reference.sourceFile)!.push(reference)
			}
		}
		return {
			dependencies: Array.from(dependencies.entries()).map(([file, references]) => ({ file, references })),
			dependents: Array.from(dependents.entries()).map(([file, references]) => ({ file, references })),
		}
	}

	/** All circular dependency cycles in the reference graph. */
	findCircularDependencies(): string[][] {
		const cycles: string[][] = []
		const visited = new Set<string>()
		const recursionStack = new Set<string>()
		const dfs = (node: string, stack: string[]): void => {
			if (recursionStack.has(node)) {
				const cycleStart = stack.indexOf(node)
				if (cycleStart !== -1) {
					cycles.push([...stack.slice(cycleStart), node])
				}
				return
			}
			if (visited.has(node)) {
				return
			}
			visited.add(node)
			recursionStack.add(node)
			stack.push(node)
			for (const edge of this.graph.outEdges(node) || []) {
				dfs(edge.w, stack)
			}
			recursionStack.delete(node)
			stack.pop()
		}
		for (const node of this.graph.nodes()) {
			if (!visited.has(node)) {
				dfs(node, [])
			}
		}
		return cycles
	}

	/** Maximum dependency depth reachable from a file. */
	getFileDependencyDepth(filePath: string): number {
		const visited = new Set<string>()
		let maxDepth = 0
		const dfs = (node: string, depth: number): void => {
			if (visited.has(node)) {
				return
			}
			visited.add(node)
			maxDepth = Math.max(maxDepth, depth)
			for (const edge of this.graph.outEdges(node) || []) {
				dfs(edge.w, depth + 1)
			}
		}
		dfs(filePath, 0)
		return maxDepth
	}

	/** Aggregate statistics over the reference graph. */
	getProjectStatistics(): {
		totalFiles: number
		totalReferences: number
		averageDependencies: number
		averageDependents: number
		maxDependencies: number
		maxDependents: number
		circularDependencies: number
		isolatedFiles: number
	} {
		const totalFiles = this.fileNodes.size
		const totalReferences = this.fileReferences.length
		let totalDependencies = 0
		let totalDependents = 0
		let maxDependencies = 0
		let maxDependents = 0
		let isolatedFiles = 0
		for (const node of this.fileNodes.values()) {
			const depCount = node.dependencies.length
			const depentCount = node.dependents.length
			totalDependencies += depCount
			totalDependents += depentCount
			maxDependencies = Math.max(maxDependencies, depCount)
			maxDependents = Math.max(maxDependents, depentCount)
			if (depCount === 0 && depentCount === 0) {
				isolatedFiles++
			}
		}
		return {
			totalFiles,
			totalReferences,
			averageDependencies: totalFiles > 0 ? totalDependencies / totalFiles : 0,
			averageDependents: totalFiles > 0 ? totalDependents / totalFiles : 0,
			maxDependencies,
			maxDependents,
			circularDependencies: this.findCircularDependencies().length,
			isolatedFiles,
		}
	}

	/** Load a previously-saved analysis result (references + nodes) from disk. */
	loadAnalysisResult(inputPath: string): boolean {
		try {
			if (!fs.existsSync(inputPath)) {
				return false
			}
			const data = JSON.parse(fs.readFileSync(inputPath, "utf-8"))
			this.fileReferences = []
			this.fileNodes.clear()
			this.graph = new Graph({ directed: true })
			if (Array.isArray(data.references)) {
				this.fileReferences = data.references.map((ref: any) => ({
					sourceFile: ref.sourceFile,
					targetFile: ref.targetFile,
					referenceType: ref.referenceType,
					line: ref.line || 0,
					column: ref.column || 0,
					importPath: ref.importPath,
					targetFileName: ref.targetFileName,
				}))
			}
			if (Array.isArray(data.files)) {
				for (const fileData of data.files) {
					const node: FileNode = {
						label: fileData.label || path.basename(fileData.path),
						type: "file",
						path: fileData.path,
						dependencies: fileData.dependencies || [],
						dependents: fileData.dependents || [],
						lastModified: fileData.lastModified || 0,
						size: fileData.size || 0,
					}
					this.fileNodes.set(fileData.path, node)
					this.graph.setNode(fileData.path, { ...node })
				}
			}
			for (const reference of this.fileReferences) {
				if (this.graph.hasNode(reference.sourceFile) && this.graph.hasNode(reference.targetFile)) {
					this.graph.setEdge(reference.sourceFile, reference.targetFile, { type: reference.referenceType })
				}
			}
			return true
		} catch (error) {
			Logger.warn(`Failed to load analysis result: ${error instanceof Error ? error.message : String(error)}`)
			return false
		}
	}
}
