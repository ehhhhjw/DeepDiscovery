import re
import random
import string
import statistics


# 平均值
def statistics_mean(data, default=0):
    return statistics.mean(data) if data else default


# 获取 dict 的值
def get_dict_value(data, path, default=False):
    """
    封装的方法，通过指定路径获取数据，当路径不存在时返回默认值。

    :param data: 需要操作的字典数据
    :param path: 需要尝试的路径，以点表示法（例如 "a.b.c"）
    :param default: 当路径无法匹配时使用的默认值
    :return: 匹配路径的数据或默认值
    """
    parts = path.split(".")
    current_data = data

    for part in parts:
        if part in current_data:
            current_data = current_data[part]
        else:
            return default

    return current_data


# 随机字符串
def generate_random_string(length: int) -> str:
    # 字母 + 数字
    letters_and_digits = string.ascii_letters + string.digits
    return "".join(random.choice(letters_and_digits) for i in range(length))


def extract_text_between_markers(text, start_marker, end_marker):
    """
    提取 start_marker 和 end_marker 之间的文本内容。

    :param text: 输入的长文本
    :param start_marker: 开始标识符
    :param end_marker: 结束标识符
    :return: 提取出的文本内容，如果找不到匹配内容则返回 None
    """
    pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()  # 删除前后空白字符
    return None
