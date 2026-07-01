import os
import json
import queue

dirMP={}
outPutMessage=set()
visited_nodes=set()
targetOutPutMessage=set()
meetRequirementsFile={}


# 读取文件夹下的所有文件
def list_files_recursively(folder_path):
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files

# 读取文件夹下所有文件的文件名
def get_file_names_without_extension(file_paths):
    file_names = []
    for file_path in file_paths:
        # 获取文件名（包含扩展名）
        base_name = os.path.basename(file_path)
        # 去除扩展名
        name_without_extension = os.path.splitext(base_name)[0]
        file_names.append(name_without_extension)
    return file_names


# 读取文件的文件名
def get_file_name_without_extension(file_path):
    base_name = os.path.basename(file_path)
    name_without_extension = os.path.splitext(base_name)[0]
    return name_without_extension

def extract_filename(file_path):
    return os.path.basename(file_path)

# 读取json文件
def read_json_file(file_path):
    """
    读取并解析JSON文件。

    参数:
    file_path (str): JSON文件的路径。

    返回:
    dict: 解析后的数据，以字典形式返回。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except json.JSONDecodeError:
        print("文件内容不是有效的JSON格式: {file_path}")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")

# 将数据保存为json格式
def save_to_json(data, file_path):
    """
    将数据保存到JSON文件。

    参数:
    data (dict 或 list): 要保存的数据。
    file_path (str): 保存数据的文件路径。
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"数据已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存到JSON文件时发生错误: {e}")

def BFS(node_name, nodes):
    q = queue.Queue()
    q.put(node_name)
    flag = 1
    while flag==1:
        q2 = queue.Queue()
        while not q.empty():
            temp=q.get()
            visited_nodes.add(temp)
            dependencies = nodes[temp].get('Dependent', [])
            for dependency in dependencies:
                dotInformation = "\"" + get_file_name_without_extension(temp) + "\"" + " -> " + "\"" + get_file_name_without_extension(dependency) + "\"\n"
                
                if get_file_name_without_extension(temp) in meetRequirementsFile and get_file_name_without_extension(dependency) in meetRequirementsFile:
                    # print(dotInformation)
                    targetOutPutMessage.add(dotInformation)

                if dependency not in nodes:
                    continue

                if dotInformation not in outPutMessage:
                    outPutMessage.add(dotInformation)
                    q2.put(dependency)
        while not q2.empty():
            temp=q2.get()
            q.put(temp)
        if q.empty():
            break


if __name__ == "__main__":
    Target_Fold_Path='/path/to/project/result_state'
    Static_Info_Path = '/path/to/project/allBunlde.json'
    Output_Dot_File_Path='/path/to/project/Output/targetDot.txt'
    Output_Json_File_Path='/path/to/project/Output/target_graph_information.json'
    original_root='PageA1.page'
    
    # 读取文件夹路径下的所有文件
    all_files = list_files_recursively(Target_Fold_Path)


    file_names = get_file_names_without_extension(all_files)


    # 将符合要求的文件名进行标记
    for name in file_names:
        meetRequirementsFile[name]=name

    # # 输出文件名
    # for name in file_names:
    #     print(name)

    data = read_json_file(Static_Info_Path)
    GraphDir={}
    for type_index in data['target_bundle']:
        if type_index == "style":
            continue
        for file_index in data['target_bundle'][type_index]:
            message_temp={}
            dependent_list=[]
            message_temp['Type']=type_index
            message_temp['Name']=get_file_name_without_extension(file_index)
            message_temp['Root']=data['target_bundle'][type_index][file_index]['dir']+"/"+file_index
            for dependent_index in range(len(data['target_bundle'][type_index][file_index]['dependent'])):
                dependent_list.append(data['target_bundle'][type_index][file_index]['dependent'][dependent_index]['base'])
            message_temp['Dependent']=dependent_list
            GraphDir[file_index]=message_temp
            # name_dir.append(file_index)
    # print(GraphDir)


    BFS(original_root,GraphDir)

    with open(Output_Dot_File_Path, 'w') as file:
        for item in targetOutPutMessage:
            file.write(item)


    # 输出target文件的json数据
    OutputJsonDir=[]

    for type_index in data['target_bundle']:
        if type_index == "style":
            continue
        for file_index in data['target_bundle'][type_index]:
            message_temp={}
            dependent_list=[]
            message_temp['Type']=type_index
            message_temp['Name']=get_file_name_without_extension(file_index)
            if message_temp['Name'] not in meetRequirementsFile:
                continue
            message_temp['Root']=data['target_bundle'][type_index][file_index]['dir']+"/"+file_index
            for dependent_index in range(len(data['target_bundle'][type_index][file_index]['dependent'])):
                if data['target_bundle'][type_index][file_index]['dependent'][dependent_index]['name'] in meetRequirementsFile:
                    dependent_list.append(data['target_bundle'][type_index][file_index]['dependent'][dependent_index]['name'])
            message_temp['Dependent']=dependent_list
            OutputJsonDir.append(message_temp)

    # print(outPutMessage)
    save_to_json(OutputJsonDir, Output_Json_File_Path)

