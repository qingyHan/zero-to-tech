"""第 9 课：项目拆分——APIRouter、配置与 lifespan。

运行：cd 09_router_structure && uvicorn main:app --reload
验收：
    curl http://127.0.0.1:8000/api/users          → 用户列表（前缀 /api/users 自动拼好）
    curl http://127.0.0.1:8000/api/items?page=1   → 物品列表（分页依赖来自 deps.py）
    curl http://127.0.0.1:8000/health             → {"app": ..., "debug": ...}（读自环境变量）
自检：
    1. 单文件长到几百行后，第 9 课的拆法把什么和什么分开了？
    2. prefix="/api/users" 写在 include_router 里和写在 APIRouter 里有什么区别？
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings           # pydantic-settings：配置集中一处，来自环境变量
from routers import items, users


# ---- lifespan：应用启动/关闭的钩子（替代已弃用的 on_event） ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    # yield 之前 = 启动时：放"连数据库、预热缓存"这类一次性工作
    print(f"[启动] {settings.app_name} (debug={settings.debug})")
    yield
    # yield 之后 = 关闭时：放"断开连接、清临时文件"
    print("[关闭] 清理完成")


# debug=True 时 /docs 可用，生产关掉——配置驱动行为，不改代码
app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

# include_router：把拆出去的模块挂回主应用；prefix/tags 在这里统一给
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(items.router, prefix="/api/items", tags=["物品"])


@app.get("/health")
def health():
    """配置的使用示例：同一份代码，靠环境变量改变行为。"""
    return {"app": settings.app_name, "debug": settings.debug}
