"""第 6 课：异常处理、中间件与 CORS。

运行：cd 06_errors && uvicorn main:app --reload
验收：
    curl -i http://127.0.0.1:8000/divide/10/0     → 400 + {"detail": "除数不能为 0"}
    curl -i http://127.0.0.1:8000/divide/10/2     → 5.0，响应头 X-Process-Time
    curl -i -H "Origin: http://localhost:5173" \
         http://127.0.0.1:8000/divide/10/2        → 响应头有 access-control-allow-origin
自检：
    1. HTTPException(400) 和裸 raise Exception 在客户端眼里差在哪？
    2. CORS 中间件解决的是浏览器还是服务器的问题？
"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="06 异常、中间件与 CORS")


# ---- 1. 业务异常与处理器：让"业务错误"有统一的 JSON 形态 ----

class DivideByZeroError(Exception):
    """自定义业务异常：携带对客户端有意义的上下文。"""

    def __init__(self, dividend: float):
        self.dividend = dividend


@app.exception_handler(DivideByZeroError)
def divide_handler(request: Request, exc: DivideByZeroError):
    """注册后，任何路由里 raise DivideByZeroError 都会变成这个 JSON 响应——
    业务代码只管 raise，错误→响应的翻译集中在一处。"""
    return JSONResponse(
        status_code=400,
        content={"detail": f"除数不能为 0（你尝试计算 {exc.dividend}/0）"},
    )


@app.get("/divide/{a}/{b}")
def divide(a: float, b: float):
    if b == 0:
        raise DivideByZeroError(a)  # 业务代码只管抛
    return {"result": a / b}


# ---- 2. 中间件：包住所有请求的"外层洋葱" ----

@app.middleware("http")
async def add_timing(request: Request, call_next):
    """每个 HTTP 请求都先经过这里：前半段在路由前，call_next 后在响应后。
    典型用途：计时、请求 ID、全局日志。"""
    start = time.perf_counter()
    response = await call_next(request)
    cost = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{cost:.1f}ms"
    return response


# ---- 3. CORS：浏览器的同源策略要求服务器"明确允许"跨域调用 ----

app.add_middleware(
    CORSMiddleware,
    # 5.5 课件的主角：前端(5173)调后端(8000)是跨域，后端必须声明允许
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# 验证方法：带 Origin 头的请求，响应里出现 access-control-allow-origin。
# 注意：CORS 是浏览器的安全机制——curl 没有"源"概念，永远不会被拦。
