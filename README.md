# 新闻资讯平台（内置 RAG 智能客服）

一个可私有化部署的新闻资讯应用：新闻浏览、用户体系、收藏与浏览历史，并内置基于 RAG 的智能客服。

## 功能

| 模块 | 功能 |
|---|---|
| 新闻 | 分类切换、分页列表、详情页、同类推荐、浏览量统计 |
| 用户 | 注册、登录（token 鉴权）、资料修改、密码修改 |
| 互动 | 收藏 / 取消收藏、浏览历史记录 |
| 智能客服 | 基于知识库的问答：混合检索（向量 + BM25 + RRF + 精排）→ 大模型生成 → 真实性守卫 → 兜底 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | 原生 HTML / CSS / JavaScript（无构建依赖，手机风格单页） |
| 后端 | Python 3.12、FastAPI、SQLAlchemy（异步）、aiomysql、Pydantic |
| 存储 | MySQL 8（业务数据）、Redis 7（分类/列表缓存） |
| 智能客服 | LangChain、Milvus（向量库）、DeepSeek（生成）、硅基流动（Embedding / Rerank） |
| 部署 | Docker、Docker Compose、nginx 反向代理 |

## 目录结构

```
.
├── news_check_system(front)/     前端：index.html + css/ + js/
│   ├── Dockerfile                nginx 镜像
│   └── nginx.conf                静态资源 + /api/ 反向代理
├── news_check_system(back)/      后端：FastAPI
│   ├── main.py                   入口
│   ├── config/                   数据库、Redis 配置（读环境变量）
│   ├── routers/ crud/ models/    路由、数据访问、ORM 模型
│   └── Dockerfile
├── news_check_system(AI)/        智能客服：ai_server.py
│   ├── data/                     知识库（Markdown 手册 + CSV 记录表）
│   ├── vector_store.py           混合检索 + Milvus 读写
│   ├── generator.py              生成
│   └── Dockerfile
├── docker-compose.yml            一键编排 6 个容器
├── database.sql                  数据库结构 + 初始数据
└── Docker部署速查手册.md          部署、运维、排错、从零重建清单
```

## 快速开始（Docker）

```bash
# 1. 准备密钥：复制模板并填入自己的 API Key
cp news_check_system(AI)/.env.example news_check_system(AI)/.env

# 2. 一键构建并启动（首次约 5~10 分钟）
docker compose up -d --build

# 3. 导入数据库
docker compose exec -T mysql mysql -uroot -pLi123456789 \
  --default-character-set=utf8mb4 < database.sql

# 4. 构建知识库索引
curl -X POST http://127.0.0.1:8001/api/ai/init

# 5. 打开浏览器
# http://localhost:8080
```

对外只暴露 8080 端口，MySQL / Redis / Milvus / 后端 / 客服全部只绑 127.0.0.1。

详细步骤、常见故障、从零重建流程见 [Docker部署速查手册.md](Docker部署速查手册.md)。

## 本地开发

```bash
# 后端（需本机 MySQL + Redis）
cd "news_check_system(back)"
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd "news_check_system(front)"
python -m http.server 8080
# 浏览器打开 http://localhost:8080
```

## 注意

- `.env` 含 API Key，**已被 .gitignore 排除**，请自行按 `.env.example` 配置
- 默认数据库口令仅用于本地/演示，生产环境请修改 `docker-compose.yml` 中的密码后重建
