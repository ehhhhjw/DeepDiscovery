import * as path from "path"
import { describe, expect, it } from "vitest"
import { ProjectGraph } from "../src/inference/projectGraph"

const SAMPLE_REPO = path.join(__dirname, "fixtures", "sample-repo")

describe("ProjectGraph", () => {
	it("extracts import/require references from the sample repo", async () => {
		const graph = new ProjectGraph(SAMPLE_REPO)
		await graph.analyzeProject()
		const { references } = graph.getAnalysisResult()

		// paymentService imports paymentGateway and retryConfig.
		const fromService = references.filter((r) => r.sourceFileName === "paymentService.ts")
		const targets = fromService.map((r) => r.targetFileName)
		expect(targets).toContain("paymentGateway.ts")
		expect(targets).toContain("retryConfig.ts")
	})

	it("exposes per-file dependency metadata and statistics", async () => {
		const graph = new ProjectGraph(SAMPLE_REPO)
		await graph.analyzeProject()

		const servicePath = path.join(SAMPLE_REPO, "src", "payment", "paymentService.ts")
		const info = graph.getFileInfo(servicePath)
		expect(info).not.toBeNull()
		expect(info!.dependencies.length).toBeGreaterThanOrEqual(2)

		const stats = graph.getProjectStatistics()
		expect(stats.totalFiles).toBeGreaterThan(0)
		expect(stats.totalReferences).toBeGreaterThanOrEqual(2)
		expect(Array.isArray(graph.findCircularDependencies())).toBe(true)
	})
})
