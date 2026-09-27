"""物品路由模块：演示"模块内的路由也能用共享依赖"。"""

from fastapi import APIRouter, Depends

from deps import page_meta, pagination

router = APIRouter()

_items = [{"id": i, "name": f"item-{i}"} for i in range(1, 21)]


@router.get("")
def list_items(meta: dict = Depends(page_meta), p=Depends(pagination)):
    return {"meta": meta, "items": _items[p.offset : p.offset + p.size]}


@router.get("/{item_id}")
def get_item(item_id: int):
    if 1 <= item_id <= len(_items):
        return _items[item_id - 1]
    return {"error": "not found"}
