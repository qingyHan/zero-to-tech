# fastapi-learn —— FastAPI 独立学习课程

> 目标：**彻底掌握 FastAPI**。10 课递进，每课一个可独立运行的 `main.py`，带"运行 / 验收 / 自检"。所有注释都在解释**框架替你干了什么、为什么这样设计**——不只是 API 用法。

## 学习路线图

| 课 | 主题 | 掌握目标（自检标准） |
| --- | --- | --- |
| [01](./lessons/01_hello) | 最小应用与自动文档 | 能解释 `@app.get` 注册了什么、/docs 从哪来 |
| [02](./lessons/02_path_query) | 路径参数与查询参数 | 类型声明出错自动 422；枚举限定合法值 |
| [03](./lessons/03_request_body) | 请求体与 Pydantic 校验 | 嵌套模型、Field 约束、EmailStr；缺字段/超界回 422 |
| [04](./lessons/04_response) | 响应控制 | response_model 过滤字段、自定义状态码/响应头/JSONResponse |
| [05](./lessons/05_di) | 依赖注入 Depends（灵魂） | 分页参数复用、yield 前后处理、依赖覆盖 |
| [06](./lessons/06_errors) | 异常、中间件与 CORS | HTTPException、自定义异常处理器、请求计时、跨域配置 |
| [07](./lessons/07_auth) | OAuth2 + JWT 认证 | /token 签发令牌、受保护路由、401 语义 |
| [08](./lessons/08_async_db) | async、后台任务与 CRUD | async def 适用场景、BackgroundTasks、完整增删改查 |
| [09](./lessons/09_router_structure) | 项目拆分与配置 | APIRouter 拆多文件、prefix/tags、lifespan、pydantic-settings |
| [10](./lessons/10_testing) | 测试（TestClient + pytest） | 不起服务器测接口、依赖覆盖造假数据 |

## 快速开始

```bash
cd fastapi-learn
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # 或国内镜像: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

cd lessons/01_hello
uvicorn main:app --reload            # 每课在自己的目录里运行
```

每课都是**独立应用**（互不依赖），端口可自定：`uvicorn main:app --reload --port 8001`。

## 学习方法

1. 先读该课 `main.py` 的注释，再跑起来用 curl/`/docs` 打一遍"验收"里的每一条；
2. 故意制造错误（类型错、缺字段、带错令牌），**看 422/401 的报错长什么样**——排障时你靠的就是这些报错；
3. 每课结尾有"自检"问题，能口头回答再进入下一课；
4. 学完进阶读官方教程（中文）：<https://fastapi.tiangolo.com/zh/tutorial/>

## 依赖说明

见 [requirements.txt](./requirements.txt)。其中 `pyjwt`（第 7 课签发令牌）、`python-multipart`（表单解析）、`email-validator`（EmailStr 校验）、`pydantic-settings`（第 9 课配置）、`httpx` + `pytest`（第 10 课测试）。
