from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter


def create_sales_template():
    """创建销售订单导入模板"""
    wb = Workbook()
    ws = wb.active
    ws.title = "销售订单导入"
    
    # 字段说明（中英文对照）
    field_desc = {
        'sku': '商品编号',
        'order_number': '订单编号',
        'customer_name': '客户名称',
        'order_date': '下单时间',
        'quantity': '数量',
        'selling_price': '销售价格',
        'net_selling_price': '净销售价格',
        'payment_time': '付款时间',
        'shipping_method': '配送方式',
        'tracking_number': '快递单号',
        'delivery_time': '发货时间'
    }
    
    # 定义表头
    required_headers = [
        'sku*', 'order_number*', 'customer_name*', 
        'order_date*', 'quantity*', 'selling_price*', 
        'net_selling_price*'
    ]
    optional_headers = [
        'payment_time', 'shipping_method', 
        'tracking_number', 'delivery_time'
    ]
    
    headers = required_headers + optional_headers
    
    # 设置样式
    red_font = Font(color="FF0000")
    header_fill = PatternFill(start_color="E9ECEF", fill_type="solid")
    desc_fill = PatternFill(start_color="FFF3CD", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 写入字段说明
    ws.insert_rows(1)
    for col, header in enumerate(headers, 1):
        field = header.rstrip('*')
        desc = field_desc.get(field, '')
        cell = ws.cell(row=1, column=col, value=f"{field}\n{desc}")
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center')
    
    # 写入表头和样式
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.border = thin_border
        if header.endswith('*'):
            cell.font = red_font
    
    # 添加示例数据
    example_data = [
        'TSHIRT-001-M-BK', 'ORDER2025001', '测试客户',
        '2025-09-26 13:50:00', '2', '50.00', '45.00',
        '2025-09-26 14:00:00', '快递', 'SF123456789',
        '2025-09-28 15:00:00'
    ]
    
    for col, value in enumerate(example_data, 1):
        cell = ws.cell(row=3, column=col, value=value)
        cell.border = thin_border
    
    # 调整列宽和行高
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    ws.row_dimensions[1].height = 40
    
    return wb


def create_product_template():
    """创建产品导入模板"""
    wb = Workbook()
    ws = wb.active
    ws.title = "产品导入"
    
    # 字段说明（中英文对照）
    field_desc = {
        'parent_sku': '父商品编号',
        'sku': '子商品编号',
        'option_name': '规格名称',
        'cost_price': '成本价格'
    }
    
    # 定义表头
    required_headers = [
        'parent_sku*', 'sku*', 'option_name*', 'cost_price*'
    ]
    
    # 设置样式
    red_font = Font(color="FF0000")
    header_fill = PatternFill(start_color="E9ECEF", fill_type="solid")
    desc_fill = PatternFill(start_color="FFF3CD", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 写入字段说明
    ws.insert_rows(1)
    for col, header in enumerate(required_headers, 1):
        field = header.rstrip('*')
        desc = field_desc.get(field, '')
        cell = ws.cell(row=1, column=col, value=f"{field}\n{desc}")
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center')
    
    # 写入表头和样式
    for col, header in enumerate(required_headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.border = thin_border
        if header.endswith('*'):
            cell.font = red_font
    
    # 添加示例数据
    example_data = [
        'TSHIRT-001', '基础款T恤', '50',
        'TSHIRT-001-M-BK', '尺寸:M,颜色:黑色', '25.00'
    ]
    
    for col, value in enumerate(example_data, 1):
        cell = ws.cell(row=3, column=col, value=value)
        cell.border = thin_border
    
    # 调整列宽和行高
    for col in range(1, len(required_headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20
    ws.row_dimensions[1].height = 40
    
    return wb


def create_stock_template():
    """创建库存导入模板"""
    wb = Workbook()
    ws = wb.active
    ws.title = "库存导入"
    
    # 字段说明（中英文对照）
    field_desc = {
        'sku': '商品编号',
        'change_quantity': '变动数量',
        'notes': '备注说明',
        'operator_info': '操作人员'
    }
    
    # 定义表头
    required_headers = [
        'sku*', 'change_quantity*', 
        'notes*', 'operator_info*'
    ]
    
    # 设置样式
    red_font = Font(color="FF0000")
    header_fill = PatternFill(start_color="E9ECEF", fill_type="solid")
    desc_fill = PatternFill(start_color="FFF3CD", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 写入字段说明
    ws.insert_rows(1)
    for col, header in enumerate(required_headers, 1):
        field = header.rstrip('*')
        desc = field_desc.get(field, '')
        cell = ws.cell(row=1, column=col, value=f"{field}\n{desc}")
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center')
    
    # 写入表头和样式
    for col, header in enumerate(required_headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.border = thin_border
        if header.endswith('*'):
            cell.font = red_font
    
    # 添加示例数据
    example_data = [
        'TSHIRT-001-M-BK', '100',
        '首批库存', '张三'
    ]
    
    for col, value in enumerate(example_data, 1):
        cell = ws.cell(row=3, column=col, value=value)
        cell.border = thin_border
    
    # 调整列宽和行高
    for col in range(1, len(required_headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20
    ws.row_dimensions[1].height = 40
    
    return wb


def main():
    """主函数"""
    import os
    
    # 确保docs目录存在
    docs_dir = 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    
    # 创建销售订单模板
    sales_wb = create_sales_template()
    sales_wb.save(os.path.join(docs_dir, '销售订单导入模板.xlsx'))
    
    # 创建产品模板
    product_wb = create_product_template()
    product_wb.save(os.path.join(docs_dir, '产品导入模板.xlsx'))
    
    # 创建库存模板
    stock_wb = create_stock_template()
    stock_wb.save(os.path.join(docs_dir, '库存导入模板.xlsx'))
    
    print("所有模板已创建完成!")


if __name__ == '__main__':
    main()
