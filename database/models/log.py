from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..session import Base


class ActionLog(Base):
    """操作日志"""
    __tablename__ = 'action_logs'
    
    id = Column(Integer, primary_key=True)
    action = Column(String(500), nullable=False)  # 统一使用action作为字段名
    operator_info = Column(String(500), nullable=False)  # 存储格式：'名字 (IP地址)'
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())


class StockLog(Base):
    """库存变动记录"""
    __tablename__ = 'stock_logs'
    
    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey('product_variants.id'), nullable=False)
    change_quantity = Column(Integer, nullable=False)  # 正数为入库，负数为出库
    notes = Column(String(200))
    operator_info = Column(String(500), nullable=False)  # 存储格式：'名字 (IP地址)'
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    
    variant = relationship(
        'ProductVariant',
        back_populates='stock_logs',
        primaryjoin='StockLog.variant_id == ProductVariant.id'
    )
