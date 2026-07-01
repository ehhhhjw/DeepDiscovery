/**
 * Simple task-keyed JSON cache utilities.
 * Ported from ACoder's `utils/dataCacheUtils.ts` (no behavioral changes).
 */
import * as fs from "fs"
import * as path from "path"

async function fileExistsAtPath(filePath: string): Promise<boolean> {
	try {
		await fs.promises.access(filePath)
		return true
	} catch {
		return false
	}
}

/**
 * Read a cached value for `taskId` from a JSON cache file.
 * Returns "" when the file or key is missing.
 */
export async function findCacheInfo(cacheFilePath: string, taskId: string): Promise<string> {
	try {
		if (await fileExistsAtPath(cacheFilePath)) {
			const fileContent = fs.readFileSync(cacheFilePath, "utf-8")
			const cacheData = JSON.parse(fileContent)
			if (cacheData[taskId]) {
				return cacheData[taskId]
			}
			return ""
		}
		return ""
	} catch (error) {
		console.error("Failed to read cache file:", error)
		return ""
	}
}

/** Persist `cacheInfo` under `taskId` in a JSON cache file. */
export async function saveCacheInfo(cacheFilePath: string, taskId: string, cacheInfo: string): Promise<void> {
	try {
		const dir = path.dirname(cacheFilePath)
		await fs.promises.mkdir(dir, { recursive: true })
		const data = { [taskId]: cacheInfo }
		await fs.promises.writeFile(cacheFilePath, JSON.stringify(data, null, 2))
	} catch (error) {
		console.error("Failed to save cache info:", error)
	}
}
