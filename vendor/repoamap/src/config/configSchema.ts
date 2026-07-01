import type { TiktokenEncoding } from 'tiktoken';
import { z } from 'zod';

// Output style enum
export const repoamapOutputStyleSchema = z.enum(['xml', 'markdown', 'plain']);
export type repoamapOutputStyle = z.infer<typeof repoamapOutputStyleSchema>;

// Default values map
export const defaultFilePathMap: Record<repoamapOutputStyle, string> = {
  xml: 'repoamap-output.xml',
  markdown: 'repoamap-output.md',
  plain: 'repoamap-output.txt',
} as const;

// Base config schema
export const repoamapConfigBaseSchema = z.object({
  $schema: z.string().optional(),
  input: z
    .object({
      maxFileSize: z.number().optional(),
    })
    .optional(),
  output: z
    .object({
      filePath: z.string().optional(),
      style: repoamapOutputStyleSchema.optional(),
      parsableStyle: z.boolean().optional(),
      headerText: z.string().optional(),
      instructionFilePath: z.string().optional(),
      fileSummary: z.boolean().optional(),
      directoryStructure: z.boolean().optional(),
      files: z.boolean().optional(),
      removeComments: z.boolean().optional(),
      removeEmptyLines: z.boolean().optional(),
      compress: z.boolean().optional(),
      topFilesLength: z.number().optional(),
      showLineNumbers: z.boolean().optional(),
      copyToClipboard: z.boolean().optional(),
      includeEmptyDirectories: z.boolean().optional(),
      git: z
        .object({
          sortByChanges: z.boolean().optional(),
          sortByChangesMaxCommits: z.number().optional(),
          includeDiffs: z.boolean().optional(),
        })
        .optional(),
    })
    .optional(),
  include: z.array(z.string()).optional(),
  ignore: z
    .object({
      useGitignore: z.boolean().optional(),
      useDefaultPatterns: z.boolean().optional(),
      customPatterns: z.array(z.string()).optional(),
    })
    .optional(),
  security: z
    .object({
      enableSecurityCheck: z.boolean().optional(),
    })
    .optional(),
  tokenCount: z
    .object({
      encoding: z.string().optional(),
    })
    .optional(),
});

// Default config schema with default values
export const repoamapConfigDefaultSchema = z.object({
  input: z
    .object({
      maxFileSize: z
        .number()
        .int()
        .min(1)
        .default(50 * 1024 * 1024), // Default: 50MB
    })
    .default({}),
  output: z
    .object({
      filePath: z.string().default(defaultFilePathMap.xml),
      style: repoamapOutputStyleSchema.default('xml'),
      parsableStyle: z.boolean().default(false),
      headerText: z.string().optional(),
      instructionFilePath: z.string().optional(),
      fileSummary: z.boolean().default(true),
      directoryStructure: z.boolean().default(true),
      files: z.boolean().default(true),
      removeComments: z.boolean().default(false),
      removeEmptyLines: z.boolean().default(false),
      compress: z.boolean().default(false),
      topFilesLength: z.number().int().min(0).default(5),
      showLineNumbers: z.boolean().default(false),
      copyToClipboard: z.boolean().default(false),
      includeEmptyDirectories: z.boolean().optional(),
      git: z
        .object({
          sortByChanges: z.boolean().default(true),
          sortByChangesMaxCommits: z.number().int().min(1).default(100),
          includeDiffs: z.boolean().default(false),
        })
        .default({}),
    })
    .default({}),
  include: z.array(z.string()).default([]),
  ignore: z
    .object({
      useGitignore: z.boolean().default(true),
      useDefaultPatterns: z.boolean().default(true),
      customPatterns: z.array(z.string()).default([]),
    })
    .default({}),
  security: z
    .object({
      enableSecurityCheck: z.boolean().default(true),
    })
    .default({}),
  tokenCount: z
    .object({
      encoding: z
        .string()
        .default('o200k_base')
        .transform((val) => val as TiktokenEncoding),
    })
    .default({}),
});

// File-specific schema. Add options for file path and style
export const repoamapConfigFileSchema = repoamapConfigBaseSchema;

// CLI-specific schema. Add options for standard output mode
export const repoamapConfigCliSchema = repoamapConfigBaseSchema.and(
  z.object({
    output: z
      .object({
        stdout: z.boolean().optional(),
      })
      .optional(),
  }),
);

// Merged schema for all configurations
export const repoamapConfigMergedSchema = repoamapConfigDefaultSchema
  .and(repoamapConfigFileSchema)
  .and(repoamapConfigCliSchema)
  .and(
    z.object({
      cwd: z.string(),
    }),
  );

export type repoamapConfigDefault = z.infer<typeof repoamapConfigDefaultSchema>;
export type repoamapConfigFile = z.infer<typeof repoamapConfigFileSchema>;
export type repoamapConfigCli = z.infer<typeof repoamapConfigCliSchema>;
export type repoamapConfigMerged = z.infer<typeof repoamapConfigMergedSchema>;

export const defaultConfig = repoamapConfigDefaultSchema.parse({});
