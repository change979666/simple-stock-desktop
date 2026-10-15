import pandas as pd
from datetime import datetime
from typing import Dict, Union, List
import os

def export_to_excel(data: Dict[str, Union[pd.DataFrame, List]], filename: str) -> str:
    """
    将数据导出到Excel文件
    
    Args:
        data: 包含多个工作表数据的字典，键为工作表名称，值为DataFrame或list数据
        filename: 导出文件名
    
    Returns:
        str: 导出文件的完整路径
    """
    # 确保导出目录存在
    export_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'StockManager', 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    # 添加时间戳到文件名
    base, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    full_filename = f'{base}_{timestamp}{ext}'
    filepath = os.path.join(export_dir, full_filename)
    
    # 创建Excel写入器
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # 遍历所有数据表
        for sheet_name, sheet_data in data.items():
            # 如果数据不是DataFrame，转换为DataFrame
            if not isinstance(sheet_data, pd.DataFrame):
                sheet_data = pd.DataFrame(sheet_data)
            
            # 写入数据
            sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 获取工作表对象
            worksheet = writer.sheets[sheet_name]
            
            # 调整列宽
            for idx, col in enumerate(sheet_data.columns):
                max_length = max(
                    sheet_data[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
    
    return filepath