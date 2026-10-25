from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# 支持直接在 PyCharm 里右键运行本文件（等价于 uvicorn main:app --port 8000）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
