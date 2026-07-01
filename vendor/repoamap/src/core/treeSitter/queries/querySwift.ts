export const querySwift = `

; 类定义 - 匹配类声明，提取类名
(class_declaration
  name: (type_identifier) @name) @definition.class

; 协议定义 - 匹配协议声明，提取协议名
(protocol_declaration
  name: (type_identifier) @name) @definition.interface

; 类方法定义 - 匹配类内部的各种方法声明
(class_declaration
    (class_body
        [
            (function_declaration
                name: (simple_identifier) @name
            )
            (subscript_declaration
                (parameter (simple_identifier) @name)
            )
            (init_declaration "init" @name)
            (deinit_declaration "deinit" @name)
        ]
    )
) @definition.method

; 类属性定义 - 匹配类内部的属性声明
(class_declaration
    (class_body
        [
            (property_declaration
                (pattern (simple_identifier) @name)
            )
        ]
    )
) @definition.property

; 全局属性定义 - 匹配类外部的属性声明
(property_declaration
    (pattern (simple_identifier) @name)
) @definition.property

; 全局函数定义 - 匹配类外部的函数声明
(function_declaration
    name: (simple_identifier) @name) @definition.function
`;
