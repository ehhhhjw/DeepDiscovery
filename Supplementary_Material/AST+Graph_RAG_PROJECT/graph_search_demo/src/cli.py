import sys
import os
import json
import argparse
import asyncio
from graph_models import (
    ast_graph_transform,
    export_graph_to_neo4j,
    get_community_report,
    get_new_community_report,
    get_global_search_community,
)
from index import (
    create_embeddings,
    create_question_answer_create_embeddings,
    create_tech_doc_embeddings,
)
from query import GlobalSearch
from tasks_plan.transform_prd_tasks import writePRD
from utils.stdout import DualOutput
from constants import EmbeddingType, LOG_DIR_PATH, formatted_datetime
from query.local_search import local_search
from utils.args import ChatArgs
from utils import write_text_to_log, read_json_file, save_json_to_file
from utils.request import HttpClient
from utils.utils import get_base_params


async def create_knowledge_graph(args):
    ast_graph_transform(
        data_path=args.ast_data_path,
        graph_save_path=args.graph_save_path,
        community_save_path=args.community_map_save_path,
        max_cluster_size=args.max_cluster_size,
    )

    # # 社区报告不在这里生成，而是使用新生成的社区
    # await get_community_report(
    #     data_path=args.ast_data_path,
    #     graph_path=args.graph_save_path,
    #     community_path=args.community_map_save_path,
    #     save_path=args.community_reports_save_path,
    #     concurrent_num=args.concurrent_num,
    # )

    # 注释掉，目前不生成社区报告
    # 此处为生成新的社区报告 Todo 还未合入到脚本中，args还需要补充all_bundle的路径
    # await get_new_community_report(
    #     data_path=args.ast_data_path,
    #     graph_path=args.graph_save_path,
    #     community_path=args.community_map_save_path,
    #     save_path=args.community_reports_save_path,
    #     edge_power_graph_save_path=args.edge_power_graph_save_path,
    #     concurrent_num=args.concurrent_num,
    # )


async def chat_bot_task(args):
    prd, requirement_list = writePRD(
        args.prd_ui_draft_path, args.prd_business_logic_path
    )

    print(prd + "\n")

    for item in requirement_list:
        print("\n\n\n\n <<<<<<<<<<<<<<<<<<<<<<<开始处理下一个问题 " + item)
        await chat_bot_core(args, item)
        print(
            "\n 处理完成 "
            + item
            + "  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n\n\n\n "
        )
        print()


async def chat_bot_test(args):
    test_items = [
        "我想开发一个页面，页面中间有个列表，列表下方有个按钮，点击按钮发服务请求",
        "如何获取我当下的经纬度",
        "点击按钮，获取我当下的经纬度，弹框显示",
        "我需要一个按钮组件，颜色为蓝色，尺寸为大",
        "我想在页面上方加一个导航栏，点击返回页面",
        "如何实现带参数的返回页面",
        "我希望能够实现点击按钮跳转登录的操作",
        "如何监听当前网络环境，如果断网弹出错误提示",
        "通过逆地理获取我所在的poi名称",
        "在地图画一个区域",
        "在地图画一个扎点",
        "如何监听页面的pageshow事件",
        "页面pageshow事件支持哪些数据格式返回",
        "点击按钮调起分享面板",
        "实现一个展示列表，每一个列表项有个用户头像以及名字",
        "写一个搜索框，点击能够将搜索结果展示在下方列表里",
        "用轮播组件实现一个图片轮播效果，数据从服务请求",
        "实现一个评论列表，每个评论支持回复和点赞",
        "页面底部有一个tabBar，有3个选项，分别是首页、打车、个人中心，点击跳转到对应页面",
        "acorn里有城市选择器组件吗？要可以选择拼音到城市",
        "我希望能够实现点击按钮跳转一键登录的操作",
        "在fox页面如何监听页面的pageshow事件 ",
        "我想开发一个页面，页面中间有个列表，列表下方有个按钮，点击按钮发网络服务请求",
        "实现1个页面，进入页面获取定位，定位在北京弹窗提示",
    ]
    for item in test_items:
        print("\n\n\n\n <<<<<<<<<<<<<<<<<<<<<<<开始处理下一个问题 " + item)
        await chat_bot_core(args, item)
        print(
            "\n 处理完成 "
            + item
            + "  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n\n\n\n "
        )
        print()


async def chat_bot(args):
    user_question = input(
        "Hi~ 我是 AJX 全能专家, 你可以问我跟 AJX 相关的任何问题:\n"
    )

    if not user_question.strip():
        print(f"\n用户提问: 不能为空 \n\n")
        return

    await chat_bot_core(args, user_question)


async def chat_bot_core(args, user_question):
    # formatted_datetime 用与后续处理结果时读取日志的标识
    print(f"\n用户提问: {user_question} \n\n> start_time: {formatted_datetime}")

    if args.global_search:
        graph_rag = GlobalSearch(
            query=user_question,
            community_path=args.community_path,
            concurrent_num=args.concurrent_num,
        )

        final_prompt, result = await graph_rag.get_context()
    else:
        final_prompt, chunks = await local_search(
            args=args, user_question=user_question
        )
        result = ""
        for chunk in chunks:
            result += chunk
            sys.stdout.write(chunk)
            sys.stdout.flush()

    output_str = f"""{final_prompt}\n\n\n
******************************************************  LLM  结果 **********************************************************\n\n\n
{result}"""
    write_text_to_log(output_str, "chat.txt")
    # 保存结构化结果日志数据
    output_json_path = LOG_DIR_PATH / f"output.json"
    if output_json_path.is_file():
        output_json = read_json_file(output_json_path) or {}
        output_json["prompt"] = final_prompt
        output_json["chat"] = result
        save_json_to_file(output_json, output_json_path, args.search_res_fields)
    docs_output_json_path = LOG_DIR_PATH / f"docs_output.json"
    if docs_output_json_path.is_file():
        output_json = read_json_file(docs_output_json_path) or {}
        output_json["prompt"] = final_prompt
        output_json["chat"] = result
        save_json_to_file(
            output_json, docs_output_json_path, args.search_res_fields
        )


async def doc_rag_without_chat(args):
    user_question = input(
        "Hi~ 我是 AJX 全能专家, 你可以问我跟 AJX 相关的任何问题:\n"
    )

    # test
    # user_question = "帮我写一个按钮，点击按钮打开一个底部弹出框，点击遮罩可以关闭弹出框，弹出框内是引用自textBox.jsx的名为textBox的组件"

    if not user_question.strip():
        print(f"\n用户提问: 不能为空 \n\n")
        return

    params = {"user_question": user_question, **dict(args._get_kwargs())}
    url = os.environ.get(
        "http_rag_search_url",
        "http://127.0.0.1:5001/v1/local/doc_rag_without_chat",
    )
    async with HttpClient() as client:
        response = await client.request(method="POST", url=url, json=params)
        if response["data"]:
            data = response["data"]
            formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
            print(f"response : {formatted_json}")
        else:
            print(f"response error: {response}")


async def main(args):
    DualOutput.open()
    if args.create_kg:
        await create_knowledge_graph(args)

    elif args.export_to_neo4j:
        export_graph_to_neo4j(graph_path=args.graph_path)

    elif args.index:
        # create_question_answer_create_embeddings(
        #     save_path=args.db_path,
        # )
        create_embeddings(
            graph_path=args.graph_path,
            save_path=args.db_path,
            graph_type=EmbeddingType.CODE,
        )
        create_embeddings(
            graph_path=args.commit_data_path,
            save_path=args.db_path,
            graph_type=EmbeddingType.COMMIT,
        )
        # create_tech_doc_embeddings(
        #     tech_doc_path=args.tech_doc_path,
        #     save_path=args.db_path,
        # )

    elif args.index_docs:
        if not args.docs_graph_path:
            raise Exception(f"docs_graph_path不能为空")
        create_embeddings(
            graph_path=args.docs_graph_path,
            save_path=args.db_path,
            graph_type=EmbeddingType.DOCS,
        )

    elif args.chat:
        await chat_bot(ChatArgs(**dict(args._get_kwargs())))

        # test
        # await chat_bot_test(ChatArgs(**dict(args._get_kwargs())))

        # prd
        # await chat_bot_task(ChatArgs(**dict(args._get_kwargs())))
    elif args.get_global_report:
        await get_global_search_community(
            args.graph_path,
            args.community_reports_save_path,
            args.community_path,
            args.concurrent_num,
        )
    elif (not args.chat) and args.is_use_docs and not args.is_use_code:
        await doc_rag_without_chat(args)

    DualOutput.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="parameters for graph search demo"
    )
    parser.add_argument(
        "--create_kg",
        action="store_true",
        help="create knowledge graph from ast",
    )
    parser.add_argument(
        "--ast_data_path",
        type=str,
        help="ast data file path",
    )
    parser.add_argument(
        "--commit_data_path",
        type=str,
        required=False,
        help="commit data file path",
    )
    parser.add_argument(
        "--graph_save_path",
        type=str,
        help="graph save path",
    )
    parser.add_argument(
        "--community_map_save_path",
        type=str,
        help="community map save path",
    )
    parser.add_argument(
        "--community_reports_save_path",
        type=str,
        help="community reports save path",
    )
    parser.add_argument(
        "--max_cluster_size",
        default=50,
        type=int,
        help="max cluster size for leiden algorithm",
    )
    parser.add_argument(
        "--concurrent_num",
        default=5,
        type=int,
        help="concurrent number to send llm requests",
    )

    parser.add_argument(
        "--export_to_neo4j",
        action="store_true",
        help="export graph and community structure to neo4j",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="create embedding and save to vector db",
    )
    parser.add_argument(
        "--index_docs",
        action="store_true",
        help="create embedding and save to vector db",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="perform user chat to test graph search",
    )
    parser.add_argument(
        "--is_class_use_code",
        action="store_true",
        help="whether add class entity code or not",
    )
    parser.add_argument(
        "--global_search",
        action="store_true",
        help="perform global search",
    )
    parser.add_argument(
        "--graph_path",
        type=str,
        help="graph file path",
    )
    parser.add_argument(
        "--db_path",
        type=str,
        help="vector db path",
    )
    parser.add_argument(
        "--community_path",
        type=str,
        help="community report path",
    )
    parser.add_argument(
        "--top_k", default=60, type=int, help="top-k for embedding search"
    )
    parser.add_argument(
        "--open_rerank",
        action="store_true",
        help="开启最终的 entity rerank",
    )
    parser.add_argument(
        "--open_query_split",
        action="store_true",
        help="是否开启问题拆解检索，默认关闭",
    )

    parser.add_argument(
        "--is_use_docs",
        action="store_true",
        help="whether use docs or not",
    )
    parser.add_argument(
        "--is_use_code",
        action="store_true",
        help="whether use code or not",
    )
    parser.add_argument(
        "--is_use_qa",
        action="store_true",
        help="whether use QA or not",
    )
    parser.add_argument(
        "--is_use_tech_doc",
        action="store_true",
        help="whether use tech_doc or not",
    )
    parser.add_argument(
        "--docs_graph_path",
        type=str,
        help="graph file path",
    )
    parser.add_argument(
        "--docs_community_path",
        type=str,
        help="community report path",
    )
    parser.add_argument(
        "--get_global_report",
        action="store_true",
        help="get global community report",
    )
    parser.add_argument(
        "--tech_doc_path",
        default="../examples/tech_doc/tech_doc_0913.json",
        type=str,
        help="the path of tech doc information",
    )
    # 最终要结构化的字段，方便数据分析
    parser.add_argument(
        "--search_res_fields",
        default="",
        type=str,
        help="fields for search result",
    )

    # test 字段
    # 手动传入子问题
    parser.add_argument(
        "--sub_querys",
        default="",
        type=str,
        help="sub query list for user question",
    )
    # 执行的具体阶段。可以选择执行到 rag 或 rerank 阶段停止
    parser.add_argument(
        "--stage",
        default="",
        type=str,
        required=False,
        choices=["rag", "rerank"],
        help="stage for chat script",
    )

    # prd
    parser.add_argument(
        "--prd_ui_draft_path",
        type=str,
        help="prd ui path",
    )
    parser.add_argument(
        "--prd_business_logic_path",
        type=str,
        help="prd business logic path",
    )
    parser.add_argument(
        "--edge_power_graph_save_path",
        default="",
        type=str,
        help="the save path of the edge power graph",
    )
    args = parser.parse_args()
    asyncio.run(main(args=args))
