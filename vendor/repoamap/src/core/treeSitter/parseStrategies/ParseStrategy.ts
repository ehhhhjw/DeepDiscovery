import type { Query, SyntaxNode, Tree } from 'web-tree-sitter';
import type { repoamapConfigMerged } from '../../../config/configSchema.js';
import type { SupportedLang } from '../lang2Query.js';
import { CParseStrategy } from './CParseStrategy.js';
import { CppParseStrategy } from './CppParseStrategy.js';
import { CssParseStrategy } from './CssParseStrategy.js';
import { DefaultParseStrategy } from './DefaultParseStrategy.js';
import { GoParseStrategy } from './GoParseStrategy.js';
import { JavaParseStrategy } from './JavaParseStrategy.js';
import { JavaScriptParseStrategy } from './JavaScriptParseStrategy.js';
import { ObjectiveCParseStrategy } from './OCParseStrategy.js'; // 导入新的策略
import { PythonParseStrategy } from './PythonParseStrategy.js';
import { SwiftParseStrategy } from './SwiftParseStrategy.js';
import { TypeScriptParseStrategy } from './TypeScriptParseStrategy.js';
import { VueParseStrategy } from './VueParseStrategy.js';
export interface ParseContext {
  fileContent: string;
  lines: string[];
  tree: Tree;
  query: Query;
  config: repoamapConfigMerged;
}

export interface ParseStrategy {
  parseCapture(
    capture: { node: SyntaxNode; name: string },
    lines: string[],
    processedChunks: Set<string>,
    context: ParseContext,
  ): string | null;
}

export function createParseStrategy(lang: SupportedLang): ParseStrategy {
  switch (lang) {
    case 'javascript':
      return new JavaScriptParseStrategy();
    case 'typescript':
      return new TypeScriptParseStrategy();
    case 'python':
      return new PythonParseStrategy();
    case 'go':
      return new GoParseStrategy();
    case 'css':
      return new CssParseStrategy();
    case 'vue':
      return new VueParseStrategy();
    case 'java':
      return new JavaParseStrategy();
    case 'c':
      return new CParseStrategy();
    case 'cpp':
      return new CppParseStrategy();
    case 'objc':
      return new ObjectiveCParseStrategy(); // 添加Objective-C策略
    case 'swift':
      return new SwiftParseStrategy();
    default:
      return new DefaultParseStrategy();
  }
}
