import json
import os
from neo4j import GraphDatabase
import re

from langchain_openai import OpenAIEmbeddings

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_BASE_URL = "https://openkey.cloud/v1"

LLM_API_KEY = "YOUR_LLM_API_KEY"
LLM_BASE_URL = "https://your-llm-proxy.example.com/v1"

embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large", 
    openai_api_base=OPENAI_BASE_URL,
    openai_api_key=OPENAI_API_KEY
)


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
        with open(file_path, 'r', encoding='utf-8') as file:
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



graph_file_path="/path/to/project/Output/v5/new_target_graph_information.json"


# Read json file
GraphDir = read_json_file(graph_file_path)

#############此处的代码用来创建类实体信息#######################################


with driver.session() as session:
    
    # 此处导入文件夹中存在的类实体

    for item_index in range(len(GraphDir)):
        typeInfo = 'class'
        nameInfo = GraphDir[item_index]['Name']
        rootInfo = GraphDir[item_index]['Root']
        reportInfo = GraphDir[item_index]['Report']
        Description = GraphDir[item_index]['Description'] if "Description" in GraphDir[item_index] else ""
        # descriptionInfo = Class_mp_Description_Dir[nameInfo]
        class_description = f"{reportInfo + "\n" if reportInfo else ''}{Description}"
        session.run("CREATE (d:Entity_Class {entityname: $entityname, entitytype: $entitytype, entityroot: $entityroot, entitydescription: $entitydescription})",
            entityname = nameInfo, entitytype = typeInfo, entityroot = rootInfo, entitydescription = class_description)

# #############此处的代码用来创建类实体信息#######################################


# # #############此处的代码用来添加类实体关系#######################################

with driver.session() as session:
    for item_index in range(len(GraphDir)):
        nameInfo = GraphDir[item_index]['Name']
        rootInfo = GraphDir[item_index]['Root']
        messageDependentInfo = GraphDir[item_index]['Dependent']
        extends = GraphDir[item_index]['Extends']

        # 有实体的 extends
        _extends = []
        for extend in extends:
            system_entity = session.run(
                "MATCH (f:Entity_Class {entityname:$entityname}) RETURN f",
                entityname=extend
                # entityroot = rootInfo
            )
            # 如果为空
            neo4j_result = system_entity.values()
            node = neo4j_result[0] if len(neo4j_result) > 0 else None
            if node is None:
                continue
            else:
                _extends.append(extend)

        for dependent_son in messageDependentInfo:
            targeEntityName = dependent_son
            if dependent_son in _extends:
                # 如果存在继承关系
                session.run(
                    "MATCH( f: Entity_Class {entityname:$entityname_from}),(b:Entity_Class {entityname:$entityname_to}) with f, b CREATE(f)-["
                    ":__extends__]->(b)", entityname_from=nameInfo, entityname_to=dependent_son)
            else:
                session.run(
                    "MATCH( f: Entity_Class {entityname:$entityname_from}),(b:Entity_Class {entityname:$entityname_to}) with f, b CREATE(f)-["
                    ":__dependent__]->(b)", entityname_from=nameInfo, entityname_to=dependent_son)

# # #############此处的代码用来添加类实体关系#######################################


# #############此处的代码用来创建obj、func、method实体信息以及添加obj、func、method与类之间的实体关系#######################################

All_File_Target_Information_Path = '/path/to/project/Output/v5/target_graph_information_with_code_and_comment.json'

All_File_Target_Information = read_json_file(All_File_Target_Information_Path)

flag_index = 0

for one_file_target_information in All_File_Target_Information:
    Func_Name_Dir = {}
    file_name = one_file_target_information['Name']
    funcInformationDir = one_file_target_information['Children']
    New_funcInformationDir = {}

    for funcInformation in funcInformationDir:
        funcName = funcInformation['Name']
        funcType = funcInformation['Type']
        funcCode = funcInformation['Code']
        if funcName in Func_Name_Dir:
            # print(New_funcInformationDir[funcName]['Code'])
            # print(funcCode)
            New_funcInformationDir[funcName]['Code'] = New_funcInformationDir[funcName]['Code'] + funcCode
            # print(New_funcInformationDir[funcName]['Code'])
            continue
        else:
            Func_Name_Dir[funcName] = 1
            New_funcInformationDir[funcName] = funcInformation

# # #############此处的代码用来创建obj、func、method实体信息以及添加obj、func、method与类之间的实体关系#######################################


# ####################不加embedding批处理################

    Code_Text_List = []
    Code_Text_Index_Dir = {}
    Code_Index = 0

    for new_funcInformationName in New_funcInformationDir:
        new_funcInformation = New_funcInformationDir[new_funcInformationName]
        new_funcName = new_funcInformation['Name']
        new_funcCode = new_funcInformation['Code']
        Code_Text_Index_Dir[new_funcName] = Code_Index
        Code_Index = Code_Index +1
        Code_Text_List.append(new_funcCode)
    # embeddings = embedding_model.embed_documents(Code_Text_List)



    with driver.session() as session:
        for new_funcInformationName in New_funcInformationDir:
            new_funcInformation = New_funcInformationDir[new_funcInformationName]
            new_funcName = new_funcInformation['Name']
            new_funcType = new_funcInformation['Type']
            new_funcCode = new_funcInformation['Code']
            # new_funcEmbedding = embeddings[Code_Text_Index_Dir[new_funcName]]
            session.run("CREATE (d:Entity_Class_Son {entityname: $entityname, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode})",
                entityname = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode)
            session.run(
                "MATCH (f:Entity_Class_Son {entityname: $entityname_from, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode}), "
                "(b:Entity_Class {entityname:$entityname_to}) "
                "WITH f, b "
                "CREATE (f)-[:__in_this_class__]->(b)",
                entityname_from = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entityname_to=file_name
            )

    print(file_name)
    print('finished')
# ####################不加embedding批处理################


# # ####################加embedding批处理################

# #     Code_Text_List = []
# #     Code_Text_Index_Dir = {}
# #     Code_Index = 0

# #     for new_funcInformationName in New_funcInformationDir:
# #         new_funcInformation = New_funcInformationDir[new_funcInformationName]
# #         new_funcName = new_funcInformation['Name']
# #         new_funcCode = new_funcInformation['Code']
# #         Code_Text_Index_Dir[new_funcName] = Code_Index
# #         Code_Index = Code_Index +1
# #         Code_Text_List.append(new_funcCode)
# #     embeddings = embedding_model.embed_documents(Code_Text_List)
    

# #     with driver.session() as session:
# #         for new_funcInformationName in New_funcInformationDir:
# #             new_funcInformation = New_funcInformationDir[new_funcInformationName]
# #             new_funcName = new_funcInformation['Name']
# #             new_funcType = new_funcInformation['Type']
# #             new_funcCode = new_funcInformation['Code']
# #             new_funcEmbedding = embeddings[Code_Text_Index_Dir[new_funcName]]
# #             session.run("CREATE (d:Entity_Class_Son {entityname: $entityname, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode, entitycodeembedding: $entitycodeembedding})",
# #                 entityname = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entitycodeembedding = new_funcEmbedding)
# #             session.run(
# #                 "MATCH (f:Entity_Class_Son {entityname: $entityname_from, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode, entitycodeembedding: $entitycodeembedding}), "
# #                 "(b:Entity_Class {entityname:$entityname_to}) "
# #                 "WITH f, b "
# #                 "CREATE (f)-[:__in_this_class__]->(b)",
# #                 entityname_from = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entitycodeembedding = new_funcEmbedding, entityname_to=file_name
# #             )

# #     print(file_name)
# #     print('finished')
# # ####################加embedding批处理################


# # ####################embedding逐一处理################
# #     with driver.session() as session:
# #         for new_funcInformationName in New_funcInformationDir:
# #             new_funcInformation = New_funcInformationDir[new_funcInformationName]
# #             new_funcName = new_funcInformation['Name']
# #             new_funcType = new_funcInformation['Type']
# #             new_funcCode = new_funcInformation['Code']
# #             ################加embedding################
# #             # embeddings = embedding_model.embed_documents(new_funcCode)
# #             # new_funcEmbedding = embeddings[0]
# #             # session.run("CREATE (d:Entity_Class_Son {entityname: $entityname, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode, entitycodeembedding: $entitycodeembedding})",
# #             #     entityname = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entitycodeembedding = new_funcEmbedding)
# #             # session.run(
# #             #     "MATCH (f:Entity_Class_Son {entityname: $entityname_from, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode, entitycodeembedding: $entitycodeembedding}), "
# #             #     "(b:Entity_Class {entityname:$entityname_to}) "
# #             #     "WITH f, b "
# #             #     "CREATE (f)-[:__in_this_class__]->(b)",
# #             #     entityname_from = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entitycodeembedding = new_funcEmbedding, entityname_to=file_name
# #             # )
# #             ################加embedding################

# #             ################不加embedding################
# #             session.run("CREATE (d:Entity_Class_Son {entityname: $entityname, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode})",
# #                 entityname = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode)
# #             session.run(
# #                 "MATCH (f:Entity_Class_Son {entityname: $entityname_from, entitytype: $entitytype, entityclass: $entityclass, entitycode: $entitycode}), "
# #                 "(b:Entity_Class {entityname:$entityname_to}) "
# #                 "WITH f, b "
# #                 "CREATE (f)-[:__in_this_class__]->(b)",
# #                 entityname_from = new_funcName, entitytype = new_funcType, entityclass = file_name, entitycode = new_funcCode, entityname_to=file_name
# #             )
# #             ################不加embedding################
# #             # print(new_funcEmbedding)

# # ####################embedding逐一处理################
