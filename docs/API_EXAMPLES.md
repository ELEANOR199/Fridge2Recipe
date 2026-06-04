# Fridge2Recipe 前端接口文档

本文档面向前端开发。当前后端支持“已有食材 / 不需要食材 / 偏好标签”进行菜谱筛选。食材命中权重最高，其次是荤素和辣不辣，其余偏好用于小幅调整排序。默认情况下基础调味品不会计入缺失食材，例如 `盐`、`糖`、`食用油`、`生抽`、`醋`、`胡椒`、`淀粉` 等。

## 1. 后端地址

本机后端地址固定使用：

```text
http://127.0.0.1:8000
```

前端建议配置：

```ts
export const API_BASE_URL = "http://127.0.0.1:8000";
```

如果前端运行在另一台机器上，不能使用 `127.0.0.1`，需要改为后端所在机器的局域网 IP 或服务器 IP：

```ts
export const API_BASE_URL = "http://<后端机器IP>:8000";
```

例如：

```ts
export const API_BASE_URL = "http://192.168.1.23:8000";
```

如果前端运行在 Vite 默认端口 `5173`，并且浏览器出现 CORS 报错，请在后端 `.env` 中设置：

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

如果前端在另一台机器上，例如 `http://192.168.1.50:5173`，则改为：

```env
CORS_ALLOWED_ORIGINS=http://192.168.1.50:5173
```

修改后重启后端。

健康检查：

```http
GET /health
```

响应：

```json
{
  "status": "ok"
}
```

## 2. 前后端交互流程

前端第一版建议只有一个搜索页和一个详情弹窗 / 抽屉。

```text
用户输入食材
  -> 点击“搜索”或按 Enter
  -> POST /api/v1/search/by-ingredients
  -> 渲染搜索结果列表
  -> 点击某个菜谱卡片
  -> GET /api/v1/recipes/{recipe_id}
  -> 渲染菜谱详情
```

可选流程：

```text
用户输入食材
  -> 点击“解析”或输入完成后自动解析
  -> POST /api/v1/ingredients/parse
  -> 展示后端归一后的食材 tag
```

搜索接口本身也会解析食材，因此前端可以不单独调用解析接口，直接调用搜索接口。

## 3. 输入标签与后端字段对应

| 前端区域 | 前端含义 | 后端字段 | 类型 | 示例 |
|---|---|---|---|---|
| 已有食材输入框 / tag | 用户拥有、希望用于匹配的食材 | `items` | `string[]` | `["西红柿", "鸡蛋"]` |
| 不需要食材输入框 / tag | 用户不想看到的食材，含有这些食材的菜谱会被排除 | `excluded_items` | `string[]` | `["香菜"]` |

偏好标签统一放在 `filters` 中：

| 前端标签 | 后端字段 | 可选值 | 说明 |
|---|---|---|---|
| 辣 / 不辣 | `filters.spice` | `"spicy"` / `"not_spicy"` | 影响排序，辣不辣权重较高 |
| 简单 / 复杂 | `filters.complexity` | `"simple"` / `"complex"` | 简单表示步骤数 `<= 5`，复杂表示步骤数 `> 5` |
| 调味料是否算食材 | `filters.count_seasonings_as_ingredients` | `true` / `false` | `false` 时基础调味品不计入 `missing`，默认 `false` |
| 荤菜 / 素菜 | `filters.diet` | `"meat"` / `"vegetarian"` | 影响排序，荤素权重较高 |
| 是否给小孩 | `filters.for_children` | `true` / `false` | `true` 时偏好不辣、步骤不太多、少酒类词的菜谱 |
| 分量多 / 少 | `filters.serving_size` | `"large"` / `"small"` | 根据标题、描述和食材数量粗略推断 |
| 调料多 / 少 | `filters.seasoning_amount` | `"many"` / `"few"` | 根据基础调味品数量和占比推断 |
| 烹饪手法 | `filters.methods` | `["炒","蒸","煎","拌","炖"]` | 可多选 |

后端还保留以下兼容字段，当前数据中大多为空，前端第一版可以不做：

| 字段 | 类型 | 说明 |
|---|---|---|
| `filters.max_minutes` | `number \| null` | 最大烹饪时间，当前数据基本缺失 |
| `filters.difficulty_lte` | `number \| null` | 最大难度，当前数据基本缺失 |
| `filters.cuisine` | `string[] \| null` | 菜系筛选，当前数据基本缺失 |

分页字段：

| 前端区域 | 后端字段 | 类型 | 示例 |
|---|---|---|---|
| 页码 | `page` | `number` | `1` |
| 每页数量 | `page_size` | `number` | `20` |

## 4. 搜索接口

```http
POST /api/v1/search/by-ingredients
```

### 4.1 请求格式

```json
{
  "items": ["西红柿", "鸡蛋"],
  "excluded_items": ["香菜"],
  "filters": {
    "spice": "not_spicy",
    "complexity": "simple",
    "count_seasonings_as_ingredients": false,
    "diet": "vegetarian",
    "for_children": true,
    "serving_size": "small",
    "seasoning_amount": "few",
    "methods": ["炒"]
  },
  "page": 1,
  "page_size": 20
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `items` | 建议传 | `string[]` | 已有食材，可为空数组；省略时默认为 `[]` |
| `excluded_items` | 建议传 | `string[]` | 不需要食材，可为空数组；省略时默认为 `[]` |
| `filters` | 建议传 | `object` | 偏好标签对象；没有偏好时传 `{}`，省略时后端也会按 `{}` 处理 |
| `page` | 建议传 | `number` | 从 1 开始；省略时默认为 `1` |
| `page_size` | 建议传 | `number` | 1 到 100；省略时默认为 `20` |

### 4.2 响应格式

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
    "excluded_ingredients": ["香菜"],
    "need_confirmation": []
  },
  "total": 2418,
  "items": [
    {
      "recipe_id": 1,
      "source_recipe_id": "r0000067",
      "title": "超美味的西红柿蛋汤",
      "dish": "西红柿蛋汤",
      "quality_score": 1.0,
      "matched": ["番茄", "鸡蛋"],
      "missing": [],
      "bucket": "马上能做",
      "score": 1.24,
      "reason": "命中 2 个已有食材，必需食材已覆盖，偏好匹配：素菜、不辣、适合小孩、分量少，质量分 1.00",
      "recipe_tags": ["不辣", "素菜", "复杂", "调料少", "分量少", "适合小孩", "炒"],
      "preference_matches": ["素菜", "不辣", "适合小孩", "分量少", "调料少", "炒"],
      "preference_mismatches": ["简单"],
      "preference_score": 0.34
    }
  ],
  "facets": {
    "bucket": [
      {
        "name": "马上能做",
        "count": 1
      },
      {
        "name": "还差几样",
        "count": 358
      }
    ]
  }
}
```

注意：示例响应对应上方带 `excluded_items:["香菜"]` 和偏好标签的请求。实际结果会随导入数据、用户输入和偏好选择变化。
`facets.bucket` 示例只展示了部分分组，前端应按接口实际返回的数组渲染。

### 4.3 搜索响应与前端显示对应

| 后端字段 | 类型 | 前端建议显示 |
|---|---|---|
| `parsed.ingredients[].canonical` | `string` | 顶部“识别到的食材”tag，例如 `番茄` |
| `parsed.ingredients[].raw` | `string` | 原始输入，可作为 tag tooltip 或调试文本 |
| `parsed.excluded_ingredients[]` | `string[]` | 顶部“不需要”tag |
| `parsed.need_confirmation[]` | `string[]` | 需要用户确认的低置信度食材 |
| `total` | `number` | 当前请求条件下的结果总数，例如 `共 2418 个结果` |
| `items[].recipe_id` | `number` | 点击卡片后请求详情接口 |
| `items[].title` | `string` | 菜谱卡片主标题 |
| `items[].dish` | `string \| null` | 菜谱卡片副标题 / 菜品名 |
| `items[].bucket` | `string` | 结果标签，例如 `马上能做`、`再买 1 样`、`还差几样`、`灵感参考` |
| `items[].matched` | `string[]` | “已匹配”食材 tag |
| `items[].missing` | `string[]` | “还缺”食材 tag；当 `count_seasonings_as_ingredients=false` 时基础调味品不会出现在这里 |
| `items[].reason` | `string` | 推荐原因，可直接显示 |
| `items[].score` | `number` | 排序分，前端可隐藏 |
| `items[].quality_score` | `number` | 菜谱质量分，前端可隐藏 |
| `items[].recipe_tags` | `string[]` | 后端推断出的菜谱标签，可显示在卡片上 |
| `items[].preference_matches` | `string[]` | 与用户偏好匹配的标签，可显示为高亮 tag |
| `items[].preference_mismatches` | `string[]` | 未匹配的偏好标签，可隐藏或调试显示 |
| `items[].preference_score` | `number` | 偏好加权分，前端可隐藏 |
| `facets.bucket` | `{name:string,count:number}[]` | 可选，用于顶部结果分类统计 |

说明：`preference_mismatches` 只表示该菜谱没有满足某个偏好标签，不代表结果错误。因为食材匹配权重最高，一个菜谱即使没有满足“简单”等次级偏好，也可能因为食材完全匹配而排在前面。

## 5. 菜谱详情接口

```http
GET /api/v1/recipes/{recipe_id}
```

前端触发方式：用户点击搜索结果卡片时，把该卡片的 `recipe_id` 拼到 URL 中。
不要固定请求 `/api/v1/recipes/1`；详情页必须使用当前被点击卡片的 `items[].recipe_id`。

### 5.1 响应格式

```json
{
  "recipe_id": 1,
  "source_recipe_id": "r0000067",
  "title": "超美味的西红柿蛋汤",
  "dish": "西红柿蛋汤",
  "description": "人人都会做的西红柿蛋汤,我只喜欢喝我自己做的,不用加任何味精鸡精,健康美味",
  "quality_score": 1.0,
  "recipe_tags": ["不辣", "素菜", "复杂", "调料少", "分量少", "适合小孩", "炒"],
  "ingredients": [
    {
      "raw_text": "2个西红柿",
      "canonical_name": "番茄",
      "quantity": null,
      "unit": null,
      "required": true,
      "position": 1
    },
    {
      "raw_text": "1个鸡蛋",
      "canonical_name": "鸡蛋",
      "quantity": null,
      "unit": null,
      "required": true,
      "position": 2
    },
    {
      "raw_text": "2勺盐",
      "canonical_name": "盐",
      "quantity": null,
      "unit": null,
      "required": false,
      "position": 3
    },
    {
      "raw_text": "1勺淀粉",
      "canonical_name": "淀粉",
      "quantity": null,
      "unit": null,
      "required": false,
      "position": 4
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "text": "热油下葱花爆锅"
    }
  ]
}
```

说明：上面的 `steps` 只截取了第 1 步作为格式示例，实际详情接口会返回该菜谱的全部步骤。

### 5.2 详情响应与前端显示对应

| 后端字段 | 类型 | 前端建议显示 |
|---|---|---|
| `title` | `string` | 详情标题 |
| `dish` | `string \| null` | 菜品名 / 副标题 |
| `description` | `string \| null` | 简介，没有则隐藏 |
| `recipe_tags` | `string[]` | 与搜索结果一致的后端推断标签 |
| `ingredients[].raw_text` | `string` | 食材原文列表 |
| `ingredients[].canonical_name` | `string \| null` | 规范食材名，可用于 tag |
| `ingredients[].required` | `boolean` | `true` 显示为“必需食材”，`false` 显示为“基础调味品” |
| `ingredients[].position` | `number` | 食材顺序 |
| `steps[].step_no` | `number` | 步骤序号 |
| `steps[].text` | `string` | 步骤内容 |

## 6. 食材解析接口

该接口可选。用于搜索前预览后端如何理解用户输入。

```http
POST /api/v1/ingredients/parse
```

请求：

```json
{
  "items": ["西红柿2个 鸡蛋3枚", "不想吃香菜"]
}
```

响应：

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
  "excluded_ingredients": ["香菜"],
  "need_confirmation": []
}
```

## 7. 全流程示例

### 7.1 前端搜索按钮触发

用户界面：

```text
已有食材：西红柿、鸡蛋
不需要：香菜
偏好：不辣、简单、素菜、适合小孩、分量少、调料少、炒
点击：搜索
```

前端请求：

```ts
const response = await fetch("http://127.0.0.1:8000/api/v1/search/by-ingredients", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    items: ["西红柿", "鸡蛋"],
    excluded_items: ["香菜"],
    filters: {
      spice: "not_spicy",
      complexity: "simple",
      count_seasonings_as_ingredients: false,
      diet: "vegetarian",
      for_children: true,
      serving_size: "small",
      seasoning_amount: "few",
      methods: ["炒"]
    },
    page: 1,
    page_size: 10
  })
});

const data = await response.json();
```

前端渲染：

```text
顶部 tag：
识别到：番茄、鸡蛋
不需要：香菜

结果卡片：
标题：超美味的西红柿蛋汤
副标题：西红柿蛋汤
标签：马上能做
菜谱标签：不辣、素菜、复杂、调料少、分量少、适合小孩、炒
偏好匹配：素菜、不辣、适合小孩、分量少、调料少、炒
偏好未匹配：简单
已匹配：番茄、鸡蛋
还缺：无
原因：命中 2 个已有食材，必需食材已覆盖，偏好匹配：素菜、不辣、适合小孩、分量少，质量分 1.00
```

### 7.2 点击卡片查看详情

用户点击第一条搜索结果，前端读取：

```ts
const recipeId = data.items[0].recipe_id;
```

请求详情：

```ts
const detailResponse = await fetch(`http://127.0.0.1:8000/api/v1/recipes/${recipeId}`);
const detail = await detailResponse.json();
```

前端渲染：

```text
标题：超美味的西红柿蛋汤
简介：人人都会做的西红柿蛋汤...
菜谱标签：不辣、素菜、复杂、调料少、分量少、适合小孩、炒

必需食材：
- 2个西红柿
- 1个鸡蛋

基础调味品：
- 2勺盐
- 1勺淀粉

步骤：
1. 热油下葱花爆锅
2. 西红柿下锅...
```

## 8. TypeScript 类型

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
  items?: string[];
  excluded_items?: string[];
  filters?: {
    max_minutes?: number | null;
    difficulty_lte?: number | null;
    cuisine?: string[] | null;
    spice?: "spicy" | "not_spicy" | null;
    complexity?: "simple" | "complex" | null;
    count_seasonings_as_ingredients?: boolean;
    diet?: "meat" | "vegetarian" | null;
    for_children?: boolean | null;
    serving_size?: "large" | "small" | null;
    seasoning_amount?: "many" | "few" | null;
    methods?: Array<"炒" | "蒸" | "煎" | "拌" | "炖">;
  };
  page?: number;
  page_size?: number;
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
  recipe_tags: string[];
  preference_matches: string[];
  preference_mismatches: string[];
  preference_score: number;
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
  recipe_tags: string[];
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

## 9. 错误处理

| 状态码 | 场景 | 前端处理 |
|---|---|---|
| `404` | 详情接口中 `recipe_id` 不存在 | 提示“菜谱不存在” |
| `422` | 请求体格式错误，例如 `page_size` 超过 100 | 提示“搜索参数错误” |
| `500` | 后端服务异常 | 提示“服务异常，请稍后重试” |

管理接口如 `/api/v1/admin/import`、`/api/v1/admin/reset-data` 只用于数据准备，不建议普通前端页面调用。
