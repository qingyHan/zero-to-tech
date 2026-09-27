"""第 3 课：请求体与 Pydantic 校验。

运行：cd 03_request_body && uvicorn main:app --reload
验收：
    curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" \
         -d '{"text": "今天的风很轻"}'                       → 200，返回分析结果
    curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" \
         -d '{"text": "ok", "author": {"email": "bad"}}'    → 422（嵌套校验失败）
    curl -X POST http://127.0.0.1:8000/feedback -F "comment=不错" -F "rating=5"  → 200（表单）
自检：
    1. 手搓版收 POST 要做哪四件事？Pydantic 帮你做了几件？
    2. Field(gt=0) 写在参数上还是模型字段上？
"""
from fastapi import FastAPI, Form
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="03 请求体与 Pydantic 校验")


class Author(BaseModel):
    """嵌套模型：模型里还能套模型，校验会逐层进行。"""

    name: str
    email: EmailStr  # 需要 email-validator 包；格式不对 → 422


class AnalyzeRequest(BaseModel):
    """请求体模型：字段 + 类型 + 约束声明一次，解析/校验/转换全自动。

    - text: 必填，长度 1-500（Field 约束，超界 → 422）；
    - score: 有默认值的字段变为可选，调用方不传就用默认；
    - tags: list[str] —— 列表类型同样自动校验。
    """

    text: str = Field(min_length=1, max_length=500, examples=["今天的风很轻"])
    author: Author
    score: float = Field(default=0.5, gt=0, le=1)  # gt/le：大于 0 且小于等于 1
    tags: list[str] = []


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """req 已经是校验过、转换好的 Pydantic 对象，属性直接用。

    手搓版收 POST 的四件事——手读 Content-Length、收字节、json.loads、
    逐字段检查——在这里一行都不存在。字段缺失/类型错/超界 → 422 带明细。
    """
    return {
        "text": req.text,
        "author": req.author.name,   # 嵌套对象照常点出来
        "score": req.score,
        "tags": req.tags,
    }


@app.post("/feedback")
def feedback(comment: str = Form(..., min_length=1), rating: int = Form(5)):
    """表单提交（-F / HTML <form>，格式为 application/x-www-form-urlencoded）。

    注意区分：`Field(...)` 用于请求体模型字段；标量参数用 `Form(...)`/`Query(...)`
    等声明——用错地方 FastAPI 启动时就直接报错。`Form(...)` 里的 `...`
    表示必填；约束写法与 Field 相同（如 min_length）。
    """
    return {"comment": comment, "rating": rating}
