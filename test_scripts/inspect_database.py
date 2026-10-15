import sys
import sqlite3

sys.path.append('.')

# 连接数据库
db_path = 'database.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()


def inspect_database():
    print('\n=== 数据库检查 ===')
    
    # 检查表结构
    print('\n表结构:')
    c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = c.fetchall()
    print('发现表:', ', '.join(table[0] for table in tables))
    
    # 检查 stock_logs 表
    print('\nStock Logs 表结构:')
    c.execute('PRAGMA table_info(stock_logs)')
    columns = c.fetchall()
    for col in columns:
        print(f'列: {col[1]}, 类型: {col[2]}')
    
    # 检查样本数据
    print('\nStock Logs 样本数据:')
    c.execute('''
        SELECT id, operator_info, created_at, change_quantity, notes
        FROM stock_logs
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    rows = c.fetchall()
    for row in rows:
        print('\n记录:')
        print(f'ID: {row[0]}')
        print(f'Operator Info: {repr(row[1])}')
        print(f'Created At: {row[2]}')
        print(f'Change Quantity: {row[3]}')
        print(f'Notes: {row[4]}')
    
    # 检查 action_logs 表
    print('\nAction Logs 表结构:')
    c.execute('PRAGMA table_info(action_logs)')
    columns = c.fetchall()
    for col in columns:
        print(f'列: {col[1]}, 类型: {col[2]}')
    
    # 检查样本数据
    print('\nAction Logs 样本数据:')
    c.execute('''
        SELECT id, operator_info, created_at, action
        FROM action_logs
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    rows = c.fetchall()
    for row in rows:
        print('\n记录:')
        print(f'ID: {row[0]}')
        print(f'Operator Info: {repr(row[1])}')
        print(f'Created At: {row[2]}')
        print(f'Action: {row[3]}')


if __name__ == '__main__':
    try:
        inspect_database()
    finally:
        conn.close()