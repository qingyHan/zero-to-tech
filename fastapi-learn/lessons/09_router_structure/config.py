"""配置集中管理：pydantic-settings 把环境变量读成带类型的配置对象。

用法：DEBUG=true uvicorn main:app --reload   （环境变量覆盖默认值）
好处：类型自动转换（"true" → True）、配置缺失一目了然、/docs 外的地方也能 import settings。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "09 项目拆分"
    debug: bool = True


settings = Settings()
