/**
 * API cost calculation, ported from ACoder's `utils/cost.ts`.
 * The `ModelInfo` type is inlined here (was `@shared/api`) and reduced to the
 * fields DeepDiscovery actually uses for Anthropic-style pricing.
 */

export interface ModelInfo {
	/** USD per 1M input tokens. */
	inputPrice?: number
	/** USD per 1M output tokens. */
	outputPrice?: number
	/** USD per 1M cache-read tokens. */
	cacheReadsPrice?: number
	/** USD per 1M cache-write tokens. */
	cacheWritesPrice?: number
}

/**
 * Anthropic-compliant cost: `inputTokens` is the (non-cached) input total.
 * Returns cost in USD; contributions default to 0 when prices are unset.
 */
export function calculateApiCostAnthropic(
	modelInfo: ModelInfo,
	inputTokens: number,
	outputTokens: number,
	cacheCreationInputTokens = 0,
	cacheReadInputTokens = 0,
): number {
	const inputPrice = modelInfo.inputPrice || 0
	const outputPrice = modelInfo.outputPrice || 0
	const cacheReadsPrice = modelInfo.cacheReadsPrice || 0
	const cacheWritesPrice = modelInfo.cacheWritesPrice || 0

	const cacheWritesCost = (cacheWritesPrice / 1_000_000) * cacheCreationInputTokens
	const cacheReadsCost = (cacheReadsPrice / 1_000_000) * cacheReadInputTokens
	const baseInputCost = (inputPrice / 1_000_000) * inputTokens
	const outputCost = (outputPrice / 1_000_000) * outputTokens

	return cacheWritesCost + cacheReadsCost + baseInputCost + outputCost
}

/**
 * Best-effort default pricing table keyed by model-id substring (USD / 1M tokens).
 * Only used to surface an approximate cost; unknown models yield cost 0.
 */
const PRICING_TABLE: Array<{ match: RegExp; info: ModelInfo }> = [
	{
		match: /opus/i,
		info: { inputPrice: 15, outputPrice: 75, cacheReadsPrice: 1.5, cacheWritesPrice: 18.75 },
	},
	{
		match: /sonnet/i,
		info: { inputPrice: 3, outputPrice: 15, cacheReadsPrice: 0.3, cacheWritesPrice: 3.75 },
	},
	{
		match: /haiku/i,
		info: { inputPrice: 0.8, outputPrice: 4, cacheReadsPrice: 0.08, cacheWritesPrice: 1 },
	},
]

export function getModelInfo(modelId: string): ModelInfo {
	for (const entry of PRICING_TABLE) {
		if (entry.match.test(modelId)) {
			return entry.info
		}
	}
	return {}
}
