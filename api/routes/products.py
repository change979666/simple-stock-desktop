"""
产品管理API路由
提供产品和变体的CRUD操作
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.session import get_db
from crud.operations import (
    create_product,
    create_product_variant,
    get_variant_by_sku,
    create_stock_log,
    create_action_log
)
from crud.inventory_logs import get_variant_current_stock
from database.models import Product, ProductVariant

router = APIRouter(prefix="/products", tags=["products"])


# ============ 请求/响应模型 ============

class VariantCreate(BaseModel):
    """变体创建模型 - 匹配GUI格式"""
    sku: str
    option1_value: Optional[str] = None  # GUI可能发送color/size等
    option2_value: Optional[str] = None
    option3_value: Optional[str] = None
    cost_price: float
    initial_stock: int = 0
    warning_level: int = 0
    
    # GUI可能发送的额外字段（兼容）
    color: Optional[str] = None
    size: Optional[str] = None
    selling_price: Optional[float] = None


class ProductCreate(BaseModel):
    """产品创建模型 - 匹配GUI格式"""
    name: str
    category_id: Optional[int] = None
    category: Optional[str] = None  # GUI可能发送category字符串
    option1_name: Optional[str] = None
    option2_name: Optional[str] = None
    option3_name: Optional[str] = None
    variants: List[VariantCreate]
    operator_info: Optional[dict] = None  # GUI发送的操作者信息


class ProductUpdate(BaseModel):
    """产品更新模型"""
    name: Optional[str] = None
    category_id: Optional[int] = None
    operator_info: Optional[dict] = None  # 操作者信息


class VariantUpdate(BaseModel):
    """变体更新模型"""
    sku: Optional[str] = None
    option_name: Optional[str] = None  # 规格名称
    cost_price: Optional[float] = None


class StockAdjust(BaseModel):
    """库存调整模型"""
    sku: str
    quantity_change: int
    reason: str
    operator_info: str


# ============ API端点 ============

@router.get("", response_model=None)
def get_products_list(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取产品列表（支持分页）
    
    参数:
    - page: 页码（从1开始）
    - page_size: 每页数量（默认50）
    - search: 搜索关键词（匹配产品名称或SKU）
    - category_id: 可选,按分类筛选
    
    返回:
    {
        "items": [...],
        "total": 总数,
        "page": 当前页,
        "page_size": 每页数量,
        "total_pages": 总页数
    }
    """
    from crud.operations import get_products_paginated
    import math
    
    # 使用分页查询
    products, total = get_products_paginated(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id
    )
    
    # 🚀 性能优化：批量获取所有变体的库存（避免N+1查询）
    from crud.inventory_logs import get_batch_variant_stocks
    
    # 收集所有变体ID
    all_variant_ids = []
    for product in products:
        for variant in product.variants:
            all_variant_ids.append(variant.id)
    
    # 一次性查询所有变体的库存
    stock_dict = get_batch_variant_stocks(db, all_variant_ids)
    print(f"✅ 批量查询了 {len(all_variant_ids)} 个变体的库存（1次SQL查询）")
    
    # 计算总页数
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    # 转换为字典格式
    items = []
    for product in products:
        product_dict = {
            'id': product.id,
            'name': product.name,
            'category_id': product.category_id,
            'parent_sku': product.parent_sku,
            'description': product.description,
            'stock_warning_level': product.stock_warning_level,
            'variants': []
        }
        
        for variant in product.variants:
            created_at = (variant.created_at.isoformat()
                         if variant.created_at else None)
            variant_dict = {
                'id': variant.id,
                'sku': variant.sku,
                'option_name': variant.option_name,
                'cost_price': float(variant.cost_price),
                'current_stock': stock_dict.get(variant.id, 0),  # 从字典获取
                'created_at': created_at
            }
            product_dict['variants'].append(variant_dict)
        
        items.append(product_dict)
    
    # 返回分页响应
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    }


@router.post("")
def create_new_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    创建新产品及其变体
    
    参数:
    - product: 产品数据（包含operator_info）
    """
    try:
        # 从product中提取operator_info
        operator_info = product.operator_info or {}
        if isinstance(operator_info, dict):
            operator_info = str(operator_info)
        
        # 生成 parent_sku (使用产品名称的拼音首字母或直接使用名称)
        parent_sku = product.name
        
        # 创建产品
        new_product = create_product(db=db, parent_sku=parent_sku)
        
        # 创建变体
        for variant_data in product.variants:
            # 合并选项值为 option_name
            option_name = variant_data.option1_value or ''
            if variant_data.option2_value:
                option_name = f"{option_name} {variant_data.option2_value}".strip()
            if variant_data.option3_value:
                option_name = f"{option_name} {variant_data.option3_value}".strip()
            
            variant = create_product_variant(
                db=db,
                product_id=new_product.id,
                sku=variant_data.sku,
                option_name=option_name,
                cost_price=variant_data.cost_price
            )
            
            # 如果有初始库存,记录日志
            if variant_data.initial_stock > 0:
                create_stock_log(
                    db=db,
                    variant_id=variant.id,
                    change_quantity=variant_data.initial_stock,
                    notes='初始库存',
                    operator_info=operator_info
                )
        
        # 记录操作日志
        create_action_log(
            db=db,
            action_type='创建产品',
            details=f'创建产品: {product.name}, {len(product.variants)}个变体',
            operator_info=operator_info
        )
        
        # 提交事务(包括初始库存日志和操作日志)
        db.commit()
        
        return {
            "message": "产品创建成功",
            "product_id": new_product.id,
            "variants_count": len(product.variants)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{product_id}")
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db)
):
    """获取产品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    return {
        'id': product.id,
        'name': product.name,
        'category_id': product.category_id,
        'option1_name': product.option1_name,
        'option2_name': product.option2_name,
        'option3_name': product.option3_name,
        'variants': [
            {
                'id': v.id,
                'sku': v.sku,
                'option_name': v.option_name,
                'cost_price': float(v.cost_price),
                'current_stock': get_variant_current_stock(db, v.id)
            }
            for v in product.variants
        ]
    }


@router.put("/{product_id}")
def update_product_endpoint(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """更新产品信息"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    # 从product中提取operator_info
    operator_info = product.operator_info or {}
    if isinstance(operator_info, dict):
        operator_info = str(operator_info)
    
    # 更新字段
    if product.name is not None:
        db_product.name = product.name
    if product.category_id is not None:
        db_product.category_id = product.category_id
    
    # 记录操作日志
    create_action_log(
        db=db,
        action_type='更新产品',
        details=f'更新产品: {db_product.name}',
        operator_info=operator_info
    )
    
    db.commit()  # 这里需要commit，因为上面的修改没有在CRUD层
    
    return {"message": "产品更新成功"}


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """删除产品及其所有变体,包括清理库存记录"""
    from crud.operations import delete_product_with_variants
    import json
    
    try:
        # 解析操作者信息
        operator_dict = json.loads(operator_info) if isinstance(operator_info, str) else operator_info
        
        result = delete_product_with_variants(db, product_id, operator_dict)
        
        return {
            "message": "产品删除成功",
            "details": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ============ 变体相关API ============

@router.get("/variants/sku/{sku}")
def get_variant_by_sku_api(
    sku: str,
    db: Session = Depends(get_db)
):
    """通过SKU获取变体"""
    variant = get_variant_by_sku(db, sku)
    
    if not variant:
        raise HTTPException(status_code=404, detail=f"SKU {sku} 不存在")
    
    # 计算当前库存
    current_stock = get_variant_current_stock(db, variant.id)
    
    return {
        'id': variant.id,
        'sku': variant.sku,
        'product_id': variant.product_id,
        'product_name': variant.product.name if variant.product else None,
        'option_name': variant.option_name,
        'cost_price': float(variant.cost_price),
        'current_stock': current_stock
    }


@router.put("/variants/{variant_id}")
def update_variant(
    variant_id: int,
    variant: VariantUpdate,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """更新变体信息"""
    db_variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    
    if not db_variant:
        raise HTTPException(status_code=404, detail="变体不存在")
    
    # 更新SKU
    if variant.sku is not None:
        old_sku = db_variant.sku
        db_variant.sku = variant.sku
        create_action_log(
            db=db,
            operator_info=operator_info,
            action=f'更新SKU: 变体 {variant_id}: {old_sku} -> {variant.sku}'
        )
    
    # 更新规格名称
    if variant.option_name is not None:
        db_variant.option_name = variant.option_name
    
    # 更新成本价
    if variant.cost_price is not None:
        old_price = db_variant.cost_price
        db_variant.cost_price = variant.cost_price
        
        create_action_log(
            db=db,
            operator_info=operator_info,
            action=f'更新成本价: SKU {db_variant.sku}: {old_price} -> {variant.cost_price}'
        )
    
    db.commit()  # 这里需要commit，因为上面的修改没有在CRUD层
    
    return {"message": "变体更新成功"}


@router.post("/variants/adjust-stock")
def adjust_stock(
    adjust: StockAdjust,
    db: Session = Depends(get_db)
):
    """调整库存"""
    variant = get_variant_by_sku(db, adjust.sku)
    
    if not variant:
        raise HTTPException(status_code=404, detail=f"SKU {adjust.sku} 不存在")
    
    # 更新库存
    old_stock = variant.current_stock
    new_stock = old_stock + adjust.quantity_change
    
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="库存不足")
    
    variant.current_stock = new_stock
    
    # 记录库存日志
    create_stock_log(
        db=db,
        variant_id=variant.id,
        change_quantity=adjust.quantity_change,
        notes=adjust.reason,
        operator_info=adjust.operator_info
    )
    
    db.commit()  # 这里需要commit，因为上面variant.current_stock的修改
    
    return {
        "message": "库存调整成功",
        "sku": adjust.sku,
        "old_stock": old_stock,
        "new_stock": new_stock
    }


@router.delete("/variants/{variant_id}")
def delete_variant(
    variant_id: int,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """删除单个变体,包括清理库存记录"""
    from crud.operations import delete_variant_with_stock
    import json
    
    try:
        # 解析操作者信息
        operator_dict = json.loads(operator_info) if isinstance(
            operator_info, str) else operator_info
        
        result = delete_variant_with_stock(db, variant_id, operator_dict)
        
        return {
            "message": "变体删除成功",
            "details": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


class ProductImport(BaseModel):
    """批量导入产品模型"""
    products: List[dict]
    operator_info: Optional[str] = None  # 添加操作员信息


@router.post("/import")
def import_products_batch(
    data: ProductImport,
    db: Session = Depends(get_db)
):
    """
    批量导入产品
    
    参数:
    - products: 产品列表（dict格式）
    
    返回:
    - 成功和失败的统计信息
    """
    success_count = 0
    failed_count = 0
    errors = []
    
    for product_data in data.products:
        try:
            # 提取字段（严格按照模板）
            parent_sku = product_data.get('parent_sku')
            sku = product_data.get('sku')
            option_name = product_data.get('option_name', '')
            cost_price = product_data.get('cost_price', 0)
            
            if not parent_sku or not sku:
                errors.append(f"SKU {sku}: 缺少必需字段 parent_sku 或 sku")
                failed_count += 1
                continue
            
            # 查找或创建产品（使用 parent_sku 作为产品名）
            product = db.query(Product).filter(
                Product.parent_sku == parent_sku).first()
            
            if not product:
                product = create_product(
                    db=db,
                    parent_sku=parent_sku
                )
            
            # 创建变体（使用正确的函数签名）
            variant = create_product_variant(
                db=db,
                product_id=product.id,
                sku=sku,
                option_name=option_name,
                cost_price=cost_price
            )
            
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            errors.append(f"SKU {sku}: {str(e)}")
            continue
    
    # 提交所有导入的数据
    db.commit()
    
    return {
        "success": success_count,
        "failed": failed_count,
        "message": f"导入完成: 成功{success_count}, 失败{failed_count}",
        "errors": errors if errors else None
    }
