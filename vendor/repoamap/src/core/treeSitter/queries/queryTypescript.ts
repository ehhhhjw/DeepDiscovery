export const queryTypescript = `
; ========== 1、导入语句 ==========
(import_statement
  (import_clause (identifier) @name.reference.module)) @definition.import

(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @name.reference.module))) @definition.import)

; ========== 2、函数定义 ==========
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(function_signature
  name: (identifier) @name.definition.function) @definition.function

(assignment_expression
    left: [(identifier) @name.definition.function]
    right: (arrow_function)
) @definition.function

; ========== 3、方法定义 ==========
(method_definition
  name: (property_identifier) @name.definition.method) @definition.method

(method_signature
  name: (property_identifier) @name.definition.method) @definition.method

(abstract_method_signature
  name: (property_identifier) @name.definition.method) @definition.method

; ========== 4、类定义 ==========
(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

(abstract_class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

; ========== 5、接口定义 ==========
(interface_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

(interface_declaration
  name: (type_identifier) @name.definition.class) @definition.class


; ========== 6、模块定义 ==========
(module
  name: (identifier) @name.definition.module) @definition.module

`;
