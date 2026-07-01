export const queryJavascript = `
; 1、类名和父类
(class_declaration
  name: (identifier) @class.name
) @class
; 2、类属性
(class_declaration
  body: (class_body
    (field_definition
      property: (property_identifier) @property.name))) @property

; 3、方法名
(method_definition name: (property_identifier) @method.name) @method

; 4、函数名 
(function_declaration name: (identifier) @function.name) @function
(function_expression name: (identifier) @function.name) @function

; 5、箭头函数 - 如果有变量赋值
(variable_declarator 
  name: (identifier) @arrow_function.name
  value: (arrow_function)) @arrow_function

; 6、导入语句 - 只提取包名
(import_statement source: (string) @string_fragment)@import

; 7、require语句 - 只提取包名
(call_expression
  function: (identifier) @_require (#eq? @_require "require")
  arguments: (arguments (string) @require.source)) @require
`;
