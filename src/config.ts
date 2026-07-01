/**
 * Configuration loading for DeepDiscovery.
 *
 * Resolves framework parameters (κ, τ_stop, budget) and LLM settings from,
 * in order of precedence: explicit options -> environment variables -> defaults.
 */
import * as dotenv from "dotenv"

dotenv.config()

export interface ResolvedConfig {
	// LLM
	apiKey: string | undefined
	baseURL: string | undefined
	model: string
	// Framework parameters
	budget: number // B_max
	kappa: number // κ
	tauStop: number // τ_stop
	// Misc
	verbose: boolean
	cacheDir: string | undefined
}

export const DEFAULTS = {
	model: "claude-opus-4-8",
	budget: 60000,
	kappa: 0.6,
	tauStop: 0.3,
}

function numFromEnv(name: string, fallback: number): number {
	const raw = process.env[name]
	if (raw === undefined || raw.trim() === "") {
		return fallback
	}
	const parsed = Number(raw)
	return Number.isFinite(parsed) ? parsed : fallback
}

function boolFromEnv(name: string, fallback: boolean): boolean {
	const raw = process.env[name]
	if (raw === undefined) {
		return fallback
	}
	return /^(1|true|yes|on)$/i.test(raw.trim())
}

/**
 * Build the resolved configuration. Explicit `overrides` (typically from
 * {@link DeepDiscoveryOptions} or CLI flags) win over environment variables.
 */
export function loadConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
	const config: ResolvedConfig = {
		apiKey: overrides.apiKey ?? process.env.ANTHROPIC_API_KEY,
		baseURL: overrides.baseURL ?? process.env.ANTHROPIC_BASE_URL,
		model: overrides.model ?? process.env.DD_MODEL ?? DEFAULTS.model,
		budget: overrides.budget ?? numFromEnv("DD_BUDGET", DEFAULTS.budget),
		kappa: overrides.kappa ?? numFromEnv("DD_KAPPA", DEFAULTS.kappa),
		tauStop: overrides.tauStop ?? numFromEnv("DD_TAU_STOP", DEFAULTS.tauStop),
		verbose: overrides.verbose ?? boolFromEnv("DD_VERBOSE", false),
		cacheDir: overrides.cacheDir ?? process.env.DD_CACHE_DIR,
	}
	return config
}
