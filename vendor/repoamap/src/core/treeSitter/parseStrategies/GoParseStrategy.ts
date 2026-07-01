import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

enum CaptureType {
  Comment = 'comment',
  Type = 'definition.type',
  Interface = 'definition.interface',
  Struct = 'definition.struct',
  Package = 'definition.package',
  Import = 'definition.import',
  Function = 'definition.function',
  Method = 'definition.method',
  Module = 'definition.module',
  Variable = 'definition.variable',
  Constant = 'definition.constant',
  Reference = 'reference',
  Call = 'reference.call',
}

type ParseResult = {
  content: string | null;
  processedSignatures?: Set<string>;
};

export class GoParseStrategy implements ParseStrategy {
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

    const captureTypes = this.getCaptureType(name);

    // 注释处理
    if (captureTypes.has(CaptureType.Comment)) {
      return this.parseComment(lines, startRow, endRow, processedChunks).content;
    }

    // 包声明处理
    if (captureTypes.has(CaptureType.Package) || captureTypes.has(CaptureType.Module)) {
      return this.parsePackage(lines, startRow, processedChunks).content;
    }

    // 导入声明处理
    if (captureTypes.has(CaptureType.Import)) {
      return this.parseImport(lines, startRow, endRow, processedChunks).content;
    }

    // 变量声明处理
    if (captureTypes.has(CaptureType.Variable)) {
      return this.parseVariableDeclaration(lines, startRow, endRow, processedChunks).content;
    }

    // 常量声明处理
    if (captureTypes.has(CaptureType.Constant)) {
      return this.parseConstantDeclaration(lines, startRow, endRow, processedChunks).content;
    }

    // 类型定义处理
    if (
      captureTypes.has(CaptureType.Type) ||
      captureTypes.has(CaptureType.Interface) ||
      captureTypes.has(CaptureType.Struct)
    ) {
      return this.parseTypeDefinition(lines, startRow, endRow, processedChunks).content;
    }

    // 函数声明处理
    if (captureTypes.has(CaptureType.Function)) {
      return this.parseFunctionOrMethod(lines, startRow, endRow, processedChunks, false).content;
    }

    // 方法声明处理
    if (captureTypes.has(CaptureType.Method)) {
      return this.parseFunctionOrMethod(lines, startRow, endRow, processedChunks, true).content;
    }

    // 函数调用引用处理
    if (captureTypes.has(CaptureType.Call)) {
      return this.parseCallExpression(node, lines, processedChunks).content;
    }

    // 类型引用处理
    if (captureTypes.has(CaptureType.Reference)) {
      return this.parseTypeReference(node, lines, processedChunks).content;
    }

    return null;
  }

  private getCaptureType(name: string): Set<CaptureType> {
    const types = new Set<CaptureType>();
    for (const type of Object.values(CaptureType)) {
      if (name.includes(type)) {
        types.add(type);
      }
    }
    return types;
  }

  private getFunctionName(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    // "func funcName(" 模式检测
    const match = line.match(/func\s+([A-Za-z0-9_]+)\s*\(/);
    if (match?.[1]) {
      return match[1];
    }
    return null;
  }

  private getMethodWithReceiver(lines: string[], startRow: number): string | null {
    const line = lines[startRow];
    // "func (r ReceiverType) methodName(" 模式检测
    const match = line.match(/func\s+\(([^)]+)\)\s+([A-Za-z0-9_]+)\s*\(/);
    if (match?.[2]) {
      // 返回带接收者类型的方法名称，更有上下文信息
      const receiver = match[1].trim().split(/\s+/);
      const receiverType = receiver.length > 1 ? receiver[1] : receiver[0];
      return `${receiverType}.${match[2]}`;
    }
    return null;
  }

  private findClosingToken(
    lines: string[],
    startRow: number,
    endRow: number,
    openToken: string,
    closeToken: string,
  ): number {
    let balance = 0;
    for (let i = startRow; i <= endRow; i++) {
      const line = lines[i];
      
      // 计算这一行中开闭标记的数量
      for (let j = 0; j < line.length; j++) {
        if (line.substr(j, openToken.length) === openToken) {
          balance++;
          j += openToken.length - 1;
        } else if (line.substr(j, closeToken.length) === closeToken) {
          balance--;
          j += closeToken.length - 1;
          
          if (balance === 0) {
            return i;
          }
        }
      }
    }
    return startRow;
  }

  private parseSimpleDeclaration(lines: string[], startRow: number, processedChunks: Set<string>): ParseResult {
    const declaration = lines[startRow].trim();
    if (processedChunks.has(declaration)) {
      return { content: null };
    }
    processedChunks.add(declaration);
    return { content: declaration };
  }

  private parsePackage(lines: string[], startRow: number, processedChunks: Set<string>): ParseResult {
    const line = lines[startRow].trim();
    // 提取包名
    const match = line.match(/package\s+([A-Za-z0-9_]+)/);
    if (match?.[1]) {
      const packageName = `package ${match[1]}`;
      if (processedChunks.has(packageName)) {
        return { content: null };
      }
      processedChunks.add(packageName);
      return { content: packageName };
    }
    return this.parseSimpleDeclaration(lines, startRow, processedChunks);
  }

  private parseImport(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    if (lines[startRow].includes('(')) {
      // 多行导入
      const blockEndRow = this.findClosingToken(lines, startRow, endRow, '(', ')');
      
      // 提取每个导入路径
      const imports: string[] = [];
      for (let i = startRow + 1; i < blockEndRow; i++) {
        const line = lines[i].trim();
        if (!line || line === ')') continue;
        
        const importMatch = line.match(/["']([^"']+)["']/);
        if (importMatch?.[1]) {
          const importPath = `import "${importMatch[1]}"`;
          if (!processedChunks.has(importPath)) {
            imports.push(importPath);
            processedChunks.add(importPath);
          }
        }
      }
      
      if (imports.length === 0) {
        return { content: null };
      }
      
      return { content: imports.join('\n') };
    } else {
      // 单行导入
      const line = lines[startRow].trim();
      const importMatch = line.match(/import\s+["']([^"']+)["']/);
      if (importMatch?.[1]) {
        const importPath = `import "${importMatch[1]}"`;
        if (processedChunks.has(importPath)) {
          return { content: null };
        }
        processedChunks.add(importPath);
        return { content: importPath };
      }
      return this.parseSimpleDeclaration(lines, startRow, processedChunks);
    }
  }

  private parseVariableDeclaration(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    if (lines[startRow].includes('(')) {
      // 多行变量声明
      const blockEndRow = this.findClosingToken(lines, startRow, endRow, '(', ')');
      
      // 提取每个变量名及其类型
      const variables: string[] = [];
      for (let i = startRow + 1; i < blockEndRow; i++) {
        const line = lines[i].trim();
        if (!line || line === ')') continue;
        
        const varMatch = line.match(/^([A-Za-z0-9_]+)(\s+[^=]+)?/);
        if (varMatch?.[1]) {
          const varName = varMatch[1];
          const varType = varMatch[2] ? varMatch[2].trim() : '?';
          const variable = `var ${varName} ${varType}`;
          
          if (!processedChunks.has(variable)) {
            variables.push(variable);
            processedChunks.add(variable);
          }
        }
      }
      
      if (variables.length === 0) {
        return { content: null };
      }
      
      return { content: variables.join('\n') };
    } else {
      // 单行变量声明
      const line = lines[startRow].trim();
      const varMatch = line.match(/var\s+([A-Za-z0-9_]+)(\s+[^=]+)?/);
      if (varMatch?.[1]) {
        const varName = varMatch[1];
        const varType = varMatch[2] ? varMatch[2].trim() : '?';
        const variable = `var ${varName} ${varType}`;
        
        if (processedChunks.has(variable)) {
          return { content: null };
        }
        processedChunks.add(variable);
        return { content: variable };
      }
      return this.parseSimpleDeclaration(lines, startRow, processedChunks);
    }
  }

  private parseConstantDeclaration(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    if (lines[startRow].includes('(')) {
      // 多行常量声明
      const blockEndRow = this.findClosingToken(lines, startRow, endRow, '(', ')');
      
      // 提取每个常量名及其类型
      const constants: string[] = [];
      for (let i = startRow + 1; i < blockEndRow; i++) {
        const line = lines[i].trim();
        if (!line || line === ')') continue;
        
        const constMatch = line.match(/^([A-Za-z0-9_]+)(\s+[^=]+)?/);
        if (constMatch?.[1]) {
          const constName = constMatch[1];
          const constType = constMatch[2] ? constMatch[2].trim() : '?';
          const constant = `const ${constName} ${constType}`;
          
          if (!processedChunks.has(constant)) {
            constants.push(constant);
            processedChunks.add(constant);
          }
        }
      }
      
      if (constants.length === 0) {
        return { content: null };
      }
      
      return { content: constants.join('\n') };
    } else {
      // 单行常量声明
      const line = lines[startRow].trim();
      const constMatch = line.match(/const\s+([A-Za-z0-9_]+)(\s+[^=]+)?/);
      if (constMatch?.[1]) {
        const constName = constMatch[1];
        const constType = constMatch[2] ? constMatch[2].trim() : '?';
        const constant = `const ${constName} ${constType}`;
        
        if (processedChunks.has(constant)) {
          return { content: null };
        }
        processedChunks.add(constant);
        return { content: constant };
      }
      return this.parseSimpleDeclaration(lines, startRow, processedChunks);
    }
  }

  private parseComment(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    // 只处理文档注释（多行或单行）
    const line = lines[startRow].trim();
    
    // 检查是否是文档注释（// 或 /*）
    if (line.startsWith('//') || line.startsWith('/*')) {
      // 对于单行注释，检查是否是文档注释风格 (// 开头)
      if (line.startsWith('//')) {
        // 收集连续的注释行
        let commentEnd = startRow;
        while (commentEnd <= endRow && lines[commentEnd].trim().startsWith('//')) {
          commentEnd++;
        }
        commentEnd--;
        
        // 提取注释内容
        const commentLines = lines.slice(startRow, commentEnd + 1).map(l => l.trim().substring(2).trim());
        const comment = commentLines.join('\n');
        
        if (comment.length > 0 && !processedChunks.has(comment)) {
          processedChunks.add(comment);
          return { content: comment };
        }
      }
      // 对于多行注释（/* ... */）
      else if (line.startsWith('/*')) {
        // 找到注释结束行
        let commentEnd = startRow;
        while (commentEnd <= endRow && !lines[commentEnd].includes('*/')) {
          commentEnd++;
        }
        
        // 提取并清理注释内容
        const commentText = lines.slice(startRow, commentEnd + 1).join('\n');
        const cleanComment = commentText.replace(/\/\*|\*\//g, '').trim();
        
        if (cleanComment.length > 0 && !processedChunks.has(cleanComment)) {
          processedChunks.add(cleanComment);
          return { content: cleanComment };
        }
      }
    }
    
    return { content: null };
  }

  private parseFunctionOrMethod(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
    isMethod: boolean,
  ): ParseResult {
    const nameKey = isMethod ? 'method' : 'func';
    const getName = isMethod ? this.getMethodWithReceiver : this.getFunctionName;
    const name = getName.call(this, lines, startRow);

    if (!name) {
      return { content: null };
    }

    if (processedChunks.has(`${nameKey}:${name}`)) {
      return { content: null };
    }

    // 查找函数体的开始位置（第一个 { 的位置）
    let bodyStartRow = startRow;
    while (bodyStartRow <= endRow && !lines[bodyStartRow].includes('{')) {
      bodyStartRow++;
    }

    if (bodyStartRow > endRow) {
      // 如果没有找到函数体，回退到原始行处理
      bodyStartRow = startRow;
    }

    // 提取函数签名（不包括函数体）
    const signature = lines.slice(startRow, bodyStartRow + 1).join(' ').split('{')[0].trim();

    // 从签名中提取函数的参数和返回类型信息
    const paramMatch = signature.match(/\((.*?)\)/);
    const params = paramMatch ? paramMatch[1].trim() : '';
    
    // 查找返回类型
    let returnType = '';
    if (signature.includes(')') && signature.indexOf(')') < signature.length - 1) {
      returnType = signature.substring(signature.indexOf(')') + 1).trim();
    }

    // 构建更详细的函数签名
    const detailedSignature = isMethod 
      ? `${nameKey}: ${name}(${params}) ${returnType}`
      : `${nameKey}: ${name}(${params}) ${returnType}`;

    if (processedChunks.has(detailedSignature)) {
      return { content: null };
    }

    processedChunks.add(`${nameKey}:${name}`);
    processedChunks.add(detailedSignature);
    
    return { content: detailedSignature };
  }

  private parseTypeDefinition(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    
    // 检查是否是类型定义（type Name struct/interface）
    const typeMatch = line.match(/type\s+([A-Za-z0-9_]+)\s+(struct|interface)/);
    if (typeMatch) {
      const typeName = typeMatch[1];
      const typeKind = typeMatch[2];
      
      // 查找类型定义体的结束位置
      const bodyEndRow = this.findClosingToken(lines, startRow, endRow, '{', '}');
      
      // 提取字段/方法（对于结构体/接口）
      let members: string[] = [];
      if (typeKind === 'struct') {
        // 提取结构体字段
        for (let i = startRow + 1; i < bodyEndRow; i++) {
          const fieldLine = lines[i].trim();
          if (!fieldLine || fieldLine === '}') continue;
          
          // 匹配字段定义: FieldName FieldType `tags`
          const fieldMatch = fieldLine.match(/^([A-Za-z0-9_]+)\s+([^`]+)(\s+`.*`)?/);
          if (fieldMatch) {
            const fieldName = fieldMatch[1];
            const fieldType = fieldMatch[2].trim();
            members.push(`  ${fieldName} ${fieldType}`);
          }
        }
      } else if (typeKind === 'interface') {
        // 提取接口方法
        for (let i = startRow + 1; i < bodyEndRow; i++) {
          const methodLine = lines[i].trim();
          if (!methodLine || methodLine === '}') continue;
          
          // 匹配方法定义: MethodName(params) returnType
          const methodMatch = methodLine.match(/^([A-Za-z0-9_]+)\s*\(([^)]*)\)(\s+[^{]+)?/);
          if (methodMatch) {
            const methodName = methodMatch[1];
            const methodParams = methodMatch[2].trim();
            const returnType = methodMatch[3] ? methodMatch[3].trim() : '';
            members.push(`  ${methodName}(${methodParams}) ${returnType}`);
          }
        }
      }
      
      // 构建类型定义
      let typeDefinition = `type ${typeName} ${typeKind}`;
      if (members.length > 0) {
        typeDefinition += ` {\n${members.join('\n')}\n}`;
      } else {
        typeDefinition += ' {}';
      }
      
      if (processedChunks.has(typeDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(typeDefinition);
      return { content: typeDefinition };
    }
    
    // 处理类型别名
    const typeAliasMatch = line.match(/type\s+([A-Za-z0-9_]+)\s+([^{]+)$/);
    if (typeAliasMatch) {
      const typeName = typeAliasMatch[1];
      const typeValue = typeAliasMatch[2].trim();
      
      const typeAlias = `type ${typeName} = ${typeValue}`;
      if (processedChunks.has(typeAlias)) {
        return { content: null };
      }
      
      processedChunks.add(typeAlias);
      return { content: typeAlias };
    }
    
    return this.parseSimpleDeclaration(lines, startRow, processedChunks);
  }

  private parseCallExpression(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): ParseResult {
    // 提取调用的函数/方法名
    let functionName = '';
    
    // 首先检查是否有 name 子节点
    if (node.namedChild(0)?.type === 'identifier' || node.namedChild(0)?.type === 'field_identifier') {
      functionName = node.namedChild(0)?.text || '';
    }
    // 检查选择器表达式
    else if (node.childForFieldName('field')?.type === 'field_identifier') {
      const receiver = node.childForFieldName('operand')?.text || '';
      const method = node.childForFieldName('field')?.text || '';
      functionName = receiver ? `${receiver}.${method}` : method;
    }
    
    if (functionName && !processedChunks.has(`call:${functionName}`)) {
      processedChunks.add(`call:${functionName}`);
      return { content: `call ${functionName}()` };
    }
    
    return { content: null };
  }

  private parseTypeReference(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): ParseResult {
    // 提取类型引用名称
    const typeName = node.text;
    
    if (typeName && !processedChunks.has(`type:${typeName}`)) {
      processedChunks.add(`type:${typeName}`);
      return { content: `type ref: ${typeName}` };
    }
    
    return { content: null };
  }

  private parseBlockDeclaration(
    lines: string[],
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const blockEndRow = lines[startRow].includes('(')
      ? this.findClosingToken(lines, startRow, endRow, '(', ')')
      : endRow;

    const declaration = lines.slice(startRow, blockEndRow + 1).join('\n');
    if (processedChunks.has(declaration)) {
      return { content: null };
    }
    processedChunks.add(declaration);
    return { content: declaration };
  }
}