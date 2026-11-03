from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routers import news,users,favorite,history
from utils.exception import register_exception_handlers

app = FastAPI()

register_exception_handlers(app)
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


#挂载路由
app.include_router(news.news_router)
app.include_router(users.users_router)
app.include_router(favorite.router)
app.include_router(history.router)


# 响应压缩：新闻详情一条正文就有几 KB，JSON 普遍能压到 1/4~1/6，
# 手机弱网下首屏明显更快（请求头不带 Accept-Encoding 的客户端不受影响）
app.add_middleware(GZipMiddleware, minimum_size=512)


app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    # 关掉 credentials：浏览器规范不允许 "允许任意域名" 与 "携带 Cookie 凭据" 同时成立，
    # 本项目鉴权靠 Authorization 头而不是 Cookie，设成 False 才是规范用法
    allow_credentials = False,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# 支持直接在 PyCharm 里右键运行本文件（等价于 uvicorn main:app --port 8000）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
