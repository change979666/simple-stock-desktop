"""
统一错误处理模块
定义错误码、异常类和全局异常处理器
"""
from enum import Enum
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 通用错误 1xxx
    UNKNOWN_ERROR = "1000"
    VALIDATION_ERROR = "1001"
    DATABASE_ERROR = "1002"
    NOT_FOUND = "1003"
    ALREADY_EXISTS = "1004"
    
    # 产品相关错误 2xxx
    PRODUCT_NOT_FOUND = "2001"
    PRODUCT_SKU_EXISTS = "2002"
    VARIANT_NOT_FOUND = "2003"
    VARIANT_SKU_EXISTS = "2004"
    
    # 库存相关错误 3xxx
    INSUFFICIENT_STOCK = "3001"
    INVALID_QUANTITY = "3002"
    STOCK_LOG_ERROR = "3003"
    
    # 销售相关错误 4xxx
    ORDER_NOT_FOUND = "4001"
    ORDER_NUMBER_EXISTS = "4002"
    INVALID_ORDER_DATA = "4003"
    
    # 发货相关错误 5xxx
    SHIPMENT_NOT_FOUND = "5001"
    INVALID_SHIPMENT_STATUS = "5002"


class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class ProductException(AppException):
    """产品相关异常"""
    pass


class InventoryException(AppException):
    """库存相关异常"""
    pass


class SalesException(AppException):
    """销售相关异常"""
    pass


class ShipmentException(AppException):
    """发货相关异常"""
    pass


# 错误消息映射
ERROR_MESSAGES = {
    ErrorCode.UNKNOWN_ERROR: "未知错误",
    ErrorCode.VALIDATION_ERROR: "数据验证失败",
    ErrorCode.DATABASE_ERROR: "数据库操作失败",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.ALREADY_EXISTS: "资源已存在",
    
    ErrorCode.PRODUCT_NOT_FOUND: "产品不存在",
    ErrorCode.PRODUCT_SKU_EXISTS: "产品SKU已存在",
    ErrorCode.VARIANT_NOT_FOUND: "产品变体不存在",
    ErrorCode.VARIANT_SKU_EXISTS: "变体SKU已存在",
    
    ErrorCode.INSUFFICIENT_STOCK: "库存不足",
    ErrorCode.INVALID_QUANTITY: "数量无效",
    ErrorCode.STOCK_LOG_ERROR: "库存日志错误",
    
    ErrorCode.ORDER_NOT_FOUND: "订单不存在",
    ErrorCode.ORDER_NUMBER_EXISTS: "订单号已存在",
    ErrorCode.INVALID_ORDER_DATA: "订单数据无效",
    
    ErrorCode.SHIPMENT_NOT_FOUND: "发货记录不存在",
    ErrorCode.INVALID_SHIPMENT_STATUS: "发货状态无效",
}


def get_error_message(error_code: ErrorCode) -> str:
    """获取错误消息
    
    Args:
        error_code: 错误码
        
    Returns:
        错误消息
    """
    return ERROR_MESSAGES.get(error_code, "未知错误")


async def app_exception_handler(request: Request, exc: AppException):
    """应用异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON 响应
    """
    logger.error(
        f"应用异常: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "detail": exc.detail
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """数据验证异常处理器
    
    Args:
        request: 请求对象
        exc: 验证异常对象
        
    Returns:
        JSON 响应
    """
    logger.warning(
        f"数据验证失败: {request.url.path}",
        extra={"errors": exc.errors()}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": ErrorCode.VALIDATION_ERROR,
            "message": "请求数据验证失败",
            "detail": exc.errors()
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理器
    
    Args:
        request: 请求对象
        exc: 数据库异常对象
        
    Returns:
        JSON 响应
    """
    logger.error(
        f"数据库错误: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.DATABASE_ERROR,
            "message": "数据库操作失败",
            "detail": str(exc) if logger.level == logging.DEBUG else None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON 响应
    """
    logger.error(
        f"未处理的异常: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.UNKNOWN_ERROR,
            "message": "服务器内部错误",
            "detail": str(exc) if logger.level == logging.DEBUG else None
        }
    )


def register_exception_handlers(app):
    """注册异常处理器到 FastAPI 应用
    
    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("已注册全局异常处理器")
