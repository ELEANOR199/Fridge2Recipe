# Fridge2Recipe Search MVP

这是一个基于 `xiachufang` 处理后 JSONL 数据的反向食材搜索引擎基础框架。

当前版本包含：

- Docker Compose：PostgreSQL、OpenSearch、FastAPI
- PostgreSQL 核心表：菜谱、食材、别名、步骤、原始记录、搜索事件
- `xiachufang` JSONL 样例数据导入
- 食材解析、数量单位提取、alias 归一
- PostgreSQL 兜底搜索、matched / missing / bucket / reason 解释
- OpenSearch reindex 框架

项目目录和关键代码说明见 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。
远程服务器运行后端的完整步骤见 [docs/SERVER_RUNBOOK.md](docs/SERVER_RUNBOOK.md)。

当前样例数据位于 `data/xiachufang/recipes.jsonl`，已包含 12 条用于搜索测试的菜谱。

## 需要安装的工具

本地 Docker 运行需要：

- Docker Desktop
- Docker Compose v2
- Git，可选

远程服务器 Docker 运行时，本地电脑不需要安装 Docker Desktop，只需要：

- SSH 客户端
- Git 或 scp，用于把项目传到服务器

远程服务器需要：

- Linux 服务器，建议 2 核 4GB 以上
- Docker Engine
- Docker Compose v2

如果不通过 Docker 直接运行后端，还需要 Python 3.12、PostgreSQL 16、OpenSearch 2.x。当前推荐优先用 Docker。

## 本地 Docker 启动

复制环境变量文件：

```powershell
Copy-Item .env.example .env
```

默认启动只暴露 API 端口：

```powershell
docker compose up -d --build
```

检查服务：

```powershell
docker compose ps
curl http://localhost:8000/health
```

如果你还想在本地直接访问 PostgreSQL `5432` 和 OpenSearch `9200`，使用 dev override：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## 远程服务器 Docker 运行

可以。推荐方式是：后端、PostgreSQL、OpenSearch 都跑在远程服务器 Docker 中，本地只通过浏览器、curl 或前端页面访问远程 API。

### 1. 登录服务器

```bash
ssh user@your-server-ip
```

### 2. 安装 Docker

如果服务器还没有 Docker，请先安装 Docker Engine 和 Compose v2。安装完成后确认：

```bash
docker --version
docker compose version
```

### 3. 上传或拉取项目

方式一：服务器上 git clone：

```bash
git clone <your-repo-url> Fridge2Recipe
cd Fridge2Recipe
```

方式二：本地通过 scp 上传当前项目目录：

```powershell
scp -r D:\Fridge2Recipe user@your-server-ip:~/Fridge2Recipe
```

然后在服务器上：

```bash
cd ~/Fridge2Recipe
```

### 4. 配置远程环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
POSTGRES_DB=fridge2recipe
POSTGRES_USER=fridge
POSTGRES_PASSWORD=请改成强密码
API_PORT=8000
ADMIN_TOKEN=请改成强随机字符串
CORS_ALLOWED_ORIGINS=http://your-server-ip:3000,https://your-frontend-domain.com
```

如果当前只用 curl 测试 API，`CORS_ALLOWED_ORIGINS` 可以留空。

### 5. 启动远程服务

```bash
docker compose up -d --build
```

默认只向服务器宿主机暴露 API 端口 `8000`。PostgreSQL 和 OpenSearch 不暴露到公网，只允许 API 容器通过 Docker 内网访问。

### 6. 开放服务器防火墙

只需要开放 API 端口，例如 `8000`。不要开放 `5432` 和 `9200` 到公网。

云服务器还需要在安全组中放行 TCP `8000`。

### 7. 远程健康检查

在服务器上：

```bash
curl http://localhost:8000/health
```

在你的本地电脑上：

```powershell
curl http://your-server-ip:8000/health
```

## 导入样例数据

服务启动后，后端会自动创建数据表。执行导入：

```powershell
curl -X POST http://localhost:8000/api/v1/admin/import `
  -H "Content-Type: application/json" `
  -H "X-Admin-Token: dev-token" `
  -d "{}"
```

远程服务器把地址换成：

```powershell
curl -X POST http://your-server-ip:8000/api/v1/admin/import `
  -H "Content-Type: application/json" `
  -H "X-Admin-Token: 你的ADMIN_TOKEN" `
  -d "{}"
```

样例数据位置：

```text
data/xiachufang/recipes.jsonl
```

## 测试食材解析

```powershell
curl -X POST http://localhost:8000/api/v1/ingredients/parse `
  -H "Content-Type: application/json" `
  -d "{\"items\":[\"超市罐头装半盒金枪鱼\",\"5个圣女果\",\"不想吃香菜\"]}"
```

## 测试搜索

```powershell
curl -X POST http://localhost:8000/api/v1/search/by-ingredients `
  -H "Content-Type: application/json" `
  -d "{\"items\":[\"金枪鱼\",\"生菜\",\"黄瓜\"],\"excluded_items\":[],\"filters\":{},\"page\":1,\"page_size\":10}"
```

## 查看详情

搜索结果中的 `recipe_id` 可用于详情接口：

```powershell
curl http://localhost:8000/api/v1/recipes/1
```

## 重建 OpenSearch 索引

当前搜索接口先使用 PostgreSQL 兜底匹配。OpenSearch 索引可通过下面命令重建，后续可将召回切换到 `recipes_current` alias。

```powershell
curl -X POST http://localhost:8000/api/v1/admin/reindex `
  -H "X-Admin-Token: dev-token"
```

## 常用维护命令

查看日志：

```powershell
docker compose logs -f api
```

停止服务：

```powershell
docker compose down
```

停止并清空数据库和索引卷：

```powershell
docker compose down -v
```

## 后续实现重点

1. 扩充 `data/xiachufang/recipes.jsonl` 到完整数据。
2. 根据真实数据补充 `DEFAULT_ALIAS_MAP` 或改为 CSV 种子导入。
3. 将 `/api/v1/search/by-ingredients` 的召回从 PostgreSQL 切到 OpenSearch。
4. 增加黄金查询集和 Recall@20 评测脚本。
5. 增加前端搜索页和详情抽屉。
