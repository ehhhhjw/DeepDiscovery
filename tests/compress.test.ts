import * as fs from "fs"
import * as os from "os"
import * as path from "path"
import { afterAll, describe, expect, it } from "vitest"
import { compressRepository } from "../src/location/compress"

const SAMPLE_REPO = path.join(__dirname, "fixtures", "sample-repo")
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dd-compress-"))

afterAll(() => {
	try {
		fs.rmSync(tmp, { recursive: true, force: true })
	} catch {
		// ignore
	}
})

describe("adaptive compression", () => {
	it("compresses the sample repo via the vendored repoamap engine", () => {
		const result = compressRepository({ repoPath: SAMPLE_REPO, cacheDir: tmp })

		// The bundled @ali/repoamap engine should be selected (built under vendor/).
		expect(result.engine).toBe("repoamap")
		// Output is in the repomix/repoamap XML format consumed by the parser.
		expect(result.content).toContain("<file_summary>")
		expect(result.content).toMatch(/<file /)
		expect(fs.existsSync(result.outputPath)).toBe(true)
	}, 60000)

	it("resolves relative repo paths without double-resolving", () => {
		const rel = path.relative(process.cwd(), SAMPLE_REPO)
		const result = compressRepository({ repoPath: rel, cacheDir: tmp })
		expect(result.content.length).toBeGreaterThan(0)
	}, 60000)
})
