# 后端运行结果与前端接口示例

本文档给前端开发使用，假设后端运行在：

```text
http://localhost:8000
```

如果后端部署在远程服务器，把 `localhost` 替换为服务器 IP 或域名即可。

## 1. 后端运行成功表现

启动命令：

```bash
conda activate fridge2recipe
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

终端中看到类似输出，说明 FastAPI 已启动：

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

健康检查：

```bash
curl http://localhost:8000/health
```

响应：

```json
{
  "status": "ok"
}
```

浏览器也可以打开：

```text
http://localhost:8000/docs
```

这是 FastAPI 自动生成的接口调试页。

## 2. 管理接口

管理接口需要请求头：

```text
X-Admin-Token: dev-token
```

如果 `.env` 中修改了 `ADMIN_TOKEN`，这里也要同步替换。

### 2.1 初始化数据库

后端启动时会自动建表，一般不需要手动调用。需要手动初始化时：

```http
POST /api/v1/admin/init-db
```

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/admin/init-db \
  -H "X-Admin-Token: dev-token"
```

响应示例：

```json
{
  "status": "ok"
}
```

### 2.2 导入菜谱数据

如果之前已经导入过 12 条测试数据，建议先清空旧导入数据：

```http
POST /api/v1/admin/reset-data
```

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/admin/reset-data \
  -H "X-Admin-Token: dev-token"
```

响应示例：

```json
{
  "status": "ok",
  "cleared": [
    "search_events",
    "recipe_steps",
    "recipe_ingredients",
    "recipes",
    "source_records",
    "ingredient_aliases",
    "ingredients"
  ]
}
```

```http
POST /api/v1/admin/import
```

请求体：

```json
{}
```

默认导入 `.env` 中的：

```text
SAMPLE_DATA_PATH=data/xiachufang/recipes_subset.jsonl
```

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-token" \
  -d "{}"
```

响应示例：

```json
{
  "rows": 2500,
  "imported": 2500,
  "skipped": 0,
  "source_records": 2500,
  "recipe_ingredients": 20135,
  "recipe_steps": 17784,
  "skipped_ingredients": 1
}
```

字段说明：

| 字段 | 含义 |
|---|---|
| `rows` | JSONL 文件中读取到的菜谱总数 |
| `imported` | 本次新导入菜谱数 |
| `skipped` | 因为 source id 已存在而跳过的菜谱数 |
| `source_records` | 写入原始记录表的数量 |
| `recipe_ingredients` | 写入菜谱食材明细的数量 |
| `recipe_steps` | 写入菜谱步骤的数量 |
| `skipped_ingredients` | 跳过的异常食材行数量 |

前端通常不需要调用该接口，可作为后台数据准备接口。

## 3. 食材解析接口

### 3.1 解析用户输入

```http
POST /api/v1/ingredients/parse
```

请求体：

```json
{
  "items": ["西红柿2个 鸡蛋3枚", "不想吃香菜"]
}
```

响应示例：

```json
{
  "ingredients": [
    {
      "raw": "西红柿2个",
      "canonical": "番茄",
      "quantity": 2.0,
      "unit": "个",
      "confidence": 1.0
    },
    {
      "raw": "鸡蛋3枚",
      "canonical": "鸡蛋",
      "quantity": 3.0,
      "unit": "枚",
      "confidence": 1.0
    }
  ],
  "excluded_ingredients": [
    "香菜"
  ],
  "need_confirmation": []
}
```

字段说明：

| 字段 | 含义 | 前端用途 |
|---|---|---|
| `ingredients` | 已识别出的可用食材 | 展示为食材 tag |
| `raw` | 用户原始输入片段 | 可用于 hover 或纠错 |
| `canonical` | 后端归一后的规范食材名 | 搜索时使用 |
| `quantity` | 数量，可能为 `null` | 当前可展示，暂不参与排序 |
| `unit` | 单位，可能为 `null` | 当前可展示，暂不参与排序 |
| `confidence` | 归一置信度 | 低于 0.9 可提示用户确认 |
| `excluded_ingredients` | 排除食材 | 展示为“不要这些” |
| `need_confirmation` | 低置信度候选 | 前端可提示用户确认 |

前端建议：

- 用户在输入框按回车或点击“解析”时调用。
- 解析结果可以展示为 tag。
- 如果 `need_confirmation` 非空，提示“以下食材识别不确定”。

## 4. 搜索接口

### 4.1 按已有食材搜索菜谱

```http
POST /api/v1/search/by-ingredients
```

请求体：

```json
{
  "items": ["西红柿", "鸡蛋"],
  "excluded_items": [],
  "filters": {},
  "page": 1,
  "page_size": 5
}
```

完整请求体字段：

```json
{
  "items": ["西红柿", "鸡蛋"],
  "excluded_items": ["香菜"],
  "filters": {
    "max_minutes": null,
    "difficulty_lte": null,
    "cuisine": null
  },
  "page": 1,
  "page_size": 20
}
```

说明：

- 当前样例数据暂时没有 `total_minutes`、`difficulty`、`cuisine`，所以筛选字段可以先传 `{}`。
- `page` 从 1 开始。
- `page_size` 最大 100。

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":[],"filters":{},"page":1,"page_size":5}'
```

响应示例：

```json
{
  "parsed": {
    "ingredients": [
      {
        "raw": "西红柿",
        "canonical": "番茄",
        "quantity": null,
        "unit": null,
        "confidence": 1.0
      },
      {
        "raw": "鸡蛋",
        "canonical": "鸡蛋",
        "quantity": null,
        "unit": null,
        "confidence": 1.0
      }
    ],
    "excluded_ingredients": [],
    "need_confirmation": []
  },
  "total": 2500,
  "items": [
    {
      "recipe_id": 2,
      "source_recipe_id": "r0000002",
      "title": "家常番茄炒蛋",
      "dish": "番茄炒蛋",
      "quality_score": 1.0,
      "matched": ["番茄", "鸡蛋"],
      "missing": ["小葱"],
      "bucket": "再买 1 样",
      "score": 0.81,
      "reason": "命中 2 个已有食材，缺少 1 个食材，质量分 1.00"
    },
    {
      "recipe_id": 11,
      "source_recipe_id": "r0000011",
      "title": "紫菜蛋花汤",
      "dish": "蛋花汤",
      "quality_score": 1.0,
      "matched": ["鸡蛋"],
      "missing": ["紫菜", "虾皮", "小葱", "盐", "香油"],
      "bucket": "灵感参考",
      "score": 0.183,
      "reason": "命中 1 个已有食材，缺少 5 个食材，质量分 1.00"
    }
  ],
  "facets": {
    "bucket": [
      {
        "name": "灵感参考",
        "count": 2500
      }
    ]
  }
}
```

注意：`recipe_id`、`score` 和结果顺序取决于数据库导入顺序、样例数据和排序规则，后续调参后可能变化。前端不要写死这些值，只按响应字段动态渲染。

基础调味品不会计入 `missing`。例如 `盐`、`白糖`、`食用油`、`生抽`、`老抽`、`醋`、`胡椒`、`淀粉` 等仍会保留在详情食材中，但不会影响搜索分组和缺失食材数量。

重要说明：

- `total` 是当前搜索条件下的总结果数，不是当前页数量。
- `items` 是当前页结果。
- `matched` 是用户已有食材中命中的部分。
- `missing` 是菜谱还缺的食材。
- `bucket` 可作为前端分组标签。
- `reason` 可直接展示为推荐原因。

前端列表卡片建议展示：

```text
标题：title
副标题：dish
标签：bucket
命中：matched
缺少：missing
原因：reason
分数：score，可不展示给普通用户
```

### 4.2 排除食材搜索

请求：

```json
{
  "items": ["豆腐", "蒜"],
  "excluded_items": ["豆瓣酱"],
  "filters": {},
  "page": 1,
  "page_size": 5
}
```

效果：

- 如果菜谱中包含 `豆瓣酱`，不会出现在结果里。
- 前端可以把 `excluded_items` 做成单独的“不要这些”输入区域。

## 5. 菜谱详情接口

### 5.1 获取详情

```http
GET /api/v1/recipes/{recipe_id}
```

请求示例：

```bash
curl http://localhost:8000/api/v1/recipes/2
```

响应示例：

```json
{
  "recipe_id": 2,
  "source_recipe_id": "r0000002",
  "title": "家常番茄炒蛋",
  "dish": "番茄炒蛋",
  "description": "经典家常快手菜，适合番茄和鸡蛋库存充足时优先推荐。",
  "quality_score": 1.0,
  "ingredients": [
    {
      "raw_text": "2个西红柿",
      "canonical_name": "番茄",
      "quantity": 2.0,
      "unit": "个",
      "required": true,
      "position": 1
    },
    {
      "raw_text": "3枚鸡蛋",
      "canonical_name": "鸡蛋",
      "quantity": 3.0,
      "unit": "枚",
      "required": true,
      "position": 2
    },
    {
      "raw_text": "适量盐",
      "canonical_name": "盐",
      "quantity": null,
      "unit": null,
      "required": false,
      "position": 4
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "text": "西红柿切块，小葱切末，鸡蛋打散"
    },
    {
      "step_no": 2,
      "text": "热锅放油，倒入鸡蛋炒至凝固后盛出"
    }
  ]
}
```

前端详情页或详情抽屉建议展示：

- `title`
- `description`
- `ingredients.raw_text`
- `ingredients.required`，可用于区分必需食材和基础调味品
- `steps.text`
- `quality_score` 可作为调试字段，不一定展示给用户

## 6. 错误响应

### 6.1 管理接口 token 错误

请求管理接口但缺少或传错 `X-Admin-Token`：

```json
{
  "detail": "Invalid admin token"
}
```

HTTP 状态码：

```text
401
```

### 6.2 菜谱不存在

请求不存在的菜谱：

```http
GET /api/v1/recipes/999999
```

响应：

```json
{
  "detail": "Recipe not found"
}
```

HTTP 状态码：

```text
404
```

### 6.3 请求体格式错误

例如 `page_size` 超过 100，FastAPI 会返回 `422` 校验错误。

前端建议统一处理：

- `401`：提示管理权限错误。
- `404`：提示内容不存在。
- `422`：提示请求参数错误。
- `500`：提示服务异常，并保留错误日志。

## 7. 前端页面拆分建议

第一版前端可以只做一个搜索页加详情抽屉：

```text
SearchPage
├── IngredientInput
├── ExcludedInput
├── ParsedIngredientBar
├── SearchResultList
│   └── RecipeCard
└── RecipeDetailDrawer
```

推荐交互流程：

1. 用户输入已有食材。
2. 点击搜索。
3. 前端调用 `/api/v1/search/by-ingredients`。
4. 顶部展示 `parsed.ingredients` 和 `parsed.excluded_ingredients`。
5. 列表展示 `items`。
6. 点击卡片时调用 `/api/v1/recipes/{recipe_id}`。
7. 在详情抽屉展示完整食材和步骤。

## 8. TypeScript 类型参考

```ts
export interface ParsedIngredient {
  raw: string;
  canonical: string;
  quantity: number | null;
  unit: string | null;
  confidence: number;
}

export interface ParseResponse {
  ingredients: ParsedIngredient[];
  excluded_ingredients: string[];
  need_confirmation: string[];
}

export interface SearchRequest {
  items: string[];
  excluded_items: string[];
  filters: {
    max_minutes?: number | null;
    difficulty_lte?: number | null;
    cuisine?: string[] | null;
  };
  page: number;
  page_size: number;
}

export interface SearchItem {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  quality_score: number;
  matched: string[];
  missing: string[];
  bucket: string;
  score: number;
  reason: string;
}

export interface SearchResponse {
  parsed: ParseResponse;
  total: number;
  items: SearchItem[];
  facets: {
    bucket?: Array<{ name: string; count: number }>;
    [key: string]: unknown;
  };
}

export interface RecipeDetail {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  description: string | null;
  quality_score: number;
  ingredients: Array<{
    raw_text: string;
    canonical_name: string | null;
    quantity: number | null;
    unit: string | null;
    required: boolean;
    position: number;
  }>;
  steps: Array<{
    step_no: number;
    text: string;
  }>;
}
```
