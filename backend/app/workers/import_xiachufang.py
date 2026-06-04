import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Recipe, RecipeIngredient, RecipeStep, SourceRecord
from app.services.ingredients import ensure_ingredient, load_alias_map, seed_default_aliases
from app.services.normalizer import normalize_ingredient


def stable_hash(payload: Any) -> str:
    """为去重和来源审计创建稳定哈希。"""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def calc_quality_score(row: dict[str, Any], normalized_count: int) -> float:
    """根据 xiachufang 当前可用字段估算菜谱质量分。

    源数据样例暂时没有热度、烹饪时间和难度，所以 MVP 质量分先奖励可用结构：
    有足够步骤、食材数量合理、有可选描述，以及食材能成功归一。
    """
    n_steps = int(row.get("n_steps") or len(row.get("steps") or []))
    n_ingredients = int(row.get("n_ingredients") or len(row.get("ingredients") or []))
    score = 0.0
    if n_steps > 0:
        score += 0.4
    if 3 <= n_steps <= 12:
        score += 0.2
    if 3 <= n_ingredients <= 15:
        score += 0.2
    if row.get("description"):
        score += 0.1
    if n_ingredients and normalized_count >= n_ingredients:
        score += 0.1
    return round(min(score, 1.0), 3)


def iter_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL 文件，其中每一行是一条处理后的 xiachufang 菜谱。"""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
    return rows


def import_xiachufang_jsonl(db: Session, path: str | Path) -> dict[str, int]:
    """把处理后的 xiachufang 菜谱导入 MVP 关系模型。

    源数据先写入 source_records 方便追溯，再展开到 recipes、
    recipe_ingredients 和 recipe_steps，供搜索和详情使用。
    同一个 source_recipe_id 可重复执行，重复数据会被跳过。
    """
    rows = iter_jsonl(path)
    seed_default_aliases(db)
    alias_map = load_alias_map(db)

    imported = 0
    skipped = 0
    source_records = 0
    ingredient_links = 0
    step_links = 0

    for row in rows:
        source_id = row["id"]
        recipe_exists = db.scalar(
            select(Recipe).where(Recipe.source_name == "xiachufang", Recipe.source_recipe_id == source_id)
        )
        if recipe_exists is not None:
            skipped += 1
            continue

        payload_hash = stable_hash(row)

        # 保留一份原始负载，后续如果清洗逻辑有问题，
        # 可以直接追溯到导入时的处理后数据。
        source_exists = db.scalar(
            select(SourceRecord).where(SourceRecord.source_name == "xiachufang", SourceRecord.source_id == source_id)
        )
        if source_exists is None:
            db.add(
                SourceRecord(
                    source_name="xiachufang",
                    source_id=source_id,
                    source_url=None,
                    raw_payload=row,
                    payload_hash=payload_hash,
                )
            )
            source_records += 1

        raw_ingredients = row.get("ingredients") or []
        normalized_items = []
        for item in raw_ingredients:
            raw_name = item.get("name") or item.get("raw") or ""
            normalized = normalize_ingredient(raw_name, alias_map)

            # ensure_ingredient 会同时创建规范食材和别名记录，
            # 让早期导入流程可以顺手初始化一张可用的食材表。
            ingredient = ensure_ingredient(db, normalized.canonical, aliases=[normalized.candidate, raw_name])
            normalized_items.append((item, normalized, ingredient))

        recipe = Recipe(
            source_name="xiachufang",
            source_recipe_id=source_id,
            title=row["name"],
            dish=row.get("dish"),
            description=row.get("description") or "",
            quality_score=calc_quality_score(row, len(normalized_items)),
            rights_status="clear",
            takedown_status="active",
            content_hash=payload_hash,
        )
        db.add(recipe)
        db.flush()

        for position, (item, normalized, ingredient) in enumerate(normalized_items, start=1):
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    raw_text=item.get("raw") or item.get("name") or "",
                    canonical_name=normalized.canonical,
                    quantity=normalized.quantity,
                    unit=normalized.unit,
                    required=True,
                    position=position,
                )
            )
            ingredient_links += 1

        for step_no, text in enumerate(row.get("steps") or [], start=1):
            db.add(RecipeStep(recipe_id=recipe.id, step_no=step_no, text=text))
            step_links += 1

        imported += 1

    db.commit()
    return {
        "rows": len(rows),
        "imported": imported,
        "skipped": skipped,
        "source_records": source_records,
        "recipe_ingredients": ingredient_links,
        "recipe_steps": step_links,
    }
