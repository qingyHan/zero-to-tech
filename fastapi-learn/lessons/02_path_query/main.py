"""第 2 课：路径参数与查询参数——类型声明即校验。

运行：cd 02_path_query && uvicorn main:app --reload
验收：
    curl "http://127.0.0.1:8000/items/5?q=hello"       → {"item_id":5,"q":"hello"}
    curl http://127.0.0.1:8000/items/abc               → 422（int 解析失败）
    curl "http://127.0.0.1:8000/search?keyword=风&page=2&with_pinyin=true"
    curl http://127.0.0.1:8000/models/resnet           → 枚举合法值
    curl http://127.0.0.1:8000/models/xxx              → 422（不在枚举内）
自检：
    1. /items/abc 的 422 是谁产生的？你写过一行校验代码吗？
    2. 查询参数 q 不传时是什么？怎么声明"可传可不传"？
"""
from enum import Enum

from fastapi import FastAPI

app = FastAPI(title="02 路径参数与查询参数")


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    """路径参数 {item_id} + 查询参数 q。

    - item_id: int —— 类型声明让 FastAPI 自动把 "5" 转成整数 5；
      转不了（/items/abc）直接 422，错误信息精确到 'path -> item_id'；
    - q: str | None = None —— 查询参数（URL ? 后面），可传可不传。
    区分规则：**路径里出现的占位符是路径参数，函数签名里其余带默认值的是查询参数**。
    """
    return {"item_id": item_id, "q": q}


@app.get("/search")
def search(keyword: str, page: int = 1, with_pinyin: bool = False):
    """多查询参数：keyword 必填（无默认值），page/with_pinyin 有默认值可省略。

    类型转换全自动：page=2 接到的是整数 2；with_pinyin=true 接到的是布尔 True
    （1/yes/on/true 都认）。缺必填的 keyword → 422。
    """
    return {"keyword": keyword, "page": page, "with_pinyin": with_pinyin}


class ModelName(str, Enum):
    """继承 str 的枚举：文档页会生成下拉框，非法值直接 422。"""

    resnet = "resnet"
    bert = "bert"


@app.get("/models/{model_name}")
def read_model(model_name: ModelName):
    """枚举路径参数：/models/resnet 合法，/models/xxx → 422。
    model_name.value 拿到纯字符串 'resnet'。"""
    return {"model": model_name, "value": model_name.value}
