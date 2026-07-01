import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

export class CppParseStrategy implements ParseStrategy {
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
        // Handle class, struct, union definitions
        const classDefinition = this.getClassDefinition(lines, startRow, nodeType);
        if (classDefinition) {
          chunk = classDefinition;
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
      } else if (definitionType === 'method') {
        // Handle method definitions with namespace scope
        const scopeNode = this.findScopeNode(node);
        const methodSignature = this.getMethodSignature(lines, startRow, scopeNode);
        if (methodSignature) {
          chunk = methodSignature;
        } else {
          const scope = scopeNode ? scopeNode.text : '';
          chunk = scope ? `${scope}::${chunk}` : `method ${chunk}`;
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

  private getDefinitionType(captureName: string): string {
    if (captureName.includes('class')) return 'class';
    if (captureName.includes('function')) return 'function';
    if (captureName.includes('method')) return 'method';
    if (captureName.includes('type')) return 'type';
    return 'unknown';
  }

  private getTypeKeyword(nodeType: string): string {
    if (nodeType.includes('class')) return 'class';
    if (nodeType.includes('struct')) return 'struct';
    if (nodeType.includes('union')) return 'union';
    return 'type';
  }

  private getClassDefinition(lines: string[], startRow: number, nodeType: string): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // Match class/struct/union with possible inheritance
    const classMatch = line.match(/(class|struct|union)\s+(\w+)(\s*:\s*[^{]+)?/);
    if (classMatch) {
      const keyword = classMatch[1];
      const className = classMatch[2];
      const inheritance = classMatch[3];
      if (inheritance) {
        return `${keyword} ${className}${inheritance.replace(/\s*{\s*$/, '').trim()}`;
      }
      return `${keyword} ${className}`;
    }

    // Fallback to extract the line content
    return line.replace(/\s*{\s*$/, '').trim();
  }

  private getFunctionSignature(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // Try to match function signature patterns and simplify parameters
    const funcMatch = line.match(/^([^(]*)\(([^)]*)\)(\s*const)?(\s*override)?(\s*final)?/);
    if (funcMatch) {
      const beforeParams = funcMatch[1].trim();
      const params = funcMatch[2].trim();
      const afterParams = (funcMatch[3] || '') + (funcMatch[4] || '') + (funcMatch[5] || '');

      // If there are parameters, replace with ..., otherwise keep empty parentheses
      const paramsPart = params ? '(...)' : '()';

      return `${beforeParams}${paramsPart}${afterParams}`.replace(/\s*{\s*$/, '').trim();
    }

    return null;
  }

  private getMethodSignature(lines: string[], startRow: number, scopeNode: SyntaxNode | null): string | null {
    const line = lines[startRow];
    if (!line) return null;

    const signature = this.getFunctionSignature(lines, startRow);
    if (signature && scopeNode) {
      const scope = scopeNode.text;
      return `${scope}::${signature}`;
    }

    return signature;
  }

  private getTypeDefinition(lines: string[], startRow: number, nodeType: string): string | null {
    const line = lines[startRow];
    if (!line) return null;

    if (nodeType.includes('enum')) {
      // Handle enum definitions
      const enumMatch = line.match(/enum(\s+class)?\s+(\w+)(\s*:\s*\w+)?/);
      if (enumMatch) {
        const enumClass = enumMatch[1] || '';
        const enumName = enumMatch[2];
        const enumType = enumMatch[3] || '';
        return `enum${enumClass} ${enumName}${enumType}`;
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

  private findScopeNode(node: SyntaxNode): SyntaxNode | null {
    let current = node.parent;
    while (current) {
      if (current.type === 'qualified_identifier') {
        // Find the scope part of qualified identifier
        for (let i = 0; i < current.childCount; i++) {
          const child = current.child(i);
          if (child && child.type === 'namespace_identifier') {
            return child;
          }
        }
      }
      current = current.parent;
    }
    return null;
  }
}
