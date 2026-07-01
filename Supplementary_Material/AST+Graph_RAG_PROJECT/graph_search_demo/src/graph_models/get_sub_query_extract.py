from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.model_config import chat_model
from prompts.sub_query_extract import sub_query_extract_prompt


async def get_sub_query_extract(user_question):
    try:
        prompt_template = ChatPromptTemplate.from_messages(
            [("user", sub_query_extract_prompt)]
        )
        parser = StrOutputParser()
        chain = prompt_template | chat_model | parser
        chunks = chain.stream({"input_text": user_question})
        result = ""
        for chunk in chunks:
            result += chunk
        sub_questions = []
        records = [r.strip() for r in result.split("##")]
        for record in records:
            # 截取第一个 "node" 之前的无效字符
            index = record.find("<|>")
            if index != -1:
                record = record[index:]
            record_list = record.split("<|>")
            if len(record_list) >= 2:
                sub_questions.append(record_list[1])
        return sub_questions
    except Exception as e:
        print(e)
        return []
