"""
数据导入辅助工具
用于统一处理Excel/CSV文件的导入逻辑
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
from PyQt6.QtWidgets import QMessageBox, QWidget


class DataImporter:
    """数据导入工具类"""
    
    @staticmethod
    def read_file(
        file_path: str,
        column_mapping: Optional[Dict[str, str]] = None,
        dtype: Optional[Dict] = None
    ) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        统一的文件读取和列名映射
        
        Args:
            file_path: 文件路径
            column_mapping: 列名映射字典，可选
            dtype: 数据类型映射，可选
            
        Returns:
            Tuple[bool, Optional[pd.DataFrame], str]:
                (成功标志, DataFrame对象或None, 错误消息)
        """
        try:
            # 根据文件扩展名选择读取方式
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(
                    file_path,
                    dtype=dtype or str,
                    encoding='utf-8-sig'
                )
            elif file_path.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(
                    file_path,
                    dtype=dtype or str
                )
            else:
                return False, None, f"不支持的文件格式: {file_path}"
            
            # 检查文件是否为空
            if df.empty:
                return False, None, "文件为空或无法读取有效数据"
            
            # 应用列名映射
            if column_mapping:
                # 处理多行标题格式
                cleaned_columns = {}
                for col in df.columns:
                    col_str = str(col).strip()
                    # 提取第一行作为主要标识
                    if '\n' in col_str:
                        col_str = col_str.split('\n')[0].strip()
                    cleaned_columns[col] = col_str
                
                # 应用映射
                df.rename(columns=cleaned_columns, inplace=True)
                df.rename(columns=column_mapping, inplace=True)
            
            return True, df, ""
            
        except UnicodeDecodeError:
            return False, None, (
                "文件编码格式不正确\n\n"
                "请使用UTF-8编码的CSV文件，或使用Excel格式"
            )
        except PermissionError:
            return False, None, (
                "无法访问文件\n\n"
                "文件可能正在被其他程序使用，请关闭后重试"
            )
        except pd.errors.EmptyDataError:
            return False, None, "文件为空"
        except pd.errors.ParserError as e:
            return False, None, (
                f"文件格式解析错误\n\n"
                f"请检查文件格式是否正确\n"
                f"详细错误: {str(e)}"
            )
        except Exception as e:
            return False, None, (
                f"读取文件时发生未知错误\n\n"
                f"错误信息: {str(e)}\n\n"
                f"请检查文件格式是否正确"
            )
    
    @staticmethod
    def validate_required_fields(
        row: Dict,
        required_fields: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        验证必需字段
        
        Args:
            row: 数据行字典
            required_fields: 必需字段列表
            
        Returns:
            Tuple[bool, List[str]]: (验证通过标志, 缺失字段列表)
        """
        missing_fields = []
        for field in required_fields:
            value = row.get(field)
            # 检查字段是否存在且不为空
            if value is None or str(value).strip() in ['', 'nan', 'None']:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def filter_example_rows(
        df: pd.DataFrame,
        check_columns: List[str]
    ) -> pd.DataFrame:
        """
        过滤示例行（包含*的行）
        
        Args:
            df: DataFrame对象
            check_columns: 需要检查的列名列表
            
        Returns:
            pd.DataFrame: 过滤后的DataFrame
        """
        mask = pd.Series([True] * len(df))
        
        for col in check_columns:
            if col in df.columns:
                # 过滤包含*的行
                mask &= ~df[col].astype(str).str.contains(
                    r'\*',
                    na=False,
                    regex=True
                )
        
        return df[mask]
    
    @staticmethod
    def show_import_result(
        parent: QWidget,
        success_count: int,
        errors: List[str],
        title: str = "导入结果"
    ):
        """
        显示导入结果对话框
        
        Args:
            parent: 父窗口
            success_count: 成功导入数量
            errors: 错误信息列表
            title: 对话框标题
        """
        if success_count > 0 and not errors:
            QMessageBox.information(
                parent,
                title,
                f"成功导入 {success_count} 条记录！"
            )
        elif success_count > 0 and errors:
            error_summary = "\n".join(errors[:10])  # 只显示前10个错误
            if len(errors) > 10:
                error_summary += f"\n... 还有 {len(errors) - 10} 个错误"
            
            QMessageBox.warning(
                parent,
                title,
                f"导入完成，但有部分错误：\n\n"
                f"成功: {success_count} 条\n"
                f"失败: {len(errors)} 条\n\n"
                f"错误详情:\n{error_summary}"
            )
        else:
            error_summary = "\n".join(errors[:10])
            if len(errors) > 10:
                error_summary += f"\n... 还有 {len(errors) - 10} 个错误"
            
            QMessageBox.critical(
                parent,
                title,
                f"导入失败！\n\n"
                f"错误详情:\n{error_summary}"
            )
    
    @staticmethod
    def show_error_dialog(
        parent: QWidget,
        title: str,
        message: str
    ):
        """
        显示错误对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            message: 错误消息
        """
        QMessageBox.critical(parent, title, message)
