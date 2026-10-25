from fastapi import APIRouter
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_session
from crud.news import get_Categories, get_news_list, get_news_count, get_news_detail, increase_view_count, \
    get_related_news
from models.users import User
from schemas.users import user, UserInfoResponse, UserAuthResponse, UserUpdateRequest, UserChangePassword
from crud.users import get_userinfo_by_username, create_user, get_token, authenticate_user, update_user, change_password
from utils.auth import get_current_user
from utils.response import success_response

users_router = APIRouter(prefix='/api/user',tags=['users'])


#用户注册路由，网页请求信息user包含用户名和密码
@users_router.post('/register')
async def register(user_data:user,session:AsyncSession=Depends(get_session)):
    #先根据用户名查询用户名存不存在（用户名是唯一的）
    existing = await get_userinfo_by_username(session,user_data.username)
    if existing:
        raise HTTPException(status_code=400,detail="用户已存在")
    #不存在则创建用户，将用户信息写入数据库，并生成一个token给当前用户
    new_user = await create_user(session,user_data)
    token =await get_token(session,new_user.id)

    #返回的数据格式
    # return {
    #     "code": 200,
    #     "message": "注册成功",
    #     "data": {
    #         "token": token,
    #         "userInfo": {
    #             "id": new_user.id,
    #             "username": new_user.username,
    #             "bio": new_user.bio,  #用户简介
    #             "avatar": new_user.avatar,    #用户头像地址
    #         }
    #     }
    # }
    #定义数据格式（用到三个模型类）
    user_data = UserAuthResponse(token=token,user_info=UserInfoResponse.model_validate(new_user))
    return success_response(message='注册成功',data=user_data)



#用户登录路由，请求信息user为账号密码
@users_router.post('/login')
async def login(user_data:user,session:AsyncSession=Depends(get_session)):
    #通过账号密码查询数据库返回用户信息
    user_info = await authenticate_user(user_data.username,user_data.password,session)
    #如果返回None说明用户名或密码错误，没有用户信息
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="用户名或密码错误")
    #如果正确，责根据id生成一个token
    token = await get_token(session,user_info.id)

    user_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user_info))
    return success_response(message='登陆成功', data=user_data)


#获取用户主页详细信息路由
@users_router.get('/info')
async def user_info(user_info:User=Depends(get_current_user)):
    #依赖注入验证token并返回用户信息（orm对象形式），直接输出即可
    return success_response(message='获取用户信息成功', data=UserInfoResponse.model_validate(user_info))


#更新用户数据路由
@users_router.put('/update')
async def update(user_data:UserUpdateRequest,user_info:User=Depends(get_current_user),session:AsyncSession=Depends(get_session)):
    updated_user = await update_user(session,user_data,user_info.username)
    #返回更新后的数据
    return success_response(message='修改用户信息成功', data=UserInfoResponse.model_validate(updated_user))


#修改密码路由
@users_router.put('/password')
async def update_password(password:UserChangePassword,
                   user:User=Depends(get_current_user),
                   session:AsyncSession=Depends(get_session)):
    res_change_pwd = await change_password(session,user,password.old_password,password.new_password)
    if not res_change_pwd:
        #返回False则说明修改失败
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail='修改密码失败')
    return success_response(message='密码修改成功')