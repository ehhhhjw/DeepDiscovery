# 流式输出
async def stream_output(chain, prompt_input):
    res = None
    # print(prompt_input)
    async for chunk in chain.astream(prompt_input):
        res = chunk
    return res
