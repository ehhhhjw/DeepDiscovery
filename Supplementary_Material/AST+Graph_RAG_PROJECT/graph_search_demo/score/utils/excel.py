import math
import pandas as pd

# 字段配置，(原始字段, 输出字段, 是否必须)
source_fields = [
    ("问题", "question", True),
    ("标准答案", "standard", True),
    ("Graph_Search模型回答", "answer", False),
    ("关键元素", "primary_files", False),  # 关键文件，如果缺失不能进行 rag 评分
    ("问题重写", "q_rewrite", False),
    ("子问题拆分", "sub_querys", False),
    ("Rerank", "rerank", False),
    ("Aone Copilot", "aone_copilot", False),
    ("通义灵码", "tongyi", False),
]


# 判断 excel 中某一个字段为空
def check_excel_field_invalid(field):
    return (
        not field
        # 检查是否为空字符串
        or (isinstance(field, str) and field.strip() == "")
        # 检查是否为 NaN
        or (isinstance(field, float) and math.isnan(field))
    )


def get_fields_value_for_row(row, fields=source_fields):
    result = None
    for field_item in fields:
        source_field, field, is_required = field_item
        # print(source_field, source_field in row)
        if source_field in row and not check_excel_field_invalid(
            row[source_field]
        ):
            if result is None:
                result = {}
            result[field] = row[source_field]
        elif is_required:
            return None
        else:
            result[field] = ""
    return result


def read_excel_file_to_list(file_path, sheet_name="Sheet1"):
    # 工作表名称或索引
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    result = []
    for _, row in df.iterrows():
        item = get_fields_value_for_row(row)
        if item is None:
            continue
        result.append(item)
    return result
