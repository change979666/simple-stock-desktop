from sqlalchemy import (
    Column, Integer, String, Text, Float,
    ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..session import Base


class Category(Base):
    """产品类别"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    
    products = relationship('Product', back_populates='category')


class Product(Base):
    """产品基本信息"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String(100), nullable=True)  # 已不再使用，允许NULL
    description = Column(Text)
    parent_sku = Column(String(50), unique=True, nullable=False, index=True)
    stock_warning_level = Column(Integer, nullable=True)  # 已改为系统设置，允许NULL
    created_at = Column(DateTime, server_default=func.now())
    
    category = relationship('Category', back_populates='products')
    variants = relationship(
        'ProductVariant',
        back_populates='product',
        cascade="all, delete-orphan",  # 添加级联删除
        passive_deletes=True  # 启用被动删除
    )


class ProductVariant(Base):
    """产品变体（具体型号）"""
    __tablename__ = 'product_variants'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(20))
    size = Column(String(20))
    option_name = Column(String(100))
    cost_price = Column(Float, nullable=False, default=0.0)
    # 当前库存数量 - 直接存储，提升查询性能
    current_stock = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    product = relationship(
        'Product',
        back_populates='variants',
        single_parent=True  # 确保每个变体只属于一个产品
    )
    stock_logs = relationship(
        'StockLog',
        back_populates='variant',
        cascade="all, delete-orphan"  # 级联删除库存记录
    )
    sale_records = relationship(
        'SaleRecord',
        back_populates='variant',
        passive_deletes=True  # 启用被动删除销售记录
    )
