"""第 7 课：OAuth2 密码流 + JWT 认证。

运行：cd 07_auth && uvicorn main:app --reload
验收（先取令牌，再带令牌访问）：
    curl -X POST http://127.0.0.1:8000/token -d "username=alice&password=secret123"
         → {"access_token": "eyJ...", "token_type": "bearer"}
    curl -H "Authorization: Bearer eyJ..." http://127.0.0.1:8000/me   → {"username":"alice"}
    curl http://127.0.0.1:8000/me                                     → 401（没带令牌）
    curl -H "Authorization: Bearer 坏令牌" http://127.0.0.1:8000/me    → 401（令牌无效）
自检：
    1. 令牌里存了什么？服务器需要查表验证令牌吗（JWT 的特点）？
    2. OAuth2PasswordBearer 在 401 响应里加了什么头，为什么？
    3. 密钥为什么不能写死在源码里？
"""
import hashlib
import os
import secrets
import time

import jwt  # PyJWT
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI(title="07 OAuth2 + JWT")

# 签名密钥从环境变量读取；未设置时本次运行随机生成（学习场景零配置）。
# 注意区别：随机密钥重启后已签发的令牌全部失效，仅适合本地学习；
# 生产环境必须用环境变量/密钥管理服务提供固定值——密钥绝不能出现在源码里。
SECRET_KEY = os.environ.get("LEARN_JWT_SECRET") or secrets.token_hex(32)
ALGORITHM = "HS256"
TOKEN_TTL = 3600  # 令牌有效期 1 小时

# 模拟用户表：每个用户独立的随机盐 + 只存口令哈希（PBKDF2-SHA256，
# 迭代次数按 OWASP 建议取 600_000；生产建议 bcrypt/argon2 这类自适应哈希）
def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()


def _new_user(username: str, password: str) -> dict:
    salt = os.urandom(16)
    return {"salt": salt.hex(), "password_hash": _hash(password, salt), "display": username}


users_db = {"alice": _new_user("alice", "secret123"), "bob": _new_user("bob", "hunter2")}

# OAuth2PasswordBearer：声明"令牌从 Authorization: Bearer <token> 头里来"。
# 它本身不验证——只负责取出令牌；tokenUrl 告诉文档页"去 /token 换令牌"。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """换发令牌的端点。OAuth2PasswordRequestForm 自动解析表单字段
    username/password（表单编码，需要 python-multipart 包）——这是 OAuth2
    密码流的标准格式，所以这里不用 JSON 请求体。"""
    user = users_db.get(form.username)
    if user is None:
        # 统一报"用户名或密码错误"：不泄露"这个用户名存在"
        raise HTTPException(status_code=401, detail="用户名或密码错误",
                            headers={"WWW-Authenticate": "Bearer"})
    salt = bytes.fromhex(user["salt"])
    # 常量时间比较：避免逐字节比对泄露"前几位对不对"的时序信息
    if not secrets.compare_digest(_hash(form.password, salt), user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误",
                            headers={"WWW-Authenticate": "Bearer"})
    payload = {"sub": form.username, "exp": int(time.time()) + TOKEN_TTL}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    """把"验证令牌"也做成依赖：任何需要登录的接口声明这一个参数即可。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    username = payload.get("sub")
    if username not in users_db:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"username": username, "display": users_db[username]["display"]}


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    """受保护路由：没有合法令牌，Depends 链在进入函数前就返回 401。
    JWT 的特点：令牌自带身份与过期时间，服务器用密钥本地验证即可——不查表。"""
    return user
