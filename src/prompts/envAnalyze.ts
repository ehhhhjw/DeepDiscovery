/**
 * Environment-aware analysis prompt (Location stage, paper §III).
 * Infers c_q: technology stack, module scope, artifact-role priors, and constraints.
 */
import { ARTIFACT_ROLE_PRIORS } from "./artifacts"

export function envAnalyzePrompt(task: string, fileStructure: string): string {
	return `You analyze a software repository to infer the context needed to locate task-relevant files.

## Task
${task}

## Repository structure (partial)
${fileStructure}

## Instructions
Infer the environment context for this task. Respond with a SINGLE JSON object and nothing else:
{
  "techStack": string[],        // likely languages/frameworks, e.g. ["typescript","react"]
  "moduleScope": string[],      // directories/modules most likely to contain relevant files
  "rolePriors": {               // salience in [0,1] per artifact role for THIS task
    "implementation": number, "interface": number, "bridge": number,
    "configuration": number, "registration": number, "test": number, "documentation": number
  },
  "constraints": string[]       // explicit constraints extracted from the task
}

Default role priors to start from (adjust for the task): ${JSON.stringify(ARTIFACT_ROLE_PRIORS)}.
Output ONLY the JSON object.`
}
