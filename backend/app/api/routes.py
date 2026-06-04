from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.models.tables import Recipe
from app.schemas.api import ImportRequest, ParseRequest, RecipeDetail, SearchRequest
from app.services.opensearch_indexer import reindex_recipes
from app.services.parser import parse_ingredients
from app.services.search import search_by_ingredients
from app.services.normalizer import is_basic_seasoning
from app.workers.import_xiachufang import import_xiachufang_jsonl

router = APIRouter()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """用简单的请求头 token 保护管理接口。

    这对本地演示和早期团队开发已经够用。正式环境应替换为完整鉴权，
    并避免将管理接口直接暴露到公网。
    """
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/health")
def health() -> dict:
    """轻量健康检查，供人工、脚本和部署探针使用。"""
    return {"status": "ok"}


@router.post("/api/v1/admin/init-db", dependencies=[Depends(require_admin)])
def init_database() -> dict:
    """根据 SQLAlchemy 模型创建数据库表。

    应用启动时也会自动执行一次。保留显式接口方便测试全新的远程服务器。
    """
    init_db()
    return {"status": "ok"}


@router.post("/api/v1/admin/import", dependencies=[Depends(require_admin)])
def import_sample(payload: ImportRequest, db: Session = Depends(get_db)) -> dict:
    """把 xiachufang JSONL 数据导入规范化后的 PostgreSQL 表。"""
    settings = get_settings()
    path = payload.path or settings.sample_data_path
    return import_xiachufang_jsonl(db, path)


@router.post("/api/v1/admin/reset-data", dependencies=[Depends(require_admin)])
def reset_data(db: Session = Depends(get_db)) -> dict:
    """清空已导入的菜谱和食材数据，便于从测试数据切换到真实数据。"""
    cleared_tables = [
        "search_events",
        "recipe_steps",
        "recipe_ingredients",
        "recipes",
        "source_records",
        "ingredient_aliases",
        "ingredients",
    ]
    db.execute(
        text(
            "TRUNCATE TABLE search_events, recipe_steps, recipe_ingredients, recipes, "
            "source_records, ingredient_aliases, ingredients RESTART IDENTITY CASCADE"
        )
    )
    db.commit()
    return {"status": "ok", "cleared": cleared_tables}


@router.post("/api/v1/admin/reindex", dependencies=[Depends(require_admin)])
def reindex(db: Session = Depends(get_db)) -> dict:
    """从 PostgreSQL 重建 OpenSearch 索引。

    当前搜索仍使用 PostgreSQL 兜底召回。这个接口先准备好 OpenSearch
    索引，后续可以把召回层切换过去。
    """
    return reindex_recipes(db)


@router.post("/api/v1/ingredients/parse")
def parse(payload: ParseRequest, db: Session = Depends(get_db)):
    """把用户输入的食材解析为规范名和排除项。"""
    return parse_ingredients(db, payload.items)


@router.post("/api/v1/search/by-ingredients")
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    """按用户已有食材搜索菜谱，并返回可解释结果。"""
    return search_by_ingredients(db, payload)


@router.get("/api/v1/recipes/{recipe_id}", response_model=RecipeDetail)
def recipe_detail(recipe_id: int, db: Session = Depends(get_db)) -> RecipeDetail:
    """从 PostgreSQL 返回完整菜谱详情。

    搜索文档应保持轻量，完整食材明细和全部步骤从关系型事实源回查。
    """
    recipe = db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
        .where(Recipe.id == recipe_id)
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeDetail(
        recipe_id=recipe.id,
        source_recipe_id=recipe.source_recipe_id,
        title=recipe.title,
        dish=recipe.dish,
        description=recipe.description,
        quality_score=float(recipe.quality_score),
        ingredients=[
            {
                "raw_text": item.raw_text,
                "canonical_name": item.canonical_name,
                "quantity": float(item.quantity) if item.quantity is not None else None,
                "unit": item.unit,
                "required": item.required and not is_basic_seasoning(item.canonical_name),
                "position": item.position,
            }
            for item in recipe.ingredients
        ],
        steps=[{"step_no": step.step_no, "text": step.text} for step in recipe.steps],
    )
