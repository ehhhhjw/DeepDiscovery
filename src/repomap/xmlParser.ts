/**
 * Repomap XML parser (metadata/text extraction for the context package).
 * Ported from ACoder's `utils/extractRepomap.ts`; the only change is that
 * `parseAndGenerateRepoMapXML` takes an explicit cache directory instead of
 * deriving it from a VS Code workspace.
 */
import * as fs from "fs"
import * as path from "path"

export interface FileContentItem {
	path: string
	content: string
}

export interface ParseResult {
	beforeFileSummary: string
	fileSummaryContent: string
	relatedDirectoryStructure: string
	relatedFileContents: FileContentItem[]
}

export class XMLParser {
	static async parseXMLFile(filePath: string, targetFilePaths?: string[] | string): Promise<ParseResult> {
		if (!fs.existsSync(filePath)) {
			throw new Error(`File not found: ${filePath}`)
		}
		const xmlContent = fs.readFileSync(filePath, "utf-8")
		let processedTargetPaths: string[] | undefined
		if (typeof targetFilePaths === "string") {
			processedTargetPaths = targetFilePaths
				.split(";")
				.map((p) => p.trim())
				.filter((p) => p.length > 0)
		} else {
			processedTargetPaths = targetFilePaths
		}
		return this.extractContent(xmlContent, processedTargetPaths)
	}

	static extractContent(xmlContent: string, targetFilePaths?: string[]): ParseResult {
		const fileSummaryStartTag = "<file_summary>"
		const fileSummaryEndTag = "</file_summary>"
		const directoryStructureStartTag = "<directory_structure>"
		const directoryStructureEndTag = "</directory_structure>"
		const fileSummaryStartIndex = xmlContent.indexOf(fileSummaryStartTag)
		const fileSummaryEndIndex = xmlContent.indexOf(fileSummaryEndTag)
		const directoryStructureStartIndex = xmlContent.indexOf(directoryStructureStartTag)
		const directoryStructureEndIndex = xmlContent.indexOf(directoryStructureEndTag)
		let beforeFileSummary = ""
		let fileSummaryContent = ""
		let relatedDirectoryStructure = ""

		if (fileSummaryStartIndex !== -1) {
			beforeFileSummary = xmlContent.substring(0, fileSummaryStartIndex).trim()
			const fileSummaryStartPos = fileSummaryStartIndex + fileSummaryStartTag.length
			fileSummaryContent = xmlContent.substring(fileSummaryStartPos, fileSummaryEndIndex).trim()
		} else if (directoryStructureStartIndex !== -1) {
			beforeFileSummary = xmlContent.substring(0, directoryStructureStartIndex).trim()
		} else {
			beforeFileSummary = xmlContent.trim()
		}

		if (directoryStructureStartIndex !== -1) {
			const directoryStructureStartPos = directoryStructureStartIndex + directoryStructureStartTag.length
			const directoryStructureContent = xmlContent.substring(directoryStructureStartPos, directoryStructureEndIndex).trim()
			if (targetFilePaths && targetFilePaths.length > 0) {
				relatedDirectoryStructure = this.filterRelatedDirectoryStructure(directoryStructureContent, targetFilePaths)
			} else {
				relatedDirectoryStructure = directoryStructureContent
			}
		}

		const fileContents = this.extractFileContents(xmlContent)
		let relatedFileContents: FileContentItem[] = []
		if (targetFilePaths && targetFilePaths.length > 0) {
			relatedFileContents = this.filterRelatedFileContents(fileContents, targetFilePaths)
		} else {
			relatedFileContents = fileContents
		}

		return { beforeFileSummary, fileSummaryContent, relatedDirectoryStructure, relatedFileContents }
	}

	private static filterRelatedDirectoryStructure(directoryStructure: string, targetFilePaths: string[]): string {
		const lines = directoryStructure.split("\n")
		const relatedLines: string[] = []
		const addedLines = new Set<string>()
		for (const targetPath of targetFilePaths) {
			const normalizedTargetPath = targetPath.replace(/\\/g, "/")
			const pathParts = normalizedTargetPath.split("/").filter((part) => part.length > 0)
			this.addPathHierarchy(lines, pathParts, relatedLines, addedLines)
		}
		return relatedLines.sort((a, b) => lines.indexOf(a) - lines.indexOf(b)).join("\n")
	}

	private static addPathHierarchy(lines: string[], pathParts: string[], relatedLines: string[], addedLines: Set<string>): void {
		if (pathParts.length === 1) {
			this.findFileByName(lines, pathParts[0], relatedLines, addedLines)
			return
		}
		let currentIndent = 0
		for (let i = 0; i < pathParts.length; i++) {
			const targetPart = pathParts[i]
			let found = false
			for (let j = 0; j < lines.length; j++) {
				const line = lines[j]
				const lineIndent = line.length - line.trimStart().length
				const trimmedLine = line.trim()
				if (trimmedLine.length === 0) {
					continue
				}
				if (lineIndent === currentIndent) {
					const fileName = trimmedLine.replace(/\/$/, "")
					if (fileName === targetPart) {
						if (!addedLines.has(line)) {
							relatedLines.push(line)
							addedLines.add(line)
						}
						currentIndent = lineIndent + 2
						found = true
						break
					}
				}
			}
			if (!found) {
				break
			}
		}
	}

	private static findFileByName(lines: string[], fileName: string, relatedLines: string[], addedLines: Set<string>): void {
		for (let i = 0; i < lines.length; i++) {
			const line = lines[i]
			const trimmedLine = line.trim()
			if (trimmedLine.length === 0) {
				continue
			}
			const currentFileName = trimmedLine.replace(/\/$/, "")
			if (currentFileName === fileName) {
				const currentIndent = line.length - line.trimStart().length
				this.addCompletePathHierarchy(lines, i, currentIndent, relatedLines, addedLines)
				break
			}
		}
	}

	private static addCompletePathHierarchy(
		lines: string[],
		targetIndex: number,
		targetIndent: number,
		relatedLines: string[],
		addedLines: Set<string>,
	): void {
		const pathLines: string[] = []
		let currentIndent = targetIndent
		pathLines.push(lines[targetIndex])
		for (let i = targetIndex - 1; i >= 0; i--) {
			const line = lines[i]
			const lineIndent = line.length - line.trimStart().length
			if (line.trim().length === 0) {
				continue
			}
			if (lineIndent < currentIndent) {
				pathLines.unshift(line)
				currentIndent = lineIndent
				if (lineIndent === 0) {
					break
				}
			}
		}
		for (const line of pathLines) {
			if (!addedLines.has(line)) {
				relatedLines.push(line)
				addedLines.add(line)
			}
		}
	}

	private static extractFileContents(xmlContent: string): FileContentItem[] {
		const fileContents: FileContentItem[] = []
		const fileTagRegex = /<file\s+path\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/file>/gi
		let match
		while ((match = fileTagRegex.exec(xmlContent)) !== null) {
			fileContents.push({ path: match[1].trim(), content: match[2].trim() })
		}
		return fileContents
	}

	private static filterRelatedFileContents(fileContents: FileContentItem[], targetFilePaths: string[]): FileContentItem[] {
		const relatedFiles: FileContentItem[] = []
		for (const fileContent of fileContents) {
			const normalizedFilePath = fileContent.path.replace(/\\/g, "/")
			for (const targetPath of targetFilePaths) {
				const normalizedTargetPath = targetPath.replace(/\\/g, "/")
				if (this.isExactPathMatch(normalizedFilePath, normalizedTargetPath)) {
					if (!relatedFiles.some((f) => f.path === fileContent.path)) {
						relatedFiles.push(fileContent)
					}
					break
				}
			}
		}
		return relatedFiles
	}

	private static isExactPathMatch(filePath: string, targetPath: string): boolean {
		if (filePath === targetPath) {
			return true
		}
		const fileName = filePath.split("/").pop() || ""
		if (fileName === targetPath) {
			return true
		}
		if (filePath.endsWith("/" + targetPath) || filePath.endsWith(targetPath)) {
			const beforeTarget = filePath.substring(0, filePath.length - targetPath.length)
			if (beforeTarget === "" || beforeTarget.endsWith("/")) {
				return true
			}
		}
		if (targetPath.endsWith("/" + filePath) || targetPath.endsWith(filePath)) {
			const beforeFile = targetPath.substring(0, targetPath.length - filePath.length)
			if (beforeFile === "" || beforeFile.endsWith("/")) {
				return true
			}
		}
		return false
	}

	static async generateCombinedXML(
		extractedContent: ParseResult,
		outputDir = "./output",
		fileName = "combined_extracted.xml",
	): Promise<string> {
		if (!fs.existsSync(outputDir)) {
			fs.mkdirSync(outputDir, { recursive: true })
		}
		let xmlContent = ""
		let cleanedBeforeContent = extractedContent.beforeFileSummary
		cleanedBeforeContent = cleanedBeforeContent.replace(/<directory_structure>[\s\S]*?<\/directory_structure>/g, "")
		cleanedBeforeContent = cleanedBeforeContent.replace(/<file\s+path\s*=\s*["'][^"']+["'][^>]*>[\s\S]*?<\/file>/g, "")
		cleanedBeforeContent = cleanedBeforeContent.replace(/\n\s*\n\s*\n/g, "\n\n").trim()
		if (cleanedBeforeContent) {
			xmlContent += cleanedBeforeContent + "\n\n"
		}
		if (extractedContent.fileSummaryContent) {
			xmlContent += "<file_summary>\n" + extractedContent.fileSummaryContent + "\n</file_summary>\n\n"
		}
		if (extractedContent.relatedDirectoryStructure) {
			xmlContent += "<directory_structure>\n" + extractedContent.relatedDirectoryStructure + "\n</directory_structure>\n\n"
		}
		for (const fileContent of extractedContent.relatedFileContents) {
			xmlContent += `<file path="${fileContent.path}">\n${fileContent.content}\n</file>\n\n`
		}
		if (extractedContent.beforeFileSummary.includes("<document>")) {
			xmlContent += "</document>"
		}
		const outputPath = path.join(outputDir, fileName)
		fs.writeFileSync(outputPath, xmlContent, "utf-8")
		return outputPath
	}
}

/**
 * Parse the full compressed repomap and emit a filtered XML scoped to
 * `targetFilePaths`. Reads `<cacheDir>/repomap-output-all.xml` and writes
 * `<cacheDir>/repomap-output-locate.xml`. Returns the output path, or "" on error.
 */
export async function parseAndGenerateRepoMapXML(cacheDir: string, targetFilePaths?: string[]): Promise<string> {
	try {
		const inputPath = path.join(cacheDir, "repomap-output-all.xml")
		const outputPath = path.join(cacheDir, "repomap-output-locate.xml")
		const result = await XMLParser.parseXMLFile(inputPath, targetFilePaths)
		return await XMLParser.generateCombinedXML(result, path.dirname(outputPath), path.basename(outputPath))
	} catch (error) {
		return ""
	}
}
