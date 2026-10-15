"""
服务器状态路由 - 轻量级询问接口
"""
from fastapi import APIRouter
from utils.data_change_tracker import get_change_info

router = APIRouter()


@router.get("/server/status")
def get_server_status():
    """
    获取服务器数据变更状态（轻量级询问接口）
    
    客户端通过此接口判断数据是否有变化，
    避免每次都传输完整数据。
    
    Returns:
        包含最后变更时间戳的极小响应（几字节）
    """
    return get_change_info()
