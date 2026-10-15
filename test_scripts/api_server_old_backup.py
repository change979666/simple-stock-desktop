"""
SimpleStock API Server - 完整的后端服务
这是唯一允许访问数据库的程序，为客户端提供所有数据接口
"""
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
import uvicorn

from database.session import get_db
from database.models import (
    Product, ProductVariant, StockLog, SaleRecord, ActionLog,
    InventoryShipment, ShipmentItem
)
from database.inventory import ShipmentStatus
from crud.operations import (
    get_all_products, create_product, create_product_variant,
    get_variant_by_sku, update_variant_cost_price,
    create_stock_log, create_action_log,
    get_daily_sales_stats, get_yesterday_stats, get_last_week_stats,
    get_last_month_stats, get_products_below_warning_level,
    get_sku_recent_sales
)
from crud.inventory_logs import get_variant_current_stock


# ==================== Pydantic Models ====================

class ProductCreate(BaseModel):
    """创建产品请求"""
    product_name: str
    parent_sku: str
    sku: str
    option: Optional[str] = ""
    cost_price: Optional[float] = 0.0
    warning_threshold: Optional[int] = 10
    description: Optional[str] = ""


class ProductImportRequest(BaseModel):
    """批量导入产品请求"""
    products: List[Dict]


class InventoryAddRequest(BaseModel):
    """增加库存请求"""
    sku: str
    quantity: int
    notes: Optional[str] = ""


class InventoryReduceRequest(BaseModel):
    """减少库存请求"""
    sku: str
    quantity: int
    reason: Optional[str] = "销售"


class SaleCreate(BaseModel):
    """创建销售记录"""
    sku: str
    quantity: int
    sale_price: float
    sale_date: Optional[str] = None
    notes: Optional[str] = ""


class SaleImportRequest(BaseModel):
    """批量导入销售"""
    sales: List[Dict]


class ShipmentCreate(BaseModel):
    """创建发货单"""
    batch_number: str
    estimated_arrival: str
    items: List[Dict]  # [{"sku": "ABC", "quantity": 100}, ...]
    notes: Optional[str] = ""


class ShipmentStatusUpdate(BaseModel):
    """更新发货单状态"""
    status: str
    notes: Optional[str] = ""


# ==================== FastAPI App ====================

app = FastAPI(
    title="SimpleStock API Server",
    version="2.0.0",
    description="库存管理系统后端API - 纯C/S架构"
)

# 注册路由模块（优先使用模块化路由）
from api.routes import products, sales, shipment, dashboard, inventory

app.include_router(products.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(shipment.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")

# ==================== 旧的内联端点（已弃用，保留作为参考） ====================
# 所有产品、库存、销售相关端点已迁移到 api/routes/ 模块
# 如需使用旧端点，请取消下面的注释

"""
# ==================== 产品管理 ====================

@app.get("/api/products")
def get_products_api(db: Session = Depends(get_db)) -> List[Dict]:
    """获取所有产品列表"""
    try:
        products = db.query(ProductVariant).all()
        
        result = []
        for variant in products:
            result.append({
                "id": variant.id,
                "parent_sku": variant.product.parent_sku if variant.product else "",
                "product_name": variant.product.name if variant.product else "",
                "sku": variant.sku,
                "option": variant.option_name or "",
                "cost_price": float(variant.cost_price) if variant.cost_price else 0.0,
                "quantity": get_variant_current_stock(db, variant.id),
                "warning_threshold": variant.product.stock_warning_level if variant.product else 10,
                "description": variant.product.description if variant.product else ""
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取产品列表失败: {str(e)}")


@app.get("/api/products/{product_id}")
def get_product_api(product_id: int, db: Session = Depends(get_db)) -> Dict:
    """获取单个产品详情"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == product_id).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    return {
        "id": variant.id,
        "parent_sku": variant.product.parent_sku if variant.product else "",
        "product_name": variant.product.name if variant.product else "",
        "sku": variant.sku,
        "option": variant.option_name or "",
        "cost_price": float(variant.cost_price) if variant.cost_price else 0.0,
        "quantity": get_variant_current_stock(db, variant.id),
        "warning_threshold": variant.product.stock_warning_level if variant.product else 10
    }


@app.post("/api/products")
def create_product_api(
    product: ProductCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """创建产品"""
    try:
        # 检查SKU是否已存在
        existing = db.query(ProductVariant).filter(
            ProductVariant.sku == product.sku
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{product.sku}' 已存在")
        
        # 查找或创建父产品
        parent = db.query(Product).filter(
            Product.parent_sku == product.parent_sku
        ).first()
        
        if not parent:
            parent = Product(
                parent_sku=product.parent_sku,
                name=product.product_name,
                description=product.description or "",
                stock_warning_level=product.warning_threshold
            )
            db.add(parent)
            db.flush()
        
        # 创建子SKU
        variant = ProductVariant(
            product_id=parent.id,
            sku=product.sku,
            option_name=product.option or "",
            cost_price=product.cost_price
        )
        db.add(variant)
        db.commit()
        
        # 记录日志
        log_action(
            db, "创建产品",
            f"创建产品: {product.product_name} ({product.sku})",
            operator, product.sku
        )
        
        return {
            "success": True,
            "id": variant.id,
            "sku": variant.sku,
            "message": "产品创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建产品失败: {str(e)}")


@app.put("/api/products/{product_id}")
def update_product_api(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """更新产品信息"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == product_id).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    try:
        # 更新子SKU信息
        variant.option_name = product.option or ""
        variant.cost_price = product.cost_price
        
        # 更新父产品信息
        if variant.product:
            variant.product.name = product.product_name
            variant.product.description = product.description or ""
            variant.product.stock_warning_level = product.warning_threshold
        
        db.commit()
        
        log_action(
            db, "更新产品",
            f"更新产品: {product.product_name} ({product.sku})",
            operator, product.sku
        )
        
        return {"success": True, "message": "产品更新成功"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新产品失败: {str(e)}")


@app.delete("/api/products/{product_id}")
def delete_product_api(
    product_id: int,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """删除产品"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == product_id).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    try:
        sku = variant.sku
        db.delete(variant)
        db.commit()
        
        log_action(db, "删除产品", f"删除产品: {sku}", operator, sku)
        
        return {"success": True, "message": "产品删除成功"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除产品失败: {str(e)}")


@app.post("/api/products/import")
def import_products_api(
    request: ProductImportRequest,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """批量导入产品"""
    success_count = 0
    failed_count = 0
    errors = []
    
    for product_data in request.products:
        try:
            # 提取必需字段
            sku = product_data.get('sku')
            if not sku:
                failed_count += 1
                continue
            
            # 检查是否已存在
            existing = db.query(ProductVariant).filter(
                ProductVariant.sku == sku
            ).first()
            
            if existing:
                failed_count += 1
                errors.append(f"SKU {sku} 已存在")
                continue
            
            # 创建产品
            product = ProductCreate(
                product_name=product_data.get('product_name', ''),
                parent_sku=product_data.get('parent_sku', sku.split('-')[0]),
                sku=sku,
                option=product_data.get('option', ''),
                cost_price=float(product_data.get('cost_price', 0)),
                warning_threshold=int(product_data.get('warning_threshold', 10))
            )
            
            # 使用相同的创建逻辑
            parent = db.query(Product).filter(
                Product.parent_sku == product.parent_sku
            ).first()
            
            if not parent:
                parent = Product(
                    parent_sku=product.parent_sku,
                    name=product.product_name,
                    stock_warning_level=product.warning_threshold
                )
                db.add(parent)
                db.flush()
            
            variant = ProductVariant(
                product_id=parent.id,
                sku=product.sku,
                option_name=product.option,
                cost_price=product.cost_price
            )
            db.add(variant)
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            errors.append(f"SKU {product_data.get('sku', 'Unknown')}: {str(e)}")
    
    try:
        db.commit()
        
        log_action(
            db, "批量导入产品",
            f"导入 {success_count} 个产品，失败 {failed_count} 个",
            operator
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    
    return {
        "success": success_count,
        "failed": failed_count,
        "message": f"成功导入 {success_count} 个产品" + 
                   (f"，失败 {failed_count} 个" if failed_count > 0 else ""),
        "errors": errors[:10]  # 最多返回10个错误
    }


# ==================== 库存管理 ====================

@app.get("/api/inventory")
def get_inventory_api(
    sku: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取库存信息"""
    try:
        query = db.query(ProductVariant)
        
        if sku:
            query = query.filter(ProductVariant.sku.like(f"%{sku}%"))
        
        variants = query.all()
        
        result = []
        for variant in variants:
            result.append({
                "id": variant.id,
                "sku": variant.sku,
                "product_name": variant.product.name if variant.product else "",
                "option": variant.option_name or "",
                "quantity": get_variant_current_stock(db, variant.id),
                "cost_price": float(variant.cost_price) if variant.cost_price else 0.0,
                "warning_threshold": variant.product.stock_warning_level if variant.product else 10
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取库存失败: {str(e)}")


@app.post("/api/inventory/add")
def add_inventory_api(
    request: InventoryAddRequest,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """增加库存"""
    variant = db.query(ProductVariant).filter(
        ProductVariant.sku == request.sku
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail=f"SKU '{request.sku}' 不存在")
    
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    
    try:
        # 记录库存日志 (库存通过日志计算,不需要直接修改current_stock)
        stock_log = StockLog(
            variant_id=variant.id,
            change_quantity=request.quantity,  # 正数表示入库
            operator_info=operator,
            notes=request.notes,
            created_at=datetime.now()
        )
        db.add(stock_log)
        
        # 记录操作日志
        log_action(
            db, "增加库存",
            f"SKU {request.sku} 入库 {request.quantity} 件",
            operator, request.sku
        )
        
        db.commit()
        
        # 获取新的库存数量
        new_quantity = get_variant_current_stock(db, variant.id)
        
        return {
            "success": True,
            "sku": request.sku,
            "new_quantity": new_quantity,
            "message": f"成功入库 {request.quantity} 件"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"入库失败: {str(e)}")


@app.post("/api/inventory/reduce")
def reduce_inventory_api(
    request: InventoryReduceRequest,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """减少库存"""
    variant = db.query(ProductVariant).filter(
        ProductVariant.sku == request.sku
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail=f"SKU '{request.sku}' 不存在")
    
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    
    # 检查当前库存
    current_stock = get_variant_current_stock(db, variant.id)
    if current_stock < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"库存不足: 当前库存 {current_stock}，需要 {request.quantity}"
        )
    
    try:
        # 记录库存日志 (负数表示出库)
        stock_log = StockLog(
            variant_id=variant.id,
            change_quantity=-request.quantity,  # 负数表示出库
            operator_info=operator,
            notes=request.reason,
            created_at=datetime.now()
        )
        db.add(stock_log)
        
        # 记录操作日志
        log_action(
            db, "减少库存",
            f"SKU {request.sku} 出库 {request.quantity} 件 - {request.reason}",
            operator, request.sku
        )
        
        db.commit()
        
        # 获取新的库存数量
        new_quantity = get_variant_current_stock(db, variant.id)
        
        return {
            "success": True,
            "sku": request.sku,
            "new_quantity": new_quantity,
            "message": f"成功出库 {request.quantity} 件"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"出库失败: {str(e)}")


@app.get("/api/inventory/warnings")
def get_inventory_warnings_api(db: Session = Depends(get_db)) -> List[Dict]:
    """获取库存预警列表"""
    try:
        # 获取所有有预警阈值的产品
        variants = db.query(ProductVariant).join(Product).filter(
            Product.stock_warning_level > 0
        ).all()
        
        result = []
        for variant in variants:
            # 计算当前库存
            current_stock = get_variant_current_stock(db, variant.id)
            warning_level = variant.product.stock_warning_level if variant.product else 0
            
            # 只返回库存低于预警阈值的
            if current_stock < warning_level:
                result.append({
                    "sku": variant.sku,
                    "product_name": variant.product.name if variant.product else "",
                    "option": variant.option_name or "",
                    "current_stock": current_stock,
                    "warning_threshold": warning_level,
                    "shortage": warning_level - current_stock
                })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预警列表失败: {str(e)}")


# ==================== 销售管理 ====================

@app.post("/api/sales")
def create_sale_api(
    sale: SaleCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator_info)
) -> Dict:
    """创建销售记录"""
    variant = db.query(ProductVariant).filter(
        ProductVariant.sku == sale.sku
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail=f"SKU '{sale.sku}' 不存在")
    
    try:
        # 创建销售记录
        sale_date = datetime.fromisoformat(sale.sale_date) if sale.sale_date else datetime.now()
        
        sale_record = SaleRecord(
            variant_id=variant.id,
            quantity=sale.quantity,
            sale_price=sale.sale_price,
            sale_date=sale_date,
            notes=sale.notes,
            operator=operator
        )
        db.add(sale_record)
        
        # 减少库存 - 记录库存日志
        current_stock = get_variant_current_stock(db, variant.id)
        if current_stock >= sale.quantity:
            # 记录库存日志 (负数表示销售出库)
            stock_log = StockLog(
                variant_id=variant.id,
                change_quantity=-sale.quantity,  # 负数表示出库
                operator_info=operator,
                notes=f"销售: {sale.notes}" if sale.notes else "销售",
                created_at=datetime.now()
            )
            db.add(stock_log)
        
        db.commit()
        
        log_action(
            db, "创建销售",
            f"SKU {sale.sku} 销售 {sale.quantity} 件",
            operator, sale.sku
        )
        
        return {
            "success": True,
            "message": "销售记录创建成功"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建销售记录失败: {str(e)}")


@app.get("/api/sales")
def get_sales_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取销售记录"""
    try:
        query = db.query(SaleRecord)
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(SaleRecord.sale_date >= start)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(SaleRecord.sale_date <= end)
        
        sales = query.order_by(SaleRecord.sale_date.desc()).all()
        
        result = []
        for sale in sales:
            variant = sale.variant
            result.append({
                "id": sale.id,
                "sku": variant.sku if variant else "",
                "product_name": variant.product.name if variant and variant.product else "",
                "quantity": sale.quantity,
                "sale_price": float(sale.sale_price),
                "total_amount": float(sale.quantity * sale.sale_price),
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else "",
                "notes": sale.notes or "",
                "operator": sale.operator or ""
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取销售记录失败: {str(e)}")


@app.get("/api/sales/daily/{date}")
def get_daily_sales_api(date: str, db: Session = Depends(get_db)) -> Dict:
    """获取指定日期的销售统计"""
    try:
        target_date = datetime.fromisoformat(date).date()
        
        sales = db.query(SaleRecord).filter(
            SaleRecord.sale_date >= datetime.combine(target_date, datetime.min.time()),
            SaleRecord.sale_date < datetime.combine(target_date, datetime.max.time())
        ).all()
        
        total_sales = sum(sale.quantity * sale.sale_price for sale in sales)
        total_orders = len(sales)
        
        return {
            "date": date,
            "total_sales": float(total_sales),
            "total_orders": total_orders
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取销售统计失败: {str(e)}")


# ==================== 操作日志 ====================

@app.get("/api/logs/operations")
def get_operation_logs_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取操作日志(库存变动记录)"""
    try:
        query = db.query(StockLog)
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(StockLog.created_at >= start)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(StockLog.created_at <= end)
        
        # action_type参数暂时忽略,因为StockLog没有这个字段
        
        logs = query.order_by(StockLog.created_at.desc()).limit(1000).all()
        
        result = []
        for log in logs:
            variant = log.variant
            # 根据change_quantity判断操作类型
            operation_type = '入库' if log.change_quantity > 0 else '出库'
            
            # 计算变动后库存(需要从stock_logs累加计算)
            after_stock = None
            if variant:
                from crud.inventory_logs import get_variant_current_stock
                after_stock = get_variant_current_stock(db, variant.id)
            
            result.append({
                "id": log.id,
                "sku": variant.sku if variant else "",
                "operation_type": operation_type,
                "quantity": abs(log.change_quantity),
                "quantity_change": log.change_quantity,  # GUI期望这个字段
                "after_stock": after_stock,  # 添加变动后库存
                "notes": log.notes or "",
                "operator": log.operator_info or "",
                "time": log.created_at.isoformat() if log.created_at else "",  # 改为time
                "timestamp": log.created_at.isoformat() if log.created_at else ""  # 保留兼容
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取操作日志失败: {str(e)}"
        )


@app.get("/api/logs/actions")
def get_action_logs_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取动作日志"""
    try:
        query = db.query(ActionLog)
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(ActionLog.created_at >= start)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(ActionLog.created_at <= end)
        
        logs = query.order_by(
            ActionLog.created_at.desc()
        ).limit(1000).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "action": log.action,
                "operator": log.operator_info or "",
                "timestamp": log.created_at.isoformat() if log.created_at else ""
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取操作日志失败: {str(e)}"
        )


# ==================== 仪表板统计 ====================

@app.get("/api/dashboard/stats/today")
def get_dashboard_today_stats(db: Session = Depends(get_db)) -> Dict:
    """获取今日销售统计"""
    try:
        return get_daily_sales_stats(db, datetime.now())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.get("/api/dashboard/stats/yesterday")
def get_dashboard_yesterday_stats(db: Session = Depends(get_db)) -> Dict:
    """获取昨日销售统计"""
    try:
        return get_yesterday_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.get("/api/dashboard/stats/week")
def get_dashboard_week_stats(db: Session = Depends(get_db)) -> Dict:
    """获取最近7天销售统计"""
    try:
        return get_last_week_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.get("/api/dashboard/stats/month")
def get_dashboard_month_stats(db: Session = Depends(get_db)) -> Dict:
    """获取最近30天销售统计"""
    try:
        return get_last_month_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.get("/api/dashboard/warnings")
def get_dashboard_warnings(
    threshold: float = 1.0,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取库存预警列表
    
    Args:
        threshold: 警告阈值(默认1.0表示100%)
    """
    try:
        warnings = get_products_below_warning_level(db, threshold)
        
        # 为每个警告项添加销量数据
        for warning in warnings:
            variant = get_variant_by_sku(db, warning['variant_sku'])
            if variant:
                sales_data = get_sku_recent_sales(db, variant.id)
                warning['sales_stats'] = {
                    'today': sales_data['today']['total_quantity'],
                    'yesterday': sales_data['yesterday']['total_quantity'],
                    'week': sales_data['week']['total_quantity'],
                    'month': sales_data['month']['total_quantity']
                }
            else:
                warning['sales_stats'] = {
                    'today': 0, 'yesterday': 0, 'week': 0, 'month': 0
                }
        
        return warnings
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取库存预警失败: {str(e)}"
        )


# ==================== Server Startup ====================
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取动作日志失败: {str(e)}")
"""

# ==================== Health Check (保留) ====================

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "SimpleStock API Server",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


# ==================== 启动服务器 ====================

def start_server(host: str = "0.0.0.0", port: int = 8001):
    """启动API服务器
    
    Args:
        host: 监听地址，0.0.0.0表示监听所有网卡
        port: 监听端口
    """
    print("="*60)
    print("SimpleStock API Server")
    print("="*60)
    print(f"🚀 服务器启动中...")
    print(f"📡 监听地址: {host}:{port}")
    print(f"📖 API文档: http://localhost:{port}/docs")
    print(f"🔧 健康检查: http://localhost:{port}/api/health")
    print("="*60)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
