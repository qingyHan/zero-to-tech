"""第 10 课：测试——TestClient 不起服务器、不开端口，直接进程内调用接口。

运行：cd 10_testing && pytest -v

三个要点：
  1. TestClient(httpx) 进程内调用：比 curl 快、可断言、可塞测试数据；
  2. 依赖覆盖 app.dependency_overrides：把"要登录"的依赖换成假实现，
     业务代码一行不改——这正是第 5 课依赖注入在测试里的回报；
  3. 每个用例前清空状态：测试互不影响，谁先谁后都能过。
"""
import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """autouse 夹具：每个用例运行前自动清空内存库，保证用例独立。"""
    main._memos.clear()
    main._next_id = 1


@pytest.fixture
def authorized_client():
    """覆盖认证依赖：让受保护接口以为"已登录 alice"。"""
    def fake_user() -> str:
        return "alice"

    app.dependency_overrides[main.get_current_user] = fake_user
    yield client
    app.dependency_overrides.clear()  # 用例结束拆掉覆盖，避免影响其他测试文件


def test_未登录时创建返回_401():
    assert client.post("/memos", json={"title": "x"}).status_code == 401


def test_创建备忘录_201(authorized_client):
    resp = authorized_client.post("/memos", json={"title": "学完 FastAPI"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "学完 FastAPI"
    assert body["owner"] == "alice"
    assert body["id"] == 1


def test_查询不存在的备忘录_404(authorized_client):
    resp = authorized_client.get("/memos/999")
    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


def test_标题为空字符串仍可创建_因为模型只要求有值(authorized_client):
    resp = authorized_client.post("/memos", json={"title": ""})
    assert resp.status_code == 201  # 想拒绝空标题？去 main.py 的模型加 min_length=1
