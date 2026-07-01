import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

export class PythonParseStrategy implements ParseStrategy {
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
    const isDocstringCapture = name.includes('docstring');
    const isImportCapture = name.includes('import');
    const shouldSelect = isNameCapture || isCommentCapture || isDocstringCapture || isImportCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;

    // 捕获命名
    if (isNameCapture) {
      chunk = node.text;

      const nodeType = node.parent?.type || node.type;

      if (nodeType.includes('function_definition')) {
        // 处理函数定义，包括装饰器
        const decorators = this.getDecorators(lines, startRow);
        const signature = this.getFunctionSignature(lines, startRow);
        if (signature) {
          chunk = decorators.length > 0 ? `${decorators.join('\n')}\n${signature}` : signature;
        } else {
          chunk = `def ${chunk}`;
        }
      } else if (nodeType.includes('class_definition')) {
        // 处理类定义，包括继承和装饰器
        const decorators = this.getDecorators(lines, startRow);
        const classDefinition = this.getClassInheritance(lines, startRow);
        if (classDefinition) {
          chunk = decorators.length > 0 ? `${decorators.join('\n')}\n${classDefinition}` : classDefinition;
        } else {
          chunk = `class ${chunk}`;
        }
      } else if (nodeType.includes('call')) {
        // 处理函数调用
        chunk = `call ${chunk}`;
      } else if (nodeType.includes('assignment')) {
        // 处理变量赋值
        const assignmentLine = lines[startRow]?.trim();
        if (assignmentLine) {
          // 检查是否是类型别名或常量
          if (assignmentLine.includes('TypeAlias') || assignmentLine.includes('Type[')) {
            chunk = `type ${chunk}`;
          } else if (chunk === chunk.toUpperCase() && chunk.includes('_')) {
            chunk = `const ${chunk}`;
          } else {
            chunk = `var ${chunk}`;
          }
        }
      }
    } else if (isImportCapture) {
      // 捕获导入语句
      const importText = node.text;
      chunk = importText.trim();
    } else if (isCommentCapture || isDocstringCapture) {
      // 处理注释和文档字符串
      const selectedLines = lines.slice(startRow, endRow + 1);
      if (selectedLines.length < 1) {
        return null;
      }
      chunk = selectedLines.join('\n').trim();

      // 如果是文档字符串，添加标识
      if (isDocstringCapture) {
        chunk = `"""${chunk}"""`;
      }
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

  private getDecorators(lines: string[], startRow: number): string[] {
    const decorators: string[] = [];
    let currentRow = startRow - 1;

    while (currentRow >= 0) {
      const line = lines[currentRow]?.trim();
      if (line && line.startsWith('@')) {
        decorators.unshift(line); // Add to beginning to maintain order
      } else if (line && line.trim() !== '') {
        break; // Stop if we hit a non-empty, non-decorator line
      }
      currentRow--;
    }

    return decorators;
  }

  private getClassInheritance(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    const classMatch = line.match(/class\s+(\w+)(\s*\([^)]*\))?:/);
    if (classMatch) {
      const className = classMatch[1];
      const inheritance = classMatch[2];
      if (inheritance) {
        return `class ${className}${inheritance.replace(/:\s*$/, '')}`;
      } else {
        return `class ${className}`;
      }
    }
    return line.replace(/:\s*$/, '');
  }

  private getFunctionSignature(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    if (!line) return null;

    // 匹配函数定义模式：def function_name(parameters) -> return_type:
    const funcMatch = line.match(/def\s+(\w+)\s*\(([^)]*)\)(\s*->\s*[^:]+)?:/);
    if (funcMatch) {
      const funcName = funcMatch[1];
      const params = funcMatch[2].trim();
      const returnType = funcMatch[3] || '';

      // 如果有参数，用 (...) 替换，否则保持空括号
      const paramsPart = params ? '(...)' : '()';

      return `def ${funcName}${paramsPart}${returnType}`;
    }
    return null;
  }
}
