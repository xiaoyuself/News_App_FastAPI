# 新闻系统 · Docker 部署速查手册

> 项目：新闻资讯平台 + RAG 智能客服
> 代码仓库：https://github.com/xiaoyuself/News_App_FastAPI
> 适用：Ubuntu 24.04 · **2核2G 或 2核4G** 云服务器

---

## 一、系统架构

```
浏览器 ──8080──> nginx(news-web) ──/api/────→ backend(news-backend) ──→ mysql / redis
                        └────/api/ai/──→ ai(news-ai:8001) ──→ milvus-lite（进程内 .db 文件）
                                                          └──→ DeepSeek + 硅基流动
```

- 唯一对外端口：**8080**
- 其余服务全部只绑 `127.0.0.1`，公网访问不到
- 向量库使用 **milvus-lite**：运行在 ai 进程内、数据存本地 `.db` 文件，省掉约 1.2G 内存，2核2G 也能跑

## 二、容器清单（5 个）

| 容器名 | 镜像 | 端口映射 | 数据存放 |
|---|---|---|---|
| news-web | news-web:v1 | 0.0.0.0:8080 → 80 | 无（配置打进镜像） |
| news-backend | news-backend:v1 | 127.0.0.1:8000 → 8000 | 无 |
| news-ai | news-ai:v1 | 127.0.0.1:8001 → 8001 | 知识库挂载宿主机 `data/`；向量存卷 `milvus_lite_data` |
| news-mysql | mysql:8.0 | 127.0.0.1:3306 → 3306 | 卷 `news_app_mysql_data` |
| news-redis | redis:7.2-alpine | 127.0.0.1:6379 → 6379 | 卷 `news_app_redis_data` |

### 2核2G 内存预算

| 组件 | 约占用 |
|---|---|
| 系统 + Docker | 400~500M |
| MySQL（缓冲池已调小到 64M） | 250~350M |
| 智能客服（含 milvus-lite） | 450~600M |
| 后端 + Redis + nginx | 200M |
| **合计** | **1.3~1.7G** |

> 建议仍开 2G swap 兜底——构建镜像时 pip 安装依赖会短暂吃满内存。

---

## 三、服务器目录结构

```
/opt/news_app/
├── docker-compose.yml                     编排文件（5 个服务）
├── news_check_system(back)/               后端代码（含 Dockerfile）
├── news_check_system(front)/              前端代码（含 Dockerfile + nginx.conf）
└── news_check_system(AI)/                 智能客服代码（含 Dockerfile + data/ + .env）
    └── data/                              ← 知识库文件，挂载进 ai 容器
        ├── doc_a_clean.md
        └── doc_b_clean.csv
```

---

## 四、查看状态

| 命令 | 作用 |
|---|---|
| `docker compose ps` | 本项目所有容器状态（最常用） |
| `docker ps` | 正在运行的容器 |
| `docker ps -a` | 所有容器（含已停止） |
| `docker images` | 本地镜像 |
| `docker network ls` | 网络列表 |
| `docker volume ls` | 数据卷列表 |
| `docker stats` | 实时 CPU/内存占用 |
| `df -h /` | 磁盘剩余 |
| `free -h` | 内存占用 |

---

## 五、镜像操作

| 命令 | 作用 |
|---|---|
| `docker build -t 名字:标签 .` | 用当前目录 Dockerfile 构建镜像 |
| `docker rmi 名字:标签` | 删除镜像 |
| `docker image prune` | 清理悬空镜像（`<none>`） |
| `docker image inspect 名字:标签 --format '{{.Created}}'` | 查看镜像构建时间 |

---

## 六、容器操作

| 命令 | 作用 |
|---|---|
| `docker logs -f 容器名` | 实时日志（Ctrl+C 退出，不影响容器） |
| `docker logs --tail=50 容器名` | 看最后 50 行 |
| `docker exec -it 容器名 bash` | 进入容器内部 |
| `docker exec 容器名 命令` | 在容器里执行一条命令 |
| `docker stop / start / restart 容器名` | 停止 / 启动 / 重启 |
| `docker rm -f 容器名` | 强制删除容器（镜像仍在） |
| `docker run -d --name 名字 -p 宿主:容器 镜像` | 手动创建并启动容器 |

---

## 七、Compose 操作（日常主力）

| 命令 | 作用 |
|---|---|
| `docker compose up -d` | 启动全部（镜像不存在才构建） |
| `docker compose up -d --build` | **强制重新构建再启动**（改代码必用） |
| `docker compose up -d --build backend` | 只重建某个服务 |
| `docker compose ps` | 查看本项目容器状态 |
| `docker compose logs -f backend` | 实时看某服务日志 |
| `docker compose restart web` | 重启某服务（不重建） |
| `docker compose build web` | 只构建不启动 |
| `docker compose stop` | 停止（容器保留） |
| `docker compose start` | 启动已停止的 |
| `docker compose down` | 停止并删除容器+网络（**数据卷保留**） |
| `docker compose down -v` | ⚠️ 连数据卷一起删（**数据全丢**） |
| `docker compose config --services` | 列出服务名（校验 YAML 是否正常） |
| `docker compose config` | 打印完整解析结果 |

---

## 八、五个固定套路

### ① 改了后端代码

```bash
cd /opt/news_app
docker compose up -d --build backend
docker compose restart web          # 后端重建后 IP 变了，nginx 必须重启
```

### ② 改了前端（html / js / css / nginx.conf）

```bash
cd /opt/news_app
docker compose up -d --build web
```

### ③ 改了 docker-compose.yml

```bash
cd /opt/news_app
docker compose up -d
```

### ④ 更新知识库（不用重建镜像）

```bash
# 1. 修改知识库文件（或用 scp 覆盖）
nano /opt/news_app/news_check_system(AI)/data/doc_a_clean.md

# 2. 强制重建索引
curl -X POST http://127.0.0.1:8001/api/ai/init

# 3. 等 1~2 分钟生效
```

### ⑤ 排错三连

```bash
docker compose ps
docker compose logs --tail=50 backend
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
```

---

## 九、数据查询

```bash
# 进 MySQL 看表
docker compose exec mysql mysql -uroot -pLi123456789 --default-character-set=utf8mb4 -e "use news_app; show tables;"

# 新闻条数
docker compose exec mysql mysql -uroot -pLi123456789 -e "select count(*) from news_app.news;"

# Redis 所有键
docker compose exec redis redis-cli -a Li123456789 KEYS '*'

# 某个键的剩余存活时间（秒）
docker compose exec redis redis-cli -a Li123456789 TTL news:categories

# 客服容器的环境变量
docker compose exec ai printenv | grep -E 'DEEPSEEK|SI_|MILVUS'
```

> 往 MySQL 导入数据时必须加 `--default-character-set=utf8mb4`，否则中文乱码。

---

## 十、网络与数据卷

```bash
# 看容器各自的 IP
docker network inspect news_app_default --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'

# 看数据卷在磁盘上的位置
docker volume inspect news_app_mysql_data
```

- 网络：`news_app_default`（compose 自动创建，自定义 bridge，**内置 DNS**）
- 容器之间用**服务名**访问：`mysql:3306`、`backend:8000`、`ai:8001`
- 容器 IP 是 172.18.x，重建后会变，所以代码里从不写 IP

---

## 十一、常见故障对照

| 现象 | 原因 | 处理 |
|---|---|---|
| 改了代码但没生效 | `up -d` 不会重建已有镜像 | `up -d --build` |
| 网站 502 | 后端重建后 nginx 缓存了旧 IP | `docker compose restart web` |
| 页面能开但接口 500 | 后端报错 | `docker compose logs --tail=50 backend` |
| 中文乱码 | MySQL 连接没指定字符集 | 加 `--default-character-set=utf8mb4` |
| 容器反复 Restarting | 启动崩溃 | `docker compose logs --tail=100 服务名` |
| Milvus 报 `embedded etcd can not be used under distributed mode` | 缺部署模式变量 | compose 加 `DEPLOY_MODE=STANDALONE`、`CLUSTER_ENABLED=false` |
| 端口被占 | 宿主机已有程序占用 | `ss -lntp \| grep 8080` |
| AI 回"知识库暂无相关信息" | 检索置信度低 / Key 额度不足 | 看 `docker compose logs ai`；查硅基流动余额 |
| AI 回"Milvus 未启动" | 向量库连不上 | lite 模式下看 `docker compose logs ai`；确认 `MILVUS_MODE=lite`、`/app/milvus_data` 可写 |
| 公网打不开 | 安全组没放行 | 腾讯云 → 安全组 → 入站规则加 TCP:8080 |

---

## 十二、部署信息备忘

| 项目 | 值 |
|---|---|
| 系统 | Ubuntu 24.04 LTS |
| 规格 | 2核 4G（3.6G 可用）+ swap |
| 磁盘 | 50G |
| 项目目录 | `/opt/news_app` |
| 对外端口 | 8080（安全组放行 TCP:8080） |
| MySQL 库名 | `news_app`（8 张表） |
| Redis 键 | `news:categories`、`news_list:{分类}{页}{条数}` |
| 向量库 | milvus-lite，文件 `/app/milvus_data/milvus.db`，集合 `doc_chunks` |
| 密码 | 见 `docker-compose.yml`（当前 `Li123456789`，**上线前改成强密码**） |
| API Key | `/opt/news_app/news_check_system(AI)/.env` |

---

## 十三、更新代码的标准流程（本地 → 服务器）

```powershell
# 1. 本地改代码

# 2. 上传（只传改动的文件，或整个文件夹）
scp "D:\RAG\news_check_system(back)\config\db_config.py" ubuntu@服务器IP:/home/ubuntu/

# 3. 服务器上放到位
mv /home/ubuntu/db_config.py "/opt/news_app/news_check_system(back)/config/db_config.py"

# 4. 重建并重启
cd /opt/news_app
docker compose up -d --build backend
docker compose restart web
```

> `/opt/news_app` 属于 root，而 scp 用的是 `ubuntu` 账号，所以必须"先传到 /home/ubuntu，再 mv 进项目"。

---

## 十四、待办收尾项

- [ ] MySQL / Redis 密码改成强密码（改 `docker-compose.yml` + 重建）
- [ ] 公网 IP 换弹性 IP（EIP）或绑域名，避免重启后地址变化
- [ ] MySQL 定时备份（cron + `mysqldump`）
- [ ] 真实重启验证：`reboot` 后确认 5 个容器自动恢复
- [ ] 如需 HTTPS：加一层 Caddy，或在 nginx 里配证书

---

## 十五、从零重建清单（换服务器 / 重装系统时翻这里）

> 前提：本地 `D:\RAG` 里的三份代码 + `docker-compose.yml` + `database.sql` 都在。
> 说明：compose 里没有写死任何 IP，**换服务器不需要改任何文件**。

### 第 1 步：买服务器

| 项 | 选择 |
|---|---|
| 类型 | 轻量应用服务器（更便宜）或 CVM |
| 系统 | **Ubuntu 24.04 LTS 64 位** |
| 规格 | **2 核 2G** 可用（已改 milvus-lite）；预算够选 2核4G 更稳 |
| 磁盘 | 40~50G |
| 带宽 | 3~5 Mbps |
| 计费 | 长期放链接 → **包年包月**（按量计费 24h 运行很贵） |

### 第 1.5 步：加 Swap（2G 机器必做，否则构建镜像可能被 OOM 杀掉）

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h      # 确认 Swap 那行有 2.0Gi
```

### 第 2 步：装 Docker（Ubuntu 24.04，阿里云源）

```bash
apt-get update && apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu noble stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker.io docker-compose-v2
systemctl enable --now docker
```

### 第 3 步：配镜像加速（不配拉不到镜像）

```bash
mkdir -p /etc/docker
tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com", "https://docker.m.daocloud.io"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
systemctl daemon-reload && systemctl restart docker
docker pull hello-world     # 验证能拉
```

### 第 4 步：上传代码（本地 Windows PowerShell）

```powershell
cd D:\RAG
scp -r "news_check_system(back)" ubuntu@服务器IP:/home/ubuntu/
scp -r "news_check_system(front)" ubuntu@服务器IP:/home/ubuntu/
scp -r "news_check_system(AI)" ubuntu@服务器IP:/home/ubuntu/
scp "docker-compose.yml" ubuntu@服务器IP:/home/ubuntu/
```

### 第 5 步：服务器上放到位

```bash
mkdir -p /opt/news_app
cd /opt/news_app
mv /home/ubuntu/news_check_system* /home/ubuntu/docker-compose.yml /opt/news_app/
ls        # 确认四个东西都在
```

### 第 6 步：构建并启动（首次 5~10 分钟）

```bash
cd /opt/news_app
docker compose up -d --build
docker compose ps        # 等 5 个容器 Up，mysql/redis 变 healthy
```

### 第 7 步：导入数据库（必须带 utf8mb4）

```bash
# database.sql 先 scp 到 /home/ubuntu/
cd /opt/news_app
docker compose exec -T mysql mysql -uroot -pLi123456789 --default-character-set=utf8mb4 < /home/ubuntu/database.sql
```

### 第 8 步：建知识库索引

```bash
curl -X POST http://127.0.0.1:8001/api/ai/init
```

### 第 9 步：放行端口

腾讯云控制台 → 安全组（或轻量的防火墙）→ 入站规则 → `TCP:8080`，来源 `0.0.0.0/0`。

### 第 10 步：验证

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
curl -s -X POST http://127.0.0.1:8080/api/ai/chat \
  -H "Content-Type: application/json" -d '{"question":"你好"}'
curl -s "http://127.0.0.1:8080/api/news/categories" | head -c 200
```

### 重建时哪些会重新生成，哪些必须带过去

| 数据 | 会不会丢 | 说明 |
|---|---|---|
| 业务数据（新闻/用户/收藏） | ❌ 靠 `database.sql` 恢复 | **必须本地留一份** |
| 知识库索引（Milvus 向量） | ✅ 自动重算 | 花几分钟 + 消耗 embedding 额度 |
| Redis 缓存 | ✅ 无所谓 | 自动重建，首屏慢一点 |
| 镜像 | ✅ 重新 build | 约 5 分钟 |
| API Key | ❌ 靠 `news_check_system(AI)/.env` | 本地留一份（勿外传） |
| 域名 / EIP | ❌ 服务器上没了就是没了 | 控制台重新绑 |
