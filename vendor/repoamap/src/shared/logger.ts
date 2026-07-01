import util from 'node:util';
import pc from 'picocolors';

export const repoamapLogLevels = {
  SILENT: -1, // No output
  ERROR: 0, // error
  WARN: 1, // warn
  INFO: 2, // success, info, log, note
  DEBUG: 3, // debug, trace
} as const;

export type repoamapLogLevel = (typeof repoamapLogLevels)[keyof typeof repoamapLogLevels];

class repoamapLogger {
  private level: repoamapLogLevel = repoamapLogLevels.INFO;

  constructor() {
    this.init();
  }

  init() {
    this.setLogLevel(repoamapLogLevels.INFO);
  }

  setLogLevel(level: repoamapLogLevel) {
    this.level = level;
  }

  getLogLevel(): repoamapLogLevel {
    return this.level;
  }

  error(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.ERROR) {
      console.error(pc.red(this.formatArgs(args)));
    }
  }

  warn(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.WARN) {
      console.log(pc.yellow(this.formatArgs(args)));
    }
  }

  success(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.INFO) {
      console.log(pc.green(this.formatArgs(args)));
    }
  }

  info(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.INFO) {
      console.log(pc.cyan(this.formatArgs(args)));
    }
  }

  log(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.INFO) {
      console.log(this.formatArgs(args));
    }
  }

  note(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.INFO) {
      console.log(pc.dim(this.formatArgs(args)));
    }
  }

  debug(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.DEBUG) {
      console.log(pc.blue(this.formatArgs(args)));
    }
  }

  trace(...args: unknown[]) {
    if (this.level >= repoamapLogLevels.DEBUG) {
      console.log(pc.gray(this.formatArgs(args)));
    }
  }

  private formatArgs(args: unknown[]): string {
    return args
      .map((arg) => (typeof arg === 'object' ? util.inspect(arg, { depth: null, colors: true }) : arg))
      .join(' ');
  }
}

export const logger = new repoamapLogger();

export const setLogLevel = (level: repoamapLogLevel) => {
  logger.setLogLevel(level);
};

/**
 * Set logger log level from repoamap_LOGLEVEL environment variable if valid.
 */
export const setLogLevelByEnv = () => {
  const logLevelStr = process.env.repoamap_LOGLEVEL;
  const logLevelNum = Number(logLevelStr);
  if (
    logLevelNum === repoamapLogLevels.SILENT ||
    logLevelNum === repoamapLogLevels.ERROR ||
    logLevelNum === repoamapLogLevels.WARN ||
    logLevelNum === repoamapLogLevels.INFO ||
    logLevelNum === repoamapLogLevels.DEBUG
  ) {
    setLogLevel(logLevelNum);
  }
};
