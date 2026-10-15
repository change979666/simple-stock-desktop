"""发货相关模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..session import Base


class InventoryShipment(Base):
    """发货单表"""
    __tablename__ = 'inventory_shipments'

    id = Column(Integer, primary_key=True)
    batch_number = Column(String, nullable=False)  # 批次号，用于标识一批发货
    # 使用String类型存储状态,避免枚举转换问题
    status = Column(String, nullable=False, default='pending')
    estimated_arrival = Column(DateTime)
    arrival_date = Column(DateTime)  # 实际到货日期
    operator = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    notes = Column(String)

    # 关系
    shipment_items = relationship(
        'ShipmentItem',
        back_populates='shipment',
        cascade='all, delete-orphan',
        lazy='joined'  # 这将自动加载关联的 shipment_items
    )
    transit_logs = relationship(
        'InventoryTransitLog',
        back_populates='shipment',
        cascade='all, delete-orphan'
    )


class ShipmentItem(Base):
    """发货单明细表"""
    __tablename__ = 'shipment_items'

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey('inventory_shipments.id'), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variants.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    tracking_number = Column(String)  # 每个SKU可以有不同的追踪号

    # 关系
    shipment = relationship('InventoryShipment', back_populates='shipment_items')
    variant = relationship('ProductVariant', lazy='joined')  # 自动加载关联的 variant


class InventoryTransitLog(Base):
    """发货状态变更记录表"""
    __tablename__ = 'inventory_transit_logs'

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey('inventory_shipments.id'), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variants.id'), nullable=False)
    # 使用String类型存储状态,与InventoryShipment保持一致,避免枚举转换问题
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    shipment = relationship('InventoryShipment', back_populates='transit_logs')
    variant = relationship('ProductVariant')

