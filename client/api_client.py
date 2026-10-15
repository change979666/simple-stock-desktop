"""
API客户端 - 所有与服务器的通信接口
这是客户端访问数据的唯一入口，完全隔离数据库访问
"""
import requests
from typing import List, Dict, Optional, Any
import json
import urllib.parse
from datetime import datetime


class APIClientError(Exception):
    """API客户端异常基类"""
    pass


class APIConnectionError(APIClientError):
    """服务器连接失败"""
    pass


class AuthenticationError(APIClientError):
    """认证失败"""
    pass


class ValidationError(APIClientError):
    """数据验证失败"""
    pass


class APIClient:
    """API客户端单例类"""
    
    _instance = None
    _base_url = ""
    _operator_info = ""
    _timeout = 10  # 默认超时10秒
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def configure(self, host: str, port: int = 8001, operator_info: str = ""):
        """配置API客户端
        
        Args:
            host: 服务器IP地址
            port: 服务器端口
            operator_info: 操作者信息（格式：昵称 (IP)）
        """
        self._base_url = f"http://{host}:{port}"
        self._operator_info = operator_info
    
    def set_operator_info(self, operator_info: str):
        """设置操作者信息"""
        self._operator_info = operator_info
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头
        
        Note: HTTP headers必须是ASCII/Latin-1编码，因此对中文进行URL编码
        """
        # 对操作者信息进行URL编码，避免中文字符导致的编码错误
        encoded_operator = urllib.parse.quote(self._operator_info, safe='')
        
        return {
            "Content-Type": "application/json",
            "X-Operator-Info": encoded_operator
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """统一的请求处理
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点路径
            **kwargs: requests库的其他参数
            
        Returns:
            响应的JSON数据
            
        Raises:
            APIConnectionError: 连接失败
            ValidationError: 数据验证失败
            APIClientError: 其他API错误
        """
        if not self._base_url:
            raise APIConnectionError("API客户端未配置，请先调用configure()方法")
        
        url = f"{self._base_url}{endpoint}"
        kwargs.setdefault('headers', self._get_headers())
        kwargs.setdefault('timeout', self._timeout)
        
        try:
            response = requests.request(method, url, **kwargs)
            
            # 处理HTTP状态码
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise ValidationError(f"数据验证失败: {response.text}")
            elif response.status_code == 401:
                raise AuthenticationError("认证失败")
            elif response.status_code == 404:
                raise APIClientError(f"资源不存在: {endpoint}")
            elif response.status_code >= 500:
                raise APIClientError(f"服务器错误: {response.status_code}")
            else:
                response.raise_for_status()
                return response.json()
                
        except requests.exceptions.Timeout:
            raise APIConnectionError(f"连接超时: 服务器未在{self._timeout}秒内响应")
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"无法连接到服务器 {self._base_url}: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"请求失败: {str(e)}")
    
    # ==================== 健康检查 ====================
    
    def health_check(self) -> Dict:
        """检查服务器健康状态"""
        return self._request('GET', '/api/health')
    
    def get_server_status(self) -> Dict:
        """
        获取服务器数据变更状态（轻量级询问接口）
        
        Returns:
            包含最后变更时间戳的字典：
            {
                "last_change": float,  # Unix时间戳
                "change_count": int,   # 变更次数
                "timestamp_readable": str  # 可读时间
            }
        """
        return self._request('GET', '/api/server/status')
    
    # ==================== 产品管理 ====================
    
    def get_products(self, limit_first_page: bool = False) -> List[Dict]:
        """获取所有产品列表,返回嵌套结构(Product + variants)
        
        Args:
            limit_first_page: 如果为True，只返回第一页数据（快速响应，推荐启动时使用）
        
        注意：当 limit_first_page=False 时会获取所有产品（自动处理分页），可能较慢。
        推荐使用 get_products_paginated() 进行分页查询。
        """
        all_products = []
        page = 1
        page_size = 100  # 每页获取100个以减少请求次数
        
        while True:
            # 获取当前页数据
            response = self._request('GET', '/api/products', params={
                'page': page,
                'page_size': page_size
            })
            
            # 后端返回的是分页结果：{'items': [...], 'total': N, 'page': 1, ...}
            if isinstance(response, dict) and 'items' in response:
                products = response['items']
                total_pages = response.get('total_pages', 1)
                
                # 转换为客户端期望的格式
                for p in products:
                    product = {
                        'id': p['id'],
                        'parent_sku': p.get('parent_sku', ''),
                        'name': p.get('name', ''),
                        'description': p.get('description', ''),
                        'stock_warning_level': p.get('stock_warning_level'),
                        'category_id': p.get('category_id'),
                        'variants': []
                    }
                    
                    # 处理变体
                    for v in p.get('variants', []):
                        variant = {
                            'id': v['id'],
                            'sku': v['sku'],
                            'option_name': v.get('option_name', ''),
                            'cost_price': v.get('cost_price', 0.0),
                            'current_stock': v.get('current_stock', 0),
                            'warning_level': 10,  # 变体预警值（待删除）
                            'product_id': product['id'],
                            'product': product
                        }
                        product['variants'].append(variant)
                    
                    all_products.append(product)
                
                # ========== 关键优化：支持只加载第一页 ==========
                if limit_first_page or page >= total_pages:
                    break
                page += 1
            else:
                # 如果返回格式不对，中断循环
                break
        
        return all_products
    
    def get_products_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Dict:
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
        params = {
            'page': page,
            'page_size': page_size
        }
        if search:
            params['search'] = search
        if category_id is not None:
            params['category_id'] = category_id
        
        response = self._request('GET', '/api/products', params=params)
        
        # 转换items为客户端期望的格式
        items = []
        for p in response.get('items', []):
            product = {
                'id': p['id'],
                'parent_sku': p.get('parent_sku', ''),
                'name': p.get('name', ''),
                'description': p.get('description', ''),
                'stock_warning_level': p.get('stock_warning_level'),
                'category_id': p.get('category_id'),
                'variants': []
            }
            
            for v in p.get('variants', []):
                variant = {
                    'id': v['id'],
                    'sku': v['sku'],
                    'option_name': v.get('option_name', ''),
                    'cost_price': v.get('cost_price', 0.0),
                    'current_stock': v.get('current_stock', 0),
                    'warning_level': 10,
                    'product_id': product['id'],
                    'product': product
                }
                product['variants'].append(variant)
            
            items.append(product)
        
        return {
            'items': items,
            'total': response.get('total', 0),
            'page': response.get('page', 1),
            'page_size': response.get('page_size', 50),
            'total_pages': response.get('total_pages', 0)
        }
    
    def get_product(self, product_id: int) -> Dict:
        """获取单个产品详情"""
        return self._request('GET', f'/api/products/{product_id}')
    
    def create_product(self, product_data: Dict) -> Dict:
        """创建产品
        
        Args:
            product_data: {
                "name": "产品名称",
                "parent_sku": "父SKU",
                "description": "描述",
                "warning_threshold": 10
            }
        """
        return self._request('POST', '/api/products', json=product_data)
    
    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        """更新产品"""
        return self._request('PUT', f'/api/products/{product_id}',
                           json=product_data)
    
    def delete_product(self, product_id: int, operator_info: Dict) -> Dict:
        """删除产品及所有变体"""
        params = {'operator_info': json.dumps(operator_info)}
        return self._request('DELETE', f'/api/products/{product_id}',
                           params=params)
    
    def delete_variant(self, variant_id: int, operator_info: Dict) -> Dict:
        """删除单个变体"""
        params = {'operator_info': json.dumps(operator_info)}
        return self._request('DELETE', f'/api/products/variants/{variant_id}',
                           params=params)
    
    def update_variant(self, variant_id: int, variant_data: Dict, 
                      operator_info: Dict) -> Dict:
        """更新变体信息
        
        Args:
            variant_id: 变体ID
            variant_data: {
                "sku": str (可选),
                "option1_value": str (可选),
                "option2_value": str (可选),
                "option3_value": str (可选),
                "cost_price": float (可选),
                "warning_level": int (可选)
            }
            operator_info: 操作者信息字典
            
        Returns:
            {"message": "变体更新成功"}
        """
        params = {'operator_info': json.dumps(operator_info)}
        return self._request('PUT', f'/api/products/variants/{variant_id}',
                           json=variant_data, params=params)
    
    def get_variant_by_id(self, variant_id: int) -> Optional[Dict]:
        """通过ID获取变体
        
        Args:
            variant_id: 变体ID
            
        Returns:
            变体信息字典，不存在则返回None
        """
        try:
            # 先尝试获取所有产品，然后查找
            products = self.get_products()
            for product in products:
                for variant in product.get('variants', []):
                    if variant.get('id') == variant_id:
                        return variant
            return None
        except Exception:
            return None
    
    def get_variant_by_sku(self, sku: str) -> Optional[Dict]:
        """通过SKU获取变体
        
        Args:
            sku: 变体SKU
            
        Returns:
            变体信息字典，不存在则返回None
        """
        return self._request('GET', f'/api/products/variants/sku/{sku}')
    
    def import_products(self, products: List[Dict], operator_info: Dict = None) -> Dict:
        """批量导入产品
        
        Args:
            products: [{
                "product_name": "产品名",
                "sku": "SKU",
                "option": "规格",
                "cost_price": 100.0,
                "warning_threshold": 10
            }, ...]
            operator_info: 操作员信息
            
        Returns:
            {"success": 10, "failed": 0, "message": "..."}
        """
        data = {"products": products}
        if operator_info:
            data["operator_info"] = json.dumps(operator_info, ensure_ascii=False)
        return self._request('POST', '/api/products/import', json=data)
    
    # ==================== 库存管理 ====================
    
    def get_inventory(self, sku: Optional[str] = None) -> List[Dict]:
        """获取库存信息
        
        Args:
            sku: 可选，指定SKU查询
        """
        params = {"sku": sku} if sku else {}
        return self._request('GET', '/api/inventory', params=params)
    
    def add_inventory(self, sku: str, quantity: int, notes: str = "") -> Dict:
        """增加库存
        
        Args:
            sku: 产品SKU
            quantity: 数量（正数）
            notes: 备注
        """
        data = {
            "sku": sku,
            "quantity": quantity,
            "notes": notes
        }
        return self._request('POST', '/api/inventory/add', json=data)
    
    def reduce_inventory(self, sku: str, quantity: int, 
                        reason: str = "销售") -> Dict:
        """减少库存
        
        Args:
            sku: 产品SKU
            quantity: 数量（正数）
            reason: 原因
        """
        data = {
            "sku": sku,
            "quantity": quantity,
            "reason": reason
        }
        return self._request('POST', '/api/inventory/reduce', json=data)
    
    def get_transit_inventory(self) -> List[Dict]:
        """获取在途库存"""
        return self._request('GET', '/api/inventory/transit')
    
    def get_operation_logs(self, start_date=None, end_date=None) -> List[Dict]:
        """获取库存操作日志
        
        Args:
            start_date: 开始日期(datetime或ISO字符串)
            end_date: 结束日期(datetime或ISO字符串)
        
        Returns:
            操作日志列表
        """
        params = {}
        if start_date:
            # 转换为ISO格式字符串
            if hasattr(start_date, 'isoformat'):
                params['start_date'] = start_date.isoformat()
            else:
                params['start_date'] = str(start_date)
        if end_date:
            if hasattr(end_date, 'isoformat'):
                params['end_date'] = end_date.isoformat()
            else:
                params['end_date'] = str(end_date)
        
        response = self._request('GET', '/api/inventory/logs', params=params)
        return response.get('logs', [])
    
    def adjust_inventory(self, sku: str, quantity: int, notes: str,
                        operator_info: Dict) -> Dict:
        """调整库存
        
        Args:
            sku: SKU
            quantity: 数量变化(正数入库,负数出库)
            notes: 备注
            operator_info: 操作者信息
        
        Returns:
            调整结果
        """
        data = {
            'sku': sku,
            'quantity': quantity,
            'notes': notes,
            'operator_info': operator_info
        }
        return self._request('POST', '/api/inventory/adjust', json=data)
    
    # ==================== 销售订单管理 ====================
    
    def get_sales_orders(self, **filters) -> List[Dict]:
        """获取销售订单列表
        
        Args:
            filters: status, start_date, end_date, customer_name等
        """
        params = {}
        for k, v in filters.items():
            if v is not None:
                # 转换datetime对象为ISO格式字符串
                if hasattr(v, 'isoformat'):
                    params[k] = v.isoformat()
                else:
                    params[k] = v
        return self._request('GET', '/api/sales/orders', params=params)
    
    def get_sales_orders_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
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
        params = {
            'page': page,
            'page_size': page_size
        }
        if search:
            params['search'] = search
        if status:
            params['status'] = status
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        return self._request('GET', '/api/sales/orders', params=params)
    
    def get_sale_order(self, order_id: int) -> Dict:
        """获取销售订单详情"""
        return self._request('GET', f'/api/sales/orders/{order_id}')
    
    def get_shipments_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sku: Optional[str] = None
    ) -> Dict:
        """分页获取发货记录
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            status: 发货状态筛选
            start_date: 开始日期
            end_date: 结束日期
            sku: SKU搜索
        
        Returns:
            {
                'items': [...],
                'total': 总数,
                'page': 当前页,
                'page_size': 每页数量,
                'total_pages': 总页数
            }
        """
        params = {
            'page': page,
            'page_size': page_size
        }
        if status:
            params['status'] = status
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if sku:
            params['sku'] = sku
        
        return self._request('GET', '/api/shipments/paginated', params=params)
    
    def create_sale_order(self, order_data: Dict) -> Dict:
        """创建销售订单"""
        return self._request('POST', '/api/sales/orders', json=order_data)
    
    def update_sale_order(self, order_id: int, order_data: Dict) -> Dict:
        """更新销售订单"""
        return self._request('PUT', f'/api/sales/orders/{order_id}', 
                            json=order_data)
    
    def delete_sale_order(self, order_id: int, 
                         operator_info: Optional[Dict] = None) -> Dict:
        """删除销售订单"""
        import json
        params = {}
        if operator_info:
            params['operator_info'] = json.dumps(operator_info, 
                                                ensure_ascii=False)
        return self._request('DELETE', f'/api/sales/orders/{order_id}',
                           params=params)
    
    def search_sales_orders(self, search_text: str) -> List[Dict]:
        """搜索销售订单（按订单号或客户名，不限时间范围）
        
        Args:
            search_text: 搜索文本（匹配订单号或客户名）
            
        Returns:
            匹配的订单列表，按日期降序排列
        """
        params = {'search': search_text}
        return self._request('GET', '/api/sales/orders/search', params=params)
    
    # ==================== 销售管理 ====================
    
    def create_sale(self, sale_data: Dict) -> Dict:
        """创建销售记录
        
        Args:
            sale_data: {
                "sku": "SKU",
                "quantity": 10,
                "sale_price": 199.0,
                "sale_date": "2025-10-12",
                "notes": "备注"
            }
        """
        return self._request('POST', '/api/sales', json=sale_data)
    
    def get_sales(self, start_date: Optional[str] = None, 
                  end_date: Optional[str] = None) -> List[Dict]:
        """获取销售记录
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        return self._request('GET', '/api/sales', params=params)
    
    def get_daily_sales(self, date: str) -> Dict:
        """获取指定日期的销售统计
        
        Args:
            date: 日期 YYYY-MM-DD
            
        Returns:
            {
                "date": "2025-10-12",
                "total_sales": 1999.0,
                "total_orders": 10
            }
        """
        return self._request('GET', f'/api/sales/daily/{date}')
    
    def import_sales(self, sales: List[Dict]) -> Dict:
        """批量导入销售记录"""
        return self._request('POST', '/api/sales/import', 
                            json={"sales": sales})
    
    # ==================== 发货管理 ====================
    
    def create_shipment(self, shipment_data: Dict) -> Dict:
        """创建发货单
        
        Args:
            shipment_data: {
                "batch_number": "批次号",
                "estimated_arrival": "2025-10-20",
                "items": [
                    {"sku": "ABC001", "quantity": 100},
                    {"sku": "ABC002", "quantity": 50}
                ],
                "notes": "备注"
            }
        """
        return self._request('POST', '/api/shipments', json=shipment_data)
    
    def get_shipments(self, 
                     status: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     sku: Optional[str] = None) -> List[Dict]:
        """获取发货单列表（支持服务端过滤）
        
        Args:
            status: 可选，筛选状态 (pending/in_transit/arrived/shelved/cancelled)
            start_date: 可选，创建开始日期 (YYYY-MM-DD)
            end_date: 可选，创建结束日期 (YYYY-MM-DD)
            sku: 可选，SKU搜索（模糊匹配）
        """
        params = {}
        if status:
            params['status'] = status
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if sku:
            params['sku'] = sku
        return self._request('GET', '/api/shipments', params=params)
    
    def update_shipment_status(self, shipment_id: int, 
                              new_status: str, notes: str = "") -> Dict:
        """更新发货单状态
        
        Args:
            shipment_id: 发货单ID
            new_status: 新状态 (shipped/arrived)
            notes: 备注
        """
        data = {
            "status": new_status,
            "notes": notes
        }
        return self._request('PUT', f'/api/shipments/{shipment_id}/status', 
                            json=data)
    
    def delete_shipment(self, shipment_id: int) -> Dict:
        """删除发货记录
        
        Args:
            shipment_id: 发货单ID
            
        Returns:
            删除结果
        """
        # API需要operator_info参数
        params = {'operator_info': self._operator_info}
        return self._request('DELETE', f'/api/shipments/{shipment_id}', 
                            params=params)
    
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
        params = {}
        if variant_sku:
            params['sku'] = variant_sku
        return self._request('GET', '/api/shipments/in-transit', params=params)
    
    # ==================== 操作日志 ====================
    
    def get_operation_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        operator: Optional[str] = None
    ) -> Dict:
        """分页获取操作日志
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            start_date: 开始日期
            end_date: 结束日期
            operator: 操作人员筛选
        
        Returns:
            {
                'items': [...],
                'total': 总数量,
                'page': 当前页,
                'page_size': 每页数量,
                'total_pages': 总页数
            }
        """
        params = {
            'page': page,
            'page_size': page_size
        }
        if start_date:
            if isinstance(start_date, datetime):
                params['start_date'] = start_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params['start_date'] = start_date
        if end_date:
            if isinstance(end_date, datetime):
                params['end_date'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params['end_date'] = end_date
        if operator:
            params['operator'] = operator
        
        return self._request('GET', '/api/logs/operations/paginated', params=params)
    
    def get_operation_logs(self, start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          action_type: Optional[str] = None) -> List[Dict]:
        """获取操作日志
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            action_type: 操作类型筛选
        """
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if action_type:
            params['action_type'] = action_type
        return self._request('GET', '/api/logs/operations', params=params)
    
    def get_action_logs(self, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict]:
        """获取动作日志"""
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        return self._request('GET', '/api/logs/actions', params=params)
    
    def get_operation_logs_count(self, cutoff_date) -> Dict:
        """获取指定日期之前的操作日志数量（用于清空前预览）
        
        Args:
            cutoff_date: 截止日期
            
        Returns:
            包含count的字典
        """
        return self._request(
            'GET',
            '/api/logs/operations/count',
            params={'cutoff_date': cutoff_date.isoformat()}
        )
    
    def clear_old_logs(self, cutoff_date) -> Dict:
        """清空指定日期之前的操作日志
        
        Args:
            cutoff_date: 截止日期
            
        Returns:
            包含success和deleted_count的字典
        """
        return self._request(
            'DELETE',
            '/api/logs/operations/clear',
            params={
                'cutoff_date': cutoff_date.isoformat(),
                'operator_info': self._operator_info
            }
        )
    
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
        try:
            self._request(
                'POST',
                '/api/logs/actions',
                json={
                    'action': action,
                    'details': details,
                    'operator_info': operator_info or self._operator_info
                }
            )
            return True
        except Exception as e:
            print(f"创建操作日志失败: {e}")
            return False
    
    # ==================== 仪表板统计 ====================
    
    def get_batch_dashboard_data(self, threshold: float = 1.0) -> Dict:
        """批量获取仪表盘所有数据（性能优化）
        
        一次API调用获取所有统计数据和库存警告
        
        Args:
            threshold: 库存警告阈值(默认1.0表示100%)
            
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
        params = {"threshold": threshold}
        return self._request('GET', '/api/dashboard/all', params=params)
    
    def get_dashboard_stats(self) -> Dict:
        """获取仪表板所有统计数据
        
        Returns:
            包含today, yesterday, week, month的统计数据字典
        """
        return {
            'today': self.get_dashboard_stats_today(),
            'yesterday': self.get_dashboard_stats_yesterday(),
            'week': self.get_dashboard_stats_week(),
            'month': self.get_dashboard_stats_month()
        }
    
    def get_dashboard_stats_today(self) -> Dict:
        """获取今日销售统计"""
        return self._request('GET', '/api/dashboard/stats/today')
    
    def get_dashboard_stats_yesterday(self) -> Dict:
        """获取昨日销售统计"""
        return self._request('GET', '/api/dashboard/stats/yesterday')
    
    def get_dashboard_stats_week(self) -> Dict:
        """获取最近7天销售统计"""
        return self._request('GET', '/api/dashboard/stats/week')
    
    def get_dashboard_stats_month(self) -> Dict:
        """获取最近30天销售统计"""
        return self._request('GET', '/api/dashboard/stats/month')
    
    def get_dashboard_warnings(self, threshold: float = 1.0) -> List[Dict]:
        """获取库存预警列表
        
        Args:
            threshold: 警告阈值(默认1.0表示100%)
        """
        params = {"threshold": threshold}
        return self._request('GET', '/api/dashboard/warnings', params=params)
    
    def get_inventory_warnings(self, threshold: float = 1.0) -> List[Dict]:
        """获取库存预警列表(别名方法,与get_dashboard_warnings相同)"""
        return self.get_dashboard_warnings(threshold)
    
    def get_variant_sales_stats(self, variant_sku: str) -> Dict:
        """获取指定SKU的销量统计
        
        Args:
            variant_sku: 变体SKU
            
        Returns:
            {'variant_sku': str, 'today': int, 'yesterday': int, 
             'week': int, 'month': int}
        """
        return self._request(
            'GET',
            f'/api/dashboard/sales-stats/{variant_sku}'
        )
    
    def get_batch_variant_sales_stats(
        self,
        variant_skus: List[str]
    ) -> Dict[str, Dict]:
        """批量获取多个SKU的销量统计（性能优化）
        
        Args:
            variant_skus: SKU列表
            
        Returns:
            {'sku1': {'today': 0, 'yesterday': 0, ...}, 'sku2': {...}}
        """
        return self._request(
            'POST',
            '/api/dashboard/sales-stats/batch',
            json=variant_skus
        )
    
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
        data = {
            'orders': orders,
            'operator_info': json.dumps(operator_info, ensure_ascii=False)
        }
        return self._request('POST', '/api/sales/import', json=data)
    
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
        data = {
            'shipments': shipments,
            'operator_info': json.dumps(operator_info, ensure_ascii=False)
        }
        return self._request('POST', '/api/shipments/import', json=data)
    
    def update_shipment_item(self, item_id: int, **kwargs) -> bool:
        """更新发货项
        
        Args:
            item_id: 发货项ID
            **kwargs: variant_id, quantity, tracking_number 等字段
            
        Returns:
            是否成功
        """
        try:
            self._request(
                'PUT',
                f'/api/shipments/items/{item_id}',
                json=kwargs
            )
            return True
        except Exception as e:
            print(f"更新发货项失败: {e}")
            return False
    
    # ==================== 配置管理 ====================
    
    def get_all_config(self) -> Dict:
        """获取所有配置
        
        Returns:
            完整的配置字典
        """
        response = self._request('GET', '/api/config/all')
        return response.get('config', {})
    
    def get_config_value(self, path: str) -> Any:
        """获取指定配置项
        
        Args:
            path: 配置路径，使用点分隔，例如 "server.host_ip"
            
        Returns:
            配置值
        """
        params = {'path': path}
        response = self._request('GET', '/api/config/get', params=params)
        return response.get('value')
    
    def set_config_value(self, path: List[str], value: Any) -> Dict:
        """设置配置项
        
        Args:
            path: 配置路径列表，例如 ['server', 'host_ip']
            value: 配置值
            
        Returns:
            操作结果
        """
        data = {
            'path': path,
            'value': value
        }
        return self._request('POST', '/api/config/set', json=data)
    
    def update_config(self, config: Dict[str, Any]) -> Dict:
        """批量更新配置
        
        Args:
            config: 配置字典
            
        Returns:
            操作结果
        """
        data = {'config': config}
        return self._request('POST', '/api/config/update', json=data)
    
    def reload_config(self) -> Dict:
        """重新加载配置
        
        Returns:
            操作结果
        """
        return self._request('POST', '/api/config/reload')
    
    def get_sku_sales_stats(
        self,
        start_date,
        end_date
    ) -> List[Dict]:
        """获取SKU销量统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            SKU销量统计列表
        """
        from datetime import datetime
        
        # 确保是datetime对象
        if isinstance(start_date, datetime):
            start_str = start_date.isoformat()
        else:
            start_str = str(start_date)
            
        if isinstance(end_date, datetime):
            end_str = end_date.isoformat()
        else:
            end_str = str(end_date)
        
        return self._request(
            'GET',
            '/api/sales/sku_stats',
            params={
                'start_date': start_str,
                'end_date': end_str
            }
        )


# 全局API客户端实例
api_client = APIClient()


# ==================== 便捷函数 ====================

def get_api_client() -> APIClient:
    """获取全局API客户端实例
    
    Returns:
        APIClient: 全局API客户端实例
    """
    return api_client


def configure_client(host: str, port: int, operator_info: str):
    """配置全局API客户端"""
    api_client.configure(host, port, operator_info)


def set_operator_info(operator_info: str):
    """设置操作者信息"""
    api_client.set_operator_info(operator_info)


def test_connection() -> bool:
    """测试服务器连接
    
    Returns:
        True: 连接成功
        False: 连接失败
    """
    try:
        api_client.health_check()
        return True
    except Exception:
        return False

