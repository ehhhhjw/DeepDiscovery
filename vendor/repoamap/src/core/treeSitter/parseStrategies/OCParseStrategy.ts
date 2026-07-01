import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';

enum CaptureType {
  Class = 'class',
  Protocol = 'protocol',
  Method = 'method',
  Property = 'property',
  Field = 'field',
  Category = 'category',
  Type = 'type',
  Macro = 'macro',
  Import = 'import',
  Call = 'call',
  Name = 'name',
  Comment = 'comment',
  Implementation = 'implementation',
}

interface ParseResult {
  content: string | null;
}

export class ObjectiveCParseStrategy implements ParseStrategy {
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
    
    // 基于名称判断是否应该选择该节点
    const isNameCapture = name.includes('name');
    const isCommentCapture = name.includes('comment');
    const isImplementationCapture = captureTypes.has(CaptureType.Implementation);
    const isClassCapture = captureTypes.has(CaptureType.Class);
    const isProtocolCapture = captureTypes.has(CaptureType.Protocol);
    const isMethodCapture = captureTypes.has(CaptureType.Method);
    const isPropertyCapture = captureTypes.has(CaptureType.Property);
    const isCategoryCapture = captureTypes.has(CaptureType.Category);
    const isImportCapture = captureTypes.has(CaptureType.Import);
    const isCallCapture = captureTypes.has(CaptureType.Call);
    const isTypeCapture = captureTypes.has(CaptureType.Type);
    const isMacroCapture = captureTypes.has(CaptureType.Macro);

    // 根据查询语句中的标签决定是否选择该节点
    if (name.includes('definition.class')) {
      return this.parseClassDeclaration(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.implementation')) {
      return this.parseImplementationDeclaration(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.protocol')) {
      return this.parseProtocolDeclaration(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.method')) {
      return this.parseMethodDefinition(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.property')) {
      return this.parsePropertyDeclaration(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.type')) {
      return this.parseTypeDefinition(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.macro')) {
      return this.parseMacroDefinition(lines, node, startRow, endRow, processedChunks).content;
    }
    
    if (name.includes('definition.import')) {
      return this.parseImport(lines, node, startRow, processedChunks).content;
    }
    
    if (name.includes('reference.call')) {
      return this.parseMethodCall(node, lines, processedChunks).content;
    }

    if (isNameCapture) {
      return this.parseNameCapture(node, lines, startRow, processedChunks).content;
    }

    if (isCommentCapture) {
      return this.parseComment(lines, node, startRow, endRow, processedChunks).content;
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

  private parseNameCapture(
    node: SyntaxNode, 
    lines: string[], 
    startRow: number, 
    processedChunks: Set<string>
  ): ParseResult {
    const nodeName = node.text.trim();
    const nodeType = node.parent?.type || node.type;
    
    let chunk: string = nodeName;
    
    if (nodeType.includes('class_interface') || nodeType.includes('implementation_definition')) {
      // 处理类名
      const line = lines[startRow].trim();
      const interfaceMatch = line.match(/@(interface|implementation)\s+([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?/);
      
      if (interfaceMatch && interfaceMatch[2] === nodeName) {
        const declarationType = interfaceMatch[1];
        const superClass = interfaceMatch[3] || 'NSObject';
        
        // 查找协议
        const protocolMatch = line.match(/<([^>]+)>/);
        const protocols = protocolMatch ? ` <${protocolMatch[1]}>` : '';
        
        chunk = declarationType === 'interface' 
          ? `class ${nodeName} : ${superClass}${protocols}`
          : `implementation ${nodeName}`;
      }
    } else if (nodeType.includes('protocol_declaration')) {
      // 处理协议名
      const line = lines[startRow].trim();
      const protocolMatch = line.match(/@protocol\s+([A-Za-z0-9_]+)(?:\s*<([^>]+)>)?/);
      
      if (protocolMatch && protocolMatch[1] === nodeName) {
        const parentProtocols = protocolMatch[2] ? ` <${protocolMatch[2]}>` : '';
        chunk = `protocol ${nodeName}${parentProtocols}`;
      }
    } else if (nodeType.includes('method_definition')) {
      // 处理方法名
      chunk = `method ${nodeName}`;
    } else if (nodeType.includes('message_expression')) {
      // 处理方法调用
      chunk = `call ${nodeName}`;
    }
    
    if (processedChunks.has(chunk)) {
      return { content: null };
    }
    
    processedChunks.add(chunk);
    return { content: chunk };
  }

  private parseComment(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>
  ): ParseResult {
    const selectedLines = lines.slice(startRow, endRow + 1);
    if (selectedLines.length < 1) {
      return { content: null };
    }
    
    const commentText = selectedLines.join('\n').trim();
    
    if (processedChunks.has(commentText)) {
      return { content: null };
    }
    
    processedChunks.add(commentText);
    return { content: commentText };
  }

  private parseClassDeclaration(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // @interface ClassName : SuperClass <Protocol1, Protocol2>
    const interfaceMatch = line.match(/@interface\s+([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?/);
    
    if (interfaceMatch) {
      const className = interfaceMatch[1];
      const superClass = interfaceMatch[2] || 'NSObject';
      
      // 查找协议
      const protocolMatch = line.match(/<([^>]+)>/);
      const protocols = protocolMatch ? protocolMatch[1].split(/\s*,\s*/).join(', ') : '';
      
      let classDefinition = protocols 
        ? `@interface ${className} : ${superClass} <${protocols}>`
        : `@interface ${className} : ${superClass}`;
      
      if (processedChunks.has(classDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(classDefinition);
      return { content: classDefinition };
    }
    
    return { content: null };
  }

  private parseImplementationDeclaration(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // @implementation ClassName
    const implementationMatch = line.match(/@implementation\s+([A-Za-z0-9_]+)/);
    
    if (implementationMatch) {
      const className = implementationMatch[1];
      const implementationDefinition = `@implementation ${className}`;
      
      if (processedChunks.has(implementationDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(implementationDefinition);
      return { content: implementationDefinition };
    }
    
    return { content: null };
  }

  private parseProtocolDeclaration(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // @protocol ProtocolName <Protocol1, Protocol2>
    const protocolMatch = line.match(/@protocol\s+([A-Za-z0-9_]+)(?:\s*<([^>]+)>)?/);
    
    if (protocolMatch) {
      const protocolName = protocolMatch[1];
      const parentProtocols = protocolMatch[2] || '';
      
      const protocolDefinition = parentProtocols 
        ? `@protocol ${protocolName} <${parentProtocols}>`
        : `@protocol ${protocolName}`;
      
      if (processedChunks.has(protocolDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(protocolDefinition);
      return { content: protocolDefinition };
    }
    
    return { content: null };
  }

  private parseMethodDefinition(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // +(void)methodName:(NSString *)param1 withParam:(NSInteger)param2;
    // -(NSString *)methodName;
    const methodMatch = line.match(/([+-])\s*\(([^)]+)\)\s*([^;{]+)/);
    
    if (methodMatch) {
      const methodType = methodMatch[1] === '+' ? 'class' : 'instance';
      const returnType = methodMatch[2].trim();
      const signature = methodMatch[3].trim();
      
      // 提取方法名称（不含参数）
      let methodName = signature;
      const colonIndex = signature.indexOf(':');
      if (colonIndex !== -1) {
        methodName = signature.substring(0, colonIndex);
      }
      
      // 构建更简洁的方法签名展示
      const methodDefinition = `${methodType} method (${returnType}) ${methodName}`;
      
      if (processedChunks.has(methodDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(methodDefinition);
      return { content: methodDefinition };
    }
    
    return { content: null };
  }

  private parsePropertyDeclaration(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // @property (nonatomic, strong) NSString *name;
    const propertyMatch = line.match(/@property\s*(?:\(([^)]+)\))?\s*([^;]+)\s+\*?([A-Za-z0-9_]+);/);
    
    if (propertyMatch) {
      const attributes = propertyMatch[1] ? `(${propertyMatch[1]})` : '';
      const type = propertyMatch[2].trim();
      const name = propertyMatch[3];
      
      const propertyDefinition = attributes 
        ? `@property ${attributes} ${type} ${name}`
        : `@property ${type} ${name}`;
      
      if (processedChunks.has(propertyDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(propertyDefinition);
      return { content: propertyDefinition };
    }
    
    return { content: null };
  }

  private parseTypeDefinition(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // typedef enum { ... } EnumName;
    // typedef struct { ... } StructName;
    // typedef NSString* MyStringType;
    
    // 处理枚举类型
    const enumMatch = line.match(/typedef\s+enum[^{]*{[^}]*}\s*([A-Za-z0-9_]+)/);
    if (enumMatch) {
      const typeName = enumMatch[1];
      const typeDefinition = `typedef enum ${typeName}`;
      
      if (processedChunks.has(typeDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(typeDefinition);
      return { content: typeDefinition };
    }
    
    // 处理结构体类型
    const structMatch = line.match(/typedef\s+struct[^{]*{[^}]*}\s*([A-Za-z0-9_]+)/);
    if (structMatch) {
      const typeName = structMatch[1];
      const typeDefinition = `typedef struct ${typeName}`;
      
      if (processedChunks.has(typeDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(typeDefinition);
      return { content: typeDefinition };
    }
    
    // 处理简单类型别名
    const typedefMatch = line.match(/typedef\s+([^;]+)\s+([A-Za-z0-9_]+);/);
    if (typedefMatch) {
      const baseType = typedefMatch[1].trim();
      const typeName = typedefMatch[2];
      const typeDefinition = `typedef ${baseType} ${typeName}`;
      
      if (processedChunks.has(typeDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(typeDefinition);
      return { content: typeDefinition };
    }
    
    return { content: null };
  }

  private parseMacroDefinition(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // #define MACRO_NAME value
    const defineMatch = line.match(/#define\s+([A-Za-z0-9_]+)(?:\s+(.*))?$/);
    
    if (defineMatch) {
      const macroName = defineMatch[1];
      const macroValue = defineMatch[2] ? ` ${defineMatch[2].trim()}` : '';
      
      const macroDefinition = `#define ${macroName}${macroValue}`;
      
      if (processedChunks.has(macroDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(macroDefinition);
      return { content: macroDefinition };
    }
    
    return { content: null };
  }

  private parseCategoryDeclaration(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    endRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // @interface ClassName (CategoryName)
    // @implementation ClassName (CategoryName)
    const categoryMatch = line.match(/@(interface|implementation)\s+([A-Za-z0-9_]+)\s*\(([A-Za-z0-9_]+)\)/);
    
    if (categoryMatch) {
      const declarationType = categoryMatch[1];
      const className = categoryMatch[2];
      const categoryName = categoryMatch[3];
      
      const categoryDefinition = `@${declarationType} ${className} (${categoryName})`;
      
      if (processedChunks.has(categoryDefinition)) {
        return { content: null };
      }
      
      processedChunks.add(categoryDefinition);
      return { content: categoryDefinition };
    }
    
    return { content: null };
  }

  private parseImport(
    lines: string[],
    node: SyntaxNode,
    startRow: number,
    processedChunks: Set<string>,
  ): ParseResult {
    const line = lines[startRow].trim();
    // #import <Foundation/Foundation.h>
    // #import "MyHeader.h"
    const importMatch = line.match(/#import\s+[<"]([^>"]+)[>"]/);
    
    if (importMatch) {
      const importPath = importMatch[1];
      const isSystemImport = line.includes('<');
      const importStatement = isSystemImport 
        ? `#import <${importPath}>`
        : `#import "${importPath}"`;
      
      if (processedChunks.has(importStatement)) {
        return { content: null };
      }
      
      processedChunks.add(importStatement);
      return { content: importStatement };
    }
    
    return { content: null };
  }

  private parseMethodCall(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): ParseResult {
    // 提取方法调用的完整信息，包括接收者和方法名
    const text = node.text.trim();
    
    // 尝试匹配完整的方法调用格式: [receiver method:arg]
    const methodCallMatch = text.match(/\[([^\s\]]+)\s+([^\]]+)\]/);
    
    if (methodCallMatch) {
      const receiver = methodCallMatch[1];
      const methodName = methodCallMatch[2];
      
      // 提取方法名的基本部分（不含参数值）
      let formattedMethodName = methodName;
      if (methodName.includes(':')) {
        // 对于带参数的方法，提取方法名的各个部分
        formattedMethodName = methodName.replace(/\s*[^\s:]+\s*(?=:|$)/g, '');
      }
      
      const callSignature = `${receiver} ${formattedMethodName.trim()}`;
      
      if (processedChunks.has(`call:${callSignature}`)) {
        return { content: null };
      }
      
      processedChunks.add(`call:${callSignature}`);
      return { content: `call ${callSignature}` };
    } else if (text) {
      // 简单的情况，直接使用完整文本
      if (processedChunks.has(`call:${text}`)) {
        return { content: null };
      }
      
      processedChunks.add(`call:${text}`);
      return { content: `call ${text}` };
    }
    
    return { content: null };
  }
}