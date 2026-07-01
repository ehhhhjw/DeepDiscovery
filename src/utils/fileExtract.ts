/**
 * Extract candidate file paths/names from free-form LLM text.
 * Ported from ACoder's `codeAnalyzer.extractAllFilesName` / `isValidFileWithExtension`.
 */
import * as path from "path"

export function isValidFileWithExtension(file: string): boolean {
	if (!file || typeof file !== "string") {
		return false
	}
	const invalidPatterns = [/^https?:\/\//, /^ftp:\/\//, /^mailto:/, /\s{2,}/, /[<>|*?]/]
	return !invalidPatterns.some((pattern) => pattern.test(file))
}

/**
 * Pull unique file basenames out of a block of text (e.g. an LLM answer).
 * Keeps the shortest path seen per basename, then returns sorted basenames.
 */
export function extractAllFilesName(text: string): string[] {
	if (!text || typeof text !== "string") {
		return []
	}
	const filePattern = /([a-zA-Z_][a-zA-Z0-9_\-/]*\.[a-zA-Z0-9]{1,10})/g
	const matches: string[] = []
	let match: RegExpExecArray | null
	while ((match = filePattern.exec(text)) !== null) {
		matches.push(match[1])
	}

	const fileMap = new Map<string, string>()
	const uniqueFilePaths = new Set<string>()

	matches
		.filter((file) => file.length > 0 && file.length < 200)
		.map((file) => file.trim())
		.filter((file) => isValidFileWithExtension(file))
		.forEach((filePath) => {
			if (!uniqueFilePaths.has(filePath)) {
				uniqueFilePaths.add(filePath)
				const fileName = path.basename(filePath)
				if (!fileMap.has(fileName) || filePath.length < fileMap.get(fileName)!.length) {
					fileMap.set(fileName, filePath)
				}
			}
		})

	return Array.from(fileMap.values())
		.map((filePath) => path.basename(filePath))
		.sort()
}
