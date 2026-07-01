import fs from 'node:fs/promises';
import path from 'node:path';
import * as prompts from '@clack/prompts';
import pc from 'picocolors';
import {
  defaultConfig,
  defaultFilePathMap,
  type repoamapConfigFile,
  type repoamapOutputStyle,
} from '../../config/configSchema.js';
import { getGlobalDirectory } from '../../config/globalDirectory.js';
import { getVersion } from '../../core/file/packageJsonParse.js';
import { logger } from '../../shared/logger.js';

const onCancelOperation = () => {
  prompts.cancel('Initialization cancelled.');
  process.exit(0);
};

export const runInitAction = async (rootDir: string, isGlobal: boolean): Promise<void> => {
  prompts.intro(pc.bold(`Welcome to repoamap ${isGlobal ? 'Global ' : ''}Configuration!`));

  try {
    // Step 1: Ask if user wants to create a config file
    const isCreatedConfig = await createConfigFile(rootDir, isGlobal);

    // Step 2: Ask if user wants to create a .repoamapignore file
    const isCreatedIgnoreFile = await createIgnoreFile(rootDir, isGlobal);

    if (!isCreatedConfig && !isCreatedIgnoreFile) {
      prompts.outro(
        pc.yellow('No files were created. You can run this command again when you need to create configuration files.'),
      );
    } else {
      prompts.outro(pc.green('Initialization complete! You can now use repoamap with your specified settings.'));
    }
  } catch (error) {
    logger.error('An error occurred during initialization:', error);
  }
};

export const createConfigFile = async (rootDir: string, isGlobal: boolean): Promise<boolean> => {
  const configPath = path.resolve(isGlobal ? getGlobalDirectory() : rootDir, 'repoamap.config.json');

  const isCreateConfig = await prompts.confirm({
    message: `Do you want to create a ${isGlobal ? 'global ' : ''}${pc.green('repoamap.config.json')} file?`,
  });
  if (!isCreateConfig) {
    prompts.log.info(`Skipping ${pc.green('repoamap.config.json')} file creation.`);
    return false;
  }
  if (prompts.isCancel(isCreateConfig)) {
    onCancelOperation();
    return false;
  }

  let isConfigFileExists = false;
  try {
    await fs.access(configPath);
    isConfigFileExists = true;
  } catch {
    // File doesn't exist, so we can proceed
  }

  if (isConfigFileExists) {
    const isOverwrite = await prompts.confirm({
      message: `A ${isGlobal ? 'global ' : ''}${pc.green('repoamap.config.json')} file already exists. Do you want to overwrite it?`,
    });
    if (!isOverwrite) {
      prompts.log.info(`Skipping ${pc.green('repoamap.config.json')} file creation.`);
      return false;
    }
    if (prompts.isCancel(isOverwrite)) {
      onCancelOperation();
      return false;
    }
  }

  const options = await prompts.group(
    {
      outputStyle: () => {
        return prompts.select({
          message: 'Output style:',
          options: [
            { value: 'xml', label: 'XML', hint: 'Structured XML format' },
            { value: 'markdown', label: 'Markdown', hint: 'Markdown format' },
            { value: 'plain', label: 'Plain', hint: 'Simple text format' },
          ],
          initialValue: defaultConfig.output.style,
        });
      },
      outputFilePath: ({ results }) => {
        const defaultFilePath = defaultFilePathMap[results.outputStyle as repoamapOutputStyle];
        return prompts.text({
          message: 'Output file path:',
          initialValue: defaultFilePath,
          validate: (value) => (value.length === 0 ? 'Output file path is required' : undefined),
        });
      },
    },
    {
      onCancel: onCancelOperation,
    },
  );

  const config: repoamapConfigFile = {
    $schema: 'https://repoamap.com/schemas/latest/schema.json',
    ...defaultConfig,
    output: {
      ...defaultConfig.output,
      filePath: options.outputFilePath as string,
      style: options.outputStyle as repoamapOutputStyle,
    },
  };

  await fs.mkdir(path.dirname(configPath), { recursive: true });
  await fs.writeFile(configPath, JSON.stringify(config, null, 2));

  const relativeConfigPath = path.relative(rootDir, configPath);

  prompts.log.success(
    pc.green(`${isGlobal ? 'Global config' : 'Config'} file created!\n`) + pc.dim(`Path: ${relativeConfigPath}`),
  );

  return true;
};

export const createIgnoreFile = async (rootDir: string, isGlobal: boolean): Promise<boolean> => {
  if (isGlobal) {
    prompts.log.info(`Skipping ${pc.green('.repoamapignore')} file creation for global configuration.`);
    return false;
  }

  const ignorePath = path.resolve(rootDir, '.repoamapignore');
  const createIgnore = await prompts.confirm({
    message: `Do you want to create a ${pc.green('.repoamapignore')} file?`,
  });
  if (!createIgnore) {
    prompts.log.info(`Skipping ${pc.green('.repoamapignore')} file creation.`);
    return false;
  }
  if (prompts.isCancel(createIgnore)) {
    onCancelOperation();
    return false;
  }

  let isIgnoreFileExists = false;
  try {
    await fs.access(ignorePath);
    isIgnoreFileExists = true;
  } catch {
    // File doesn't exist, so we can proceed
  }

  if (isIgnoreFileExists) {
    const overwrite = await prompts.confirm({
      message: `A ${pc.green('.repoamapignore')} file already exists. Do you want to overwrite it?`,
    });

    if (!overwrite) {
      prompts.log.info(`${pc.green('.repoamapignore')} file creation skipped. Existing file will not be modified.`);
      return false;
    }
  }

  const defaultIgnoreContent = `# Add patterns to ignore here, one per line
# Example:
# *.log
# tmp/
`;

  await fs.writeFile(ignorePath, defaultIgnoreContent);
  prompts.log.success(
    pc.green('Created .repoamapignore file!\n') + pc.dim(`Path: ${path.relative(rootDir, ignorePath)}`),
  );

  return true;
};
