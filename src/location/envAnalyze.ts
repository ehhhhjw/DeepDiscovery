/**
 * Environment-aware analysis (Location stage, paper §III).
 * Produces c_q = (techStack, moduleScope, rolePriors, constraints).
 */
import type { LLMClient, LLMUsage } from "../llm/client"
import { Logger } from "../logger"
import { ARTIFACT_ROLE_PRIORS } from "../prompts/artifacts"
import { envAnalyzePrompt } from "../prompts/envAnalyze"
import type { EnvironmentContext } from "../types"

const FALLBACK_ENV: EnvironmentContext = {
	techStack: [],
	moduleScope: [],
	rolePriors: { ...ARTIFACT_ROLE_PRIORS },
	constraints: [],
}

/** Extract the first JSON object from a possibly noisy LLM response. */
function parseJsonObject(text: string): any | null {
	const start = text.indexOf("{")
	const end = text.lastIndexOf("}")
	if (start === -1 || end === -1 || end <= start) {
		return null
	}
	try {
		return JSON.parse(text.slice(start, end + 1))
	} catch {
		return null
	}
}

export async function analyzeEnvironment(
	llm: LLMClient,
	task: string,
	fileStructure: string,
): Promise<{ environment: EnvironmentContext; usage: LLMUsage }> {
	const prompt = envAnalyzePrompt(task, fileStructure)
	const { text, usage } = await llm.complete("You are a precise software repository analyst.", prompt)
	const parsed = parseJsonObject(text)

	if (!parsed) {
		Logger.warn("Environment analysis: could not parse JSON, using fallback.")
		return { environment: { ...FALLBACK_ENV }, usage }
	}

	const environment: EnvironmentContext = {
		techStack: Array.isArray(parsed.techStack) ? parsed.techStack.map(String) : [],
		moduleScope: Array.isArray(parsed.moduleScope) ? parsed.moduleScope.map(String) : [],
		rolePriors:
			parsed.rolePriors && typeof parsed.rolePriors === "object"
				? { ...ARTIFACT_ROLE_PRIORS, ...parsed.rolePriors }
				: { ...ARTIFACT_ROLE_PRIORS },
		constraints: Array.isArray(parsed.constraints) ? parsed.constraints.map(String) : [],
	}
	return { environment, usage }
}
