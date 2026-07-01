import os

VERSION = "v8"

OUTPUT_DIR = f"{os.getcwd()}/Output/{VERSION}"


Bundle_name = "target_bundle"
# 要分析的项目目录

Target_Fold_Path = f"{os.getcwd()}/.run_code/{Bundle_name}"
Static_Info_Path = f"{OUTPUT_DIR}/allBunlde.json"
Output_Dot_File_Path = f"{OUTPUT_DIR}/targetDot.txt"

Class_info_path = f"{OUTPUT_DIR}/class_info.json"

File_Function_Path = f"{OUTPUT_DIR}/file_func_information.json"

Output_Json_File_Path = f"{OUTPUT_DIR}/target_graph_information.json"
New_Target_Json_File_Path = f"{OUTPUT_DIR}/new_target_graph_information.json"

File_Comment_Path = f"{OUTPUT_DIR}/file_comment_information.json"

Target_Json_File_With_Code_Path = (
    f"{OUTPUT_DIR}/target_graph_information_with_code_and_comment.json"
)

original_root = "PageA1.page"
