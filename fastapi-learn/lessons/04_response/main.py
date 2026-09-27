"""第 4 课：响应控制——response_model、状态码、自定义响应。

运行：cd 04_response && uvicorn main:app --reload
验收：
    curl http://127.0.0.1:8000/users/1        → 返回里没有 password_hash（被过滤）
    curl -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8000/users \
         -H "Content-Type: application/json" -d '{"username":"alice","password":"x"}'  → 201
    curl -i http://127.0.0.1:8000/custom      → 看自定义响应头 X-Custom
    curl -o /dev/null -w '%{http_code} %{redirect_url}' http://127.0.0.1:8000/old  → 301 跳转
自检：
    1. response_model 过滤的是"输出"，和请求体校验（管"输入"）是什么关系？
    2. 什么场景必须返回 JSONResponse 而不是 dict？
"""
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="04 响应控制")

# 模拟数据库里的记录：内部字段比对外字段多（比如密码哈希绝不能出去）
_user_db = {
    "username": "alice",
    "email": "alice@example.com",
    "password_hash": "secret-hash-should-never-leak",
    "is_admin": False,
}


class UserOut(BaseModel):
    """对外的用户模型：只有允许公开的字段。"""

    username: str
    email: str


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    """response_model = 输出的"过滤器"：函数里随便返回内部完整对象，
    出门时按 UserOut 只保留声明的字段——password_hash 被自动剥掉。

    这是"输入靠请求体校验、输出靠 response_model 收口"的对称设计。"""
    return _user_db


class UserCreate(BaseModel):
    username: str
    password: str


@app.post("/users", status_code=201)
def create_user(req: UserCreate):
    """status_code=201（Created）：REST 语义里"创建成功"的标准码。
    正常返回 dict 即可，FastAPI 用声明的 201 作为状态行。"""
    return {"username": req.username, "id": 42}


@app.get("/custom")
def custom_header(response: Response):
    """把 Response 作为参数声明（不返回它），可以附加响应头/Cookie，
    同时照常返回 dict——FastAPI 会把两者合并成一个响应。"""
    response.headers["X-Custom"] = "fastapi-learn"
    response.set_cookie("last_visit", "today", max_age=3600)
    return {"ok": True}


@app.get("/raw")
def raw_json():
    """需要完全掌控时直接返回 JSONResponse：自带状态码/头/体。
    常见场景：返回非默认编码、流式内容、或第三方网关要求的特殊头。"""
    return JSONResponse(
        status_code=200,
        headers={"X-Powered-By": "fastapi-learn"},
        content={"message": "我完全掌控了这个响应"},
    )


@app.get("/old")
def old_page():
    """RedirectResponse：配合 3xx 语义做跳转，浏览器自动跟到新地址。"""
    return RedirectResponse(url="/users/1", status_code=301)
