/**
 * Lightweight token estimation (approximate, offline).
 * Ported from ACoder's `locationComponent.estimateTokens`.
 */
export function estimateTokens(text: string): number {
	const cleanText = text.trim().replace(/\s+/g, " ")
	const tokens = cleanText.match(/[\w']+|[.,!?;]|\s/g) || []
	return tokens.length
}
