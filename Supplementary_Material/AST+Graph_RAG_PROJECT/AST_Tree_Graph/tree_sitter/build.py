from tree_sitter import Language

Language.build_library(
  # so文件保存位置
  'build/my-languages.so',

  # vendor文件下git clone的仓库
  [
    'tree-sitter-java',
    'tree-sitter-python',
    'tree-sitter-cpp',
    'tree-sitter-c-sharp',
    'tree-sitter-javascript',
  ]
)
