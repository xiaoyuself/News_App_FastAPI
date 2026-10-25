# 新闻软件前端（无构建依赖 · 手机风格单页应用）

为 `新闻软件（无前端）` FastAPI 后端制作的前端页面。
纯原生 HTML/CSS/JS 实现，**不需要安装 Node.js / npm**，双击或用一行命令即可启动。

---

## 一、功能总览

底部三个分区（从左到右）：**新闻** / **AI对话** / **个人中心**

| 页面 | 功能 |
|---|---|
| 新闻 | 顶部新闻分类切换；点击分类展示该分类新闻列表（分页加载）；点击新闻进入详情 |
| 新闻详情 | 展示标题/作者/时间/浏览量/正文；**右上角收藏按钮**（需登录）；进入时自动记录浏览历史（需登录）；**底部同类推荐**：同分类浏览量最高的 5 条新闻 |
| AI对话 | 内置智能客服助手（LangChain + Milvus RAG，知识库来自 `智能客服/knowledge.txt`），支持快捷提问 |
| 个人中心 | **首次进入需注册**（用户名唯一，注册成功发放 token 自动登录）；展示头像/用户名/个性签名；提供**详细信息、收藏列表、浏览记录、修改密码**四个功能；修改密码需输入原密码 + 两次新密码 |

---

## 二、项目结构

```
新闻软件前端/
├── index.html          入口页面
├── css/style.css       全部样式（手机风格）
├── js/
│   ├── config.js       配置：后端地址 / AI 服务地址
│   ├── utils.js        工具：toast、日期格式化、存储等
│   ├── api.js          API 请求层（token、数据归一化、错误处理、AI 接口）
│   ├── router.js       hash 路由
│   ├── app.js          入口：头部/底部 Tab 控制
│   └── views/
│       ├── news.js     新闻列表
│       ├── detail.js   新闻详情（收藏 + 推荐）
│       ├── chat.js     AI 对话
│       └── profile.js  个人中心（注册/登录/资料/收藏/历史/改密码）
├── README.md           本文件
└── 修改说明.md          所有代码改动的详细说明
```

---

## 三、启动步骤

### 第 1 步：启动后端（必须）

后端依赖 **MySQL（数据库 `news_app`）** 和 **Redis**。

> ⚠️ **务必先启动 Redis 和 MySQL 再启动后端！**
> 新闻分类/新闻列表接口会先查 Redis 缓存（`cache_config.py`）。Redis 未启动时，
> 接口可能长时间挂起不返回，导致前端新闻页面**一直显示"加载中"**。
> 已踩坑验证：启动 Redis 后页面立即恢复正常。
> Windows 服务启动方式：`net start Redis`（或服务管理器启动 Redis 服务）。

```bash
cd "D:\新闻软件内置智能客服\新闻软件（无前端）"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> 请使用你运行该后端时的 Python 环境（PyCharm 中配置的解释器）。
> 本机检测到的环境依赖情况（供参考）：
> - `D:\miniconda\python.exe`（3.13）有 fastapi / sqlalchemy，但**缺 aiomysql、redis**；
> - 若后端启动报 `ModuleNotFoundError`，先安装缺失依赖：
>   `pip install fastapi uvicorn sqlalchemy aiomysql redis passlib bcrypt`
>
> 确认 `http://localhost:8000` 能访问（浏览器打开可见 `{"message":"Hello World"}`）。
> 首次使用需要数据库里已有新闻分类和新闻数据（`news_category`、`news` 表）。

### 第 2 步：启动前端

前端是纯静态页面，任选一种方式：

**方式 A（最简单）：直接双击**
直接双击 `index.html`，用浏览器打开即可使用。

**方式 B：Python 静态服务器（推荐，更接近真实环境）**
```bash
cd "D:\新闻软件内置智能客服\新闻软件前端"
python -m http.server 8080
```
浏览器访问 http://localhost:8080

**方式 C：任意静态服务器**
```bash
npx serve 新闻软件前端      # 需要 Node.js
```
或使用 VS Code 的 Live Server 插件等。

> 前端默认请求后端地址 `http://localhost:8000`，如需修改，编辑 `js/config.js` 中的 `API_BASE_URL`。

### 第 3 步（可选）：启动 AI 智能客服服务

AI 对话页依赖独立的 AI 服务（LangChain + Milvus），**不启动也能打开页面**，
但提问时会收到"智能客服暂时无法回答"的提示。

> ⚠️ **需要先自行部署并启动 Milvus 服务**（默认 `http://localhost:19530`），AI 问答才能使用知识库。
> - Milvus 是知识库向量数据库，部署方式由你自行选择（Docker 部署 Milvus Standalone 等）；
> - 未启动 Milvus 时：问候语（你好/您好）仍可直接回复，其余提问会返回"知识库服务（Milvus）不可用"提示
>   （新版已做快速探测 + 超时保护，不会卡住）；
> - "你好/您好"等问候语直接回复，不依赖知识库。

启动 AI 服务需要：Milvus 服务已启动、`智能客服/.env` 中 API Key 有效、
已安装 langchain、pymilvus 等依赖（运行过 `main.ipynb` 即说明环境就绪）。

> 本机已验证 `D:\miniconda\envs\langchain1.2` 环境（Python 3.13）依赖齐全
> （langchain 1.2.12 / pymilvus 2.6.12 / fastapi / uvicorn），可直接使用：
> `D:\miniconda\envs\langchain1.2\python.exe ai_server.py`

```bash
cd "D:\新闻软件内置智能客服\智能客服"
python ai_server.py
```

服务运行在 `http://localhost:8001`。服务启动时若 Milvus 可达会自动构建知识库（首次约需 1~2 分钟）。
如需强制重建知识库（修改 `knowledge.txt` 后），调用一次：

```bash
curl -X POST http://localhost:8001/api/ai/init
```

前端 AI 服务地址配置在 `js/config.js` 的 `AI_BASE_URL`（默认 `http://localhost:8001`）。

---

## 四、使用说明

1. **注册登录**：进入"个人中心"，首次使用请注册（用户名唯一），注册成功自动登录；
   老用户可切换到"登录"页签。
2. **浏览新闻**：新闻页顶部点分类 → 列表点新闻 → 详情页阅读，底部有同类推荐。
3. **收藏新闻**：登录后，在详情页右上角点 ☆ 收藏，★ 表示已收藏，再点取消。
4. **浏览记录**：登录后浏览新闻自动记录，可在个人中心 → 浏览记录查看/删除/清空。
5. **修改密码**：个人中心 → 修改密码，输入原密码 + 两次一致的新密码（不少于 6 位）。
6. **AI 对话**：AI对话页可直接提问（如"如何注册账号？"），也可点快捷问题。

---

## 五、常见问题

**Q：页面报"无法连接服务器"？**
A：后端未启动或地址不对。先完成第 1 步，确认 http://localhost:8000 可访问；再检查 `js/config.js`。

**Q：新闻页面一直显示"加载中"？**
A：绝大多数情况是 **Redis 未启动**。后端新闻列表/分类接口依赖 Redis 缓存，Redis 未启动时接口会挂起不返回。
先启动 Redis 服务（`net start Redis`）再重启后端即可。

**Q：登录后请求 401？**
A：后端 token 解析有特殊写法（详见 `修改说明.md`），前端已按"发送原始 token、不带 Bearer 前缀"
的方式适配，正常无需处理。若仍 401，请重新登录获取新 token。

**Q：收藏列表/浏览记录打开报错？**
A：收藏列表接口已修复（`crud/favorite.py` 的 `lable` 拼写错误，详见 `修改说明.md`）；
请确认后端是修改后的代码并已重启（`uvicorn --reload` 会自动生效）。

**Q：AI 对话提示"智能客服服务暂未连接"？**
A：AI 服务未启动。按第 3 步启动 `智能客服/ai_server.py` 即可；也可先跳过，不影响其他功能。
