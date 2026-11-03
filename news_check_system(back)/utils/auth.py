
#根据
from typing import Optional

from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_session
from crud.users import get_user_by_token


def _extract_token(authorization: str) -> str:
    """从 Authorization 头里取出 token。

    兼容两种写法（历史遗留导致前端一直发裸 token）：
      "Bearer <token>"  -> 标准写法，推荐
      "<token>"         -> 老写法，继续支持，避免老客户端突然全部 401
    """
    token = (authorization or "").strip()
    lower = token.lower()
    # "Beared" 是早期代码里的拼写错误，顺手兼容掉
    for prefix in ("bearer ", "beared "):
        if lower.startswith(prefix):
            token = token[len(prefix):].strip()
            break
    return token


#验证token，authorization为前端返回数据中的一部分，其中包含token
async def get_current_user(authorization:Optional[str]=Header(None,alias='Authorization'),
                           session:AsyncSession=Depends(get_session)):
    # 没带 Authorization 头：这属于"未登录"，应该回 401。
    # 如果把该参数写成必填，FastAPI 会先返回 422「缺少必填参数」，语义不对，前端也不好判断该不该跳登录页
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='未登录，请先登录')
    #authorization形式为'Bearer token'或裸 token，两种都能解析
    token = _extract_token(authorization)
    #根据token查询用户信息
    user_info = await get_user_by_token(session,token)
    if not user_info:
        #如果用户信息不存在则返回401错误
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='令牌无效或过期')
    #存在则返回用户信息
    return user_info
