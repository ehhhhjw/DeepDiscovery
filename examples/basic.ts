/**
 * Minimal library usage example.
 *
 * Run with:  ANTHROPIC_API_KEY=... npx tsx examples/basic.ts <repo-path> "<task>"
 */
import { run } from "../src/index"

async function main() {
	const repoPath = process.argv[2] ?? "tests/fixtures/sample-repo"
	const task = process.argv[3] ?? "Add retry logic to the payment flow"

	const pkg = await run({
		repoPath,
		task,
		onProgress: (msg) => console.error(`• ${msg}`),
	})

	console.log("\nTask-relevant files:")
	for (const f of pkg.relatedFiles) {
		console.log(`  - ${f}`)
	}
	console.log(`\nEntities: ${pkg.entities.length}, relations: ${pkg.relations.length}`)
	console.log(`Estimated cost: $${pkg.usage.cost.toFixed(4)}`)
}

main().catch((err) => {
	console.error(err)
	process.exit(1)
})
