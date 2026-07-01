import aiohttp
import asyncio
from typing import Any, Dict, Optional, Union


class HttpClient:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {
            "status": 0,
            "headers": {},
            "data": None,
            "message": None,
        }
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json,
            ) as response:
                result["status"] = response.status
                result["headers"] = dict(response.headers)

                if response.status != 200:
                    response_data = await response.text()
                    raise Exception(
                        f"请求失败: {response.status}, 响应内容: {response_data}"
                    )
                if json:
                    response_data = await response.json()
                else:
                    response_data = await response.text()
                result["data"] = response_data
        except aiohttp.ClientError as e:
            error_message = f"aiohttp 客户端错误: {e}"
            print(error_message)
            result["message"] = error_message
            result["status"] = 500
        except asyncio.TimeoutError as e:
            error_message = f"请求超时: {e}"
            print(error_message)
            result["message"] = error_message
            result["status"] = 504
        except Exception as e:
            error_message = f"其他错误: {e}"
            print(error_message)
            result["message"] = error_message
            result["status"] = 500
        return result
