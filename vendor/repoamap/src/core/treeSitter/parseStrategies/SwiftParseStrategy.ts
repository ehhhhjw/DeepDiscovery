import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

export class SwiftParseStrategy implements ParseStrategy {
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
    const isImportCapture = name.includes('import');
    const shouldSelect = isNameCapture || isCommentCapture || isImportCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;

    // 捕获命名
    if (isNameCapture) {
      chunk = node.text;

      const definitionType = this.getDefinitionType(name);

      if (definitionType === 'class') {
        // 处理类定义
        const classDefinition = this.getClassDefinition(lines, startRow);
        if (classDefinition) {
          chunk = classDefinition;
        } else {
          chunk = `class ${chunk}`;
        }
      } else if (definitionType === 'interface') {
        // 处理协议定义
        const protocolDefinition = this.getProtocolDefinition(lines, startRow);
        if (protocolDefinition) {
          chunk = protocolDefinition;
        } else {
          chunk = `protocol ${chunk}`;
        }
      } else if (definitionType === 'function') {
        // 处理函数定义
        const functionSignature = this.getFunctionSignature(lines, startRow);
        if (functionSignature) {
          chunk = functionSignature;
        } else {
          chunk = `func ${chunk}`;
        }
      } else if (definitionType === 'method') {
        // 处理方法定义
        const methodSignature = this.getMethodSignature(lines, startRow, node);
        if (methodSignature) {
          chunk = methodSignature;
        } else {
          chunk = `method ${chunk}`;
        }
      } else if (definitionType === 'property') {
        // 处理属性定义
        const propertyDefinition = this.getPropertyDefinition(lines, startRow);
        if (propertyDefinition) {
          chunk = propertyDefinition;
        } else {
          chunk = `var ${chunk}`;
        }
      }
    } else if (isImportCapture) {
      // 捕获导入语句
      const importText = node.text;
      chunk = importText.trim();
    } else if (isCommentCapture) {
      // 处理注释
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
    if (captureName.includes('interface')) return 'interface';
    if (captureName.includes('function')) return 'function';
    if (captureName.includes('method')) return 'method';
    if (captureName.includes('property')) return 'property';
    return 'unknown';
  }

  private getClassDefinition(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 匹配类定义：class ClassName: SuperClass, Protocol { 或 class ClassName {
    const classMatch = line.match(/class\s+(\w+)(\s*:\s*[^{]+)?/);
    if (classMatch) {
      const className = classMatch[1];
      const inheritance = classMatch[2];
      if (inheritance) {
        return `class ${className}${inheritance.replace(/\s*{\s*$/, '').trim()}`;
      }
      return `class ${className}`;
    }

    return line.replace(/\s*{\s*$/, '').trim();
  }

  private getProtocolDefinition(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 匹配协议定义：protocol ProtocolName: ParentProtocol { 或 protocol ProtocolName {
    const protocolMatch = line.match(/protocol\s+(\w+)(\s*:\s*[^{]+)?/);
    if (protocolMatch) {
      const protocolName = protocolMatch[1];
      const inheritance = protocolMatch[2];
      if (inheritance) {
        return `protocol ${protocolName}${inheritance.replace(/\s*{\s*$/, '').trim()}`;
      }
      return `protocol ${protocolName}`;
    }

    return line.replace(/\s*{\s*$/, '').trim();
  }

  private getFunctionSignature(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 匹配函数定义：func functionName(parameters) -> ReturnType
    const funcMatch = line.match(/func\s+(\w+)\s*\(([^)]*)\)(\s*->\s*[^{]+)?/);
    if (funcMatch) {
      const funcName = funcMatch[1];
      const params = funcMatch[2].trim();
      const returnType = funcMatch[3] || '';

      // 如果有参数，用 (...) 替换，否则保持空括号
      const paramsPart = params ? '(...)' : '()';

      return `func ${funcName}${paramsPart}${returnType}`.replace(/\s*{\s*$/, '').trim();
    }

    return null;
  }

  private getMethodSignature(lines: string[], startRow: number, node: SyntaxNode): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 检查是否是 init 或 deinit
    if (line.includes('init')) {
      const initMatch = line.match(/init\s*\(([^)]*)\)/);
      if (initMatch) {
        const params = initMatch[1].trim();
        const paramsPart = params ? '(...)' : '()';
        return `init${paramsPart}`;
      }
      return 'init';
    }

    if (line.includes('deinit')) {
      return 'deinit';
    }

    // 处理下标方法
    if (line.includes('subscript')) {
      const subscriptMatch = line.match(/subscript\s*\(([^)]*)\)\s*->\s*([^{]+)/);
      if (subscriptMatch) {
        const params = subscriptMatch[1].trim();
        const returnType = subscriptMatch[2].trim();
        const paramsPart = params ? '(...)' : '()';
        return `subscript${paramsPart} -> ${returnType}`;
      }
      return 'subscript';
    }

    // 普通方法定义
    return this.getFunctionSignature(lines, startRow);
  }

  private getPropertyDefinition(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 匹配属性定义：var/let propertyName: Type
    const propertyMatch = line.match(/(var|let)\s+(\w+)\s*:\s*([^={]+)/);
    if (propertyMatch) {
      const keyword = propertyMatch[1];
      const propertyName = propertyMatch[2];
      const type = propertyMatch[3].trim();
      return `${keyword} ${propertyName}: ${type}`;
    }

    // 简单的 var/let 声明
    const simpleMatch = line.match(/(var|let)\s+(\w+)/);
    if (simpleMatch) {
      const keyword = simpleMatch[1];
      const propertyName = simpleMatch[2];
      return `${keyword} ${propertyName}`;
    }

    return line.replace(/\s*[={]\s*.*$/, '').trim();
  }
}