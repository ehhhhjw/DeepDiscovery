import re
import json
def get_attributes(extracted_data):
    node_tag = '"node'
    import_tag = '"import'
    file_comment_tag = '"filecomment'
    # 模型有些没按结构返回，特殊处理
    if node_tag not in extracted_data:
        if '`node`' in extracted_data:
            node_tag = '`node`'
    if import_tag not in extracted_data:
        if '`import`' in extracted_data:
            import_tag = '`import`'
    if file_comment_tag not in extracted_data:
        if '`filecomment`' in extracted_data:
            file_comment_tag = '`filecomment`'
    # 截取第一个 "node" 之前的无效字符
    index = extracted_data.find(node_tag)
    if index != -1:
        extracted_data = extracted_data[index:]
    records = [r.strip() for r in extracted_data.split('##')]
    result = {}
    file_comment = {}
    for record in records:
        record_index = record.find(node_tag)
        if record_index != -1:
            record = record[record_index:]
        record = re.sub(r"^\(|\)$", "", record.strip())
        record_attributes = record.split('<|>')
        if record_attributes[0].startswith(node_tag) and len(record_attributes) >= 6:
            result[record_attributes[1].strip()] = {
                "Report": record_attributes[2],
                "ShortReport": record_attributes[3],
                "RelatedScore": record_attributes[4],
                "ScoreReason": record_attributes[5],
                "EdgeType": "Children"
            }
        if record_attributes[0].startswith(import_tag) and len(record_attributes) >= 5:
            result[record_attributes[1].strip()] = {
                "RelationDescription": record_attributes[2],
                "RelatedScore": record_attributes[3],
                "ScoreReason": record_attributes[4],
                "EdgeType": "Dependent"
            }
        if record_attributes[0].startswith(file_comment_tag) and len(record_attributes) >= 3:
            file_comment[record_attributes[1].strip()] = {
                "FileComment": record_attributes[2]
            }

    return result, file_comment
