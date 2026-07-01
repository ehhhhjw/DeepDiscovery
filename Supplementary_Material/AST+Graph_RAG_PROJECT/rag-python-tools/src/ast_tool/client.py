from tree_sitter import Language, Parser
from const.dir import AST_TREE_SITTER_DIR

my_language_path = AST_TREE_SITTER_DIR / "build/my-languages.so"
Language.build_library(
    my_language_path,
    [
        AST_TREE_SITTER_DIR / "tree-sitter-javascript",
        AST_TREE_SITTER_DIR / "tree-sitter-typescript/tsx",
    ],
)

js_language = Language(my_language_path, "javascript")
ts_language = Language(my_language_path, "tsx")

js_parser = Parser()
js_parser.set_language(js_language)

ts_parser = Parser()
ts_parser.set_language(ts_language)


def get_tree_sitter_parser(language="js"):
    language_map = {
        "js": js_parser,
        "ts": ts_parser,
        "default": js_parser,
    }
    if language in language_map:
        return language_map[language]
    return language_map["default"]


def tree_sitter_parse_code(source_code, file_path):
    language = "js"
    if file_path.endswith(".ts") or file_path.endswith(".tsx"):
        language = "ts"
    parser = get_tree_sitter_parser(language)
    tree = parser.parse(source_code)
    return tree.root_node


node = tree_sitter_parse_code(bytes("const a = 1", "utf-8"), "a.ts")
print(node.type)
