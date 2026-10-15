"""数据库管理"""
import logging
import os
import sys
import time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# 导入resource_path工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.resource_path import get_app_data_path

logger = logging.getLogger(__name__)

# 创建声明性基类
Base = declarative_base()


def get_database_path():
    """获取数据库文件的绝对路径，支持多种访问路径
    
    注意：服务端启动时始终创建数据库，不受app_mode影响
    """
    # 使用get_app_data_path确保数据库在exe所在目录或项目根目录
    db_path = get_app_data_path('database.db')
    
    # 确保父目录存在
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    else:
        os.makedirs('.', exist_ok=True)
    
    print(f"使用数据库路径: {db_path}")
    return db_path


# 获取数据库文件的绝对路径并创建数据库引擎
DB_PATH = get_database_path()
print(f"使用数据库: {DB_PATH}")

# 确保数据库目录存在
parent_dir = os.path.dirname(DB_PATH)
if parent_dir:
    os.makedirs(parent_dir, exist_ok=True)

# 创建数据库引擎，优化配置
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    echo=False,
    # SQLite连接优化
    connect_args={
        'check_same_thread': False,  # 允许多线程访问
        'timeout': 30,               # 增加连接超时时间(秒)
    },
    # 连接池配置优化
    pool_size=10,           # 适度增加连接池大小
    max_overflow=20,        # 增加最大溢出连接数
    pool_timeout=30,        # 增加连接获取超时
    pool_recycle=1800,      # 30分钟回收一次连接
    pool_pre_ping=True      # 连接前ping，确保连接有效
)

# 创建会话工厂和线程安全的会话管理
Session = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 注意：推荐使用 get_db() 依赖注入，而不是直接使用 SessionLocal
# SessionLocal 仅为向后兼容保留
SessionLocal = Session

# 数据库性能监控
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(
    conn, cursor, statement,
    parameters, context, executemany
):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(
    conn, cursor, statement,
    parameters, context, executemany
):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.5:  # 记录执行时间超过0.5秒的查询
        logger.warning(f"慢查询 ({total:.2f}秒): {statement}")



class DBSessionManager:
    """
    数据库会话管理器（已弃用）
    
    警告: 此类已弃用，仅为向后兼容保留。
    推荐使用: 在 FastAPI 路由中使用 Depends(get_db) 进行依赖注入
    
    示例:
        @router.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            items = db.query(Model).all()
            return items
    """
    
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3
        self.backoff_time = 1  # 初始退避时间(秒)
        self.session = None

    def __enter__(self):
        """进入上下文管理器,返回数据库会话"""
        while self.retry_count < self.max_retries:
            try:
                self.session = Session()
                return self.session
            except SQLAlchemyError as e:
                self.retry_count += 1
                logger.error(f"数据库连接失败: {str(e)}")
                
                if self.retry_count >= self.max_retries:
                    logger.error(
                        f"数据库连接重试次数已达上限({self.max_retries}次)"
                    )
                    raise
                    
                # 指数退避
                time.sleep(self.backoff_time)
                self.backoff_time *= 2  # 下一次等待时间加倍

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器,确保关闭数据库会话"""
        if self.session:
            if exc_type is not None:
                # 发生异常时回滚
                try:
                    self.session.rollback()
                    logger.info("数据库会话已回滚")
                except Exception as e:
                    logger.error(f"回滚失败: {str(e)}")
            else:
                # 正常退出时提交
                try:
                    self.session.commit()
                    logger.debug("数据库会话已提交")
                except Exception as e:
                    logger.error(f"提交失败: {str(e)}")
                    self.session.rollback()
                    raise
            
            # 清理会话
            self.session.close()


def get_db():
    """获取数据库会话，适用于 FastAPI 的依赖注入
    
    使用示例:
    @router.get("/")
    async def read_items(db: Session = Depends(get_db)):
        # 在这里使用数据库会话
        items = await run_in_threadpool(lambda: db.query(Model).all())
        return items
    """
    db = Session()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表结构"""
    try:
        # 创建数据库表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化成功")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise


def get_optimizer(session):
    """获取查询优化器实例"""
    # 动态导入，避免循环导入
    from .query_optimizer import QueryOptimizer
    return QueryOptimizer(session)
