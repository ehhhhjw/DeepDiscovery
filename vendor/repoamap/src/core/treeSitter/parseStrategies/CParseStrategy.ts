import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

/**
 * Parse strategy for C language code
 * Handles C-specific syntax patterns including structs, unions, functions, typedefs, and enums
 */
export class CParseStrategy implements ParseStrategy {
  parseCapture(
    capture: { node: SyntaxNode; name: string },
    lines: string[],
    processedChunks: Set<string>,
    context: ParseContext,
  ): string | null {
    const { node, name } = capture;
    const startRow = node.startPosition.row;
    const endRow = node.endPosition.row;

    if (!lines[startRow]) {
      return null;
    }

    const isNameCapture = name.includes('name');
    const isCommentCapture = name.includes('comment');
    const isIncludeCapture = name.includes('include');
    const shouldSelect = isNameCapture || isCommentCapture || isIncludeCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;

    // Handle name captures
    if (isNameCapture) {
      chunk = node.text;

      const nodeType = node.parent?.type || node.type;
      const definitionType = this.getDefinitionType(name);

      if (definitionType === 'class') {
        // Handle struct and union definitions
        const structDefinition = this.getStructDefinition(lines, startRow, nodeType);
        if (structDefinition) {
          chunk = structDefinition;
        } else {
          chunk = `${this.getTypeKeyword(nodeType)} ${chunk}`;
        }
      } else if (definitionType === 'function') {
        // Handle function definitions
        const functionSignature = this.getFunctionSignature(lines, startRow);
        if (functionSignature) {
          chunk = functionSignature;
        } else {
          chunk = `function ${chunk}`;
        }
      } else if (definitionType === 'type') {
        // Handle type definitions and enums
        const typeDefinition = this.getTypeDefinition(lines, startRow, nodeType);
        if (typeDefinition) {
          chunk = typeDefinition;
        } else {
          chunk = nodeType.includes('enum') ? `enum ${chunk}` : `typedef ${chunk}`;
        }
      }
    } else if (isIncludeCapture) {
      // Handle include statements
      const includeLine = lines[startRow]?.trim();
      if (includeLine) {
        chunk = includeLine;
      } else {
        chunk = node.text.trim();
      }
    } else if (isCommentCapture) {
      // Handle comments
      const selectedLines = lines.slice(startRow, endRow + 1);
      if (selectedLines.length < 1) {
        return null;
      }
      chunk = selectedLines.join('\n').trim();
    } else {
      const selectedLines = lines.slice(startRow, endRow + 1);
      if (selectedLines.length < 1) {
        return null;
      }
      chunk = selectedLines.join('\n');
    }

    const normalizedChunk = chunk.trim();
    if (processedChunks.has(normalizedChunk)) {
      return null;
    }

    processedChunks.add(normalizedChunk);
    return chunk;
  }

  /**
   * Extract definition type from capture name
   * @param captureName - The capture name from tree-sitter query
   * @returns The definition type
   */
  private getDefinitionType(captureName: string): string {
    if (captureName.includes('class')) return 'class';
    if (captureName.includes('function')) return 'function';
    if (captureName.includes('type')) return 'type';
    return 'unknown';
  }

  /**
   * Get appropriate type keyword for C constructs
   * @param nodeType - The node type from tree-sitter
   * @returns The corresponding C keyword
   */
  private getTypeKeyword(nodeType: string): string {
    if (nodeType.includes('struct')) return 'struct';
    if (nodeType.includes('union')) return 'union';
    return 'type';
  }

  /**
   * Extract struct or union definition from source lines
   * @param lines - Source code lines
   * @param startRow - Starting row number
   * @param nodeType - The node type from tree-sitter
   * @returns Formatted struct/union definition or null
   */
  private getStructDefinition(lines: string[], startRow: number, nodeType: string): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // Match struct/union definitions
    const structMatch = line.match(/(struct|union)\s+(\w+)/);
    if (structMatch) {
      const keyword = structMatch[1];
      const structName = structMatch[2];
      return `${keyword} ${structName}`;
    }

    // Fallback to extract the line content
    return line.replace(/\s*{\s*$/, '').trim();
  }

  /**
   * Extract function signature from source lines
   * @param lines - Source code lines
   * @param startRow - Starting row number
   * @returns Formatted function signature or null
   */
  private getFunctionSignature(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // Try to match function signature patterns and simplify parameters
    const funcMatch = line.match(/^([^(]*)\(([^)]*)\)/);
    if (funcMatch) {
      const beforeParams = funcMatch[1].trim();
      const params = funcMatch[2].trim();

      // If there are parameters, replace with ..., otherwise keep empty parentheses
      const paramsPart = params ? '(...)' : '()';

      return `${beforeParams}${paramsPart}`.replace(/\s*{\s*$/, '').trim();
    }

    return null;
  }

  /**
   * Extract type definition from source lines
   * @param lines - Source code lines
   * @param startRow - Starting row number
   * @param nodeType - The node type from tree-sitter
   * @returns Formatted type definition or null
   */
  private getTypeDefinition(lines: string[], startRow: number, nodeType: string): string | null {
    const line = lines[startRow];
    if (!line) return null;

    if (nodeType.includes('enum')) {
      // Handle enum definitions
      const enumMatch = line.match(/enum\s+(\w+)/);
      if (enumMatch) {
        const enumName = enumMatch[1];
        return `enum ${enumName}`;
      }
    } else if (nodeType.includes('type_definition')) {
      // Handle typedef
      const typedefMatch = line.match(/typedef\s+[^;]+/);
      if (typedefMatch) {
        return typedefMatch[0];
      }
    }

    return line.replace(/\s*[{;]\s*$/, '').trim();
  }
}
