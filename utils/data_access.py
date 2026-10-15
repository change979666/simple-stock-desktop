"""
数据访问层 - 统一的数据访问接口
根据运行模式自动选择使用本地数据库或API客户端

重要: 所有方法统一返回字典或字典列表，无论在 Local 还是 Client 模式
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.app_mode import app_mode
from utils.type_safe import (
    to_dict,
    to_dict_list,
    ensure_dict,
    ensure_dict_list
)


class DataAccessLayer:
    """数据访问层 - 自动路由到数据库或API"""
    
    def __init__(self):
        self._db_session = None
    
    def _get_db_session(self):
        """获取数据库会话(仅本地模式)"""
        if app_mode.is_client_mode():
            raise RuntimeError("客户端模式不应访问本地数据库")
        
        if self._db_session is None:
            from database.session import SessionLocal
            self._db_session = SessionLocal()
        return self._db_session
    
    def _get_api_client(self):
        """获取API客户端(仅客户端模式)"""
        if app_mode.is_local_mode():
            raise RuntimeError("本地模式不应使用API客户端")
        
        from client.api_client import api_client
        return api_client
    
    # =========================
    # 内部辅助方法
    # =========================
    
    def _convert_products_to_dict(self, products: List[Any]) -> List[Dict]:
        """将 SQLAlchemy 产品对象列表转换为字典列表
        
        Args:
            products: SQLAlchemy 产品对象列表
            
        Returns:
            字典列表，包含产品和变体信息
        """
        result = []
        for product in products:
            product_dict = {
                'id': product.id,
                'parent_sku': product.parent_sku,
                'name': getattr(product, 'name', ''),
                'description': getattr(product, 'description', ''),
                'stock_warning_level': product.stock_warning_level,
                'category_id': getattr(product, 'category_id', None),
                'variants': []
            }
            
            # 转换变体列表
            for variant in product.variants:
                variant_dict = {
                    'id': variant.id,
                    'sku': variant.sku,
                    'option_name': variant.option_name,
                    'cost_price': variant.cost_price or 0.0,
                    'current_stock': variant.current_stock or 0,
                    'product_id': product.id
                }
                product_dict['variants'].append(variant_dict)
            
            result.append(product_dict)
        
        return result
    
    def _convert_variant_to_dict(self, variant: Any) -> Dict:
        """将 SQLAlchemy 变体对象转换为字典
        
        Args:
            variant: SQLAlchemy 变体对象
            
        Returns:
            变体字典
        """
        if variant is None:
            return None
        
        return {
            'id': variant.id,
            'sku': variant.sku,
            'option_name': variant.option_name,
            'cost_price': variant.cost_price or 0.0,
            'current_stock': variant.current_stock or 0,
            'product_id': variant.product_id
        }
    
    # =========================
    # 仪表板相关方法
    # =========================
    
    def get_batch_dashboard_data(self, threshold: float = 1.0) -> Dict[str, Any]:
        """批量获取仪表盘所有数据（性能优化）
        
        Args:
            threshold: 库存警告阈值
            
        Returns:
            {
                'stats': {
                    'today': {...},
                    'yesterday': {...},
                    'week': {...},
                    'month': {...}
                },
                'warnings': [...]
            }
        """
        if app_mode.is_client_mode():
            # 客户端模式: 使用批量API（5次调用 → 1次）
            client = self._get_api_client()
            return client.get_batch_dashboard_data(threshold)
        else:
            # 本地模式: 模拟批量获取
            return {
                'stats': self.get_dashboard_stats(),
                'warnings': self.get_inventory_warnings(threshold)
            }
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表板统计数据"""
        if app_mode.is_client_mode():
            # 客户端模式: 使用API
            client = self._get_api_client()
            return client.get_dashboard_stats()
        else:
            # 本地模式: 使用数据库
            from crud.sales import (
                get_daily_sales_stats,
                get_yesterday_stats,
                get_last_week_stats,
                get_last_month_stats
            )
            db = self._get_db_session()
            today = datetime.now()
            
            return {
                'today': get_daily_sales_stats(db, today),
                'yesterday': get_yesterday_stats(db),
                'week': get_last_week_stats(db),
                'month': get_last_month_stats(db)
            }
    
    def get_inventory_warnings(self, threshold: float = 1.0) -> List[Dict]:
        """获取库存预警列表"""
        if app_mode.is_client_mode():
            # 客户端模式: 使用API
            client = self._get_api_client()
            return client.get_inventory_warnings(threshold)
        else:
            # 本地模式: 使用数据库
            from crud.operations import get_products_below_warning_level
            db = self._get_db_session()
            return get_products_below_warning_level(db, threshold)
    
    # =========================
    # 产品相关方法
    # =========================
    
    def get_all_products(self) -> List[Dict]:
        """获取所有产品（统一返回字典列表）
        
        优化：优先使用缓存，避免重复全量加载
        通过循环分页获取所有数据，避免单次查询过大
        
        Returns:
            产品字典列表，每个产品包含 variants 列表
        """
        if app_mode.is_client_mode():
            # 客户端模式: 使用API（已返回字典）
            # 优化策略：优先从缓存获取完整产品列表
            from utils.cache import data_cache
            
            # 先尝试从缓存获取完整列表
            cached = data_cache.get('products_list_full')
            if cached:
                return cached
            
            # 缓存未命中，循环分页获取全部产品
            client = self._get_api_client()
            all_products = []
            page = 1
            page_size = 100  # 每页100条，合理的批次大小
            
            while True:
                response = client.get_products_paginated(
                    page=page,
                    page_size=page_size
                )
                items = response.get('items', [])
                if not items:
                    break
                    
                all_products.extend(items)
                
                # 检查是否还有更多数据
                total = response.get('total', 0)
                if len(all_products) >= total:
                    break
                    
                page += 1
            
            # 缓存结果
            data_cache.set('products_list_full', all_products, ttl=600)
            
            return all_products
        else:
            # 本地模式: 使用数据库，转换为字典
            from crud.operations import get_all_products
            db = self._get_db_session()
            products = get_all_products(db)
            
            # 将 SQLAlchemy 对象转换为字典
            return self._convert_products_to_dict(products)
    
    def get_products_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """分页获取产品列表
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词
            category_id: 分类ID筛选
        
        Returns:
            {
                'items': [...],
                'total': 总数,
                'page': 当前页,
                'page_size': 每页数量,
                'total_pages': 总页数
            }
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_products_paginated(
                page, page_size, search, category_id
            )
        else:
            from crud.operations import get_products_paginated
            import math
            db = self._get_db_session()
            products, total = get_products_paginated(
                db, page, page_size, search, category_id
            )
            total_pages = math.ceil(total / page_size) if page_size > 0 else 0
            # 转换 SQLAlchemy 对象为字典
            items_dict = self._convert_products_to_dict(products)
            return {
                'items': items_dict,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
    
    def get_inventory_stats(self) -> Dict[str, int]:
        """获取库存统计信息
        
        优化: 在服务端进行聚合计算，避免传输大量数据到客户端
        
        Returns:
            {
                'total_stock': 总库存数量,
                'in_stock_count': 有货SKU数量
            }
        """
        if app_mode.is_client_mode():
            # 客户端模式: 优先从缓存获取
            from utils.cache import data_cache
            
            cached = data_cache.get('inventory_global_stats')
            if cached:
                return cached
            
            # 缓存未命中，调用API获取
            client = self._get_api_client()
            # 注意: 这里需要API支持统计接口
            # 如果API不支持，暂时使用本地计算
            try:
                stats = client.get_inventory_stats()
                # 缓存5分钟
                data_cache.set('inventory_global_stats', stats, ttl=300)
                return stats
            except AttributeError:
                # API客户端暂不支持统计接口，使用产品数据计算
                products = self.get_all_products()
                total_stock = 0
                in_stock_count = 0
                for product in products:
                    variants = product.get('variants', [])
                    for variant in variants:
                        stock = variant.get('current_stock', 0)
                        total_stock += stock
                        if stock > 0:
                            in_stock_count += 1
                
                stats = {
                    'total_stock': total_stock,
                    'in_stock_count': in_stock_count
                }
                # 缓存5分钟
                data_cache.set('inventory_global_stats', stats, ttl=300)
                return stats
        else:
            # 本地模式: 直接数据库聚合查询
            from database.models import ProductVariant
            db = self._get_db_session()
            
            # 使用SQL聚合，性能最优
            from sqlalchemy import func
            total_stock = db.query(
                func.sum(ProductVariant.current_stock)
            ).scalar() or 0
            
            in_stock_count = db.query(
                func.count(ProductVariant.id)
            ).filter(
                ProductVariant.current_stock > 0
            ).scalar() or 0
            
            return {
                'total_stock': int(total_stock),
                'in_stock_count': int(in_stock_count)
            }
    
    def create_product(self, product_data: Dict) -> Any:
        """创建产品"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.create_product(product_data)
        else:
            from crud.operations import create_product
            db = self._get_db_session()
            return create_product(db, **product_data)
    
    def update_product(self, product_id: int, product_data: Dict) -> Any:
        """更新产品信息"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.update_product(product_id, product_data)
        else:
            from crud.operations import update_product
            db = self._get_db_session()
            return update_product(db, product_id, **product_data)
    
    def delete_product(self, product_id: int, operator_info: Dict) -> Any:
        """删除产品"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.delete_product(product_id, operator_info)
        else:
            from crud.operations import delete_product_with_variants
            db = self._get_db_session()
            return delete_product_with_variants(db, product_id, operator_info)
    
    def delete_variant(self, variant_id: int, operator_info: Dict) -> Any:
        """删除变体"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.delete_variant(variant_id, operator_info)
        else:
            from crud.operations import delete_variant_with_stock
            db = self._get_db_session()
            return delete_variant_with_stock(db, variant_id, operator_info)
    
    def get_variant_by_sku(self, sku: str) -> Optional[Dict]:
        """通过SKU获取产品变体（统一返回字典）
        
        Args:
            sku: 变体SKU
            
        Returns:
            变体字典，不存在则返回None
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_variant_by_sku(sku)
        else:
            from crud.operations import get_variant_by_sku
            db = self._get_db_session()
            variant = get_variant_by_sku(db, sku)
            return self._convert_variant_to_dict(variant)
    
    def get_variant_by_id(self, variant_id: int) -> Optional[Dict]:
        """通过ID获取变体（统一返回字典）
        
        Args:
            variant_id: 变体ID
            
        Returns:
            变体字典，不存在则返回None
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_variant_by_id(variant_id)
        else:
            from database.models import ProductVariant
            db = self._get_db_session()
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == variant_id
            ).first()
            return self._convert_variant_to_dict(variant)
    
    def update_variant(
        self,
        variant_id: int,
        variant_data: Dict,
        operator_info: Dict
    ) -> Any:
        """更新变体信息
        
        Args:
            variant_id: 变体ID
            variant_data: {
                "sku": str (可选),
                "option_name": str (可选),  # 规格名称
                "cost_price": float (可选)
            }
            operator_info: 操作者信息字典
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.update_variant(variant_id, variant_data, operator_info)
        else:
            from database.models import ProductVariant
            from crud.operations import create_action_log
            db = self._get_db_session()
            
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == variant_id
            ).first()
            
            if not variant:
                raise ValueError(f"变体 {variant_id} 不存在")
            
            # 更新字段（只更新存在的字段）
            if 'sku' in variant_data:
                variant.sku = variant_data['sku']
            
            # 支持 option_name 和 option1_value（兼容旧代码）
            if 'option_name' in variant_data:
                variant.option_name = variant_data['option_name']
            elif 'option1_value' in variant_data:
                variant.option_name = variant_data['option1_value']
            
            if 'cost_price' in variant_data:
                variant.cost_price = variant_data['cost_price']
            
            db.commit()
            
            # 记录日志
            create_action_log(
                db,
                operator_info,
                f'更新变体 {variant.sku}: {variant_data}'
            )
            
            return {"message": "变体更新成功"}
    
    # =========================
    # 产品导入/导出方法
    # =========================
    
    def export_products(self) -> List[Dict]:
        """导出产品数据（用于Excel导出）"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            # 获取所有产品和变体
            products = client.get_products()
            # 将嵌套结构展开为平面结构（与GUI导出格式一致）
            flat_data = []
            for product in products:
                product_name = product.get('name') if isinstance(product, dict) else product.name
                variants = product.get('variants', []) if isinstance(product, dict) else product.variants
                for variant in variants:
                    flat_data.append({
                        'product_name': product_name,
                        'sku': variant.get('sku') if isinstance(variant, dict) else variant.sku,
                        'option1_value': variant.get('option1_value') if isinstance(variant, dict) else getattr(variant, 'option1_value', ''),
                        'option2_value': variant.get('option2_value') if isinstance(variant, dict) else getattr(variant, 'option2_value', ''),
                        'cost_price': variant.get('cost_price') if isinstance(variant, dict) else variant.cost_price,
                        'stock': variant.get('current_stock') if isinstance(variant, dict) else variant.current_stock,
                    })
            return flat_data
        else:
            from crud.operations import get_all_products
            from crud.inventory_logs import get_variant_current_stock
            db = self._get_db_session()
            products = get_all_products(db)
            # 展开为平面结构
            flat_data = []
            for product in products:
                for variant in product.variants:
                    # 计算当前库存
                    current_stock = get_variant_current_stock(db, variant.id)
                    flat_data.append({
                        'product_name': product.name,
                        'sku': variant.sku,
                        'option1_value': variant.option1_value or '',
                        'option2_value': variant.option2_value or '',
                        'cost_price': variant.cost_price,
                        'stock': current_stock,
                    })
            return flat_data
    
    def import_products(self, products, operator_info: Dict) -> Dict:
        """批量导入产品
        
        Args:
            products: 产品列表（可以是List[Dict]或DataFrame）
            operator_info: 操作者信息
            
        Returns:
            {"success": int, "failed": int, "message": str}
        """
        # 如果是DataFrame，转换为字典列表
        if hasattr(products, 'to_dict'):
            products = products.to_dict('records')
        
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.import_products(products, operator_info)
        else:
            # 本地模式批量导入
            from crud.operations import create_product
            db = self._get_db_session()
            success_count = 0
            failed_count = 0
            errors = []
            
            for product_data in products:
                try:
                    create_product(db, **product_data)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(str(e))
            
            return {
                "success": success_count,
                "failed": failed_count,
                "message": f"导入完成: 成功{success_count}, 失败{failed_count}",
                "errors": errors if errors else None
            }
    
    def batch_update_variants(self, variant_updates: List[Dict],
                             operator_info: Dict) -> Dict:
        """批量更新变体
        
        Args:
            variant_updates: [{
                "variant_id": int,
                "sku": str (可选),
                "option1_value": str (可选),
                "cost_price": float (可选)
            }]
            operator_info: 操作者信息
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            # 客户端模式循环调用update_variant
            success_count = 0
            for update_data in variant_updates:
                try:
                    variant_id = update_data.pop('variant_id')
                    client.update_variant(variant_id, update_data, operator_info)
                    success_count += 1
                except Exception as e:
                    print(f"更新变体失败: {e}")
            
            return {
                "success": success_count,
                "failed": len(variant_updates) - success_count,
                "message": f"成功更新 {success_count} 个变体"
            }
        else:
            from database.models import ProductVariant
            from crud.operations import create_action_log
            db = self._get_db_session()
            
            success_count = 0
            for update_data in variant_updates:
                try:
                    variant_id = update_data.pop('variant_id')
                    variant = db.query(ProductVariant).filter(
                        ProductVariant.id == variant_id
                    ).first()
                    
                    if variant:
                        for key, value in update_data.items():
                            setattr(variant, key, value)
                        success_count += 1
                except Exception as e:
                    print(f"更新变体失败: {e}")
            
            db.commit()
            
            create_action_log(
                db,
                operator_info,
                f'批量更新 {success_count} 个变体'
            )
            
            return {
                "success": success_count,
                "failed": len(variant_updates) - success_count,
                "message": f"成功更新 {success_count} 个变体"
            }
    
    # =========================
    # 销售相关方法
    # =========================
    
    def _convert_sales_orders_to_dict(
        self,
        orders: List[Any]
    ) -> List[Dict[str, Any]]:
        """将 SQLAlchemy SalesOrder 对象列表转换为字典列表
        
        Args:
            orders: SalesOrder 对象列表
            
        Returns:
            字典列表
        """
        from utils.type_safe import to_dict
        return [to_dict(order) for order in orders]
    
    def get_sales_orders(self, **filters) -> List[Dict]:
        """获取销售订单（统一返回字典列表）"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            result = client.get_sales_orders(**filters)
            # API 返回分页格式，提取 items
            if isinstance(result, dict) and 'items' in result:
                return result['items']
            return result if isinstance(result, list) else []
        else:
            from crud.sales import get_sales_orders
            db = self._get_db_session()
            orders = get_sales_orders(db, **filters)
            return self._convert_sales_orders_to_dict(orders)
    
    def get_sales_orders_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """分页获取销售订单
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（订单号或客户名）
            status: 订单状态筛选
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            {
                'items': [...],
                'total': 总数,
                'page': 当前页,
                'page_size': 每页数量,
                'total_pages': 总页数
            }
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_sales_orders_paginated(
                page, page_size, search, status, start_date, end_date
            )
        else:
            from crud.sales import get_sales_orders_paginated
            from datetime import datetime
            import math
            db = self._get_db_session()
            
            # 转换日期字符串为 datetime
            start_dt = (datetime.fromisoformat(start_date)
                       if start_date else None)
            end_dt = datetime.fromisoformat(end_date) if end_date else None
            
            orders, total = get_sales_orders_paginated(
                db, page, page_size, search, status, start_dt, end_dt
            )
            total_pages = math.ceil(total / page_size) if page_size > 0 else 0
            # 转换 SQLAlchemy 对象为字典
            items_dict = self._convert_sales_orders_to_dict(orders)
            return {
                'items': items_dict,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
    
    def search_sales_orders(self, search_text: str) -> List[Dict]:
        """搜索销售订单（按订单号或客户名，不限时间范围）"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.search_sales_orders(search_text)
        else:
            from crud.sales import search_sales_orders
            db = self._get_db_session()
            return search_sales_orders(db, search_text)
    
    def get_sale_order(self, order_id: int) -> Optional[Dict]:
        """获取单个销售订单"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_sale_order(order_id)
        else:
            from crud.sales import get_sale_order_by_id
            db = self._get_db_session()
            return get_sale_order_by_id(db, order_id)
    
    def create_sale_order(self, order_data: Dict) -> Any:
        """创建销售订单"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.create_sale_order(order_data)
        else:
            from crud.sales import create_sale_order
            db = self._get_db_session()
            return create_sale_order(db, order_data)
    
    def update_sale_order(self, order_id: int, order_data: Dict) -> Any:
        """更新销售订单"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.update_sale_order(order_id, order_data)
        else:
            from crud.sales import update_sale_order_status
            db = self._get_db_session()
            if 'status' in order_data:
                update_sale_order_status(db, order_id, order_data['status'])
            return {"message": "更新成功"}
    
    def delete_sale_order(self, order_id: int,
                         operator_info: Optional[Dict] = None) -> Any:
        """删除销售订单并恢复库存"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.delete_sale_order(order_id, operator_info)
        else:
            from crud.sales import delete_sale_order
            db = self._get_db_session()
            delete_sale_order(db, order_id, operator_info)
            return {"message": "删除成功"}
    
    # =========================
    # 发货相关方法
    # =========================
    
    def _convert_shipments_to_dict(
        self,
        shipments: List[Any]
    ) -> List[Dict[str, Any]]:
        """将 SQLAlchemy Shipment 对象列表转换为字典列表
        
        Args:
            shipments: Shipment 对象列表
            
        Returns:
            字典列表
        """
        from utils.type_safe import to_dict
        return [to_dict(shipment) for shipment in shipments]
    
    def get_shipments(self, **filters) -> List[Dict]:
        """获取发货记录（统一返回字典列表）"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            result = client.get_shipments(**filters)
            # API 可能返回分页格式或列表，统一处理
            if isinstance(result, dict) and 'items' in result:
                return result['items']
            return result if isinstance(result, list) else []
        else:
            from crud.shipment_operations import get_shipments
            db = self._get_db_session()
            shipments = get_shipments(db, **filters)
            return self._convert_shipments_to_dict(shipments)
    
    def get_shipment(self, shipment_id: int) -> Optional[Dict]:
        """获取单个发货记录"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            # 需要添加这个方法到api_client
            shipments = client.get_shipments()
            for s in shipments:
                if s.get('id') == shipment_id:
                    return s
            return None
        else:
            from crud.shipment_operations import get_shipment_by_id
            db = self._get_db_session()
            return get_shipment_by_id(db, shipment_id)
    
    def get_shipment_by_id(self, shipment_id: int) -> Optional[Dict]:
        """获取单个发货记录（别名方法）"""
        return self.get_shipment(shipment_id)
    
    def update_shipment_item(self, item_id: int, **kwargs) -> bool:
        """更新发货项（variant_id 或 quantity）
        
        Args:
            item_id: 发货项ID
            **kwargs: variant_id, quantity 等字段
            
        Returns:
            是否成功
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.update_shipment_item(item_id, **kwargs)
        else:
            from database.models import ShipmentItem
            db = self._get_db_session()
            
            item = db.query(ShipmentItem).filter(
                ShipmentItem.id == item_id
            ).first()
            
            if not item:
                return False
            
            # 更新字段
            if 'variant_id' in kwargs:
                item.variant_id = kwargs['variant_id']
            if 'quantity' in kwargs:
                item.quantity = kwargs['quantity']
            if 'tracking_number' in kwargs:
                item.tracking_number = kwargs['tracking_number']
            
            db.commit()
            return True
    
    def create_shipment(self, shipment_data: Dict) -> Any:
        """创建发货记录"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.create_shipment(shipment_data)
        else:
            from crud.shipment_operations import create_shipment
            db = self._get_db_session()
            return create_shipment(db, shipment_data)
    
    def update_shipment(self, shipment_id: int, 
                       shipment_data: Dict) -> Any:
        """更新发货记录"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            # 如果是更新状态,使用状态更新API
            if 'status' in shipment_data:
                try:
                    response = client._request(
                        'PATCH',
                        f'/api/shipments/{shipment_id}/status',
                        params={
                            'status': shipment_data['status'],
                            'operator_info': client._operator_info
                        }
                    )
                    return response
                except Exception as e:
                    print(f"更新发货状态失败: {e}")
                    raise
            else:
                # 其他更新使用PUT端点
                try:
                    response = client._request(
                        'PUT',
                        f'/api/shipments/{shipment_id}',
                        json=shipment_data,
                        params={'operator_info': client._operator_info}
                    )
                    return response
                except Exception as e:
                    print(f"更新发货记录失败: {e}")
                    raise
        else:
            from crud.shipment_operations import update_shipment_status
            db = self._get_db_session()
            if 'status' in shipment_data:
                update_shipment_status(
                    db, shipment_id, shipment_data['status']
                )
            return {"message": "更新成功"}
    
    def delete_shipment(self, shipment_id: int) -> Any:
        """删除发货记录"""
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.delete_shipment(shipment_id)
        else:
            from crud.shipment_operations import delete_shipment
            db = self._get_db_session()
            delete_shipment(db, shipment_id)
            return {"message": "删除成功"}
    
    def get_in_transit_inventory(
        self,
        variant_sku: Optional[str] = None
    ) -> Dict[str, int]:
        """获取在途库存数量
        
        Args:
            variant_sku: 可选，指定SKU
            
        Returns:
            字典，key为SKU，value为在途数量
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_in_transit_inventory(variant_sku)
        else:
            from crud.shipment_operations import get_in_transit_inventory
            db = self._get_db_session()
            return get_in_transit_inventory(db, variant_sku)
    
    # =========================
    # 库存日志相关方法
    # =========================
    
    def get_operation_logs(self, start_date=None, end_date=None) -> List[Dict]:
        """获取库存操作日志
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            操作日志列表
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            logs = client.get_operation_logs(start_date=start_date,
                                            end_date=end_date)
            # 转换时间字符串回datetime对象
            for log in logs:
                if log.get('time') and isinstance(log['time'], str):
                    log['time'] = datetime.fromisoformat(log['time'])
            return logs
        else:
            from crud.inventory_logs import get_all_operation_logs
            db = self._get_db_session()
            return get_all_operation_logs(db, start_date=start_date,
                                         end_date=end_date)
    
    def adjust_inventory(self, sku: str, quantity: int, notes: str,
                        operator_info: Dict) -> Any:
        """调整库存
        
        Args:
            sku: SKU
            quantity: 数量变化(正数入库,负数出库)
            notes: 备注
            operator_info: 操作者信息
        
        Returns:
            调整结果
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            # API需要所有参数打包
            return client.adjust_inventory(sku, quantity, notes, operator_info)
        else:
            from crud.operations import (create_stock_log, get_variant_by_sku,
                                        create_action_log)
            db = self._get_db_session()
            
            # 获取变体
            variant = get_variant_by_sku(db, sku)
            if not variant:
                raise ValueError(f"SKU {sku} 不存在")
            
            # 记录库存日志
            create_stock_log(db, variant_id=variant.id,
                           change_quantity=quantity,
                           notes=notes,
                           operator_info=operator_info)
            
            # 记录操作日志
            action_type = '入库' if quantity > 0 else '出库'
            create_action_log(db, operator_info,
                            f'{action_type}: {sku} ({abs(quantity)} 件)')
            
            db.commit()
            db.refresh(variant)
            
            return {
                "message": f"库存{action_type}成功",
                "sku": sku,
                "current_stock": variant.current_stock
            }
    
    def __del__(self):
        """清理数据库会话"""
        if self._db_session:
            self._db_session.close()
    
    def import_sales_orders(
        self,
        orders: List[Dict],
        operator_info: Dict
    ) -> Dict:
        """批量导入销售订单
        
        Args:
            orders: 订单列表
            operator_info: 操作员信息
            
        Returns:
            {'success': int, 'failed': int, 'errors': list}
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.import_sales_orders(orders, operator_info)
        else:
            from crud.sales import import_sales_orders
            db = self._get_db_session()
            return import_sales_orders(db, orders, operator_info)
    
    def import_shipments(
        self,
        shipments: List[Dict],
        operator_info: Dict
    ) -> Dict:
        """批量导入发货记录
        
        Args:
            shipments: 发货列表
            operator_info: 操作员信息
            
        Returns:
            {'success': int, 'failed': int, 'errors': list}
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.import_shipments(shipments, operator_info)
        else:
            from crud.shipment_operations import import_shipments
            db = self._get_db_session()
            return import_shipments(db, shipments, operator_info)
    
    # =========================
    # 操作日志相关方法
    # =========================
    
    def create_action_log(
        self,
        action: str,
        details: str,
        operator_info: Optional[Dict] = None
    ) -> bool:
        """创建操作日志
        
        Args:
            action: 操作类型
            details: 操作详情
            operator_info: 操作员信息
            
        Returns:
            是否成功
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.create_action_log(action, details, operator_info)
        else:
            from crud.operations import create_action_log
            db = self._get_db_session()
            try:
                create_action_log(db, action, details, operator_info)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                print(f"创建操作日志失败: {e}")
                return False
    
    def get_sku_sales_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取SKU销量统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            SKU销量统计列表
        """
        if app_mode.is_client_mode():
            client = self._get_api_client()
            return client.get_sku_sales_stats(start_date, end_date)
        else:
            from crud.sales import get_sku_sales_stats
            db = self._get_db_session()
            try:
                return get_sku_sales_stats(db, start_date, end_date)
            except Exception as e:
                print(f"获取SKU销量统计失败: {e}")
                return []


# 全局数据访问层实例
dal = DataAccessLayer()
