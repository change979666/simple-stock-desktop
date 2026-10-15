from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import sys

# 导入resource_path工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.resource_path import get_app_data_path

# 创建基类
Base = declarative_base()

def get_database_path():
    """获取数据库文件的绝对路径，兼容打包后的环境"""
    # 使用get_app_data_path确保数据库在exe所在目录
    return get_app_data_path('database.db')

# 获取数据库文件的绝对路径
DB_PATH = get_database_path()
print(f"使用数据库: {DB_PATH}")

# 确保数据库目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 创建数据库引擎，优化配置 - 减小连接池大小，适合桌面应用
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    echo=False,
    # SQLite连接优化
    connect_args={
        'check_same_thread': False,  # 允许多线程访问
        'timeout': 20,               # 连接超时时间(秒)
    },
    # 连接池配置 - 更适合桌面应用的参数
    pool_size=5,            # 减小连接池大小
    max_overflow=10,        # 减小最大溢出连接数
    pool_timeout=15,        # 减少连接获取超时
    pool_recycle=300,       # 更频繁地回收连接
    pool_pre_ping=True      # 连接前ping，确保连接有效
)

# 创建会话工厂
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    # 设置expire_on_commit=False来避免不必要的数据库查询
    expire_on_commit=False
)

def get_db():
    """获取数据库会话 - 增加错误恢复机制"""
    retry_count = 0
    max_retries = 3
    backoff_time = 1  # 初始退避时间(秒)
    last_error = None
    
    while retry_count < max_retries:
        try:
            db = SessionLocal()
            yield db
            break
        except Exception as e:
            retry_count += 1
            last_error = e
            
            if retry_count >= max_retries:
                # 所有重试都失败了
                print(f"数据库连接失败，已重试{max_retries}次: {str(e)}")
                raise
                
            # 指数退避
            import time
            time.sleep(backoff_time)
            backoff_time *= 2  # 下一次等待时间加倍
        finally:
            if 'db' in locals():
                db.close()

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)