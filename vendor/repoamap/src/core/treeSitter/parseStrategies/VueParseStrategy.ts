import type { SyntaxNode } from 'web-tree-sitter';
import type { ParseContext, ParseStrategy } from './ParseStrategy.js';
import { JavaScriptParseStrategy } from './JavaScriptParseStrategy.js';

export class VueParseStrategy implements ParseStrategy {
  private jsStrategy = new JavaScriptParseStrategy();

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

    // 处理不同的 Vue 部分
    if (name === 'template') {
      return this.parseTemplateElement(node, lines, processedChunks);
    } else if (name === 'script') {
      return this.parseScriptElement(node, lines, processedChunks, context);
    } else if (name === 'style') {
      return this.parseStyleElement(node, lines, processedChunks);
    } else if (name === 'interpolation') {
      return this.parseInterpolation(node, lines, processedChunks);
    }

    return node.text.trim();
  }

  private parseTemplateElement(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): string | null {
    // 提取模板中的组件名称和自定义元素
    const componentPattern = /<([A-Z][a-zA-Z0-9]*|[a-z]+-[a-z-]+)(\s|\/>|>)/g;
    
    const startRow = node.startPosition.row;
    const endRow = node.endPosition.row;
    const selectedLines = lines.slice(startRow, endRow + 1);
    const templateText = selectedLines.join('\n');
    
    const components = new Set<string>();
    let match;
    while ((match = componentPattern.exec(templateText)) !== null) {
      const componentName = match[1];
      components.add(componentName);
    }
    
    if (components.size === 0) {
      return null;
    }
    
    const componentsChunk = `template components: ${Array.from(components).join(', ')}`;
    
    if (!processedChunks.has(componentsChunk)) {
      processedChunks.add(componentsChunk);
      return componentsChunk;
    }
    
    return null;
  }

  private parseScriptElement(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
    context: ParseContext,
  ): string | null {
    // 在脚本部分内查找组件定义、属性、方法等
    const startRow = node.startPosition.row;
    const endRow = node.endPosition.row;
    
    // 查找 Vue 组件名称
    const componentNamePattern = /name:\s*['"]([^'"]+)['"]/;
    const selectedLines = lines.slice(startRow, endRow + 1);
    const scriptText = selectedLines.join('\n');
    
    // 提取组件名称
    const nameMatch = scriptText.match(componentNamePattern);
    if (nameMatch) {
      const componentName = `Vue component: ${nameMatch[1]}`;
      if (!processedChunks.has(componentName)) {
        processedChunks.add(componentName);
        return componentName;
      }
    }
    
    // 查找属性定义
    // Removed 's' flag for compatibility with lower ECMAScript targets
    const propPattern = /props:\s*{([\s\S]*?)}/;
    const propsMatch = scriptText.match(propPattern);
    if (propsMatch) {
      const propsText = propsMatch[1];
      const propNamePattern = /(\w+):/g;
      let propMatch;
      const props: string[] = [];
      
      while ((propMatch = propNamePattern.exec(propsText)) !== null) {
        props.push(propMatch[1]);
      }
      
      if (props.length > 0) {
        const propsChunk = `Vue props: ${props.join(', ')}`;
        if (!processedChunks.has(propsChunk)) {
          processedChunks.add(propsChunk);
          return propsChunk;
        }
      }
    }
    
    // 对于script标签中的普通JavaScript代码，使用JavaScriptParseStrategy处理
    for (let i = startRow; i <= endRow; i++) {
      const line = lines[i];
      // 查找 script 标签内部的节点
      if (node.children && node.children.length > 0) {
        for (const child of node.children) {
          if (child.type === 'raw_text') {
            // 创建一个模拟的 capture 对象，使用 JavaScript 策略解析
            const jsCapture = {
              node: child,
              name: 'script.content'
            };
            
            const jsResult = this.jsStrategy.parseCapture(
              jsCapture,
              lines,
              processedChunks,
              context
            );
            
            if (jsResult) {
              return jsResult;
            }
          }
        }
      }
    }
    
    return null;
  }

  private parseStyleElement(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): string | null {
    // 提取样式部分的信息，如 scoped 和预处理器类型
    const startRow = node.startPosition.row;
    
    const stylePattern = /<style([^>]*)>/;
    const lineText = lines[startRow];
    const styleMatch = lineText.match(stylePattern);
    
    if (styleMatch) {
      const styleAttrs = styleMatch[1] || '';
      const scoped = styleAttrs.includes('scoped');
      
      // 检查预处理器
      const langMatch = styleAttrs.match(/lang=["']([^"']+)["']/);
      const lang = langMatch ? langMatch[1] : 'css';
      
      const styleInfo = `style: ${lang}${scoped ? ' (scoped)' : ''}`;
      
      if (!processedChunks.has(styleInfo)) {
        processedChunks.add(styleInfo);
        return styleInfo;
      }
    }
    
    return null;
  }

  private parseInterpolation(
    node: SyntaxNode,
    lines: string[],
    processedChunks: Set<string>,
  ): string | null {
    // 提取模板插值表达式中的变量或表达式
    const startRow = node.startPosition.row;
    const endRow = node.endPosition.row;
    
    const selectedLines = lines.slice(startRow, endRow + 1);
    const interpolationText = selectedLines.join('\n');
    
    // 提取 {{ expression }} 中的表达式
    const expressionPattern = /{{([^{}]+)}}/;
    const expressionMatch = interpolationText.match(expressionPattern);
    
    if (expressionMatch) {
      const expression = expressionMatch[1].trim();
      
      // 跳过简单的变量引用
      if (expression.split('.').length <= 2 && !expression.includes('(')) {
        return null;
      }
      
      const interpolationChunk = `template expression: ${expression}`;
      
      if (!processedChunks.has(interpolationChunk)) {
        processedChunks.add(interpolationChunk);
        return interpolationChunk;
      }
    }
    
    return null;
  }
}