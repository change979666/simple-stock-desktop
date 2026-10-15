"""
配置管理 API 路由
提供配置的读取和更新接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from config.unified_config import (
    get_all_config,
    get_config,
    set_config,
    save_config
)

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    path: list[str]  # 配置路径，例如 ["server", "host_ip"]
    value: Any       # 配置值


class ConfigBatchUpdateRequest(BaseModel):
    """批量配置更新请求"""
    config: Dict[str, Any]


@router.get("/all")
async def get_all_configuration():
    """获取所有配置
    
    Returns:
        完整的配置字典
    """
    return {
        "success": True,
        "config": get_all_config()
    }


@router.get("/get")
async def get_configuration(path: str):
    """获取指定配置项
    
    Args:
        path: 配置路径，使用点分隔，例如 "server.host_ip"
        
    Returns:
        配置值
    """
    keys = path.split('.')
    value = get_config(*keys)
    
    if value is None:
        raise HTTPException(
            status_code=404,
            detail=f"配置项不存在: {path}"
        )
    
    return {
        "success": True,
        "path": path,
        "value": value
    }


@router.post("/set")
async def set_configuration(request: ConfigUpdateRequest):
    """设置配置项
    
    Args:
        request: 配置更新请求
        
    Returns:
        操作结果
    """
    try:
        set_config(*request.path, value=request.value)
        save_config()
        
        return {
            "success": True,
            "message": "配置已更新",
            "path": '.'.join(request.path),
            "value": request.value
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"配置更新失败: {str(e)}"
        )


@router.post("/update")
async def batch_update_configuration(request: ConfigBatchUpdateRequest):
    """批量更新配置
    
    Args:
        request: 批量配置更新请求
        
    Returns:
        操作结果
    """
    try:
        from config.unified_config import config_manager
        config_manager.update(request.config)
        save_config()
        
        return {
            "success": True,
            "message": "配置已批量更新",
            "updated_keys": list(request.config.keys())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"配置批量更新失败: {str(e)}"
        )


@router.post("/reload")
async def reload_configuration():
    """重新加载配置文件
    
    Returns:
        操作结果
    """
    try:
        from config.unified_config import reload_config
        reload_config()
        
        return {
            "success": True,
            "message": "配置已重新加载"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"配置重新加载失败: {str(e)}"
        )


@router.get("/server")
async def get_server_config():
    """获取服务器配置"""
    return {
        "success": True,
        "config": get_config('server')
    }


@router.get("/inventory")
async def get_inventory_config():
    """获取库存配置"""
    return {
        "success": True,
        "config": get_config('inventory')
    }


@router.get("/user")
async def get_user_config():
    """获取用户配置"""
    return {
        "success": True,
        "config": get_config('user_info')
    }
