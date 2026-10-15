"""销售记录模型"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from ..session import Base


class SaleRecord(Base):
    """销售记录表，用于记录产品变体的销售情况"""
    __tablename__ = 'sale_records'

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey('product_variants.id'), nullable=False)
    order_number = Column(String(50), nullable=False, index=True)
    quantity_sold = Column(Integer, nullable=False)
    unit_price = Column(Float)
    total_amount = Column(Float)
    order_date = Column(DateTime, nullable=False)

    variant = relationship(
        'ProductVariant',
        back_populates='sale_records',
        primaryjoin='SaleRecord.variant_id == ProductVariant.id'
    )