from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    items: list[str] = Field(default_factory=list)


class ParsedIngredient(BaseModel):
    raw: str
    canonical: str
    quantity: float | None = None
    unit: str | None = None
    confidence: float


class ParseResponse(BaseModel):
    ingredients: list[ParsedIngredient]
    excluded_ingredients: list[str]
    need_confirmation: list[str]


class SearchFilters(BaseModel):
    max_minutes: int | None = None
    difficulty_lte: int | None = None
    cuisine: list[str] | None = None


class SearchRequest(BaseModel):
    items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchItem(BaseModel):
    recipe_id: int
    source_recipe_id: str | None
    title: str
    dish: str | None = None
    quality_score: float
    matched: list[str]
    missing: list[str]
    bucket: str
    score: float
    reason: str


class SearchResponse(BaseModel):
    parsed: ParseResponse
    total: int
    items: list[SearchItem]
    facets: dict


class ImportRequest(BaseModel):
    path: str | None = None


class RecipeIngredientOut(BaseModel):
    raw_text: str
    canonical_name: str | None
    quantity: float | None = None
    unit: str | None = None
    position: int


class RecipeStepOut(BaseModel):
    step_no: int
    text: str


class RecipeDetail(BaseModel):
    recipe_id: int
    source_recipe_id: str | None
    title: str
    dish: str | None = None
    description: str | None = None
    quality_score: float
    ingredients: list[RecipeIngredientOut]
    steps: list[RecipeStepOut]
