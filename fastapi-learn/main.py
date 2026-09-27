"""快速体验入口：在本目录直接 uvicorn main:app --reload 即可跑起最小应用。

这是 README 课程表里第 1 课的极简版。**完整课程在 lessons/ 目录**——
每课独立可运行，按 README 的学习路线图逐课推进。
"""
from fastapi import FastAPI

app = FastAPI(title="fastapi-learn 快速体验")


@app.get("/")
def read_root():
    return {"Hello": "World", "next": "去 lessons/01_hello 开始正式课程"}
