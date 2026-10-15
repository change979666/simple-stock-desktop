from typing import Optional
from sqlalchemy.orm import Session
from database.models import Product, ProductVariant


def extract_parent_sku(child_sku: str) -> str:
    """
    从子SKU提取父SKU
    例如: 'BD001-RED' -> 'BD001'
         'BD002-XL-BLACK' -> 'BD002'
    """
    # 按照 - 分割，取第一部分
    return child_sku.split('-')[0]


def find_or_create_product_by_child_sku(
    db: Session,
    child_sku: str,
    stock_warning_level: int = 500
) -> Optional[Product]:
    """
    根据子SKU查找或创建父产品
    
    Args:
        db: 数据库会话
        child_sku: 子SKU编号
        stock_warning_level: 库存警告阈值

    Returns:
        Product: 找到或新创建的父产品
    """
    # 从子SKU提取父SKU
    parent_sku = extract_parent_sku(child_sku)
    
    # 先尝试查找现有的父产品
    product = db.query(Product).filter(
        Product.parent_sku == parent_sku
    ).first()
    
    # 如果没找到，创建新的父产品
    if not product:
        product = Product(
            parent_sku=parent_sku,
            stock_warning_level=stock_warning_level
        )
        db.add(product)
        db.commit()
        db.refresh(product)
    
    return product


def get_variant_details_by_child_sku(
    db: Session,
    child_sku: str
) -> tuple[Optional[ProductVariant], Optional[Product]]:
    """
    根据子SKU获取变体和父产品信息
    
    Args:
        db: 数据库会话
        child_sku: 子SKU编号

    Returns:
        tuple: (ProductVariant, Product) 如果找到
               (None, None) 如果未找到
    """
    # 尝试直接查找变体
    variant = db.query(ProductVariant).filter(
        ProductVariant.sku == child_sku
    ).first()
    
    if variant:
        return variant, variant.product
    
    # 如果没找到变体，尝试查找父产品
    parent_sku = extract_parent_sku(child_sku)
    product = db.query(Product).filter(
        Product.parent_sku == parent_sku
    ).first()
    
    return None, product