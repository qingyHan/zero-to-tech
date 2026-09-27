"""第 10 课：被测应用——TestClient 可以不起服务器直接测它。

运行（先测后跑都行）：
    cd 10_testing
    pytest -v            # 跑 test_main.py 的全部用例
    uvicorn main:app --reload

本课应用：一个极简备忘录 API + 一个"需要登录"的接口，
专门演示测试的两件大事：正常功能断言、依赖覆盖绕开认证。
"""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="10 备忘录 API（被测应用）")

_memos: dict[int, dict] = {}
_next_id = 1


def get_current_user() -> str:
    """模拟的认证依赖：测试时会用依赖覆盖把它换成假用户（不真做认证）。"""
    raise HTTPException(status_code=401, detail="未登录（测试中会被覆盖掉）")


class MemoIn(BaseModel):
    title: str


@app.post("/memos", status_code=201)
def create_memo(req: MemoIn, user: str = Depends(get_current_user)):
    global _next_id
    memo = {"id": _next_id, "title": req.title, "owner": user}
    _memos[_next_id] = memo
    _next_id += 1
    return memo


@app.get("/memos/{memo_id}")
def get_memo(memo_id: int, user: str = Depends(get_current_user)):
    if memo_id not in _memos:
        raise HTTPException(status_code=404, detail="备忘录不存在")
    return _memos[memo_id]
