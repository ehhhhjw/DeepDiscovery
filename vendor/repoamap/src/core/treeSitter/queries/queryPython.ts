
export const queryPython = `
; Import statements - 更全面的导入语句匹配
(import_statement
  name: (dotted_name) @name.reference.module) @definition.import

(import_statement
  name: (aliased_import
    name: (dotted_name) @name.reference.module)) @definition.import

(import_from_statement
  module_name: (dotted_name) @name.reference.module) @definition.import

(import_from_statement
  module_name: (relative_import) @name.reference.module) @definition.import

(import_from_statement
  name: (dotted_name) @name.reference.module) @definition.import

(import_from_statement
  name: (aliased_import
    name: (dotted_name) @name.reference.module)) @definition.import

; 类定义
(class_definition
  name: (identifier) @name.definition.class) @definition.class

; 函数定义
(function_definition
  name: (identifier) @name.definition.function) @definition.function

; 类方法定义 - 在类定义内部的函数
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.definition.method))) @definition.method

; 函数调用
(call
  function: [
    (identifier) @name.reference.call
    (attribute
      attribute: (identifier) @name.reference.call)
  ]) @reference.call
  
`;
