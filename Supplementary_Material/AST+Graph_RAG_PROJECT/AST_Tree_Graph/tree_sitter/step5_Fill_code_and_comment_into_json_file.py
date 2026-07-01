from const import (
    Target_Fold_Path,
    New_Target_Json_File_Path,
    Target_Json_File_With_Code_Path,
    File_Comment_Path,
)
from utils import (
    list_files_recursively,
    check_node_modules,
    get_file_name_without_extension,
    read_json_file,
    save_to_json,
    extract_lines_from_file,
    get_file_extension,
    get_file_name,
)

if __name__ == "__main__":
    all_files = list_files_recursively(Target_Fold_Path)
    Target_Json_File_Information = read_json_file(New_Target_Json_File_Path)
    Target_Json_Comment_Information = read_json_file(File_Comment_Path)

    File_Name_Path_Dir = {}

    All_Information_With_Func_Code = []

    ##################读取comment信息##################
    All_File_Comment_Dir = {}

    for one_file_comment_information in Target_Json_Comment_Information:
        # print(one_file_comment_information)
        this_file_comment_list = Target_Json_Comment_Information[
            one_file_comment_information
        ]
        This_File_Comment_Dir = {}
        for this_comment_information in this_file_comment_list:
            this_comment = this_comment_information["Name"]
            End_Point_Position = this_comment_information["End_Point"][0]
            This_File_Comment_Dir[End_Point_Position] = this_comment
            # print(End_Point_Position,this_comment)
        All_File_Comment_Dir[one_file_comment_information] = This_File_Comment_Dir

    ##################读取comment信息##################

    # 将文件名与文件进行映射
    for file_path in all_files:
        is_contain_node_module = check_node_modules(file_path)
        if is_contain_node_module == 1:
            continue
        file_extension_name = get_file_extension(file_path)
        file_name_with_extension = get_file_name(file_path)
        if (
            file_extension_name != "js"
            and file_extension_name != "jsx"
            and file_extension_name != "page"
            and file_extension_name != "ts"
            and file_extension_name != "tsx"
        ):
            continue

        file_name = get_file_name_without_extension(file_path)
        File_Name_Path_Dir[file_name_with_extension] = file_path

    for one_target_json_message in Target_Json_File_Information:
        this_target_file_name = one_target_json_message["Name"]

        new_target_json_message = {}
        new_target_json_message["Type"] = one_target_json_message["Type"]
        new_target_json_message["Name"] = one_target_json_message["Name"]
        new_target_json_message["Root"] = one_target_json_message["Root"]
        new_target_json_message["Dependent"] = one_target_json_message["Dependent"]
        new_target_json_message["Report"] = one_target_json_message["Report"]
        if "Description" in one_target_json_message:
            new_target_json_message["Description"] = one_target_json_message[
                "Description"
            ]
        else:
            new_target_json_message["Description"] = ""
        if "Extends" in one_target_json_message:
            new_target_json_message["Extends"] = one_target_json_message["Extends"]
        else:
            new_target_json_message["Extends"] = []
        if "Imports" in one_target_json_message:
            new_target_json_message["Imports"] = one_target_json_message["Imports"]
        else:
            new_target_json_message["Imports"] = []

        new_target_json_message_children = []

        target_json_message_name = one_target_json_message["Name"]
        if target_json_message_name in File_Name_Path_Dir:
            target_json_message_path = File_Name_Path_Dir[target_json_message_name]
        else:
            new_target_json_message["Children"] = one_target_json_message["Children"]
            All_Information_With_Func_Code.append(new_target_json_message)
            continue
        target_json_message_children = one_target_json_message["Children"]
        
        # Todo  给第一个函数加注释信息，现在是第一个函数没加注释

        index_pos_flag = 0
        the_previous_one = 0
        for message_children_point in target_json_message_children:
            message_children_point_message = {}
            message_children_point_message["Name"] = message_children_point["Name"]
            message_children_point_message["Type"] = message_children_point["Type"]
            if "Call" in message_children_point:
                message_children_point_message["Call"] = message_children_point["Call"]
            str_temp = ""
            start_point_line = message_children_point["Start_Point"][0]
            end_point_line = message_children_point["End_Point"][0]

            str_temp = ""
            if index_pos_flag == 0:
                if start_point_line - 1 in All_File_Comment_Dir[target_json_message_name]:
                    str_temp = All_File_Comment_Dir[target_json_message_name][
                        start_point_line - 1
                    ]
                    str_temp = str_temp + "\n"
                index_pos_flag = 1
                the_previous_one = end_point_line + 1
            else: 
                target_comment = ''
                for the_line_index in range(the_previous_one,start_point_line):
                    if the_line_index  in All_File_Comment_Dir[target_json_message_name]:
                        target_comment = target_comment + All_File_Comment_Dir[target_json_message_name][
                        the_line_index
                        ]
                        target_comment = target_comment +"\n"
                str_temp = target_comment
                the_previous_one = end_point_line + 1



            the_target_code = extract_lines_from_file(
                target_json_message_path, start_point_line + 1, end_point_line + 1
            )

            for a_target_code in the_target_code:
                str_temp = str_temp + a_target_code
            message_children_point_message["Code"] = str_temp
            new_target_json_message_children.append(message_children_point_message)

        new_target_json_message["Children"] = new_target_json_message_children
        All_Information_With_Func_Code.append(new_target_json_message)

    save_to_json(All_Information_With_Func_Code, Target_Json_File_With_Code_Path)

    # the_target_code = extract_lines_from_file(file_path, start_line, end_line)
    # # Print the extracted lines
    # for line in the_target_code:
    #     print(line, end='')
