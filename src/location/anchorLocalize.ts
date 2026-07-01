/**
 * Rule-guided anchor localization (Location stage, paper §III).
 *
 * Ranks candidate entities via an LLM that fuses semantic, structural-summary,
 * rule, and role-prior signals (an executable approximation of Score_loc), then
 * returns the high-confidence task anchors Ĥ. Mirrors the first round of
 * ACoder's `locationComponent.performCombinedFileLocation`.
 */
import type { LLMClient, LLMUsage } from "../llm/client"
import { Logger } from "../logger"
import { anchorLocalizePrompt } from "../prompts/anchorLocalize"
import type { EnvironmentContext } from "../types"
import { extractAllFilesName } from "../utils/fileExtract"
import { estimateTokens } from "../utils/tokens"

const MAX_VIEW_TOKENS = 60000

export interface LocalizeResult {
	/** Task anchors as file names/paths mentioned by the model. */
	anchors: string[]
	/** Raw LLM answer text. */
	rawText: string
	usage: LLMUsage
	/** Whether the LLM call actually ran (false if the view was too large / empty). */
	ran: boolean
}

/**
 * Localize task anchors from a repository view (compressed repomap or structure).
 * If the view exceeds the token guard, the call is skipped and `ran=false`.
 */
export async function localizeAnchors(
	llm: LLMClient,
	task: string,
	repoView: string,
	environment?: EnvironmentContext,
): Promise<LocalizeResult> {
	const empty: LocalizeResult = {
		anchors: [],
		rawText: "",
		usage: { inputTokens: 0, outputTokens: 0, cacheWriteTokens: 0, cacheReadTokens: 0, cost: 0 },
		ran: false,
	}
	if (!repoView || repoView.trim() === "") {
		return empty
	}

	const tokenCount = estimateTokens(repoView)
	Logger.info(`Anchor localization view token estimate: ${tokenCount}`)
	if (tokenCount >= MAX_VIEW_TOKENS) {
		Logger.warn(`Repository view too large (${tokenCount} tokens); skipping this localization round.`)
		return empty
	}

	const prompt = anchorLocalizePrompt(task, repoView, environment)
	const { text, usage } = await llm.complete(
		"You are an expert software engineer locating task-relevant files in a repository.",
		prompt,
	)

	const anchors = extractAllFilesName(text)
	return { anchors, rawText: text, usage, ran: true }
}
