from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Ingredient, IngredientAlias
from app.services.normalizer import DEFAULT_ALIAS_MAP, NormalizedIngredient, normalize_ingredient


def load_alias_map(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(IngredientAlias.alias, Ingredient.canonical_name).join(Ingredient, Ingredient.id == IngredientAlias.ingredient_id)
    ).all()
    alias_map = DEFAULT_ALIAS_MAP.copy()
    alias_map.update({alias: canonical for alias, canonical in rows})
    return alias_map


def ensure_ingredient(db: Session, canonical_name: str, aliases: list[str] | None = None) -> Ingredient:
    ingredient = db.scalar(select(Ingredient).where(Ingredient.canonical_name == canonical_name))
    if ingredient is None:
        ingredient = Ingredient(canonical_name=canonical_name)
        db.add(ingredient)
        db.flush()

    alias_values = set(aliases or [])
    alias_values.add(canonical_name)
    for alias in alias_values:
        if not alias:
            continue
        existing_alias = db.scalar(select(IngredientAlias).where(IngredientAlias.alias == alias))
        if existing_alias is None:
            db.add(IngredientAlias(ingredient_id=ingredient.id, alias=alias, source="auto", confidence=1.0))

    return ingredient


def seed_default_aliases(db: Session) -> int:
    created = 0
    for alias, canonical in DEFAULT_ALIAS_MAP.items():
        before = db.scalar(select(IngredientAlias).where(IngredientAlias.alias == alias))
        ensure_ingredient(db, canonical, aliases=[alias])
        if before is None:
            created += 1
    return created


def normalize_with_db(db: Session, raw: str) -> NormalizedIngredient:
    return normalize_ingredient(raw, load_alias_map(db))
