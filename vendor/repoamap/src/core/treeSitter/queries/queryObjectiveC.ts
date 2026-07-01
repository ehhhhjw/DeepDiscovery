export const queryObjectiveC = `
; 定义
(class_interface) @definition.class
(implementation_definition) @definition.implementation
(protocol_declaration) @definition.protocol
(method_definition) @definition.method
(preproc_def) @definition.macro

; 引用
(preproc_include) @reference.import
(message_expression) @reference.call

`;