/**
 * Anthropic-compatible LLM client.
 *
 * Replaces ACoder's heavyweight `ApiHandler` + `locationComponent.createLLMMessage`.
 * Streams a single-turn completion and aggregates token usage / cost. The
 * {@link LLMClient} interface lets tests inject a mock (see MockLLMClient).
 */
import Anthropic from "@anthropic-ai/sdk"
import { Logger } from "../logger"
import { calculateApiCostAnthropic, getModelInfo } from "./cost"

export interface LLMUsage {
	inputTokens: number
	outputTokens: number
	cacheWriteTokens: number
	cacheReadTokens: number
	cost: number
}

export interface LLMResult {
	text: string
	usage: LLMUsage
}

export interface LLMClient {
	/** Run a single system+user turn and return the aggregated text and usage. */
	complete(systemPrompt: string, userMessage: string): Promise<LLMResult>
	readonly model: string
}

export const EMPTY_USAGE: LLMUsage = {
	inputTokens: 0,
	outputTokens: 0,
	cacheWriteTokens: 0,
	cacheReadTokens: 0,
	cost: 0,
}

export function addUsage(a: LLMUsage, b: LLMUsage): LLMUsage {
	return {
		inputTokens: a.inputTokens + b.inputTokens,
		outputTokens: a.outputTokens + b.outputTokens,
		cacheWriteTokens: a.cacheWriteTokens + b.cacheWriteTokens,
		cacheReadTokens: a.cacheReadTokens + b.cacheReadTokens,
		cost: a.cost + b.cost,
	}
}

export interface AnthropicClientOptions {
	apiKey: string
	baseURL?: string
	model: string
	maxTokens?: number
}

export class AnthropicLLMClient implements LLMClient {
	private client: Anthropic
	readonly model: string
	private maxTokens: number

	constructor(options: AnthropicClientOptions) {
		if (!options.apiKey) {
			throw new Error(
				"Missing API key. Set ANTHROPIC_API_KEY (or pass apiKey) to run the LLM-driven stages.",
			)
		}
		this.client = new Anthropic({
			apiKey: options.apiKey,
			...(options.baseURL ? { baseURL: options.baseURL } : {}),
		})
		this.model = options.model
		this.maxTokens = options.maxTokens ?? 8192
	}

	async complete(systemPrompt: string, userMessage: string): Promise<LLMResult> {
		const stream = await this.client.messages.create({
			model: this.model,
			max_tokens: this.maxTokens,
			system: systemPrompt,
			messages: [{ role: "user", content: userMessage }],
			stream: true,
		})

		let text = ""
		let inputTokens = 0
		let outputTokens = 0
		let cacheWriteTokens = 0
		let cacheReadTokens = 0

		for await (const event of stream) {
			if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
				text += event.delta.text
			} else if (event.type === "message_start") {
				const usage = event.message.usage
				inputTokens += usage.input_tokens ?? 0
				outputTokens += usage.output_tokens ?? 0
				cacheWriteTokens += usage.cache_creation_input_tokens ?? 0
				cacheReadTokens += usage.cache_read_input_tokens ?? 0
			} else if (event.type === "message_delta") {
				outputTokens += event.usage?.output_tokens ?? 0
			}
		}

		const cost = calculateApiCostAnthropic(
			getModelInfo(this.model),
			inputTokens,
			outputTokens,
			cacheWriteTokens,
			cacheReadTokens,
		)

		Logger.log(
			`LLM usage — in:${inputTokens} out:${outputTokens} cacheW:${cacheWriteTokens} cacheR:${cacheReadTokens} cost:$${cost.toFixed(4)}`,
		)

		return {
			text,
			usage: { inputTokens, outputTokens, cacheWriteTokens, cacheReadTokens, cost },
		}
	}
}
