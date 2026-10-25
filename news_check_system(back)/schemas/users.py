from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

#用户请求账号密码（用于登录和注册）
class user(BaseModel):
    username: str
    password: str




#用户自定义信息模型类
class UserInfoBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")

#用户基本信息模型类
class UserInfoResponse(UserInfoBase):
    id: int
    username: str

    model_config = ConfigDict(
        from_attributes=True  # 允许从 ORM 对象属性中取值
    )
#以上两者加起来为全部用户信息

#用户信息响应格式模型类
class UserAuthResponse(BaseModel):
    token: str
    user_info: UserInfoResponse = Field(..., alias="userInfo")

    model_config = ConfigDict(
        populate_by_name=True,  # alias / 字段名兼容
        from_attributes=True  # 允许从 ORM 对象属性中取值
    )


# 用户更新信息的模型类
class UserUpdateRequest(BaseModel):
    nickname: str = None
    avatar: str = None
    gender: str = None
    bio: str = None
    phone: str = None


#更改密码请求传入的模型类，包含新旧密码
class UserChangePassword(BaseModel):
    old_password:str = Field(...,alias='oldPassword',description = '旧密码')
    new_password:str = Field(...,min_length=6,alias='newPassword',description = '新密码')

