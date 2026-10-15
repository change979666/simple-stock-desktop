from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Product(Base):
    """父产品表"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    parent_sku = Column(String, unique=True, nullable=False)
    stock_warning_level = Column(Integer)  # 不再使用产品级别预警，使用全局设置
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    category = relationship('Category', back_populates='products')
    variants = relationship('ProductVariant', back_populates='product',
                          cascade='all, delete-orphan')


class ProductVariant(Base):
    """子产品/SKU变体表"""
    __tablename__ = 'product_variants'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    sku = Column(String, unique=True, nullable=False)
    option_name = Column(String, nullable=False)
    cost_price = Column(Float, nullable=False)

    # 关系
    product = relationship('Product', back_populates='variants')
    stock_logs = relationship('StockLog', back_populates='variant',
                            cascade='all, delete-orphan')
    sale_records = relationship('SaleRecord', back_populates='variant',
                              cascade='all, delete-orphan')
    shipment_items = relationship('ShipmentItem', back_populates='variant',
                                cascade='all, delete-orphan')


from .models.log import StockLog  # 引用新的StockLog模型


class SaleRecord(Base):
    """销售记录表"""
    __tablename__ = 'sale_records'

    id = Column(Integer, primary_key=True)
    order_number = Column(String, nullable=False)
    customer_name = Column(String, nullable=False)
    order_date = Column(DateTime, nullable=False)
    payment_time = Column(DateTime)
    shipping_method = Column(String)
    tracking_number = Column(String)
    delivery_time = Column(DateTime)
    variant_id = Column(Integer, ForeignKey('product_variants.id'),
                       nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    selling_price = Column(Float, nullable=False)
    net_selling_price = Column(Float, nullable=False)
    operator_info = Column(String, nullable=False)
    imported_at = Column(DateTime, default=datetime.now)

    # 关系
    variant = relationship('ProductVariant', back_populates='sale_records')


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


class ActionLog(Base):
    """通用操作日志表"""
    __tablename__ = 'action_logs'

    id = Column(Integer, primary_key=True)
    operator_info = Column(String, nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
