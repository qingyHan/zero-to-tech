"""跨路由共享的依赖：分页参数包（第 5 课的知识在这里落地）。"""

from fastapi import Depends


class Pagination:
    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(page, 1)
        self.size = min(size, 50)
        self.offset = (self.page - 1) * self.size


def pagination(page: int = 1, size: int = 10) -> Pagination:
    """函数式依赖：任何路由声明 `p: Pagination = Depends(pagination)` 即可复用。"""
    return Pagination(page=page, size=size)


def page_meta(p: Pagination = Depends(pagination)) -> dict:
    return {"page": p.page, "size": p.size, "offset": p.offset}
