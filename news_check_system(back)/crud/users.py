from datetime import datetime,timedelta

import uuid
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken
from schemas.users import user, UserUpdateRequest
from utils import security
from utils.security import get_hash_password,verify_password


#通过用户名查询数据库中用户信息
async def get_userinfo_by_username(session:AsyncSession,username:str):
    order = select(User).where(User.username == username)
    result = await session.execute(order)
    #如果没查到则返回None
    return result.scalar_one_or_none()

#创建用户
async def create_user(session:AsyncSession,user_info:user):
    #将用户注册的密码加密
    new_password = get_hash_password(user_info.password)
    #整合用户名和加密的密码
    new_user_info = User(
        username = user_info.username,
        password = new_password,
    )
    session.add(new_user_info)
    await session.commit()
    await session.refresh(new_user_info)
    return new_user_info


#为用户生成一个token并存入数据库
async def get_token(session:AsyncSession,user_id:int):
    #生成token并定义到期时间（7天）
    new_token = str(uuid.uuid4())
    new_expires_at = datetime.now() + timedelta(days=7)
    #先查询数据库中当前用户是否有token
    order = select(UserToken).where(UserToken.user_id == user_id)
    res = await session.execute(order)
    token = res.scalar_one_or_none()
    #如果当前用户有token，更新token数据（给与一个新token并更新到期时间）
    if token:
        token.expires_at = new_expires_at
        token.token = new_token
    #没有则添加新数据
    else:
        session.add(UserToken(user_id=user_id,token=new_token,expires_at=new_expires_at))
    await session.commit()
    #不管更没更新数据，当前用户的token都为新生成的new_token
    return new_token


#验证用户账号密码是否正确
async def authenticate_user(username:str,password:str,session:AsyncSession):
    #先用用户名查询用户信息
    user = await get_userinfo_by_username(session,username)
    #如果查不到，说明用户不存在，返回None
    if not user:
        return None
    #用户存在则验证密码，因为密码是hash加密后存入数据库的，所以要验证密码
    #如果验证密码返回False说明密码不匹配即密码错误，返回None
    if not verify_password(password,user.password):
        return None
    #验证成功返回用户信息
    return user

#通过token获取用户信息
async def get_user_by_token(session:AsyncSession,token:str):
    #先获取user_token表中的数据
    order = select(UserToken).where(UserToken.token == token)
    res = await session.execute(order)
    db_token_info = res.scalar_one_or_none()
    #如果token不存在或者到期，返回None
    if not db_token_info or db_token_info.expires_at < datetime.now():
        return None
    #user_token表返回的用户id进入用户表查询用户数据
    order = select(User).where(User.id == db_token_info.user_id)
    result = await session.execute(order)
    return result.scalar_one_or_none()


#更新数据库中的用户信息
async def update_user(session:AsyncSession,user_date:UserUpdateRequest,user_name:str):
    #根据用户名修改对应的数据，其中user_date是自定义的模型类，需要先转成字典再转成k=v形式，参数设置为排除空值和默认值
    order = update(User).where(User.username == user_name).values(**user_date.model_dump(
        exclude_none=True,
        exclude_unset=True,
    ))
    res = await session.execute(order)
    await session.commit()
    #如果没有受影响的行数，报错
    if res.rowcount == 0:
        raise HTTPException(status_code=404,detail='用户不存在')
    #修改完成后再通过用户名获取更新后的信息
    updated_info = await get_userinfo_by_username(session,user_name)
    return updated_info


async def change_password(session:AsyncSession,user:User,old_password:str,new_password:str):
    #先验证用户输入的原密码是否和旧密码相同
    if not security.verify_password(old_password,user.password):
        return False
    #先将新密码加密
    new_hashed_password = get_hash_password(new_password)
    #通过user数据库模型类直接修改密码然后刷新数据库
    user.password = new_hashed_password
    await session.commit()
    await session.refresh(user)
    #返回成功
    return True





