"""
创建导入模板 - v2.0.1
包含详细的字段说明和测试数据
根据当前系统实际的导入逻辑创建模板
"""
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
import os


def create_product_import_template():
    """创建产品导入模板（符合v2.0.1规范）"""
    wb = Workbook()
    ws = wb.active
    ws.title = "产品导入"
    
    # 定义表头（根据实际导入逻辑）
    headers = ['parent_sku*', 'sku*', 'option_name*', 'cost_price*']
    
    # 字段说明
    field_descriptions = {
        'parent_sku': '父SKU编号（产品组标识）',
        'sku': '子SKU编号（唯一标识）',
        'option_name': '规格名称（如：颜色:黑色,尺寸:M）',
        'cost_price': '成本价格（数字）'
    }
    
    # 设置样式
    red_font = Font(color="FF0000", bold=True)
    header_fill = PatternFill(start_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    desc_fill = PatternFill(start_color="FFF2CC", fill_type="solid")
    example_fill = PatternFill(start_color="E2EFDA", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 第1行：字段说明
    for col, header in enumerate(headers, 1):
        field = header.rstrip('*')
        desc = field_descriptions.get(field, '')
        cell = ws.cell(row=1, column=col, value=f"{desc}")
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        cell.font = Font(size=9, italic=True)
    
    # 第2行：表头
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.border = thin_border
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 第3-7行：测试数据
    test_data = [
        # T恤系列
        ['TSHIRT', 'TSHIRT-M-BK', '尺寸:M,颜色:黑色', '25.00'],
        ['TSHIRT', 'TSHIRT-M-WH', '尺寸:M,颜色:白色', '25.00'],
        ['TSHIRT', 'TSHIRT-L-BK', '尺寸:L,颜色:黑色', '26.00'],
        # 帽子系列
        ['HAT', 'HAT-RED', '颜色:红色', '15.00'],
        ['HAT', 'HAT-BLUE', '颜色:蓝色', '15.00'],
        # 围巾系列
        ['SCARF', 'SCARF-SILK-RED', '材质:丝绸,颜色:红色', '45.00'],
        ['SCARF', 'SCARF-WOOL-BLK', '材质:羊毛,颜色:黑色', '55.00'],
    ]
    
    for row_idx, data in enumerate(test_data, start=3):
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.fill = example_fill
            cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # 调整列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 12
    
    # 调整行高
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    
    # 添加说明文本
    ws.cell(row=11, column=1, value="📝 导入说明：")
    ws.cell(row=12, column=1, value="1. parent_sku: 同一产品的不同规格使用相同的父SKU")
    ws.cell(row=13, column=1, value="2. sku: 每个产品变体的唯一编号，不能重复")
    ws.cell(row=14, column=1, value="3. option_name: 规格格式为 '属性:值,属性:值'")
    ws.cell(row=15, column=1, value="4. cost_price: 成本价格，必须是数字")
    ws.cell(row=16, column=1, value="5. 带 * 的字段为必填项")
    
    for row in range(11, 17):
        ws.cell(row=row, column=1).font = Font(size=9, italic=True, color="666666")
    
    return wb


def create_inventory_import_template():
    """创建库存导入模板（符合v2.0.1规范）"""
    wb = Workbook()
    ws = wb.active
    ws.title = "库存导入"
    
    # 定义表头 - 移除operator_info，由程序自动填充
    headers = ['sku*', 'change_quantity*', 'notes*']
    
    # 字段说明
    field_descriptions = {
        'sku': 'SKU编号（必须存在于系统中）',
        'change_quantity': '变动数量（正数=入库，负数=出库）',
        'notes': '备注说明（操作原因）'
    }
    
    # 设置样式
    header_fill = PatternFill(start_color="70AD47", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    desc_fill = PatternFill(start_color="FFF2CC", fill_type="solid")
    example_fill = PatternFill(start_color="E2EFDA", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 第1行：字段说明
    for col, header in enumerate(headers, 1):
        field = header.rstrip('*')
        desc = field_descriptions.get(field, '')
        cell = ws.cell(row=1, column=col, value=desc)
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        cell.font = Font(size=9, italic=True)
    
    # 第2行：表头
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.border = thin_border
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 第3-9行：测试数据（入库和出库示例）- 移除操作员列
    test_data = [
        ['BD79-Beige', '100', '首批入库'],
        ['BD79-Black', '100', '首批入库'],
        ['BD79-Blue', '100', '首批入库'],
        ['BD79-Khaki', '100', '首批入库'],
        ['BD79-Brown', '100', '首批入库'],
        ['BD80-Black', '100', '首批入库'],
        ['BD80-Brown Black', '100', '首批入库'],
        ['BD80-Dark brown', '100', '首批入库'],
        ['BD80-Light brown', '100', '首批入库'],
        ['BD81-Blue', '100', '首批入库'],
        ['BD81-Black', '100', '首批入库'],
        ['BD81-Pink', '100', '首批入库'],
        ['BD81-Apricot', '100', '首批入库'],
        ['BD81-Dark grey', '100', '首批入库'],
    ]
    
    for row_idx, data in enumerate(test_data, start=3):
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.fill = example_fill
            # 数量列右对齐
            if col == 2:
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # 调整列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 30
    
    # 调整行高
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    
    # 添加说明
    ws.cell(row=18, column=1, value="📝 导入说明：")
    ws.cell(row=19, column=1, value="1. sku: 必须是系统中已存在的SKU编号")
    ws.cell(row=20, column=1, value="2. change_quantity: 正数表示入库，负数表示出库")
    ws.cell(row=21, column=1, value="3. notes: 必填，说明入库/出库原因")
    ws.cell(row=22, column=1, value="4. 操作人员自动从当前登录用户获取")
    ws.cell(row=23, column=1, value="5. 导入前请确保SKU已在产品管理中创建")
    
    for row in range(18, 24):
        ws.cell(row=row, column=1).font = Font(size=9, italic=True, color="666666")
    
    return wb


def create_sales_import_template():
    """创建销售导入模板（符合v2.0.1规范）"""
    wb = Workbook()
    ws = wb.active
    ws.title = "销售订单导入"
    
    # 定义表头（必填字段）
    required_headers = ['sku*', 'order_number*', 'customer_name*', 'order_date*', 
                       'quantity*', 'selling_price*', 'total_amount*']
    
    all_headers = required_headers
    
    # 字段说明
    field_descriptions = {
        'sku': 'SKU编号',
        'order_number': '订单编号（唯一）',
        'customer_name': '客户名称',
        'order_date': '下单时间（YYYY-MM-DD HH:MM:SS）',
        'quantity': '销售数量',
        'selling_price': '销售单价',
        'total_amount': '订单总价（直接填写实际金额）'
    }
    
    # 设置样式
    required_fill = PatternFill(start_color="C00000", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    desc_fill = PatternFill(start_color="FFF2CC", fill_type="solid")
    example_fill = PatternFill(start_color="E2EFDA", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 第1行：字段说明
    for col, header in enumerate(all_headers, 1):
        field = header.rstrip('*')
        desc = field_descriptions.get(field, '')
        cell = ws.cell(row=1, column=col, value=desc)
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(
            wrap_text=True, horizontal='center', vertical='center'
        )
        cell.font = Font(size=9, italic=True)
    
    # 第2行：表头
    for col, header in enumerate(all_headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = required_fill
        cell.border = thin_border
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 第3-8行：测试数据
    base_date = datetime.now()
    test_data = [
        ['TSHIRT-M-BK', 'ORD2025001', '李明',
         (base_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
         '2', '59.90', '119.80'],

        ['TSHIRT-M-WH', 'ORD2025002', '王芳',
         (base_date - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S'),
         '1', '59.90', '59.90'],

        ['HAT-RED', 'ORD2025003', '张伟',
         (base_date - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
         '3', '35.00', '105.00'],

        ['SCARF-SILK-RED', 'ORD2025004', '刘静',
         (base_date - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
         '1', '89.90', '89.90'],

        ['TSHIRT-L-BK', 'ORD2025005', '赵强',
         (base_date - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
         '2', '59.90', '119.80'],

        ['HAT-BLUE', 'ORD2025006', '孙丽',
         base_date.strftime('%Y-%m-%d %H:%M:%S'),
         '1', '35.00', '35.00'],
    ]
    
    for row_idx, data in enumerate(test_data, start=3):
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.fill = example_fill
            # 数量和价格右对齐
            if col in [5, 6, 7]:
                cell.alignment = Alignment(
                    horizontal='right', vertical='center'
                )
            else:
                cell.alignment = Alignment(
                    horizontal='left', vertical='center'
                )
    
    # 调整列宽
    column_widths = [18, 15, 12, 20, 10, 12, 15]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # 调整行高
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    
    # 添加说明
    ws.cell(row=10, column=1, value="📝 导入说明：")
    ws.cell(row=11, column=1, value="1. 所有字段均为必填")
    ws.cell(
        row=12, column=1,
        value="2. order_number: 订单编号必须唯一，重复的订单会被跳过"
    )
    ws.cell(
        row=13, column=1,
        value="3. order_date: 时间格式 YYYY-MM-DD HH:MM:SS"
    )
    ws.cell(
        row=14, column=1,
        value="4. quantity: 销售数量，会自动扣减库存"
    )
    ws.cell(
        row=15, column=1,
        value="5. total_amount: 订单总价，直接填写实际支付金额"
    )
    ws.cell(
        row=16, column=1,
        value="6. 导入前请确保SKU存在且库存充足"
    )
    
    for row in range(10, 17):
        ws.cell(row=row, column=1).font = Font(
            size=9, italic=True, color="666666"
        )
    
    return wb


def create_shipment_import_template():
    """创建发货导入模板"""
    wb = Workbook()
    ws = wb.active
    ws.title = "发货记录导入"
    
    # 定义表头
    required_headers = ['sku*', 'quantity*', 'tracking_number*', 'estimated_arrival*']
    optional_headers = ['notes', 'batch_number']
    
    all_headers = required_headers + optional_headers
    
    # 字段说明
    field_descriptions = {
        'sku': 'SKU编号',
        'quantity': '发货数量',
        'tracking_number': '物流追踪号',
        'estimated_arrival': '预计到货日期（YYYY-MM-DD）',
        'notes': '备注（可选）',
        'batch_number': '批次号（可选）'
    }
    
    # 设置样式
    required_fill = PatternFill(start_color="FF6B00", fill_type="solid")
    optional_fill = PatternFill(start_color="A6A6A6", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    desc_fill = PatternFill(start_color="FFF2CC", fill_type="solid")
    example_fill = PatternFill(start_color="E2EFDA", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 第1行：字段说明
    for col, header in enumerate(all_headers, 1):
        field = header.rstrip('*')
        desc = field_descriptions.get(field, '')
        cell = ws.cell(row=1, column=col, value=desc)
        cell.fill = desc_fill
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        cell.font = Font(size=9, italic=True)
    
    # 第2行：表头
    for col, header in enumerate(all_headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        if header.endswith('*'):
            cell.fill = required_fill
        else:
            cell.fill = optional_fill
        cell.border = thin_border
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 第3-8行：测试数据
    arrival_date = datetime.now() + timedelta(days=7)
    test_data = [
        ['TSHIRT-M-BK', '200', 'YD2025010001', arrival_date.strftime('%Y-%m-%d'), '厂家直发', 'BATCH001'],
        ['TSHIRT-M-WH', '150', 'YD2025010002', arrival_date.strftime('%Y-%m-%d'), '厂家直发', 'BATCH001'],
        ['TSHIRT-L-BK', '180', 'YD2025010003', (arrival_date + timedelta(days=1)).strftime('%Y-%m-%d'), '补货', 'BATCH002'],
        ['HAT-RED', '100', 'SF2025010004', (arrival_date + timedelta(days=2)).strftime('%Y-%m-%d'), '新品到货', ''],
        ['HAT-BLUE', '100', 'SF2025010005', (arrival_date + timedelta(days=2)).strftime('%Y-%m-%d'), '新品到货', ''],
        ['SCARF-WOOL-BLK', '50', 'JD2025010006', (arrival_date + timedelta(days=3)).strftime('%Y-%m-%d'), '', 'BATCH003'],
    ]
    
    for row_idx, data in enumerate(test_data, start=3):
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
            cell.fill = example_fill
            if col == 2:  # 数量右对齐
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # 调整列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 15
    
    # 调整行高
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    
    # 添加说明
    ws.cell(row=10, column=1, value="📝 导入说明：")
    ws.cell(row=11, column=1, value="1. sku: 必须是系统中已存在的SKU")
    ws.cell(row=12, column=1, value="2. quantity: 发货数量，会创建在途库存记录")
    ws.cell(row=13, column=1, value="3. tracking_number: 物流追踪号，用于跟踪货物")
    ws.cell(row=14, column=1, value="4. estimated_arrival: 预计到货日期，格式 YYYY-MM-DD")
    ws.cell(row=15, column=1, value="5. 发货后需要手动确认到货以更新实际库存")
    
    for row in range(10, 16):
        ws.cell(row=row, column=1).font = Font(size=9, italic=True, color="666666")
    
    return wb


def main():
    """主函数 - 创建所有导入模板"""
    # 确保docs目录存在
    docs_dir = 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    
    print("=" * 60)
    print("SimpleStock 导入模板生成工具 v2.0.1")
    print("=" * 60)
    print()
    
    # 1. 产品导入模板
    print("📦 创建产品导入模板...")
    product_wb = create_product_import_template()
    product_file = os.path.join(docs_dir, '产品导入模板_v2.0.1.xlsx')
    product_wb.save(product_file)
    print(f"   ✅ 已保存: {product_file}")
    
    # 2. 库存导入模板
    print("📊 创建库存导入模板...")
    inventory_wb = create_inventory_import_template()
    inventory_file = os.path.join(docs_dir, '库存导入模板_v2.0.1.xlsx')
    inventory_wb.save(inventory_file)
    print(f"   ✅ 已保存: {inventory_file}")
    
    # 3. 销售导入模板
    print("💰 创建销售导入模板...")
    sales_wb = create_sales_import_template()
    sales_file = os.path.join(docs_dir, '销售订单导入模板_v2.0.1.xlsx')
    sales_wb.save(sales_file)
    print(f"   ✅ 已保存: {sales_file}")
    
    # 4. 发货导入模板
    print("🚚 创建发货导入模板...")
    shipment_wb = create_shipment_import_template()
    shipment_file = os.path.join(docs_dir, '发货记录导入模板_v2.0.1.xlsx')
    shipment_wb.save(shipment_file)
    print(f"   ✅ 已保存: {shipment_file}")
    
    print()
    print("=" * 60)
    print("✨ 所有模板创建完成！")
    print("=" * 60)
    print()
    print("📁 模板位置: ./docs/")
    print()
    print("📝 使用说明:")
    print("   1. 每个模板包含字段说明、表头和测试数据")
    print("   2. 带 * 的字段为必填项")
    print("   3. 可以直接编辑测试数据进行导入测试")
    print("   4. 详细字段说明请查看模板中的说明行")
    print()


if __name__ == '__main__':
    main()
