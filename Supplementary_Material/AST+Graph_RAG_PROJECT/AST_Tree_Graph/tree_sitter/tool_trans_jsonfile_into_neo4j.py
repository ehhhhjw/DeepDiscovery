# ##################################

# 该文件用来将实体图谱转化为图数据库语句，并且将数据存储到NEO4J中

# ##################################


import json
import os
from neo4j import GraphDatabase
import re
from const import OUTPUT_DIR

NEO4J_URI = "neo4j://localhost"  # or neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"
NEO4J_DATABASE = "neo4j"

# Create a Neo4j driver
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def read_json_file(file_path):
    """
    读取并解析JSON文件。

    参数:
    file_path (str): JSON文件的路径。

    返回:
    dict: 解析后的数据，以字典形式返回。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except json.JSONDecodeError:
        print("文件内容不是有效的JSON格式: {file_path}")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")


# 读取文件夹下的所有文件
def list_files_recursively(folder_path):
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files


# 读取文件的文件名
def get_file_name_without_extension(file_path):
    base_name = os.path.basename(file_path)
    name_without_extension = os.path.splitext(base_name)[0]
    return name_without_extension


def write_string_to_file(file_name, content):
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(content)


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


def extract_entities(text):
    # 使用正则表达式提取 "Entities" 部分中的ID
    matches = re.findall(r"Entities\s*\(([^)]+)\)", text)
    if matches:
        # 将匹配到的ID转换为整数列表
        entities = [int(x) for x in matches[0].split(",")]
        return {"Entity": entities}
    else:
        return {"Entity": []}


# json_file_path=f'/path/to/data.json'
graph_file_path = f"{OUTPUT_DIR}/target_graph_information.json"


# Read json file
# data = read_json_file(json_file_path)
GraphDir = read_json_file(graph_file_path)


#############此处的代码用来创建类实体信息#######################################


with driver.session() as session:

    # 此处导入文件夹中存在的类实体

    for item_index in range(len(GraphDir)):
        typeInfo = "class"
        nameInfo = GraphDir[item_index]["Name"]
        rootInfo = GraphDir[item_index]["Root"]
        # descriptionInfo = Class_mp_Description_Dir[nameInfo]
        session.run(
            "CREATE (d:Entity_Class {entityname: $entityname, entitytype: $entitytype, entityroot: $entityroot})",
            entityname=nameInfo,
            entitytype=typeInfo,
            entityroot=rootInfo,
        )

    # 此处相当于手动导入存在于其他文件夹中的类实体
    session.run(
        "CREATE (d:Entity_Class {entityname: $entityname, entitytype: $entitytype, entityroot: $entityroot, entitydescription: $entitydescription})",
        entityname="ExampleData",
        entitytype="none",
        entityroot="none",
        entitydescription="该对象内包含懒加载模块的方法，通过调用getter方法动态引入模块，减小初始加载时间。涉及到路线动态云配置、地图定位、POI工具等。",
    )

# #############此处的代码用来创建类实体信息#######################################


# # #############此处的代码用来添加类实体关系#######################################

with driver.session() as session:
    for item_index in range(len(GraphDir)):
        nameInfo = GraphDir[item_index]["Name"]
        messageDependentInfo = GraphDir[item_index]["Dependent"]
        for dependent_son in messageDependentInfo:
            targeEntityName = dependent_son
            # print(nameInfo,dependent_son)
            session.run(
                "MATCH( f: Entity_Class {entityname:$entityname_from}),(b:Entity_Class {entityname:$entityname_to}) with f, b CREATE(f)-["
                ":__dependent__]->(b)",
                entityname_from=nameInfo,
                entityname_to=dependent_son,
            )

# # #############此处的代码用来添加类实体关系#######################################


# #############此处的代码用来创建obj、func、method实体信息以及添加obj、func、method与类之间的实体关系#######################################

Class_Son_Entity_Information_Path = f"{OUTPUT_DIR}/file_func_information.json"

Class_Son_Entity_Information = read_json_file(Class_Son_Entity_Information_Path)

Target_Fold_Path = f"{os.getcwd()}/result_state_js"

all_files = list_files_recursively(Target_Fold_Path)

for file_path in all_files:
    Func_Name_Dir = {}
    file_name = get_file_name_without_extension(file_path)
    if file_name == ".DS_Store":
        continue
    funcInformationDir = Class_Son_Entity_Information[file_name]

    with driver.session() as session:
        for funcInformation in funcInformationDir:
            funcName = funcInformation["Name"]
            funcType = funcInformation["Type"]
            son_func = []  # 调用的函数
            if funcName in Func_Name_Dir:
                continue
            else:
                Func_Name_Dir[funcName] = 1
                session.run(
                    "CREATE (d:Entity_Class_Son {entityname: $entityname, entitytype: $entitytype, entityclass: $entityclass})",
                    entityname=funcName,
                    entitytype=funcType,
                    entityclass=file_name,
                )
                session.run(
                    "MATCH (f:Entity_Class_Son {entityname:$entityname_from, entitytype:$entitytype, entityclass:$entityclass}), "
                    "(b:Entity_Class {entityname:$entityname_to}) "
                    "WITH f, b "
                    "CREATE (f)-[:__in_this_class__]->(b)",
                    entityname_from=funcName,
                    entitytype=funcType,
                    entityclass=file_name,
                    entityname_to=file_name,
                )

            # 函数依赖关系建立
            Call = (
                funcInformation["Call"] if "Call" in funcInformation else []
            )  # ["this.startNavi", "xx"]
            if len(Call) <= 0:  # 没有依赖或者不是函数
                continue
            for call_item in Call:  # call_item =》 this.startNavi

                call_item_split = call_item.split(".")

                # TODO 跨文件实体未处理、super、i18n 等公共实体未处理
                if call_item_split[0] in ["super", "require", "Lazy"]:
                    # 如果是 super 等关键字，不建立连接
                    # entitytype = "fn_system"
                    # system_entity = session.run(
                    #     "MATCH (f:Entity_Fun_Son {entityname:$entityname, entitytype:$entitytype, entityfunc:$entityfunc}) RETURN f",
                    #     entityname=call_arr_item,
                    #     entitytype=entitytype,
                    #     entityfunc=funcName,
                    # )
                    # if system_entity.peek():
                    #     # 数据为空,创建实体
                    #     session.run(
                    #         "CREATE (d:Entity_Fun_Son {entityname: $entityname, entitytype: $entitytype, entityfunc: $entityfunc})",
                    #         entityname=call_arr_item,
                    #         entitytype=entitytype,
                    #         entityfunc=funcName,
                    #     )
                    # # 建立连接
                    # session.run(
                    #     "MATCH (f:Entity_Fun_Son {entityname:$entityname_from, entitytype:$entitytype, entityfunc:$funcName}), "
                    #     "(b:Entity_Class_Son {entityname:$funcName},{entitytype:$funcType},{entityclass:$entityclass}) "
                    #     "WITH f, b "
                    #     "CREATE (f)-[:__in_this_function__]->(b)",
                    #     entityname_from=funcName,
                    #     entitytype=entitytype,
                    #     entityname_to=file_name,
                    #     funcType=funcType,
                    #     entityclass=file_name,
                    # )
                    continue

                func_son_name = call_item_split[0]
                if call_item_split[0] in ["this"]:
                    # 如果是 this，使用第二个值为函数名
                    func_son_name = call_item_split[1]
                #  兼容 ?. 的调用
                func_son_name = func_son_name.replace("?", "")

                # 首先查询当前文件是否有这个实体
                class_son_entity = session.run(
                    "MATCH (f:Entity_Class_Son {entityname:$entityname, entityclass:$entityclass}) RETURN f",
                    entityname=func_son_name,
                    entityclass=file_name,
                )

                class_son_entity = [record["f"] for record in class_son_entity]
                if len(class_son_entity) <= 0:
                    # 如果没有则 continue
                    continue
                class_son_entity = class_son_entity[0]
                # print(class_son_entity["_properties"])
                if func_son_name in son_func:
                    # 如果已经存在，则 continue
                    continue

                print("run --", func_son_name in son_func, func_son_name, funcName)
                son_func.append(func_son_name)
                # 如果查询到，建立连接
                session.run(
                    "MATCH (f:Entity_Class_Son {entityname:$entityname_from,entityclass:$entityclass}), "
                    "(b:Entity_Class_Son {entityname:$funcName, entitytype:$entitytype, entityclass:$entityclass}) "
                    "WITH f, b "
                    "CREATE (f)-[:__in_this_func__]->(b)",
                    entityname_from=func_son_name,
                    entitytype=funcType,
                    funcName=funcName,
                    entityclass=file_name,
                )

# # # #############此处的代码用来创建obj、func、method实体信息以及添加obj、func、method与类之间的实体关系#######################################
