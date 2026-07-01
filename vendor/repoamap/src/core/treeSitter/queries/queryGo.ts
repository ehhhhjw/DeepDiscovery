
export const queryGo = `
; 包声明
(package_clause
  (package_identifier) @name) @definition.package

; 导入声明
(import_declaration
  (import_spec_list
    (import_spec
      path: (interpreted_string_literal) @name))) @definition.import

(import_declaration
  (import_spec
    path: (interpreted_string_literal) @name)) @definition.import

; 类型定义（结构体和接口）
(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (struct_type))) @definition.type

(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (interface_type))) @definition.type


; 函数定义
(function_declaration
  name: (identifier) @name) @definition.function

; 方法定义
(method_declaration
  name: (field_identifier) @name) @definition.method

; 类型引用
(type_identifier) @name @reference.type

; 函数/方法调用
(call_expression
  function: [
    (identifier) @name
    (selector_expression field: (field_identifier) @name)
  ]) @reference.call
`;