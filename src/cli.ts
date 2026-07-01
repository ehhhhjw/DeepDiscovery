#!/usr/bin/env node
/**
 * DeepDiscovery CLI.
 *
 *   deepdiscovery --repo <path> --task "<description>" [--budget N] [--json] [--verbose]
 */
import { Command } from "commander"
import * as fs from "fs"
import * as path from "path"
import { runDeepDiscovery } from "./core/deepDiscovery"
import type { DeepDiscoveryOptions } from "./types"

const program = new Command()

program
	.name("deepdiscovery")
	.description("Location–Inference framework for task-level repository understanding")
	.requiredOption("-r, --repo <path>", "path to the repository to analyze")
	.requiredOption("-t, --task <text>", "natural-language task description")
	.option("-b, --budget <number>", "exploration budget B_max (approx tokens)", (v) => Number(v))
	.option("-k, --kappa <number>", "metadata->full-text promotion threshold κ (0..1)", (v) => Number(v))
	.option("-s, --tau-stop <number>", "expansion stop threshold τ_stop (0..1)", (v) => Number(v))
	.option("-m, --model <id>", "model id override")
	.option("-o, --output <file>", "write the serialized context package to a file")
	.option("--json", "print the full result as JSON", false)
	.option("-v, --verbose", "verbose logging", false)
	.action(async (opts) => {
		const repoPath = path.resolve(opts.repo)
		if (!fs.existsSync(repoPath) || !fs.statSync(repoPath).isDirectory()) {
			console.error(`Error: repository path not found or not a directory: ${repoPath}`)
			process.exit(1)
		}

		if (opts.verbose) {
			process.env.DD_VERBOSE = "true"
		}

		const options: DeepDiscoveryOptions = {
			repoPath,
			task: opts.task,
			budget: opts.budget,
			kappa: opts.kappa,
			tauStop: opts.tauStop,
			model: opts.model,
			onProgress: (msg) => console.error(`• ${msg}`),
		}

		try {
			const result = await runDeepDiscovery(options)

			if (opts.output) {
				fs.writeFileSync(opts.output, result.serialized, "utf-8")
				console.error(`Context package written to ${opts.output}`)
			}

			if (opts.json) {
				process.stdout.write(JSON.stringify(result, null, 2) + "\n")
			} else {
				console.log("\n=== Task-relevant files (Ŷ) ===")
				for (const f of result.relatedFiles) {
					console.log(`  ${f}`)
				}
				console.log("\n=== Structured context package ===\n")
				console.log(result.serialized)
				console.log(
					`\n[usage] in:${result.usage.inputTokens} out:${result.usage.outputTokens} cost:$${result.usage.cost.toFixed(4)}`,
				)
			}
		} catch (err) {
			console.error(`\nDeepDiscovery failed: ${err instanceof Error ? err.message : String(err)}`)
			process.exit(1)
		}
	})

program.parseAsync(process.argv)
