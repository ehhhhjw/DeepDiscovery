/**
 * Minimal standalone logger for DeepDiscovery.
 *
 * Replaces ACoder's `@/shared/services/Logger`. Verbosity is controlled by
 * {@link setVerbose} (wired from config / the `--verbose` CLI flag).
 */

let verbose = false

export function setVerbose(value: boolean): void {
	verbose = value
}

export function isVerbose(): boolean {
	return verbose
}

export const Logger = {
	/** Debug/trace-level output. Only shown when verbose mode is enabled. */
	log(message: string): void {
		if (verbose) {
			console.error(`[deepdiscovery] ${message}`)
		}
	},
	/** Informational output. Only shown when verbose mode is enabled. */
	info(message: string): void {
		if (verbose) {
			console.error(`[deepdiscovery] ${message}`)
		}
	},
	/** Warnings are always shown. */
	warn(message: string): void {
		console.error(`[deepdiscovery] WARN: ${message}`)
	},
	/** Errors are always shown. */
	error(message: string): void {
		console.error(`[deepdiscovery] ERROR: ${message}`)
	},
}
