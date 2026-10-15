"""
类型安全工具模块
提供统一的数据访问辅助函数，兼容 SQLAlchemy 对象和字典
"""
from typing import Any, Optional, Dict, List
from datetime import datetime


def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """安全地获取对象属性或字典键值
    
    兼容三种数据类型：
    1. 字典 (dict) - 使用 obj.get(attr, default)
    2. SQLAlchemy 对象 - 使用 getattr(obj, attr, default)
    3. 字符串或其他类型 - 返回默认值
    
    Args:
        obj: 数据源对象（字典、ORM对象或其他类型）
        attr: 属性名或键名
        default: 默认值（当属性不存在时返回）
        
    Returns:
        属性值或默认值
        
    Example:
        >>> product = {'id': 1, 'name': 'Product A'}
        >>> safe_get_attr(product, 'name')  # 'Product A'
        >>> safe_get_attr(product, 'price', 0.0)  # 0.0
        
        >>> from database.models import Product
        >>> product = Product(id=1, name='Product A')
        >>> safe_get_attr(product, 'name')  # 'Product A'
    """
    if obj is None:
        return default
    
    if isinstance(obj, dict):
        return obj.get(attr, default)
    elif isinstance(obj, str):
        # 字符串类型直接返回默认值
        return default
    elif hasattr(obj, attr):
        return getattr(obj, attr, default)
    else:
        return default


def safe_get_nested(
    obj: Any,
    path: str,
    default: Any = None,
    separator: str = '.'
) -> Any:
    """安全地获取嵌套属性或键值
    
    Args:
        obj: 数据源对象
        path: 属性路径，使用分隔符连接（如 'user.profile.name'）
        default: 默认值
        separator: 路径分隔符（默认为 '.'）
        
    Returns:
        嵌套属性值或默认值
        
    Example:
        >>> data = {'user': {'profile': {'name': 'Alice'}}}
        >>> safe_get_nested(data, 'user.profile.name')  # 'Alice'
        >>> safe_get_nested(data, 'user.email', 'N/A')  # 'N/A'
    """
    if obj is None:
        return default
    
    keys = path.split(separator)
    current = obj
    
    for key in keys:
        current = safe_get_attr(current, key, None)
        if current is None:
            return default
    
    return current


def to_dict(obj: Any, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """将 SQLAlchemy 对象或其他对象转换为字典
    
    Args:
        obj: 要转换的对象
        exclude: 要排除的属性列表
        
    Returns:
        字典表示
        
    Example:
        >>> from database.models import Product
        >>> product = Product(id=1, name='Product A')
        >>> to_dict(product)  # {'id': 1, 'name': 'Product A', ...}
    """
    if obj is None:
        return {}
    
    # 如果已经是字典，直接返回
    if isinstance(obj, dict):
        if exclude:
            return {k: v for k, v in obj.items() if k not in exclude}
        return obj.copy()
    
    exclude = exclude or []
    result = {}
    
    # 处理 SQLAlchemy 对象
    if hasattr(obj, '__table__'):
        # SQLAlchemy 模型对象
        for column in obj.__table__.columns:
            key = column.name
            if key not in exclude:
                value = getattr(obj, key, None)
                # 处理特殊类型
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
    else:
        # 普通对象，使用 __dict__
        if hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if not key.startswith('_') and key not in exclude:
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                    else:
                        result[key] = value
    
    return result


def to_dict_list(
    objects: List[Any],
    exclude: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """批量将对象列表转换为字典列表
    
    Args:
        objects: 对象列表
        exclude: 要排除的属性列表
        
    Returns:
        字典列表
    """
    return [to_dict(obj, exclude) for obj in objects]


def ensure_dict(obj: Any) -> Dict[str, Any]:
    """确保对象是字典类型，如果不是则转换
    
    Args:
        obj: 对象
        
    Returns:
        字典
    """
    if isinstance(obj, dict):
        return obj
    return to_dict(obj)


def ensure_dict_list(objects: List[Any]) -> List[Dict[str, Any]]:
    """确保对象列表是字典列表，如果不是则转换
    
    Args:
        objects: 对象列表
        
    Returns:
        字典列表
    """
    return [ensure_dict(obj) for obj in objects]


def safe_int(value: Any, default: int = 0) -> int:
    """安全地转换为整数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        整数值或默认值
    """
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全地转换为浮点数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        浮点数值或默认值
    """
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """安全地转换为字符串
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        字符串值或默认值
    """
    if value is None:
        return default
    return str(value)
