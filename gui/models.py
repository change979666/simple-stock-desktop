"""
此模块包含GUI相关的数据模型和共享状态
"""

class SharedState:
    """共享状态类，用于跨组件共享数据"""
    def __init__(self):
        self.main_window = None

# 创建一个全局的共享状态实例
shared_state = SharedState()