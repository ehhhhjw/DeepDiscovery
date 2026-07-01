/**
 * Cache-path and project-name helpers.
 * Ported/simplified from ACoder's `utils/codeAnalyzer.ts` (VS Code coupling removed).
 */
import * as fs from "fs"
import * as os from "os"
import * as path from "path"
import { Logger } from "../logger"

const APP_DIR_NAME = "DeepDiscovery"

/** Derive a project name from the repository root (its folder basename). */
export function getProjectName(rootPath: string): string {
	return path.basename(path.resolve(rootPath))
}

/**
 * Base cache directory for the tool, honoring an explicit override first,
 * then OS conventions, falling back to the system temp dir when unwritable.
 */
export function getBaseCacheDir(override?: string): string {
	if (override && override.trim() !== "") {
		return path.resolve(override)
	}
	try {
		switch (os.platform()) {
			case "win32":
				return process.env.LOCALAPPDATA
					? path.join(process.env.LOCALAPPDATA, APP_DIR_NAME)
					: path.join(os.homedir(), "AppData", "Local", APP_DIR_NAME)
			case "darwin":
				return path.join(os.homedir(), "Library", "Caches", APP_DIR_NAME)
			default: {
				const base = process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache", APP_DIR_NAME)
				if (!fs.existsSync(base)) {
					return base
				}
				try {
					fs.accessSync(base, fs.constants.W_OK)
					return base
				} catch {
					return path.join(os.tmpdir(), APP_DIR_NAME)
				}
			}
		}
	} catch (e) {
		Logger.warn(`Failed to resolve cache dir, using temp: ${e instanceof Error ? e.message : String(e)}`)
		return path.join(os.tmpdir(), APP_DIR_NAME)
	}
}

/** Per-project cache directory (created if missing). Returns "" on failure. */
export function getProjectCacheDir(rootPath: string, override?: string): string {
	const projectName = getProjectName(rootPath)
	const dir = path.join(getBaseCacheDir(override), projectName)
	try {
		if (!fs.existsSync(dir)) {
			fs.mkdirSync(dir, { recursive: true })
		}
		return dir
	} catch (e) {
		Logger.warn(`Failed to create cache dir ${dir}: ${e instanceof Error ? e.message : String(e)}`)
		return ""
	}
}
