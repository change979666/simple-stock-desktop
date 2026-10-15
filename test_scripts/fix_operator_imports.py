"""Fix operator_info imports"""
import os
from pathlib import Path

files = [
    "gui/inventory_view.py",
    "gui/product_view.py",
    "gui/sales_view.py",
    "test_delete_order.py",
    "test_inventory_operations.py",
    "test_product_operations.py",
    "test_sales_operations.py",
    "test_shipment_operations.py"
]

old_import = "from utils.operator_info import get_operator_info"
new_import = "from utils.operator import get_operator_info"

total_replaced = 0

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = content.replace(old_import, new_import)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            count = original.count(old_import)
            total_replaced += count
            print(f"✓ {file_path} - replaced {count} occurrences")
    else:
        print(f"✗ {file_path} - not found")

print(f"\nTotal replaced: {total_replaced} import statements")
