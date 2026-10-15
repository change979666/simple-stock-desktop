"""
服务端状态API路由
用于客户端查询数据是否发生变化
"""
from fastapi import APIRouter
from utils.server_state import server_state

router = APIRouter(prefix="/server", tags=["server"])


@router.get("/status")
def get_server_status():
    """
    获取服务端数据状态
    
    Returns:
        {
            "last_change": 1701320000.123,  # 最后数据变更的时间戳
            "timestamp": 1701320100.456      # 当前服务器时间
        }
    """
    from datetime import datetime
    return {
        "last_change": server_state.get_last_change_timestamp(),
        "timestamp": datetime.now().timestamp()
    }
