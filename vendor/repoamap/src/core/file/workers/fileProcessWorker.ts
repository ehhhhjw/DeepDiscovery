import type { repoamapConfigMerged } from '../../../config/configSchema.js';
import { logger, setLogLevelByEnv } from '../../../shared/logger.js';
import { processContent } from '../fileProcessContent.js';
import type { ProcessedFile, RawFile } from '../fileTypes.js';

export interface FileProcessTask {
  rawFile: RawFile;
  config: repoamapConfigMerged;
}

// Set logger log level from environment variable if provided
setLogLevelByEnv();

export default async ({ rawFile, config }: FileProcessTask): Promise<ProcessedFile> => {
  const processedContent = await processContent(rawFile, config);
  return {
    path: rawFile.path,
    content: processedContent,
  };
};
