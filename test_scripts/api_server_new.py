"""
SimpleStock API Server - 模块化版本
使用 api/routes/ 中的路由模块
"""
from fastapi import FastAPI
from datetime import datetime
import uvicorn

# 创建FastAPI应用
app = FastAPI(
    title="SimpleStock API Server",
    version="2.0.0",
    description="库存管理系统后端API - 模块化架构"
)

# 注册路由模块
from api.routes import products, sales, shipment, dashboard, inventory

app.include_router(products.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(shipment.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")


# Health Check
@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "SimpleStock API Server",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


# 启动服务器
def start_server(host: str = "0.0.0.0", port: int = 8001):
    """启动API服务器"""
    print("=" * 60)
    print("SimpleStock API Server")
    print("=" * 60)
    print(f"🚀 服务器启动中...")
    print(f"📡 监听地址: {host}:{port}")
    print(f"📖 API文档: http://localhost:{port}/docs")
    print(f"🔧 健康检查: http://localhost:{port}/api/health")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
