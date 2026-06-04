# 非 Docker 运行后端步骤

本文档给出两种运行方式：

1. Windows 本机使用 WSL 运行后端。
2. 远程 Linux 服务器直接运行后端。

当前后端不依赖 Docker。搜索主链路使用 PostgreSQL 兜底匹配，因此不安装 OpenSearch 也可以完成导入、解析、搜索和详情查询。

## 1. Windows + WSL 本机运行

推荐把后端、Conda 环境、PostgreSQL 都放在 WSL Ubuntu 内运行。Windows 浏览器或 PowerShell 可以直接访问：

```text
http://localhost:8000
```

### 1.1 安装 WSL

在 Windows PowerShell 中检查 WSL：

```powershell
wsl --status
```

如果尚未安装 WSL，可在管理员 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装完成后重启电脑，并打开 Ubuntu 终端完成用户名和密码初始化。

### 1.2 安装 WSL 内系统依赖并确认 Conda

在 WSL Ubuntu 中执行：

```bash
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

先确认当前 WSL 里能否直接使用 `conda`：

```bash
conda --version
```

如果能看到版本号，继续检查其他工具：

```bash
psql --version
git --version
```

如果提示 `conda: command not found`，说明 Windows 里的 Anaconda 没有进入 WSL 环境。WSL 是独立的 Linux 系统，需要在 WSL 内也安装 Anaconda 或 Miniconda。推荐安装轻量的 Miniconda：

```bash
cd /tmp
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version
```

安装过程中建议接受默认安装路径，并在提示是否初始化 shell 时选择 `yes`。

如果你确认 Anaconda 已经安装在 WSL 内，但 shell 没初始化，可以执行：

```bash
conda init bash
source ~/.bashrc
conda --version
```

### 1.3 进入项目目录

如果项目仍在 Windows 的 `D:\Fridge2Recipe`：

```bash
cd /mnt/d/Fridge2Recipe
```

这能直接运行，但 WSL 访问 `/mnt/d` 的文件性能通常比 WSL home 目录慢。更推荐复制到 WSL home：

```bash
cp -r /mnt/d/Fridge2Recipe ~/Fridge2Recipe
cd ~/Fridge2Recipe
```

如果你已经把项目推到 GitHub / GitLab / Gitee，也可以直接 clone：

```bash
git clone <your-repo-url> Fridge2Recipe
cd Fridge2Recipe
```

### 1.4 启动并配置 PostgreSQL

WSL 中通常用 `service` 启动 PostgreSQL：

```bash
sudo service postgresql start
sudo service postgresql status
```

进入 PostgreSQL 管理命令行：

```bash
sudo -u postgres psql
```

执行以下 SQL：

```sql
CREATE USER fridge WITH PASSWORD 'fridge_dev_password';
CREATE DATABASE fridge2recipe OWNER fridge;
\q
```

测试连接：

```bash
psql "postgresql://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe" -c "select now();"
```

如果重复执行创建用户或数据库时报已存在，可以跳过或先删除旧库。测试阶段也可以重建数据库，但注意这会清空已有数据。

### 1.5 创建 Conda 环境

在项目根目录执行：

```bash
conda env create -f environment.yml
conda activate fridge2recipe
```

如果环境已经存在，更新环境：

```bash
conda activate fridge2recipe
conda env update -f environment.yml --prune
```

如果创建环境时访问 `repo.anaconda.com` 超时，可以先配置 Conda 国内镜像：

```bash
conda config --set show_channel_urls yes
conda config --remove-key channels 2>/dev/null || true
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
conda clean -i
conda env create -f environment.yml
```

如果仍然超时，可以把 Conda 超时时间调大：

```bash
conda config --set remote_connect_timeout_secs 30
conda config --set remote_read_timeout_secs 60
```

### 1.6 配置环境变量

复制模板：

```bash
cp .env.example .env
```

确认 `.env` 至少包含：

```env
DATABASE_URL=postgresql+psycopg://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe
OPENSEARCH_URL=http://127.0.0.1:9200
API_PORT=8000
ADMIN_TOKEN=dev-token
SAMPLE_DATA_PATH=data/xiachufang/recipes.jsonl
CORS_ALLOWED_ORIGINS=
```

### 1.7 启动后端

```bash
cd /mnt/d/Fridge2Recipe
conda activate fridge2recipe
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

另开一个终端测试：

```bash
curl http://localhost:8000/health
```
预期返回：

```json
{"status":"ok"}


清空旧数据：
```bash
curl -X POST http://localhost:8000/api/v1/admin/reset-data \
  -H "X-Admin-Token: dev-token"
```


```

## 2. 导入和测试接口

以下命令在 WSL 或远程服务器中都适用。

导入测试数据：


如果你 WSL 里设置了代理，建议这样绕过代理访问本机后端：
```bash
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
```

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

测试搜索：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["西红柿","鸡蛋"],"excluded_items":[],"filters":{},"page":1,"page_size":3}'
```
bucket 规则是按“缺少多少食材”分组：
  缺 0 个 -> 马上能做
  缺 1 个 -> 再买 1 样
  缺 2-3 个 -> 还差几样
  缺 4 个以上 -> 灵感参考
  （调整了对于基本调味料缺失的考虑）


测试排除食材：

```bash
curl -X POST http://localhost:8000/api/v1/search/by-ingredients \
  -H "Content-Type: application/json" \
  -d '{"items":["豆腐","蒜"],"excluded_items":["豆瓣酱"],"filters":{},"page":1,"page_size":5}'
```

查看详情：

```bash
curl http://localhost:8000/api/v1/recipes/1
```
可以规避请求方式不对造成的错误显示：
```bash
curl http://localhost:8000/health
```
浏览器直接打开http://localhost:8000/health

## 3. 远程 Linux 服务器运行

远程服务器步骤和 WSL 基本一致，只是项目路径、端口开放和后台运行方式不同。

### 3.1 登录服务器

```bash
ssh user@your-server-ip
```

### 3.2 安装依赖

```bash
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

你已经安装了 Anaconda 时，不需要再安装 Miniconda。确认服务器上能使用 Conda：

```bash
conda --version
```

如果服务器提示 `conda: command not found`，但确认已安装 Anaconda，可以执行：

```bash
conda init bash
source ~/.bashrc
conda --version
```

### 3.3 获取项目

方式一：服务器直接拉取仓库：

```bash
git clone <your-repo-url> Fridge2Recipe
cd Fridge2Recipe
```

其中 `<your-repo-url>` 替换成你的 GitHub / GitLab / Gitee 仓库地址，例如：

```bash
git clone https://github.com/你的用户名/Fridge2Recipe.git Fridge2Recipe
```

方式二：从 Windows 上传：

```powershell
scp -r D:\Fridge2Recipe user@your-server-ip:~/Fridge2Recipe
```

然后在服务器上：

```bash
cd ~/Fridge2Recipe
```

### 3.4 配置 PostgreSQL、Conda 和 .env

启动 PostgreSQL：

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl status postgresql
```

创建用户和数据库：

```bash
sudo -u postgres psql
```

```sql
CREATE USER fridge WITH PASSWORD 'fridge_dev_password';
CREATE DATABASE fridge2recipe OWNER fridge;
\q
```

创建 Conda 环境：

```bash
conda env create -f environment.yml
conda activate fridge2recipe
```

如果远程服务器访问 `repo.anaconda.com` 超时，可以参考 WSL 部分的 Conda 镜像配置，先切换到清华镜像再创建环境。

复制并编辑配置：

```bash
cp .env.example .env
nano .env
```

建议把 `ADMIN_TOKEN` 和数据库密码改成强密码。

### 3.5 前台启动测试

```bash
conda activate fridge2recipe
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

检查：

```bash
curl http://localhost:8000/health
```

### 3.6 开放服务器端口

只需要开放 API 端口，例如 `8000`：

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

云服务器还需要在安全组中放行 TCP `8000`。

不要把 PostgreSQL `5432` 暴露到公网。

## 4. 使用 systemd 后台运行远程服务器后端

WSL 本机调试通常不需要 systemd。远程服务器正式演示建议使用 systemd。

创建服务文件：

```bash
sudo nano /etc/systemd/system/fridge2recipe-api.service
```

写入以下内容，并把 `YOUR_USER` 和路径替换成你的实际用户和项目路径：

```ini
[Unit]
Description=Fridge2Recipe FastAPI backend
After=network.target postgresql.service

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/Fridge2Recipe
Environment=PYTHONPATH=/home/YOUR_USER/Fridge2Recipe/backend
ExecStart=/home/YOUR_USER/anaconda3/envs/fridge2recipe/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable fridge2recipe-api
sudo systemctl start fridge2recipe-api
sudo systemctl status fridge2recipe-api
```

查看日志：

```bash
journalctl -u fridge2recipe-api -f
```

如果你的 Anaconda 安装路径不是 `/home/YOUR_USER/anaconda3`，先用下面命令确认 Python 路径：

```bash
conda activate fridge2recipe
which python
```

然后把 `ExecStart` 中的 Python 路径替换为 `which python` 输出的路径。

## 5. 更新代码或数据

如果是 git clone：

```bash
cd ~/Fridge2Recipe
git pull
conda activate fridge2recipe
conda env update -f environment.yml --prune
```

远程服务器使用 systemd 时重启：

```bash
sudo systemctl restart fridge2recipe-api
```

WSL 本机调试时，停止并重新运行 `uvicorn` 即可。

如果只是更新了 `data/xiachufang/recipes.jsonl`，可以重新导入：

```bash
curl -X POST http://localhost:8000/api/v1/admin/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-token" \
  -d "{}"
```

注意：同一个菜谱 `id` 已导入后会跳过。如果希望重新导入全部测试数据，需要手动清空相关数据库表或重建数据库。

## 6. 可选：安装并使用 OpenSearch

当前 MVP 不依赖 OpenSearch 完成搜索。如果你已经安装并启动 OpenSearch，可以在 `.env` 中配置：

```env
OPENSEARCH_URL=http://127.0.0.1:9200
```

然后调用：

```bash
curl -X POST http://localhost:8000/api/v1/admin/reindex \
  -H "X-Admin-Token: dev-token"
```

## 7. 常见问题

WSL 中 PostgreSQL 没启动：

```bash
sudo service postgresql start
sudo service postgresql status
```

WSL 中 `apt install` 下载失败：

如果出现 `Connection timed out`、`Connection failed`，或者请求地址解析到类似 `198.18.x.x`，通常是 WSL 访问 Ubuntu 官方源不稳定，或本机代理/VPN 的 fake-ip 影响了 apt。可以先把 Ubuntu 源换成国内镜像，再刷新索引。

先确认 Ubuntu 版本代号：

```bash
. /etc/os-release
echo $VERSION_CODENAME
```

Ubuntu 24.04 通常输出 `noble`。如果是 Ubuntu 24.04，可执行：

```bash
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
sudo tee /etc/apt/sources.list.d/ubuntu.sources > /dev/null <<'EOF'
Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
sudo apt clean
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

如果你的 Ubuntu 版本不是 `noble`，不要直接复制上面的源配置；需要把 `noble` 替换成你的版本代号，例如 `jammy`。

WSL 中提示 `Unable to locate package postgresql`：

这个错误说明 apt 当前包索引里没有 PostgreSQL 包，通常是源配置缺失、版本代号写错，或没有成功执行 `sudo apt update`。先检查版本代号：

```bash
. /etc/os-release
echo $VERSION_CODENAME
```

然后用版本代号自动重写 Ubuntu 源。下面命令适用于 Ubuntu 24.04 的 deb822 源格式，也可用于较新的 WSL Ubuntu：

```bash
CODENAME=$(. /etc/os-release && echo $VERSION_CODENAME)
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak 2>/dev/null || true
sudo tee /etc/apt/sources.list.d/ubuntu.sources > /dev/null <<EOF
Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: ${CODENAME} ${CODENAME}-updates ${CODENAME}-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu/
Suites: ${CODENAME}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
sudo apt clean
sudo apt update
apt-cache policy postgresql postgresql-contrib
sudo apt install -y git curl postgresql postgresql-contrib
```

如果 `apt-cache policy postgresql` 仍然没有候选版本，可以直接安装版本包。Ubuntu 24.04 通常是 PostgreSQL 16：

```bash
sudo apt install -y postgresql-16 postgresql-contrib
```

如果仍然找不到 `postgresql-16`，说明 apt 源仍未正确生效。请执行：

```bash
grep -R "URIs\\|Suites\\|Components\\|^deb " /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null
```

确认输出中有你的 Ubuntu 版本代号，例如 `noble`，并且 `Components` 包含 `main` 和 `universe`。

如果输出里还有旧的 Docker 源，例如 `/etc/apt/sources.list.d/docker.list`，而当前项目不再使用 Docker，可以先移除它，避免它干扰 `apt update`：

```bash
sudo mkdir -p /etc/apt/disabled-sources
sudo mv /etc/apt/sources.list.d/docker.list /etc/apt/disabled-sources/docker.list.bak 2>/dev/null || true
```

然后强制清理并刷新 apt 索引：

```bash
sudo rm -rf /var/lib/apt/lists/*
sudo apt clean
sudo apt update
```

刷新后检查 PostgreSQL 包是否进入索引：

```bash
apt-cache search '^postgresql$'
apt-cache search '^postgresql-[0-9]+$'
apt-cache policy postgresql postgresql-16 postgresql-contrib
```

如果 `apt-cache search '^postgresql$'` 仍然没有输出，说明 `sudo apt update` 仍未成功从 Ubuntu 源下载包索引。此时请先看 `sudo apt update` 的完整输出，重点检查是否有 `Err`、`NO_PUBKEY`、`Release file`、`Temporary failure resolving` 或 `Connection timed out`。

Windows 访问不到 WSL 后端：

- 确认 uvicorn 使用 `--host 0.0.0.0`
- 在 WSL 中先测试 `curl http://localhost:8000/health`
- 再在 Windows PowerShell 中测试 `curl http://localhost:8000/health`

数据库连接失败：

- 检查 `.env` 中 `DATABASE_URL`
- 检查 PostgreSQL 是否启动
- 用 `psql "postgresql://fridge:fridge_dev_password@127.0.0.1:5432/fridge2recipe" -c "select now();"` 单独测试

导入数据后搜索为空：

- 确认已经调用 `/api/v1/admin/import`
- 确认导入响应中 `imported` 大于 0
- 如果之前导入过旧数据，相同 `id` 会被跳过
