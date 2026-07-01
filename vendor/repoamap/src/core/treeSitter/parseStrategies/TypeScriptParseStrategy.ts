import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

enum CaptureType {
  Comment = 'comment',
  Interface = 'definition.interface',
  Type = 'definition.type',
  Enum = 'definition.enum',
  Class = 'definition.class',
  Import = 'definition.import',
  Function = 'definition.function',
  Method = 'definition.method',
  Property = 'definition.property',
  Module = 'definition.module',
  Reference = 'reference',
}

export class TypeScriptParseStrategy implements ParseStrategy {
  private static readonly FUNCTION_NAME_PATTERN = /(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=/;

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
    const isDefinitionCapture = name.includes('definition');
    const isReferenceCapture = name.includes('reference');

    const shouldSelect =
      isNameCapture || isCommentCapture || isImportCapture || isDefinitionCapture || isReferenceCapture;

    if (!shouldSelect) {
      return null;
    }

    let chunk: string;

    // 处理命名捕获
    if (isNameCapture) {
      chunk = this.handleNameCapture(node, name, lines, startRow);
    }
    // 处理导入语句
    else if (isImportCapture) {
      chunk = this.handleImportCapture(node);
    }
    // 处理定义捕获
    else if (isDefinitionCapture) {
      chunk = this.handleDefinitionCapture(node, name, lines, startRow);
    }
    // 处理引用捕获
    else if (isReferenceCapture) {
      chunk = this.handleReferenceCapture(node, name);
    }
    // 处理注释
    else if (isCommentCapture) {
      chunk = node.text.trim();
    }
    // 默认处理
    else {
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

  private handleNameCapture(node: SyntaxNode, name: string, lines: string[], startRow: number): string {
    const nodeText = node.text;
    const nodeType = node.parent?.type || node.type;

    // 函数名称
    if (name.includes('function')) {
      return `function ${nodeText}`;
    }
    // 方法名称
    else if (name.includes('method')) {
      return `method ${nodeText}`;
    }
    // 类名称
    else if (name.includes('class')) {
      return this.handleClassNameCapture(node, nodeText, lines, startRow);
    }
    // 接口名称
    else if (name.includes('interface')) {
      return `interface ${nodeText}`;
    }
    // 类型别名名称
    else if (name.includes('type')) {
      return `type ${nodeText}`;
    }
    // 枚举名称
    else if (name.includes('enum')) {
      return `enum ${nodeText}`;
    }
    // 模块名称
    else if (name.includes('module')) {
      return `module ${nodeText}`;
    }
    // 属性名称
    else if (nodeType.includes('property') || nodeType.includes('field')) {
      return this.handlePropertyNameCapture(node, nodeText);
    }
    // 默认处理
    else {
      return nodeText;
    }
  }

  private handleClassNameCapture(node: SyntaxNode, nodeText: string, lines: string[], startRow: number): string {
    // 查找包含当前节点的类声明
    let classNode: SyntaxNode | null = node;
    while (classNode && classNode.type !== 'class_declaration' && classNode.type !== 'abstract_class_declaration') {
      classNode = classNode.parent;
    }

    if (classNode) {
      // 尝试通过字段获取父类
      const superclassNode = classNode.childForFieldName('heritage');
      if (superclassNode) {
        const superclassName = superclassNode.text;
        return `class ${nodeText} extends ${superclassName}`;
      } else {
        // 通过文本解析查找 extends 或 implements
        const classText = classNode.text;
        const extendsMatch = classText.match(/class\s+\w+\s+extends\s+([^\s{]+)/);
        const implementsMatch = classText.match(/class\s+\w+\s+implements\s+([^\s{]+)/);

        if (extendsMatch) {
          const superclassName = extendsMatch[1];
          return `class ${nodeText} extends ${superclassName}`;
        } else if (implementsMatch) {
          const interfaceName = implementsMatch[1];
          return `class ${nodeText} implements ${interfaceName}`;
        } else {
          return `class ${nodeText}`;
        }
      }
    } else {
      // 如果找不到类声明节点，直接在原始文本中查找
      const lineText = lines[startRow] || '';
      const contextLines = lines.slice(Math.max(0, startRow - 2), startRow + 3).join(' ');
      const extendsMatch = contextLines.match(/class\s+\w+\s+extends\s+([^\s{]+)/);
      const implementsMatch = contextLines.match(/class\s+\w+\s+implements\s+([^\s{]+)/);

      if (extendsMatch) {
        const superclassName = extendsMatch[1];
        return `class ${nodeText} extends ${superclassName}`;
      } else if (implementsMatch) {
        const interfaceName = implementsMatch[1];
        return `class ${nodeText} implements ${interfaceName}`;
      } else {
        return `class ${nodeText}`;
      }
    }
  }

  private handlePropertyNameCapture(node: SyntaxNode, nodeText: string): string {
    const propertyDeclaration = node.parent;
    if (propertyDeclaration) {
      const propertyText = propertyDeclaration.text;

      if (propertyText.includes('const ')) {
        return `const ${nodeText}`;
      } else if (propertyText.includes('let ')) {
        return `let ${nodeText}`;
      } else if (propertyText.includes('var ')) {
        return `var ${nodeText}`;
      } else if (propertyText.includes('static ')) {
        return `static ${nodeText}`;
      } else if (propertyText.includes('readonly ')) {
        return `readonly ${nodeText}`;
      } else if (propertyText.includes('private ')) {
        return `private ${nodeText}`;
      } else if (propertyText.includes('protected ')) {
        return `protected ${nodeText}`;
      } else if (propertyText.includes('public ')) {
        return `public ${nodeText}`;
      } else {
        return `property ${nodeText}`;
      }
    }
    return `property ${nodeText}`;
  }

  private handleImportCapture(node: SyntaxNode): string {
    const importText = node.text;

    // 处理 ES6 import 语句
    const es6ImportMatch = importText.match(/import\s+.*?\s+from\s+['"]([^'"]+)['"]/);
    if (es6ImportMatch) {
      return `import ${es6ImportMatch[1]}`;
    } else {
      // 处理简单的 import 语句（如 import 'module'）
      const simpleImportMatch = importText.match(/import\s+['"]([^'"]+)['"]/);
      if (simpleImportMatch) {
        return `import ${simpleImportMatch[1]}`;
      } else {
        // 处理 require 语句
        const requireMatch = importText.match(/require\s*\(\s*['"]([^'"]+)['"]\s*\)/);
        if (requireMatch) {
          return `require ${requireMatch[1]}`;
        } else {
          // 如果都不匹配，尝试提取任何引号中的路径
          const pathMatch = importText.match(/['"]([^'"]+)['"]/);
          if (pathMatch) {
            return `import ${pathMatch[1]}`;
          } else {
            return node.text;
          }
        }
      }
    }
  }

  private handleDefinitionCapture(node: SyntaxNode, name: string, lines: string[], startRow: number): string {
    const nodeText = node.text;

    // 函数定义
    if (name.includes('function')) {
      return this.cleanFunctionSignature(nodeText);
    }
    // 方法定义
    else if (name.includes('method')) {
      return this.cleanMethodSignature(nodeText);
    }
    // 类定义
    else if (name.includes('class')) {
      return this.cleanClassSignature(nodeText);
    }
    // 接口定义
    else if (name.includes('interface')) {
      return this.cleanInterfaceSignature(nodeText);
    }
    // 类型定义
    else if (name.includes('type')) {
      return this.cleanTypeSignature(nodeText);
    }
    // 枚举定义
    else if (name.includes('enum')) {
      return this.cleanEnumSignature(nodeText);
    }
    // 模块定义
    else if (name.includes('module')) {
      return this.cleanModuleSignature(nodeText);
    }
    // 默认处理
    else {
      return nodeText.trim();
    }
  }

  private handleReferenceCapture(node: SyntaxNode, name: string): string {
    const nodeText = node.text;

    // 检查是否为构造函数调用（new 表达式）
    if (nodeText.trim().startsWith('new ')) {
      const constructorMatch = nodeText.match(/new\s+([A-Za-z0-9_$]+)/);
      if (constructorMatch) {
        return `ref constructor ${constructorMatch[1]}`;
      }
    }

    // 检查是否为箭头函数
    if (nodeText.includes('=>')) {
      return this.cleanArrowFunctionSignature(nodeText);
    }

    if (name.includes('type')) {
      return `ref type ${nodeText}`;
    } else if (name.includes('class')) {
      return `ref class ${nodeText}`;
    } else if (name.includes('module')) {
      return `ref module ${nodeText}`;
    } else if (name.includes('function')) {
      return `ref function ${nodeText}`;
    } else {
      return `ref ${nodeText}`;
    }
  }

  private cleanFunctionSignature(nodeText: string): string {
    // 检查是否为箭头函数 - 改进检查逻辑
    if (nodeText.includes('=>')) {
      // 检查是否是赋值形式的箭头函数
      const assignmentMatch = nodeText.match(/^((?:export\s+)?(?:const|let|var)\s+[a-zA-Z0-9_$]+\s*=\s*)/);
      if (assignmentMatch) {
        return this.cleanArrowFunctionSignature(nodeText);
      }
    }

    const lines = nodeText.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.includes(')') && (line.endsWith('{') || line.endsWith('=>'))) {
        if (line.includes('{')) {
          lines[i] = line.substring(0, line.indexOf('{')).trim();
        } else if (line.includes('=>')) {
          lines[i] = line.substring(0, line.indexOf('=>')).trim();
        }
        return lines
          .slice(0, i + 1)
          .join('\n')
          .trim();
      }
    }
    return nodeText.trim();
  }

  private cleanArrowFunctionSignature(nodeText: string): string {
    // 处理箭头函数，只保留参数部分
    const arrowIndex = nodeText.indexOf('=>');
    if (arrowIndex === -1) {
      return nodeText.trim();
    }

    const signaturePart = nodeText.substring(0, arrowIndex).trim();

    // 检查是否有函数名（变量赋值的箭头函数）
    const functionNameMatch = signaturePart.match(TypeScriptParseStrategy.FUNCTION_NAME_PATTERN);
    if (functionNameMatch) {
      const functionName = functionNameMatch[1];
      // 提取参数部分
      const paramStart = signaturePart.indexOf('(');
      const paramEnd = signaturePart.lastIndexOf(')');
      if (paramStart !== -1 && paramEnd !== -1) {
        const params = signaturePart.substring(paramStart, paramEnd + 1);
        // 检查是否有返回类型注解 - 改进正则表达式
        const returnTypeMatch = signaturePart.match(/\)\s*:\s*([^=]+?)(?=\s*$)/);
        if (returnTypeMatch) {
          const returnType = returnTypeMatch[1].trim();
          return `const ${functionName} = ${params}: ${returnType} =>`;
        }
        return `const ${functionName} = ${params} =>`;
      }
      return `const ${functionName} = () =>`;
    }

    // 处理匿名箭头函数 - 只保留参数和返回类型
    const paramMatch = signaturePart.match(/\(([^)]*)\)(.*)$/);
    if (paramMatch) {
      const params = paramMatch[1];
      const afterParams = paramMatch[2].trim();

      // 检查返回类型注解
      if (afterParams.startsWith(':')) {
        return `(${params})${afterParams} =>`;
      }
      return `(${params}) =>`;
    }

    // 处理单参数无括号的箭头函数
    const singleParamMatch = signaturePart.match(/^(\w+)(.*)$/);
    if (singleParamMatch) {
      const param = singleParamMatch[1];
      const afterParam = singleParamMatch[2].trim();

      // 检查返回类型注解
      if (afterParam.startsWith(':')) {
        return `${param}${afterParam} =>`;
      }
      return `${param} =>`;
    }

    return signaturePart + ' =>';
  }

  private cleanMethodSignature(nodeText: string): string {
    const bodyIndex = nodeText.indexOf('{');
    if (bodyIndex !== -1) {
      return nodeText.substring(0, bodyIndex).trim();
    }
    return nodeText.trim();
  }

  private cleanClassSignature(nodeText: string): string {
    const bodyIndex = nodeText.indexOf('{');
    if (bodyIndex !== -1) {
      return nodeText.substring(0, bodyIndex).trim();
    }
    return nodeText.trim();
  }

  private cleanInterfaceSignature(nodeText: string): string {
    const bodyIndex = nodeText.indexOf('{');
    if (bodyIndex !== -1) {
      return nodeText.substring(0, bodyIndex).trim();
    }
    return nodeText.trim();
  }

  private cleanTypeSignature(nodeText: string): string {
    // 对于类型别名，通常保留完整定义
    return nodeText.trim();
  }

  private cleanEnumSignature(nodeText: string): string {
    const bodyIndex = nodeText.indexOf('{');
    if (bodyIndex !== -1) {
      return nodeText.substring(0, bodyIndex).trim();
    }
    return nodeText.trim();
  }

  private cleanModuleSignature(nodeText: string): string {
    const bodyIndex = nodeText.indexOf('{');
    if (bodyIndex !== -1) {
      return nodeText.substring(0, bodyIndex).trim();
    }
    return nodeText.trim();
  }
}
