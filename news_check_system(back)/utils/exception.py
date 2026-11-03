import traceback

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

# 开发模式：返回详细错误信息
# 生产模式：返回简化错误信息
DEBUG_MODE = True  # 教学项目保持开启


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTPException 异常
    """
    # HTTPException 通常是业务逻辑主动抛出的，data 保持 None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


# pydantic 的英文报错 -> 中文提示（只翻译最常碰到的几种，其余原样带出）
_VALIDATION_MSG = {
    "Field required": "缺少必填参数",
    "Input should be a valid string": "需要是文本",
    "Input should be a valid integer": "需要是整数",
    "Input should be a valid integer, unable to parse string as an integer": "需要是整数",
    "Input should be a valid number, unable to parse string as a number": "需要是数字",
    "Input should be a valid boolean": "需要是 true/false",
    "String should have at least 6 characters": "长度不能少于 6 个字符",
    "String should have at most 50 characters": "长度不能超过 50 个字符",
}


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求参数校验失败（422）。

    默认 FastAPI 会把错误返回成 {"detail": [ {...}, {...} ]}（一个数组），
    前端拿 message 拿不到，只能显示成 [object Object]。
    这里统一成和其它接口一致的 {code, message, data} 信封，并把字段名拼进提示。
    """
    parts = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path"))
        raw = err.get("msg", "")
        msg = _VALIDATION_MSG.get(raw, raw or "格式不正确")
        parts.append(f"{loc}（{msg}）" if loc else msg)
    detail = "；".join(parts) or "请求参数有误"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": f"参数校验失败：{detail}",
            "data": None
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    处理数据库完整性约束错误

    MySQL 的报错原文形如：
      Duplicate entry 'tom' for key 'username_UNIQUE'      -> 用户名重复
      Duplicate entry '1-3' for key 'user_news_unique'      -> 同一用户重复收藏同一新闻
      Cannot add or update a child row: a foreign key ...   -> 外键不存在
    必须按"具体的约束名"分别判断，不能见到 Duplicate entry 就当成用户名重复。
    """
    error_msg = str(exc.orig)

    # 判断具体的约束错误类型（顺序很重要：先具体、后笼统）
    if "username_UNIQUE" in error_msg:
        detail = "用户名已存在"
    elif "phone_UNIQUE" in error_msg:
        detail = "该手机号已被其他账号使用"
    elif "user_news_unique" in error_msg:
        detail = "这条新闻已经在收藏夹里了"
    elif "FOREIGN KEY" in error_msg:
        detail = "关联数据不存在"
    elif "Duplicate entry" in error_msg:
        detail = "数据已存在，请勿重复提交"
    else:
        detail = "数据约束冲突，请检查输入"

    # 开发模式下返回详细错误信息
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": detail,
            "data": error_data
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    处理 SQLAlchemy 数据库错误
    """
    # 开发模式下返回详细错误信息
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            # 格式化异常信息为字符串，方便日志记录和调试
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "数据库操作失败，请稍后重试",
            "data": error_data
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的异常
    """
    # 开发模式下返回详细错误信息
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            # 格式化异常信息为字符串，方便日志记录和调试
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": error_data
        }
    )



def register_exception_handlers(app):
    """
    注册全局异常处理：子类在前，父类在后；具体在前，抽象在后
    """
    app.add_exception_handler(HTTPException, http_exception_handler)  # 业务
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # 入参校验(422)
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # 数据完整性约束
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)  # 数据库
    app.add_exception_handler(Exception, general_exception_handler)  # 兜底
