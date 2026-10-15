#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查恢复的数据库内容"""

import sqlite3

def check_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    print("=" * 60)
    print("数据库恢复检查")
    print("=" * 60)
    
    # 获取所有表
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"\n📋 数据库表({len(tables)}个):")
    for table in tables:
        table_name = table[0]
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"  • {table_name}: {count} 条记录")
        except Exception as e:
            print(f"  • {table_name}: 错误 - {e}")
    
    # 检查关键数据
    print("\n" + "=" * 60)
    print("关键数据统计")
    print("=" * 60)
    
    try:
        products = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        print(f"✅ 产品: {products}")
    except:
        print("❌ 产品表不存在或无法访问")
    
    try:
        variants = cursor.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
        print(f"✅ 变体: {variants}")
    except:
        print("❌ 变体表不存在或无法访问")
    
    try:
        orders = cursor.execute("SELECT COUNT(*) FROM sale_orders").fetchone()[0]
        print(f"✅ 销售订单: {orders}")
    except:
        print("❌ 销售订单表不存在或无法访问")
    
    try:
        items = cursor.execute("SELECT COUNT(*) FROM sale_order_items").fetchone()[0]
        print(f"✅ 订单明细: {items}")
    except:
        print("❌ 订单明细表不存在或无法访问")
    
    # 显示部分产品数据
    print("\n" + "=" * 60)
    print("产品示例(前5个)")
    print("=" * 60)
    
    try:
        products = cursor.execute("""
            SELECT p.product_code, p.product_name, COUNT(pv.id) as variant_count
            FROM products p
            LEFT JOIN product_variants pv ON p.id = pv.product_id
            GROUP BY p.id
            LIMIT 5
        """).fetchall()
        
        for code, name, var_count in products:
            print(f"  • {code} - {name} ({var_count}个变体)")
    except Exception as e:
        print(f"❌ 无法查询产品: {e}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 数据库检查完成!")
    print("=" * 60)

if __name__ == "__main__":
    check_database()
