from const import (
    New_Target_Json_File_Path,
    Target_Fold_Path,
    File_Function_Path,
    Output_Json_File_Path,
)
from utils import (
    list_files_recursively,
    get_file_names_without_extension,
    read_json_file,
    save_to_json,
)

dirMP = {}
outPutMessage = set()
visited_nodes = set()
targetOutPutMessage = set()
meetRequirementsFile = {}


def find_description(file_path, class_identifier):
    # class_identifier = '@class ExampleAgentConfig'
    description_identifier = "@description"

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if class_identifier in line:
            # Check the next lines for the description
            for j in range(i + 1, len(lines)):
                if description_identifier in lines[j]:
                    description_line = lines[j].replace("*", "").strip()
                    cleaned_description = description_line.replace("@description ", "")
                    return cleaned_description
    return None


if __name__ == "__main__":

    The_Result_Information = []

    # 读取文件夹路径下的所有文件
    note_all_files = list_files_recursively(Target_Fold_Path)
    file_names = get_file_names_without_extension(note_all_files)

    Target_Json_File = read_json_file(Output_Json_File_Path)
    File_Func_Information = read_json_file(File_Function_Path)

    print(Output_Json_File_Path)
    print(Target_Json_File)

    ############这里需要将class的description读取并存储########

    # classDescriptionDir = {}

    # for file_path_son in note_all_files:
    #     file_name = ""
    #     suffix = ""
    #     if "/" in file_path_son:
    #         file_name = file_path_son.split("/")[-1]
    #         if "." in file_path_son:
    #             suffix = file_path_son.split(".")[-1]
    #             if suffix != "txt":
    #                 continue
    #             else:
    #                 class_name = get_file_name_without_extension(file_path_son)
    #                 description_message = find_description(file_path_son, "@class ")
    #                 classDescriptionDir[class_name] = description_message

    ############这里需要将class的description读取并存储########
    null_list_info = []

    for one_target_json in Target_Json_File:
        target_name = one_target_json["Name"]
        if target_name == ".DS_Store":
            continue
        # one_target_json['Report'] = classDescriptionDir[target_name]
        one_target_json["Report"] = ""
        if target_name in File_Func_Information:
            one_target_json["Children"] = File_Func_Information[target_name]
        else:
            one_target_json["Children"] = null_list_info
        The_Result_Information.append(one_target_json)

    # print(outPutMessage)
    save_to_json(The_Result_Information, New_Target_Json_File_Path)


# {
#     "Type": "javaScript",
#     "Name": "ExampleAction",
#     "Root": "./target_bundle/src/car/example_page/logic/ExampleAction.js",
#     "Dependent": [
#         "ExampleData",
#         "ExampleAgent",
#         "ExampleCalcBusiness"
#     ],
#     "Report": "...",
#     "Children": [
#         {
#             "Name": "...",
#             "Report": "...."
#         }
#     ]
# }
####  此代码的输出为.dot文件以及一个json文件，dot文件用来绘制图谱，json文件的格式如上，存储了每个类的详细信息
# 输入：
# Static_Info_Path——静态扫描文件的结果
# Output_Dot_File_Path——.dot文件的存储路径
# Output_Json_File_Path——.json文件的存储路径
# Note_Fold_Path——具有LLM生成注释代码的文件夹路径
# original_root——要查找的路线的入口
#
# 输出：
# Output_Dot_File_Path
# Output_Json_File_Path
