import os


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
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(content)

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


if __name__ == "__main__":
    Note_Fold_Path = '/path/to/project/result_state_note/result_state_new'  # 替换为您的文件夹路径
    Description_Fold_Path='/path/to/project/Output/result_state_description'

    all_files = list_files_recursively(Note_Fold_Path)


    for file_path_son in all_files:
        file_name=''
        suffix=''
        if '/' in file_path_son:
            file_name = file_path_son.split('/')[-1]
            if '.' in file_path_son:
                suffix = file_path_son.split('.')[-1]
                if suffix != 'txt':
                    continue
                else:
                    output_file_path=Description_Fold_Path+'/'+file_name
                    class_name=get_file_name_without_extension(file_path_son)
                    description_message=find_description(file_path_son,'@class ')


                    print(class_name,description_message)
                    # Output_Description_Fold_Path=Description_Fold_Path+"/"+file_name
                    # write_string_to_file(Output_Description_Fold_Path,description_message)
                    # print(file_path_son)
                    # print(description_message)
                    # print('\n')


        # if os.path.exists(file_path):
        #     description = find_description(file_path)
        #     if description:
        #         print(f"ExampleAgentConfig: {description}")
        #     else:
        #         print(f"未找到@description信息")
        # else:
        #     print(f"文件 {file_name} 不存在于目录 {folder_path} 中")
    
