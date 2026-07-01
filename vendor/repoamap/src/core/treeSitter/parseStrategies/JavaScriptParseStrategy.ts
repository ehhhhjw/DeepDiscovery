import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

export class JavaScriptParseStrategy implements ParseStrategy {
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
    const isImportCapture = name.includes('import') || name.includes('require');
    const isExportCapture = name.includes('export');
    const shouldSelect = isNameCapture || isCommentCapture || isImportCapture || isExportCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;
    // 捕获命名
    if (isNameCapture) {
      chunk = node.text;

      const nodeType = node.parent?.type || node.type;
      if (nodeType.includes('function') || nodeType.includes('method')) {
        chunk = `function ${chunk}`;
      } else if (nodeType.includes('class')) {
        // 查找包含当前节点的类声明
        let classNode: SyntaxNode | null = node;
        while (classNode && classNode.type !== 'class_declaration') {
          classNode = classNode.parent;
        }

        if (classNode && classNode.type === 'class_declaration') {
          // 方法1: 尝试通过字段获取父类
          const superclassNode = classNode.childForFieldName('superclass');
          if (superclassNode) {
            const superclassName = superclassNode.text;
            chunk = `class ${chunk} extends ${superclassName}`;
          } else {
            // 方法2: 如果字段方式失败，通过文本解析查找 extends
            const classText = classNode.text;
            const extendsMatch = classText.match(/class\s+\w+\s+extends\s+([^\s{]+)/);
            if (extendsMatch) {
              const superclassName = extendsMatch[1];
              chunk = `class ${chunk} extends ${superclassName}`;
            } else {
              chunk = `class ${chunk}`;
            }
          }
        } else {
          // 方法3: 如果找不到类声明节点，直接在原始文本中查找
          const lineText = lines[startRow] || '';
          const contextLines = lines.slice(Math.max(0, startRow - 2), startRow + 3).join(' ');
          const extendsMatch = contextLines.match(/class\s+\w+\s+extends\s+([^\s{]+)/);
          if (extendsMatch) {
            const superclassName = extendsMatch[1];
            chunk = `class ${chunk} extends ${superclassName}`;
          } else {
            chunk = `class ${chunk}`;
          }
        }
      } else if (nodeType.includes('property') || nodeType.includes('field')) {
        // 处理类属性/字段
        const propertyDeclaration = node.parent;
        if (propertyDeclaration) {
          const propertyText = propertyDeclaration.text;

          // 检查属性声明类型
          if (propertyText.includes('const ')) {
            chunk = `const ${chunk}`;
          } else if (propertyText.includes('let ')) {
            chunk = `let ${chunk}`;
          } else if (propertyText.includes('var ')) {
            chunk = `var ${chunk}`;
          } else if (propertyText.includes('static ')) {
            chunk = `static ${chunk}`;
          } else {
            // 默认情况，可能是类字段
            chunk = `property ${chunk}`;
          }
        }
      }
    } else if (isImportCapture) {
      // 捕获导入语句
      const importText = node.text;

      // 处理 ES6 import 语句
      const es6ImportMatch = importText.match(/import\s+.*?\s+from\s+['"]([^'"]+)['"]/);
      if (es6ImportMatch) {
        chunk = `import ${es6ImportMatch[1]}`;
      } else {
        // 处理简单的 import 语句（如 import 'module'）
        const simpleImportMatch = importText.match(/import\s+['"]([^'"]+)['"]/);
        if (simpleImportMatch) {
          chunk = `import ${simpleImportMatch[1]}`;
        } else {
          // 处理 require 语句
          const requireMatch = importText.match(/require\s*\(\s*['"]([^'"]+)['"]\s*\)/);
          if (requireMatch) {
            chunk = `require ${requireMatch[1]}`;
          } else {
            // 如果都不匹配，尝试提取任何引号中的路径
            const pathMatch = importText.match(/['"]([^'"]+)['"]/);
            if (pathMatch) {
              chunk = `import ${pathMatch[1]}`;
            } else {
              chunk = node.text;
            }
          }
        }
      }
    } else if (isExportCapture) {
      // 捕获导出语句
      // 根据捕获的节点类型和名称进行精确处理
      if (name === 'export') {
        // 只是 export 关键字
        chunk = 'export';
      } else if (name.includes('export.name')) {
        // 导出的具体名称
        chunk = `export ${node.text}`;
      } else {
        // 分析 export 语句的结构
        const exportText = node.text;

        // 检查是否是默认导出
        if (node.type === 'export_statement' && exportText.includes('default')) {
          // 尝试提取默认导出的名称
          const defaultExportMatch = exportText.match(/export\s+default\s+(?:function\s+(\w+)|class\s+(\w+)|(\w+))/);
          if (defaultExportMatch) {
            const exportName = defaultExportMatch[1] || defaultExportMatch[2] || defaultExportMatch[3];
            chunk = `export default ${exportName}`;
          } else {
            chunk = 'export default';
          }
        }
        // 检查是否是命名导出
        else if (exportText.includes('export {')) {
          const namedExportMatch = exportText.match(/export\s+\{([^}]+)\}/);
          if (namedExportMatch) {
            const exports = namedExportMatch[1].trim();
            chunk = `export {${exports}}`;
          } else {
            chunk = 'export';
          }
        }
        // 检查是否是重导出
        else if (exportText.includes('export *')) {
          const reExportMatch = exportText.match(/export\s+\*\s+from\s+['"]([^'"]+)['"]/);
          if (reExportMatch) {
            chunk = `export * from "${reExportMatch[1]}"`;
          } else {
            chunk = 'export *';
          }
        }
        // 检查是否是直接导出声明
        else if (exportText.startsWith('export ')) {
          // 提取导出的声明类型和名称
          const declarationMatch = exportText.match(/export\s+(function|class|const|let|var)\s+(\w+)/);
          if (declarationMatch) {
            const [, type, name] = declarationMatch;
            chunk = `export ${type} ${name}`;
          } else {
            // 如果无法精确匹配，保留原始的简化版本
            chunk = 'export';
          }
        } else {
          chunk = 'export';
        }
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
}
