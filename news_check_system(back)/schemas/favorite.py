from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from schemas.base import NewsItemBase

#新闻状态模型类
class FavoriteCheckResponse(BaseModel):
    is_favorite : bool = Field(...,alias='isFavorite')

#添加新闻模型类
class FavoriteAddRequest(BaseModel):
    news_id:int = Field(...,alias='newsId')

class FavoriteNewsItemResponse(NewsItemBase):
    favorite_id: int = Field(...,alias='favoriteId')
    favorite_time: datetime = Field(...,alias='favoriteTime')

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

class FavoriteListRequest(BaseModel):
    list:list[FavoriteNewsItemResponse]
    total:int
    has_more:bool = Field(...,alias='hasMore')

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )