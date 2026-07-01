### 项目介绍

### 启动

1. python 包下载

```shell
pyenv local 3.10.14
poetry env use 3.10.14
poetry shell
poetry install
```

2. 复制 src/config/config.ini 到 src/config/local.config.ini。
如果新添加工具，需要在 config 中新增对应 tool 的配置。
```shell
cp ./src/config/config.ini ./src/config/local.config.ini
```
### 工具列表

1. commit 提取工具

```shell
# 根据 config.ini 文件配置，提取特定目录的 commit 记录
python ./src/main.py --tool commit

# 将提取的 json 文件转换为 图 结构
python ./src/main.py --tool commit --action graph
```

2. tree-sitter 解析器下载（TODO：待迁移）

```shell
cd src/ast/tree_sitter
git clone https://github.com/tree-sitter/tree-sitter-javascript
git clone https://github.com/tree-sitter/tree-sitter-typescript
```
