import json

files_json = '[{"name": "ExampleComponent.jsx", "path": "src/example/ExampleComponent.jsx", "change_type": "M", "content": "diff --git a/src/example/ExampleComponent.jsx b/src/example/ExampleComponent.jsx\\nindex 0000000..1111111 100644\\n--- a/src/example/ExampleComponent.jsx\\n+++ b/src/example/ExampleComponent.jsx\\n@@ -1,3 +1,4 @@\\n class ExampleComponent {\\n+    // added a comment\\n     render() {}\\n }\\n"}]'
json.loads(files_json)
