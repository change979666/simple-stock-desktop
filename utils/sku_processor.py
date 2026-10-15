"""SKU处理相关工具函数"""
from config.product_options import get_option_mapping


def process_wholesale_sku(
    sku: str,
    order_quantity: int = 1
) -> tuple[str, int]:
    """处理批发SKU,返回处理后的SKU和实际数量
    
    Args:
        sku: 原始SKU字符串,如 'BD03-咖啡×5'
        order_quantity: 订单中的数量,默认为1
        
    Returns:
        tuple: (处理后的SKU, 实际数量)
        例如:
            - ('BD03-咖色', 5) 当order_quantity=1时
            - ('BD03-咖色', 10) 当order_quantity=2时
    """
    # 获取选项映射配置
    option_mapping = get_option_mapping()
    
    if '×5' in sku:
        # 去掉×5后缀
        base_sku = sku.replace('×5', '').strip()
        # 批发数量(5)乘以订单数量
        actual_quantity = 5 * order_quantity
        
        # 处理选项名称标准化
        for old, new in option_mapping.items():
            if old in base_sku:
                base_sku = base_sku.replace(old, new)
                break
                
        return base_sku, actual_quantity
        
    # 非批发SKU返回原样和原始订单数量
    return sku, order_quantity


def standardize_option_name(option_name: str) -> str:
    """标准化选项名称
    
    Args:
        option_name: 原始选项名称
        
    Returns:
        标准化后的选项名称
    """
    # 从配置中获取映射关系
    mapping = get_option_mapping()
    return mapping.get(option_name, option_name)
