"""第 5 课：依赖注入 Depends——FastAPI 的灵魂。

运行：cd 05_di && uvicorn main:app --reload
验收：
    curl "http://127.0.0.1:8000/todos?page=2&size=5"      → 分页元信息由依赖提供
    curl "http://127.0.0.1:8000/todos"                    → 不传参数也能跑（默认值）
    curl -i  http://127.0.0.1:8000/timed                  → 响应头里有 X-Process-Time（yield 依赖的后处理）
自检：
    1. 分页需求如果散在 10 个接口里，改上限时要改几处？用依赖呢？
    2. yield 依赖里 yield 之后的代码什么时候执行？
"""
import time

from fastapi import Depends, FastAPI

app = FastAPI(title="05 依赖注入 Depends")


# ---- 1. 把"一组可复用的参数"做成依赖 ----

class Pagination:
    """分页参数包：任何接口声明 `p: Pagination = Depends()` 即可拥有
    page/size 两个查询参数（含默认值与上限钳制）。

    好处：分页规则改一处（比如 size 上限从 50 改 100），10 个接口同时生效。"""

    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(page, 1)
        self.size = min(size, 50)
        self.offset = (self.page - 1) * self.size


# ---- 2. yield 依赖：函数的前半段是"请求前"，yield 之后是"响应后" ----

def timed_request():
    start = time.perf_counter()
    yield  # ← 请求处理发生在这里
    cost_ms = (time.perf_counter() - start) * 1000
    print(f"[计时] 本次请求耗时 {cost_ms:.1f}ms")  # 也可写进响应头/日志


def fake_search(page: Pagination = Depends()):
    """依赖套依赖：这个依赖自己也声明了 Pagination 依赖——链条自动解析。"""
    return {
        "page": page.page,
        "size": page.size,
        "offset": page.offset,
        "items": [f"todo-{i + page.offset}" for i in range(1, page.size + 1)],
    }


@app.get("/todos")
def list_todos(result: dict = Depends(fake_search)):
    """接口只声明"我需要什么"（Depends），不关心它怎么构造——
    这就是依赖注入：构造逻辑与业务逻辑解耦，测试时还能整体替换（第 10 课）。"""
    return result


@app.get("/timed", dependencies=[Depends(timed_request)])
def timed():
    """dependencies=[...] 写法：只需要依赖的"副作用"（计时/鉴权/限流），
    不需要它的返回值。多个接口共用一行声明。"""
    return {"message": "看看服务端控制台的 [计时] 日志"}
