## 评测

###

1. 首先去钉钉文档下载 excel 文件，到 score/data 目录。[驾车行前代码问题](https://alidocs.dingtalk.com/i/nodes/QPGYqjpJYYMdg71vspRGyZNrJakx1Z5N)
2. 去 score/config 目录下修改配置字段。建议修改 local.config.ini 本地配置, 会合并覆盖默认配置。
3. 执行 main.py

```shell
# 执行 chat 问答队列。产物在 score/log/*
# 也可以配置 score/config/local.config.ini chat use_excel_answer = True，直接使用 excel 数据作为答案
python ./score/main.py --script_type chat

# 复制 chat 产物后的 id 到 score/config/local.config.ini score mark
# 执对 chat 产物进行 score 评分。会修改同 mark 标识的文件，添加相应字段
python ./score/main.py --script_type score

# 或者可以一起执行两个任务. score 会默认直接使用 chat 的 mark 去执行
python ./score/main.py --script_type chat_score

# 执行 excel 的评分测试 answer、aone_copilot、tongyi
python ./score/main.py --script_type score_excel --answer_type answer --row_index 10
```

评分细节见[文档](https://alidocs.dingtalk.com/i/nodes/l6Pm2Db8DajZ3BEosXar5djeWxLq0Ee4)
