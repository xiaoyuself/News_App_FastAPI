
#根据
from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_session
from crud.users import get_user_by_token


#验证token，authorization为前端返回数据中的一部分，其中包含token
async def get_current_user(authorization:str=Header(...,alias='Authorization'),
                           session:AsyncSession=Depends(get_session)):
    #authorization形式为'Bearer token'，可以用两种方式提取token
    # token = authorization.split(' ')[1]
    token = authorization.replace("Beared","")
    #根据token查询用户信息
    user_info = await get_user_by_token(session,token)
    if not user_info:
        #如果用户信息不存在则返回401错误
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='令牌无效或过期')
    #存在则返回用户信息
    return user_info

