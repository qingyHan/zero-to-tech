"""第 1 课：最小应用——路由、自动文档、OpenAPI。

运行：cd 01_hello && uvicorn main:app --reload
验收：
    curl http://127.0.0.1:8000/            → {"Hello":"World"}
    curl http://127.0.0.1:8000/profile     → 站点资料 JSON
    curl -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/docs   → 200
自检：
    1. @app.get("/") 这行代码实际"注册"了什么？
    2. /docs 的接口列表是谁生成的？你写过一行文档吗？
"""
from fastapi import FastAPI

# 创建应用实例。title/description/version 会展示在 /docs 文档页上——
# 这些元数据同时构成 OpenAPI 规范的一部分（OpenAPI = 机器可读的接口描述标准）。
app = FastAPI(
    title="01 Hello FastAPI",
    description="第 1 课：最小应用。每个 @app.get 都是一次『路径 → 函数』的注册。",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """函数返回 dict/list/str 等 Python 对象，FastAPI 自动转成 JSON 并带上
    Content-Type: application/json 响应头——手搓版里 send_response、
    send_header、json.dumps、encode 四步在这里一步都不用写。"""
    return {"Hello": "World"}


@app.get("/profile")
def read_profile():
    return {"name": "zero-to-tech", "module": 4}


# 自检答案提示：
# 1. 注册了一条"GET / → read_root"的路由；FastAPI 启动时收集全部路由，
#    生成 OpenAPI JSON（/openapi.json），/docs 页面只是把这份 JSON 画了出来。
# 2. 自动生成的——来源是你写的类型声明和函数文档，你没写任何文档代码。
