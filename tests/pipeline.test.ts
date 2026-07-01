import * as fs from "fs"
import * as os from "os"
import * as path from "path"
import { afterAll, describe, expect, it } from "vitest"
import { runDeepDiscovery } from "../src/core/deepDiscovery"
import type { ResolvedConfig } from "../src/config"
import type { LLMClient, LLMResult } from "../src/llm/client"

const SAMPLE_REPO = path.join(__dirname, "fixtures", "sample-repo")
const tmpCache = fs.mkdtempSync(path.join(os.tmpdir(), "dd-test-"))

/** Deterministic mock LLM that counts calls and branches on the prompt per stage. */
class MockLLM implements LLMClient {
	readonly model = "mock-model"
	calls = 0
	async complete(_system: string, user: string): Promise<LLMResult> {
		this.calls++
		const usage = { inputTokens: 10, outputTokens: 5, cacheWriteTokens: 0, cacheReadTokens: 0, cost: 0 }
		if (user.includes("SINGLE JSON object")) {
			return {
				text: JSON.stringify({
					techStack: ["typescript"],
					moduleScope: ["src/payment"],
					rolePriors: { implementation: 1, configuration: 0.8, test: 0.4 },
					constraints: ["add retry"],
				}),
				usage,
			}
		}
		// Anchor localization rounds (round 1 on the tree, round 2 on the repomap view).
		return { text: "The relevant files are paymentService.ts, retryConfig.ts", usage }
	}
}

function makeConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
	return {
		apiKey: "unused",
		baseURL: undefined,
		model: "mock-model",
		budget: 60000,
		kappa: 0.6,
		tauStop: 0.3,
		verbose: false,
		cacheDir: tmpCache,
		...overrides,
	}
}

afterAll(() => {
	try {
		fs.rmSync(tmpCache, { recursive: true, force: true })
	} catch {
		// ignore
	}
})

describe("DeepDiscovery pipeline (mocked LLM)", () => {
	it("locates anchors, expands, and runs second-round refinement", async () => {
		const llm = new MockLLM()
		const result = await runDeepDiscovery(
			{ repoPath: SAMPLE_REPO, task: "Add retry logic to the payment flow", useCache: false },
			{ llm, config: makeConfig() },
		)

		// Anchors from the mock plus the gateway recovered via the reference graph.
		expect(result.relatedFiles).toContain("paymentService.ts")
		expect(result.relatedFiles).toContain("retryConfig.ts")
		expect(result.relatedFiles).toContain("paymentGateway.ts")

		// Structured package is populated.
		expect(result.serialized).toContain("Task-Level Context Package")
		expect(result.entities.length).toBeGreaterThan(0)

		// Compression (repoamap) fed the context: at least one entity has real content.
		expect(result.entities.some((e) => e.content && !e.content.includes("metadata unavailable"))).toBe(true)

		// Three LLM calls: env analysis + round-1 + round-2 refinement.
		expect(llm.calls).toBe(3)
		expect(result.usage.inputTokens).toBe(30)
	}, 60000)

	it("short-circuits on a warm cache without calling the LLM", async () => {
		const cacheDir = fs.mkdtempSync(path.join(os.tmpdir(), "dd-cache-"))
		const opts = { repoPath: SAMPLE_REPO, task: "cache me", taskId: "fixed-key" }
		const cfg = makeConfig({ cacheDir })

		const first = new MockLLM()
		const r1 = await runDeepDiscovery(opts, { llm: first, config: cfg })
		expect(first.calls).toBeGreaterThan(0)

		const second = new MockLLM()
		const r2 = await runDeepDiscovery(opts, { llm: second, config: cfg })
		expect(second.calls).toBe(0) // served from cache
		expect(r2.relatedFiles).toEqual(r1.relatedFiles)

		fs.rmSync(cacheDir, { recursive: true, force: true })
	}, 60000)
})
