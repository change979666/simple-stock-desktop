"""
SimpleStock API Server - 模块化版本
使用 api/routes/ 中的路由模块
"""
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime
import uvicorn
from threading import Thread
import time
import sys
import os

# 导入错误处理和日志配置
from api.errors.handlers import register_exception_handlers
from utils.logging_config import setup_logging, get_logger
from utils.auto_backup import auto_backup

# 设置日志
setup_logging(level="INFO")
logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="SimpleStock API Server",
    version="5.2.0",
    description="库存管理系统后端API - 轻量级询问机制优化版(v5.2.0)"
)

# 🚀 启用 Gzip 压缩中间件（减少网络传输数据量 70-80%）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由模块
from api.routes import (
    products, sales, shipment, dashboard,
    inventory, logs, config, analytics, status
)

app.include_router(products.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(shipment.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(logs.router, prefix="/api/logs")
app.include_router(config.router, prefix="/api")  # 配置管理路由
app.include_router(analytics.router, prefix="/api")  # 数据分析路由
app.include_router(status.router, prefix="/api")  # 服务器状态路由（轻量级询问）


# Health Check
@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "SimpleStock API Server",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat()
    }


# 全局变量控制服务器
server_should_stop = False
server_restart_requested = False


# 自动备份任务
def auto_backup_task():
    """定时自动备份任务（每天凌晨2点）"""
    logger.info("🔄 自动备份任务已启动")
    
    while True:
        try:
            # 获取当前时间
            now = datetime.now()
            
            # 计算下次备份时间（明天凌晨2点）
            next_backup = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if now.hour >= 2:
                # 使用timedelta避免月末日期溢出问题
                from datetime import timedelta
                next_backup = next_backup + timedelta(days=1)
            
            # 等待到备份时间
            wait_seconds = (next_backup - now).total_seconds()
            logger.info(f"📅 下次自动备份时间: {next_backup.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(wait_seconds)
            
            # 执行备份
            logger.info("🔄 开始自动备份...")
            if auto_backup(max_backups=30):  # 保留30天的备份
                logger.info("✅ 自动备份成功")
            else:
                logger.error("❌ 自动备份失败")
                
        except Exception as e:
            logger.error(f"自动备份任务异常: {e}")
            time.sleep(3600)  # 出错后等待1小时再试


# 键盘监听线程
def keyboard_listener():
    """监听键盘输入"""
    global server_should_stop, server_restart_requested
    
    print("\n" + "="*60)
    print("💡 快捷键提示:")
    print("  - 按 'r' 然后回车: 重启服务器")
    print("  - 按 'q' 然后回车: 停止服务器")
    print("  - Ctrl+C: 强制停止")
    print("="*60 + "\n")
    
    while not server_should_stop:
        try:
            # Windows 下使用 msvcrt
            if os.name == 'nt':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').lower()
                    if key == 'r':
                        print("\n🔄 收到重启请求...")
                        server_restart_requested = True
                        server_should_stop = True
                        os._exit(66)  # 返回特殊退出码66表示重启
                    elif key == 'q':
                        print("\n⏹️  收到停止请求...")
                        server_should_stop = True
                        os._exit(0)  # 返回0表示正常退出
            else:
                # Linux/Mac 使用标准输入
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    if key == 'r':
                        print("\n🔄 收到重启请求...")
                        server_restart_requested = True
                        server_should_stop = True
                        os._exit(66)
                    elif key == 'q':
                        print("\n⏹️  收到停止请求...")
                        server_should_stop = True
                        os._exit(0)
            
            time.sleep(0.1)
        except Exception as e:
            # 忽略键盘监听异常
            time.sleep(1)


# 启动服务器
def start_server(host: str = "0.0.0.0", port: int = 8001):
    """启动API服务器"""
    logger.info("=" * 60)
    logger.info("SimpleStock API Server v4.0.0")
    logger.info("=" * 60)
    logger.info("服务器启动中...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info(f"API文档: http://localhost:{port}/docs")
    logger.info(f"健康检查: http://localhost:{port}/api/health")
    logger.info("=" * 60)
    
    # 启动自动备份线程
    backup_thread = Thread(target=auto_backup_task, daemon=True)
    backup_thread.start()
    logger.info("✅ 自动备份线程已启动（每天凌晨2点执行）")
    
    # 启动键盘监听线程
    keyboard_thread = Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
