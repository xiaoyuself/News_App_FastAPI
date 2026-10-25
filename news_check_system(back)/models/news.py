from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Index, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#基类
class Base(DeclarativeBase):
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

#新闻种类
class Categories(Base):
    __tablename__ = 'news_category'

    id : Mapped[int] = Column(Integer, autoincrement = True,primary_key=True,comment='分类id')
    name : Mapped[str] = Column(String(50),unique=True,nullable = False,comment='分类名')
    sort_order : Mapped[int] = Column(Integer,default = 0,nullable = False,comment='分类排序')

    def __repr__(self):
        return f'<Categories(id={self.id},name={self.name},sort_order={self.sort_order})>'


#新闻列表
class News(Base):
    __tablename__ = "news"

    # 创建索引：提升查询速度
    __table_args__ = (
        Index('fk_news_category_idx', 'category_id'),
        Index('idx_publish_time', 'publish_time')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[str | None] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[str | None] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[str | None] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('news_category.id'), nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")

    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title}', views={self.views})>"