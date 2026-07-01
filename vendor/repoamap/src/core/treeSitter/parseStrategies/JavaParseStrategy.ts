import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

export class JavaParseStrategy implements ParseStrategy {
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
    const isPackageCapture = name.includes('package');
    const isImportCapture = name.includes('import');
    const shouldSelect = isNameCapture || isPackageCapture || isImportCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;

    // 捕获命名
    if (isNameCapture) {
      chunk = node.text;

      const nodeType = node.parent?.type || node.type;

      if (nodeType.includes('method_declaration')) {
        chunk = `method ${chunk}`;
      } else if (nodeType.includes('constructor_declaration')) {
        chunk = `constructor ${chunk}`;
      } else if (nodeType.includes('class_declaration')) {
        // 查找包含当前节点的类声明
        let classNode: SyntaxNode | null = node;
        while (classNode && classNode.type !== 'class_declaration') {
          classNode = classNode.parent;
        }

        if (classNode && classNode.type === 'class_declaration') {
          // 检查是否有父类
          const superclassNode = classNode.childForFieldName('superclass');
          if (superclassNode) {
            const superclassName = superclassNode.text;
            chunk = `class ${chunk} extends ${superclassName}`;
          } else {
            // 通过文本解析查找 extends
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
          chunk = `class ${chunk}`;
        }
      } else if (nodeType.includes('interface_declaration')) {
        // 查找包含当前节点的接口声明
        let interfaceNode: SyntaxNode | null = node;
        while (interfaceNode && interfaceNode.type !== 'interface_declaration') {
          interfaceNode = interfaceNode.parent;
        }

        if (interfaceNode && interfaceNode.type === 'interface_declaration') {
          // 检查是否实现了其他接口
          const extendsNode = interfaceNode.childForFieldName('extends');
          if (extendsNode) {
            chunk = `interface ${chunk} extends ${extendsNode.text}`;
          } else {
            chunk = `interface ${chunk}`;
          }
        } else {
          chunk = `interface ${chunk}`;
        }
      } else if (nodeType.includes('field_declaration')) {
        // 处理字段声明
        const fieldDeclaration = node.parent?.parent; // variable_declarator -> field_declaration
        if (fieldDeclaration) {
          const fieldText = fieldDeclaration.text;

          // 检查修饰符
          if (fieldText.includes('static ')) {
            chunk = `static field ${chunk}`;
          } else if (fieldText.includes('final ')) {
            chunk = `final field ${chunk}`;
          } else if (fieldText.includes('private ')) {
            chunk = `private field ${chunk}`;
          } else if (fieldText.includes('public ')) {
            chunk = `public field ${chunk}`;
          } else if (fieldText.includes('protected ')) {
            chunk = `protected field ${chunk}`;
          } else {
            chunk = `field ${chunk}`;
          }
        } else {
          chunk = `field ${chunk}`;
        }
      } else if (nodeType.includes('enum_declaration')) {
        chunk = `enum ${chunk}`;
      } else if (nodeType.includes('annotation_type_declaration')) {
        chunk = `@interface ${chunk}`;
      } else if (nodeType.includes('object_creation_expression')) {
        chunk = `new ${chunk}`;
      } else if (nodeType.includes('method_invocation')) {
        chunk = `call ${chunk}`;
      }
    } else if (isPackageCapture) {
      // 捕获包声明
      const packageText = node.text;
      const packageMatch = packageText.match(/package\s+([\w.]+)/);
      if (packageMatch) {
        chunk = `package ${packageMatch[1]}`;
      } else {
        chunk = `package ${node.text}`;
      }
    } else if (isImportCapture) {
      // 捕获导入语句
      const importText = node.text;

      // 处理 import 语句
      const importMatch = importText.match(/import\s+(?:static\s+)?([\w.*]+)/);
      if (importMatch) {
        const importPath = importMatch[1];
        // 检查是否是静态导入
        if (importText.includes('static ')) {
          chunk = `import static ${importPath}`;
        } else {
          chunk = `import ${importPath}`;
        }
      } else {
        // 如果正则匹配失败，尝试提取整个导入语句
        chunk = node.text.replace(/\s+/g, ' ').trim();
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
