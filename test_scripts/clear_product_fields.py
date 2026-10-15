"""
清空产品表中的 name 和 stock_warning_level 字段
这两个字段已经不再需要：
- name 字段：产品名称不再使用
- stock_warning_level 字段：预警阈值改为在系统设置中统一配置

注意：由于 SQLite 不支持直接修改列约束，我们需要：
1. 创建新表（移除 name 的 NOT NULL 约束）
2. 复制数据
3. 删除旧表
4. 重命名新表
"""
import sys
from pathlib import Path
from sqlalchemy import update

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.session import SessionLocal, engine
from database.models.product import Product


def migrate_table_structure():
    """迁移表结构，移除 name 字段的 NOT NULL 约束"""
    
    print("🔄 开始修改表结构...")
    
    conn = engine.raw_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 创建新表（移除 name 的 NOT NULL 约束，允许 NULL）
        cursor.execute('''
            CREATE TABLE products_new (
                id INTEGER PRIMARY KEY,
                category_id INTEGER NOT NULL,
                name VARCHAR(100),  -- 移除 NOT NULL 约束
                description TEXT,
                parent_sku VARCHAR(50) UNIQUE NOT NULL,
                stock_warning_level INTEGER,  -- 移除 NOT NULL 约束
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        print("   ✅ 新表创建成功")
        
        # 2. 复制数据到新表
        cursor.execute('''
            INSERT INTO products_new 
            SELECT * FROM products
        ''')
        
        print("   ✅ 数据复制成功")
        
        # 3. 删除旧表
        cursor.execute('DROP TABLE products')
        print("   ✅ 旧表删除成功")
        
        # 4. 重命名新表
        cursor.execute('ALTER TABLE products_new RENAME TO products')
        print("   ✅ 新表重命名成功")
        
        # 5. 重新创建索引
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_parent_sku 
            ON products(parent_sku)
        ''')
        
        print("   ✅ 索引创建成功")
        
        conn.commit()
        print("✅ 表结构迁移完成!\n")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 表结构迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        cursor.close()
        conn.close()


def clear_product_fields():
    """清空产品表的 name 和 stock_warning_level 字段"""
    
    session = SessionLocal()
    
    try:
        # 统计当前有数据的记录数
        total_products = session.query(Product).count()
        products_with_name = session.query(Product).filter(
            Product.name.isnot(None),
            Product.name != ''
        ).count()
        products_with_warning = session.query(Product).filter(
            Product.stock_warning_level.isnot(None)
        ).count()
        
        print("📊 数据库统计信息:")
        print(f"   - 总产品数: {total_products}")
        print(f"   - 有名称的产品数: {products_with_name}")
        print(f"   - 有预警值的产品数: {products_with_warning}")
        print()
        
        if total_products == 0:
            print("⚠️  数据库中没有产品记录，无需清空")
            return
        
        # 确认操作
        print("⚠️  即将执行以下操作:")
        print("   1. 清空所有产品的 name 字段 (设为 NULL)")
        print("   2. 清空所有产品的 stock_warning_level 字段 (设为 NULL)")
        print()
        
        confirm = input("确认继续执行? (输入 yes 继续): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ 操作已取消")
            return
        
        print("\n🔄 开始清空字段...")
        
        # 清空 name 字段
        stmt_name = update(Product).values(name=None)
        result_name = session.execute(stmt_name)
        
        # 清空 stock_warning_level 字段
        stmt_warning = update(Product).values(stock_warning_level=None)
        result_warning = session.execute(stmt_warning)
        
        # 提交事务
        session.commit()
        
        print("✅ 字段清空成功!")
        print(f"   - name 字段已清空: {result_name.rowcount} 条记录")
        print(f"   - stock_warning_level 字段已清空: {result_warning.rowcount} 条记录")
        print()
        print("💡 提示:")
        print("   - name 字段已不再使用，产品信息通过 parent_sku 识别")
        print("   - 预警阈值现在在系统设置中统一配置")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()


def verify_clearing():
    """验证字段是否已清空"""
    session = SessionLocal()
    
    try:
        products_with_name = session.query(Product).filter(
            Product.name.isnot(None),
            Product.name != ''
        ).count()
        
        products_with_warning = session.query(Product).filter(
            Product.stock_warning_level.isnot(None)
        ).count()
        
        print("\n🔍 验证结果:")
        print(f"   - 仍有名称的产品数: {products_with_name}")
        print(f"   - 仍有预警值的产品数: {products_with_warning}")
        
        if products_with_name == 0 and products_with_warning == 0:
            print("   ✅ 所有字段已成功清空!")
        else:
            print("   ⚠️  仍有部分数据未清空")
    
    finally:
        session.close()


if __name__ == '__main__':
    print("=" * 60)
    print("清空产品表字段工具")
    print("=" * 60)
    print()
    
    # 先迁移表结构
    if migrate_table_structure():
        # 然后清空字段
        clear_product_fields()
        verify_clearing()
    else:
        print("\n❌ 表结构迁移失败，操作中止")
    
    print("\n" + "=" * 60)
    print("操作完成")
    print("=" * 60)
