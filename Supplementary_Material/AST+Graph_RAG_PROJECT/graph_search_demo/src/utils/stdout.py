import sys
import os
from constants import LOG_DIR_PATH


class DualOutput:
    def open(log_path=LOG_DIR_PATH):
        DualOutput.terminal = sys.stdout  # 保存原始标准输出
        LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)
        DualOutput.log_file = open(f"{log_path}/output.txt", "a")
        sys.stdout = DualOutput

    def close():
        DualOutput.log_file.close()
        sys.stdout = DualOutput.terminal  # 恢复原始标准输出

    def write(message):
        DualOutput.terminal.write(message)  # 将消息输出到控制台
        DualOutput.log_file.write(message)  # 将消息输出到文件

    def flush():
        DualOutput.terminal.flush()
        DualOutput.log_file.flush()  # 刷新文件输出
