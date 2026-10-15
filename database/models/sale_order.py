from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from ..session import Base

class SaleOrder(Base):
    """销售订单主表"""
    __tablename__ = 'sale_orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(100), nullable=False)
    order_date = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False, default=0)
    items = relationship("OrderItem", back_populates="order")
    
class OrderItem(Base):
    """订单明细表"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('sale_orders.id'), nullable=False)
    parent_sku = Column(String(50), nullable=False)
    variant_sku = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    item_price = Column(Float, nullable=True)  # 单个SKU的金额，允许为空
    
    order = relationship("SaleOrder", back_populates="items")