"""第 8 课：async/await、后台任务与完整 CRUD。

运行：cd 08_async_db && uvicorn main:app --reload
验收：
    curl -X POST http://127.0.0.1:8000/todos -H "Content-Type: application/json" \
         -d '{"title": "学完 FastAPI"}'                          → 201，返回带 id 的对象
    curl http://127.0.0.1:8000/todos?done=false                  → 列表（可按状态过滤）
    curl http://127.0.0.1:8000/todos/1                           → 单个；不存在的 id → 404
    curl -X PUT http://127.0.0.1:8000/todos/1 -H "Content-Type: application/json" \
         -d '{"title": "学完 FastAPI", "done": true}'            → 更新
    curl -X DELETE http://127.0.0.1:8000/todos/1                 → 204
    curl -X POST http://127.0.0.1:8000/todos/2/finish            → 201；响应已回，服务端还在"发通知"
自检：
    1. 什么时候该写 async def？全是同步 CPU 计算时写 async 有收益吗？
    2. 204 和 200 的区别？DELETE 为什么常用 204？
"""
import asyncio

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="08 异步、后台任务与 CRUD")

# 内存"数据库"：进程重启即清空。真实项目换成 SQLAlchemy/数据库，路由层写法几乎不变
_todos: dict[int, dict] = {}
_next_id = 1


class TodoIn(BaseModel):
    title: str = Field(min_length=1)


class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


@app.post("/todos", status_code=201)
def create_todo(req: TodoIn):
    global _next_id
    todo = {"id": _next_id, "title": req.title, "done": False}
    _todos[_next_id] = todo
    _next_id += 1
    return todo


@app.get("/todos")
def list_todos(done: bool | None = None):
    """查询参数 done 可选：传了就过滤，不传返回全部。"""
    items = list(_todos.values())
    if done is not None:
        items = [t for t in items if t["done"] == done]
    return items


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} 不存在")
    return _todos[todo_id]


@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, req: TodoUpdate):
    """部分更新：只改调用方传了的字段（None 表示"没传"）。"""
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} 不存在")
    todo = _todos[todo_id]
    if req.title is not None:
        todo["title"] = req.title
    if req.done is not None:
        todo["done"] = req.done
    return todo


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """204 No Content：删除成功但没有 body 可回——用 204 就不该再写响应体。"""
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} 不存在")
    del _todos[todo_id]


# ---- 后台任务：响应先回，杂活后台干 ----

def _send_notification(todo_id: int):
    """模拟耗时通知（写日志/发消息/发邮件）。真实场景换 SMTP/消息队列。"""
    print(f"[后台] todo {todo_id} 已完成，通知已发送")


@app.post("/todos/{todo_id}/finish", status_code=201)
async def finish_todo(todo_id: int, background: BackgroundTasks):
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail=f"todo {todo_id} 不存在")
    _todos[todo_id]["done"] = True
    # 加入后台任务队列：等响应发完才执行，调用方不等通知写完
    background.add_task(_send_notification, todo_id)
    return _todos[todo_id]


# ---- async def：什么时候写 ----

@app.get("/slow")
async def slow():
    """async def 的适用场景是**等待**（网络请求、数据库 IO）：
    等待时让出事件循环，其他请求不被卡住。注意：await 后面必须是
    真正的异步调用；在 async def 里跑纯 CPU 大计算反而会卡住整个循环。"""
    await asyncio.sleep(1)  # 模拟一次 1 秒的外部调用
    return {"message": "等了 1 秒，但期间服务还能响应其他请求"}
