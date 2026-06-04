# 服务器运行后端步骤

本文档给出在远程 Linux 服务器上运行当前后端的完整步骤。本地电脑可以不安装 Docker Desktop，只需要通过 SSH 操作服务器。

## 1. 服务器准备

推荐配置：

- Ubuntu 22.04 / 24.04
- 2 核 CPU
- 4GB 内存以上
- 20GB 以上磁盘

最低需要安装：

- Docker Engine
- Docker Compose v2

登录服务器：

```bash
ssh user@your-server-ip
```

检查 Docker：

```bash
docker --version
docker compose version
```

如果没有安装 Docker，可在 Ubuntu 上执行：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

可选：把当前用户加入 docker 组，避免每次都输入 `sudo`：

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 2. 上传或拉取项目

方式一：服务器直接拉取仓库：

```bash
git clone <your-repo-url> Fridge2Recipe
cd Fridge2Recipe
```

方式二：从本地上传当前项目：

```powershell
scp -r D:\Fridge2Recipe user@your-server-ip:~/Fridge2Recipe
```

然后在服务器上进入目录：

```bash
cd ~/Fridge2Recipe
```

## 3. 配置环境变量

复制模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
nano .env
```

建议至少修改：

```env
POSTGRES_DB=fridge2recipe
POSTGRES_USER=fridge
POSTGRES_PASSWORD=请改成强密码
API_PORT=8000
ADMIN_TOKEN=请改成强随机字符串
CORS_ALLOWED_ORIGINS=
```

如果前端也部署在服务器或其他域名，例如 `http://your-server-ip:3000`，则配置：

```env
CORS_ALLOWED_ORIGINS=http://your-server-ip:3000
```

## 4. 启动后端服务

在服务器项目根目录执行：

```bash
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

查看 API 日志：

```bash
docker compose logs -f api
```

当前 `docker-compose.yml` 默认只暴露 API 端口。PostgreSQL 和 OpenSearch 不会暴露到公网，只能被 API 容器通过 Docker 内网访问。

## 5. 开放服务器端口

只需要开放 API 端口，例如 `8000`。

如果使用 Ubuntu 防火墙：

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

如果使用云服务器，还需要在云厂商安全组中放行 TCP `8000`。

不要把 `5432` 和 `9200` 放行到公网。

## 6. 健康检查

服务器本机检查：

```bash
curl http://localhost:8000/health
```

本地电脑检查：

```powershell
curl http://your-server-ip:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 7. 导入测试数据

当前测试数据文件：

```text
data/xiachufang/recipes.jsonl
```

服务器上执行：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: 你的ADMIN_TOKEN" \
  -d "{}"
```

如果使用默认 token：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-token" \
  -d "{}"
```

预期会看到类似：

```json
{"rows":12,"imported":12,"skipped":0,"source_records":12,"recipe_ingredients":86,"recipe_steps":60}
```

如果之前已经导入过，相同 `id` 会被跳过，`skipped` 会增加。

## 8. 测试搜索接口

番茄鸡蛋测试：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":[],"filters":{},"page":1,"page_size":5}'
```

黄瓜凉菜测试：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["黄瓜","木耳","蒜"],"excluded_items":[],"filters":{},"page":1,"page_size":5}'
```

排除食材测试：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["豆腐","蒜"],"excluded_items":["豆瓣酱"],"filters":{},"page":1,"page_size":5}'
```

查看详情：

```bash
curl http://localhost:8000/api/v1/recipes/1
```

## 9. 重建 OpenSearch 索引

当前搜索仍先使用 PostgreSQL 兜底召回，但可以先构建 OpenSearch 索引：

```bash
curl -X POST http://localhost:8000/api/v1/admin/reindex \
  -H "X-Admin-Token: 你的ADMIN_TOKEN"
```

## 10. 更新代码或数据

如果服务器是 git clone：

```bash
git pull
docker compose up -d --build
```

如果只是更新了 `data/xiachufang/recipes.jsonl`，可以直接重新导入：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: 你的ADMIN_TOKEN" \
  -d "{}"
```

注意：同一个菜谱 `id` 已导入后会跳过。如果希望完全重新导入测试库，可以清空 Docker volume。

## 11. 清空并重建测试环境

这个操作会删除数据库和 OpenSearch 数据，仅适合测试环境：

```bash
docker compose down -v
docker compose up -d --build
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: 你的ADMIN_TOKEN" \
  -d "{}"
```

## 12. 常见问题

API 访问不到：

- 检查 `docker compose ps`
- 检查 `docker compose logs -f api`
- 检查服务器防火墙和云安全组是否放行 `8000`

OpenSearch 启动慢：

- 第一次启动可能需要几十秒到一两分钟。
- 服务器内存建议至少 4GB。

导入数据后搜索为空：

- 确认已经调用 `/api/v1/admin/import`
- 确认导入响应中 `imported` 大于 0
- 如果之前导入过旧数据，可执行 `docker compose down -v` 后重建测试环境
