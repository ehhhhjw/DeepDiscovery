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


import os
import json
import queue
import re

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



def find_description(file_path, class_identifier):
    # class_identifier = '@class ExampleAgentConfig'
    description_identifier = '@description'
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    for i, line in enumerate(lines):
        if class_identifier in line:
            # Check the next lines for the description
            for j in range(i + 1, len(lines)):
                if description_identifier in lines[j]:
                    description_line = lines[j].replace('*', '').strip()
                    cleaned_description = description_line.replace('@description ', '')
                    return cleaned_description
    return None


def read_comments_from_file(file_path):
    comments = []
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        # 使用正则表达式匹配注释
        comments_raw = re.findall(r'/\*.*?\*/', content, re.DOTALL)
        # 去掉注释的/*和*/部分
        comments = [comment.strip('/*').strip('*/').strip() for comment in comments_raw]
    return comments

def extract_name_and_description(string_list):
    results = []
    
    for content in string_list:
        # 使用正则表达式匹配@function和下一个*之间的内容
        functions = re.findall(r'@function(.*?)(?=\*)', content, re.DOTALL)
        
        for func in functions:
            # 清理@function匹配到的内容，去除换行符和多余空格
            name = re.sub(r'\n', '', func).strip()
            # 初始化description
            description = None
            
            # 查找@description的位置
            description_match = re.search(r'@description', content)
            if description_match:
                description_pos = description_match.end()
                if '*' in content[description_pos:]:
                    # 使用正则表达式匹配@description和下一个*之间的内容
                    desc_match = re.search(r'@description(.*?)(?=\*)', content, re.DOTALL)
                    if desc_match:
                        description = re.sub(r'\n', '', desc_match.group(1)).strip()
                else:
                    # 提取@description后面所有的内容
                    desc_match = re.search(r'@description(.*)', content, re.DOTALL)
                    if desc_match:
                        description = re.sub(r'\n', '', desc_match.group(1)).strip()
            
            results.append({
                'Name': name,
                'Report': description
            })
    
    return results

if __name__ == "__main__":

    Static_Info_Path = ''   
    Output_Dot_File_Path=''  
    Output_Json_File_Path='' 
    
    Note_Fold_Path = ''  # 替换为您的文件夹路径

    original_root=''
    
    # 读取文件夹路径下的所有文件
    note_all_files = list_files_recursively(Note_Fold_Path)


    ############这里需要将class的description读取并存储########

    classDescriptionDir = {}

    for file_path_son in note_all_files:
        file_name=''
        suffix=''
        if '/' in file_path_son:
            file_name = file_path_son.split('/')[-1]
            if '.' in file_path_son:
                suffix = file_path_son.split('.')[-1]
                if suffix != 'txt':
                    continue
                else:
                    class_name = get_file_name_without_extension(file_path_son)
                    description_message = find_description(file_path_son,'@class ')
                    classDescriptionDir[class_name] = description_message
                    

    ############这里需要将class的description读取并存储########




    ############这里需要将每个文件中的函数读取并存储########

    funcNameDescriptionDir = {}

    for file_path_son in note_all_files:
        class_name = get_file_name_without_extension(file_path_son)
        file_name = get_file_name_without_extension(file_path_son)
        if class_name == '.DS_Store':
            continue
        # print(file_name)
        comments_list = read_comments_from_file(file_path_son)
        output_list=extract_name_and_description(comments_list)
        funcNameDescriptionDir[class_name]=output_list
                    

    ############这里需要将每个文件中的函数读取并存储########

    file_names = get_file_names_without_extension(note_all_files)


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
            message_temp['Report'] = classDescriptionDir[message_temp['Name']]
            message_temp['Children']=funcNameDescriptionDir[message_temp['Name']]

            OutputJsonDir.append(message_temp)

    # print(outPutMessage)
    save_to_json(OutputJsonDir, Output_Json_File_Path)




