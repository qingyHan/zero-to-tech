"""用户路由模块：只关心 /users 这摊业务，不关心最终挂在哪个前缀下。"""

from fastapi import APIRouter

router = APIRouter()

_users = [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]


@router.get("")
def list_users():
    # 注意：挂载用了 prefix="/api/users" 时，这里的路径写 "" 即可，
    # 完整路径 = prefix + 路径。业务模块永远不知道自己的最终前缀。
    return _users


@router.get("/{user_id}")
def get_user(user_id: int):
    for u in _users:
        if u["id"] == user_id:
            return u
    return {"error": "not found"}
