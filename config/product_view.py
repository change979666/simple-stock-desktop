"""产品视图相关配置"""
import json
import os
import sys
from typing import Dict

from utils.resource_path import get_app_data_path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 统一配置文件路径（改为使用 erp_settings.json）
CONFIG_FILE = get_app_data_path('erp_settings.json')

# 默认列宽比例
DEFAULT_COLUMN_RATIOS = {
    'parent_sku': 0.15,  # 父SKU列
    'child_sku': 0.35,  # 子SKU列
    'spec': 0.35,      # 规格列
    'price': 0.15,     # 价格列
}


def save_column_widths(column_widths: Dict[str, int]):
    """保存列宽设置到统一配置文件

    Args:
        column_widths: 列名到宽度的映射字典
    """
    try:
        # 读取现有配置
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 确保 column_widths 结构存在
        if 'column_widths' not in config:
            config['column_widths'] = {}
        
        # 转换为列表格式以保持一致性
        widths_list = [
            column_widths.get('parent_sku', 200),
            column_widths.get('child_sku', 180),
            column_widths.get('spec', 160),
            column_widths.get('price', 120)
        ]
        
        # 保存到 product_view 配置项
        config['column_widths']['product_view'] = {
            'columns': widths_list
        }
        
        # 写回配置文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            
        print('产品视图列宽已保存到统一配置文件')
        
    except Exception as e:
        print(f'⚠️ 保存列宽配置失败: {e}')


def load_column_widths() -> Dict[str, int]:
    """从统一配置文件加载列宽设置

    Returns:
        列名到宽度的映射字典,如果配置文件不存在则返回None
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 从统一配置中读取 product_view 配置
            if ('column_widths' in config and
                    'product_view' in config['column_widths']):
                product_config = config['column_widths']['product_view']
                widths_list = product_config.get('columns', [])
                
                # 转换回字典格式
                if len(widths_list) >= 4:
                    return {
                        'parent_sku': widths_list[0],
                        'child_sku': widths_list[1],
                        'spec': widths_list[2],
                        'price': widths_list[3]
                    }
            
            # 尝试从旧的独立配置文件迁移（兼容性处理）
            old_config_file = get_app_data_path('product_view.json')
            if os.path.exists(old_config_file):
                print('检测到旧配置文件，正在迁移...')
                with open(old_config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)
                
                # 保存到新配置
                save_column_widths(old_config)
                
                # 备份并删除旧文件
                backup_file = old_config_file + '.backup'
                os.rename(old_config_file, backup_file)
                print(f'✅ 配置已迁移，旧文件已备份为: {backup_file}')
                
                return old_config
                
    except Exception as e:
        print(f'⚠️ 读取列宽配置失败: {e}')
    
    return None

