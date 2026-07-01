import queue
from const import (
    Target_Fold_Path,
    Static_Info_Path,
    Output_Dot_File_Path,
    Output_Json_File_Path,
    original_root,
    Bundle_name,
)
from utils import (
    list_files_recursively,
    read_json_file,
    save_to_json,
    get_file_extension,
    get_file_name,
    check_node_modules,
)

dirMP = {}
outPutMessage = set()
visited_nodes = set()
targetOutPutMessage = set()
meetRequirementsFile = {}
The_Rest_File = set()


def BFS(node_name, nodes):
    q = queue.Queue()
    q.put(node_name)
    flag = 1
    while flag == 1:
        q2 = queue.Queue()
        while not q.empty():
            temp = q.get()
            visited_nodes.add(temp)
            if temp not in nodes:
                continue
            dependencies = nodes[temp].get("Dependent", [])
            for dependency in dependencies:
                dotInformation = '"' + temp + '"' + " -> " + '"' + dependency + '"\n'

                if (
                    temp
                    in meetRequirementsFile
                    # and get_file_name_without_extension(dependency)
                    # in meetRequirementsFile
                ):
                    targetOutPutMessage.add(dotInformation)

                if dotInformation not in outPutMessage:
                    outPutMessage.add(dotInformation)
                    q2.put(dependency)
        while not q2.empty():
            temp = q2.get()
            q.put(temp)
        if q.empty():
            break


if __name__ == "__main__":
    # 读取文件夹路径下的所有文件
    all_files = list_files_recursively(Target_Fold_Path)
    # print(all_files)
    suit_file_root = []
    file_names_with_extension = []
    FileName2RootDIR = {}

    for this_file_root in all_files:
        is_contain_node_module = check_node_modules(this_file_root)
        if is_contain_node_module == 1:
            continue
        this_file_root_name = get_file_name(this_file_root)
        FileName2RootDIR[this_file_root_name] = this_file_root

    for file_name in all_files:
        is_contain_node_module = check_node_modules(this_file_root)
        if is_contain_node_module == 1:
            continue
        file_name_extension = get_file_extension(file_name)
        if (
            file_name_extension == "js"
            or file_name_extension == "jsx"
            or file_name_extension == "page"
            or file_name_extension == "ts"
            or file_name_extension == "tsx"
        ):
            suit_file_root.append(file_name)
            file_name_with_extension = get_file_name(file_name)
            file_names_with_extension.append(file_name_with_extension)

    # file_names = get_file_names_without_extension(all_files)

    # 将符合要求的文件名进行标记
    for name in file_names_with_extension:
        meetRequirementsFile[name] = name

    # # # 输出文件名
    # for name in file_names:
    #     print(name)

    data = read_json_file(Static_Info_Path)
    GraphDir = {}
    page_list = []
    for type_index in data[Bundle_name]:
        if type_index == "page":
            for page_item_name in data[Bundle_name][type_index]:
                page_item = data[Bundle_name][type_index][page_item_name]
                page_list.append(page_item["base"])
        if type_index == "style":
            continue
        for file_index in data[Bundle_name][type_index]:
            message_temp = {}
            dependent_list = []
            message_temp["Type"] = type_index
            # message_temp['Name']=get_file_name_without_extension(file_index)
            message_temp["Name"] = file_index

            file_extension_name = get_file_extension(file_index)
            if (
                file_extension_name != "js"
                and file_extension_name != "jsx"
                and file_extension_name != "page"
                and file_extension_name != "ts"
                and file_extension_name != "tsx"
            ):
                continue
            # print(file_index)

            message_temp["Root"] = (
                data[Bundle_name][type_index][file_index]["dir"] + "/" + file_index
            )
            for dependent_index in range(
                len(data[Bundle_name][type_index][file_index]["dependent"])
            ):
                target_base_name = data[Bundle_name][type_index][file_index][
                    "dependent"
                ][dependent_index]["base"]
                target_base_name_extension = get_file_extension(target_base_name)
                if (
                    target_base_name_extension != "js"
                    and target_base_name_extension != "jsx"
                    and target_base_name_extension != "page"
                    and target_base_name_extension != "ts"
                    and target_base_name_extension != "tsx"
                ):
                    continue
                dependent_list.append(
                    data[Bundle_name][type_index][file_index]["dependent"][
                        dependent_index
                    ]["base"]
                )
            message_temp["Dependent"] = dependent_list

            GraphDir[file_index] = message_temp

    # for page_item in page_list:
    BFS(original_root, GraphDir)

    with open(Output_Dot_File_Path, "w") as file:
        for item in targetOutPutMessage:
            file.write(item)

    # 输出target文件的json数据
    OutputJsonDir = []
    visited_nodes = set(visited_nodes)

    for now_node in visited_nodes:
        # if now_node == "HCResultEyrieEventManager.js":
        #     print(1)
        # print(now_node)
        message_temp = {}
        dependent_list = []
        if now_node in GraphDir:
            message_temp["Type"] = GraphDir[now_node]["Type"]
            message_temp["Name"] = GraphDir[now_node]["Name"]
            message_temp["Root"] = GraphDir[now_node]["Root"]
            message_temp["Dependent"] = GraphDir[now_node]["Dependent"]
        else:
            message_temp["Type"] = "javaScript"
            message_temp["Name"] = now_node
            if now_node in FileName2RootDIR:
                index_info = FileName2RootDIR[now_node].index(Bundle_name)
                message_temp["Root"] = "./" + FileName2RootDIR[now_node][index_info:]
            else:
                message_temp["Root"] = "Unknow"
            message_temp["Dependent"] = dependent_list

        OutputJsonDir.append(message_temp)

    # print(len(OutputJsonDir))
    # print(OutputJsonDir)

    # for i in visited_nodes:
    #     if i == 'TripDynamicInfoRequestUtils.js':
    #         print(123)

    # print(visited_nodes)

    # print(visited_nodes)
    # print(len(OutputJsonDir))

    # print(outPutMessage)
    save_to_json(OutputJsonDir, Output_Json_File_Path)
