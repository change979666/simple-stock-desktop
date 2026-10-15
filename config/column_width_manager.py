"""
列宽配置管理模块
负责保存和加载各个视图的列宽配置
使用统一的 erp_settings.json 配置文件
"""
import json
import os
import sys
from typing import List, Optional


class ColumnWidthManager:
    """列宽配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为根目录的 erp_settings.json
        """
        if config_path is None:
            # 使用主配置文件 erp_settings.json
            # 兼容 PyInstaller 打包后的路径
            if getattr(sys, 'frozen', False):
                # 打包后的程序，使用可执行文件所在目录（可写目录）
                # sys.executable 指向 .exe 文件
                base_dir = os.path.dirname(sys.executable)
                print(f"[打包模式] 可执行文件: {sys.executable}")
                print(f"[打包模式] 配置目录: {base_dir}")
            else:
                # 开发环境，使用项目根目录
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                print(f"[开发模式] 配置目录: {base_dir}")
            
            config_path = os.path.join(base_dir, 'erp_settings.json')
        
        self.config_path = config_path
        print(f"✅ 配置文件路径: {self.config_path}")
        print(f"   文件存在: {os.path.exists(self.config_path)}")
        print(f"   目录可写: {os.access(os.path.dirname(self.config_path), os.W_OK)}")
        self.full_config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                print(f"📂 加载配置文件: {self.config_path}")
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✅ 配置加载成功，共 {len(config)} 个配置项")
                    return config
            else:
                print(f"⚠️ 配置文件不存在: {self.config_path}")
                
                # 打包模式下，尝试从 _internal 目录复制模板
                if getattr(sys, 'frozen', False):
                    print("🔍 尝试从打包资源复制配置模板...")
                    template_path = self._find_template_config()
                    if template_path and os.path.exists(template_path):
                        print(f"📋 找到模板配置: {template_path}")
                        try:
                            import shutil
                            shutil.copy2(template_path, self.config_path)
                            print(f"✅ 已复制配置模板到: {self.config_path}")
                            with open(self.config_path, 'r', encoding='utf-8') as f:
                                return json.load(f)
                        except Exception as e:
                            print(f"❌ 复制配置模板失败: {e}")
                
                # 返回默认配置并保存
                print("📝 创建默认配置文件...")
                default_config = self._get_default_full_config()
                self._save_config_directly(default_config)
                return default_config
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_full_config()
    
    def _find_template_config(self) -> str:
        """查找打包资源中的配置模板"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后，资源在 _MEIPASS 或 sys._MEIPASS
            if hasattr(sys, '_MEIPASS'):
                # 临时解压目录（单文件模式）
                template = os.path.join(sys._MEIPASS, 'erp_settings.json')
                if os.path.exists(template):
                    return template
            
            # 单目录模式：_internal 目录
            exe_dir = os.path.dirname(sys.executable)
            template = os.path.join(exe_dir, '_internal', 'erp_settings.json')
            if os.path.exists(template):
                return template
        
        return None
    
    def _save_config_directly(self, config: dict) -> bool:
        """直接保存配置（内部使用）"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # 保存配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print(f"✅ 配置已保存到: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def _get_default_full_config(self) -> dict:
        """获取默认完整配置"""
        return {
            "server_address": "192.168.1.3:8001",
            "operator_name": "操作员",
            "auto_connect": True,
            "remember_window_size": True,
            "default_warning_level": 128,
            "warning_enabled": True,
            "notification_enabled": True,
            "database": {
                "filename": "database.db"
            },
            "column_widths": self._get_default_column_widths(),
            "table_style": {
                "show_grid": True,
                "alternate_colors": True,
                "row_height": 30
            }
        }
    
    def _get_default_column_widths(self) -> dict:
        """获取默认列宽配置"""
        return {
            "sales_view": {
                "columns": [180, 150, 80, 70, 60, 100, 160]
            },
            "inventory_view": {
                "columns": [200, 80, 90, 100, 100, 100, 100, 100]
            },
            "shipment_view": {
                "columns": [220, 90, 140, 110, 130, 180]
            },
            "inventory_log_view": {
                "columns": [150, 120, 100, 100, 120, 120, 200]
            },
            "product_view": {
                "columns": [200, 180, 160, 120]
            },
            "dashboard_view": {
                "columns": [100, 120, 120, 100, 100, 80, 80, 80, 80]
            },
            "sku_sales_stats_view": {
                "columns": [180, 100, 100, 100, 100, 100]
            }
        }
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            print(f"💾 保存配置到: {self.config_path}")
            
            # 确保目录存在
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                print(f"📁 创建配置目录: {config_dir}")
            
            # 检查目录是否可写
            if not os.access(config_dir if config_dir else '.', os.W_OK):
                print(f"❌ 配置目录不可写: {config_dir}")
                return False
            
            # 保存整个配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.full_config, f, indent=4, ensure_ascii=False)
            
            print("✅ 配置保存成功")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_column_widths(self, view_name: str) -> Optional[List[int]]:
        """
        获取指定视图的列宽配置
        
        Args:
            view_name: 视图名称 (sales_view, inventory_view等)
        
        Returns:
            列宽列表，如果不存在则返回None
        """
        # 确保 column_widths 字段存在
        if 'column_widths' not in self.full_config:
            self.full_config['column_widths'] = \
                self._get_default_column_widths()
        
        column_widths = self.full_config.get('column_widths', {})
        if view_name in column_widths:
            return column_widths[view_name].get('columns')
        return None
    
    def save_column_widths(self, view_name: str, widths: List[int]) -> bool:
        """
        保存指定视图的列宽配置
        
        Args:
            view_name: 视图名称
            widths: 列宽列表
        
        Returns:
            是否保存成功
        """
        try:
            # 确保 column_widths 字段存在
            if 'column_widths' not in self.full_config:
                self.full_config['column_widths'] = {}
            
            # 更新列宽配置
            if view_name not in self.full_config['column_widths']:
                self.full_config['column_widths'][view_name] = {}
            
            self.full_config['column_widths'][view_name]['columns'] = widths
            
            # 保存到文件
            return self._save_config()
        except Exception as e:
            print(f"保存列宽配置失败: {e}")
            return False
    
    def reset_to_default(self, view_name: str) -> bool:
        """
        重置指定视图的列宽为默认值
        
        Args:
            view_name: 视图名称
        
        Returns:
            是否重置成功
        """
        default_widths = self._get_default_column_widths()
        if view_name in default_widths:
            if 'column_widths' not in self.full_config:
                self.full_config['column_widths'] = {}
            
            self.full_config['column_widths'][view_name] = \
                default_widths[view_name]
            return self._save_config()
        return False


# 全局单例
_column_width_manager = None


def get_column_width_manager() -> ColumnWidthManager:
    """获取列宽配置管理器单例"""
    global _column_width_manager
    if _column_width_manager is None:
        _column_width_manager = ColumnWidthManager()
    return _column_width_manager
