"""
产品管理视图 - 纯客户端版本
通过API客户端访问数据，不直接操作数据库
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog,
    QHeaderView, QLabel, QLineEdit, QDialog, QFormLayout,
    QFrame, QTextEdit, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

from client.api_client import api_client, APIConnectionError, ValidationError


class ProductViewClient(QWidget):
    """产品管理视图 - 客户端版本"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.products = []  # 缓存产品数据
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 顶部工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)
        
        # 产品树形视图
        self.product_tree = QTreeWidget()
        self.product_tree.setHeaderLabels([
            'ID', '父SKU', '产品名称', 'SKU', '规格', 
            '成本价', '库存', '预警阈值', '状态'
        ])
        self.product_tree.setAlternatingRowColors(True)
        self.product_tree.setColumnWidth(0, 50)
        self.product_tree.setColumnWidth(1, 100)
        self.product_tree.setColumnWidth(2, 200)
        self.product_tree.setColumnWidth(3, 120)
        self.product_tree.setColumnWidth(4, 100)
        
        # 右键菜单
        self.product_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.product_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.product_tree)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
    
    def _create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_products)
        toolbar.addWidget(refresh_btn)
        
        # 新增产品按钮
        add_btn = QPushButton("➕ 新增产品")
        add_btn.clicked.connect(self.add_product)
        toolbar.addWidget(add_btn)
        
        # 导入按钮
        import_btn = QPushButton("📥 批量导入")
        import_btn.clicked.connect(self.import_products)
        toolbar.addWidget(import_btn)
        
        # 导出按钮
        export_btn = QPushButton("📤 导出")
        export_btn.clicked.connect(self.export_products)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索产品名称或SKU...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.filter_products)
        toolbar.addWidget(self.search_input)
        
        return toolbar
    
    def load_products(self):
        """从服务器加载产品列表"""
        try:
            self.status_label.setText("正在加载产品数据...")
            
            # 调用API获取产品列表
            products = api_client.get_products()
            self.products = products
            
            # 更新界面
            self.update_product_tree(products)
            
            self.status_label.setText(f"✅ 加载完成，共 {len(products)} 个产品")
            
        except APIConnectionError as e:
            QMessageBox.critical(
                self,
                "连接错误",
                f"无法连接到服务器:\n\n{str(e)}\n\n"
                f"请检查:\n"
                f"1. 服务器是否正在运行\n"
                f"2. 网络连接是否正常\n"
                f"3. 在设置中检查服务器配置"
            )
            self.status_label.setText("❌ 加载失败 - 连接错误")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "加载错误",
                f"加载产品数据失败:\n\n{str(e)}"
            )
            self.status_label.setText("❌ 加载失败")
    
    def update_product_tree(self, products: List[Dict]):
        """更新产品树形视图"""
        self.product_tree.clear()
        
        # 按父产品分组
        parent_groups = {}
        for product in products:
            parent_sku = product.get('parent_sku', '')
            if parent_sku not in parent_groups:
                parent_groups[parent_sku] = []
            parent_groups[parent_sku].append(product)
        
        # 添加到树形视图
        for parent_sku, variants in sorted(parent_groups.items()):
            # 创建父节点
            parent_item = QTreeWidgetItem(self.product_tree)
            parent_item.setText(1, parent_sku)
            parent_item.setText(2, variants[0].get('product_name', ''))
            parent_item.setFont(1, QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
            parent_item.setBackground(1, QColor('#e3f2fd'))
            
            # 添加子SKU
            for variant in variants:
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, str(variant.get('id', '')))
                child_item.setText(1, parent_sku)
                child_item.setText(2, variant.get('product_name', ''))
                child_item.setText(3, variant.get('sku', ''))
                child_item.setText(4, variant.get('option', ''))
                child_item.setText(5, f"¥{variant.get('cost_price', 0):.2f}")
                child_item.setText(6, str(variant.get('quantity', 0)))
                child_item.setText(7, str(variant.get('warning_threshold', 0)))
                
                # 库存预警
                quantity = variant.get('quantity', 0)
                threshold = variant.get('warning_threshold', 0)
                if quantity < threshold:
                    child_item.setForeground(6, QColor('#f44336'))
                    child_item.setText(8, '⚠️ 预警')
                else:
                    child_item.setText(8, '✅ 正常')
            
            parent_item.setExpanded(True)
    
    def filter_products(self):
        """过滤产品"""
        keyword = self.search_input.text().lower()
        
        if not keyword:
            self.update_product_tree(self.products)
            return
        
        filtered = [
            p for p in self.products
            if keyword in p.get('product_name', '').lower()
            or keyword in p.get('sku', '').lower()
            or keyword in p.get('parent_sku', '').lower()
        ]
        
        self.update_product_tree(filtered)
        self.status_label.setText(f"🔍 找到 {len(filtered)} 个匹配产品")
    
    def add_product(self):
        """新增产品"""
        dialog = AddProductDialog(self)
        if dialog.exec():
            product_data = dialog.get_product_data()
            
            try:
                # 调用API创建产品
                result = api_client.create_product(product_data)
                
                QMessageBox.information(
                    self,
                    "成功",
                    f"产品创建成功!\n\nSKU: {result.get('sku', '')}"
                )
                
                # 刷新列表
                self.load_products()
                
            except ValidationError as e:
                QMessageBox.warning(
                    self,
                    "验证错误",
                    f"产品数据验证失败:\n\n{str(e)}"
                )
            except APIConnectionError as e:
                QMessageBox.critical(
                    self,
                    "连接错误",
                    f"无法连接到服务器:\n\n{str(e)}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"创建产品失败:\n\n{str(e)}"
                )
    
    def import_products(self):
        """批量导入产品"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择产品导入文件",
            "",
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # 读取文件
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            else:
                df = pd.read_excel(file_path)
            
            # 列名映射（支持中英文）
            column_mapping = {
                'product_name': ['产品名称', 'Product Name', 'product_name'],
                'sku': ['SKU', 'sku'],
                'option': ['规格', 'Option', 'option'],
                'cost_price': ['成本价', 'Cost Price', 'cost_price'],
                'warning_threshold': ['预警阈值', 'Warning Threshold', 'warning_threshold']
            }
            
            # 标准化列名
            products = []
            for _, row in df.iterrows():
                product = {}
                for std_name, possible_names in column_mapping.items():
                    for name in possible_names:
                        if name in row.index and pd.notna(row[name]):
                            product[std_name] = row[name]
                            break
                
                if product:  # 至少有一个字段
                    products.append(product)
            
            if not products:
                QMessageBox.warning(
                    self,
                    "导入失败",
                    "文件中没有找到有效的产品数据"
                )
                return
            
            # 调用API批量导入
            self.status_label.setText(f"正在导入 {len(products)} 个产品...")
            
            result = api_client.import_products(products)
            
            success = result.get('success', 0)
            failed = result.get('failed', 0)
            message = result.get('message', '')
            
            QMessageBox.information(
                self,
                "导入完成",
                f"批量导入完成!\n\n"
                f"成功: {success} 个\n"
                f"失败: {failed} 个\n\n"
                f"{message}"
            )
            
            # 刷新列表
            self.load_products()
            
        except APIConnectionError as e:
            QMessageBox.critical(
                self,
                "连接错误",
                f"无法连接到服务器:\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "导入错误",
                f"导入产品失败:\n\n{str(e)}"
            )
    
    def export_products(self):
        """导出产品列表"""
        if not self.products:
            QMessageBox.warning(self, "提示", "没有可导出的产品数据")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存产品列表",
            f"产品列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            # 转换为DataFrame
            df = pd.DataFrame(self.products)
            
            # 选择需要导出的列
            columns = ['id', 'parent_sku', 'product_name', 'sku', 'option',
                      'cost_price', 'quantity', 'warning_threshold']
            df = df[columns]
            
            # 重命名列
            df.columns = ['ID', '父SKU', '产品名称', 'SKU', '规格',
                         '成本价', '库存', '预警阈值']
            
            # 导出
            df.to_excel(file_path, index=False)
            
            QMessageBox.information(
                self,
                "导出成功",
                f"已导出 {len(df)} 个产品到:\n\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "导出错误",
                f"导出产品列表失败:\n\n{str(e)}"
            )
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        # 这里可以添加编辑、删除等功能
        pass


class AddProductDialog(QDialog):
    """新增产品对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("新增产品")
        self.setMinimumWidth(450)
        
        layout = QFormLayout(self)
        
        # 产品名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: T恤")
        layout.addRow("产品名称*:", self.name_input)
        
        # 父SKU
        self.parent_sku_input = QLineEdit()
        self.parent_sku_input.setPlaceholderText("例如: TS-001")
        layout.addRow("父SKU*:", self.parent_sku_input)
        
        # SKU
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("例如: TS-001-S")
        layout.addRow("SKU*:", self.sku_input)
        
        # 规格
        self.option_input = QLineEdit()
        self.option_input.setPlaceholderText("例如: S码")
        layout.addRow("规格:", self.option_input)
        
        # 成本价
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText("例如: 59.90")
        layout.addRow("成本价:", self.cost_input)
        
        # 预警阈值
        self.threshold_input = QSpinBox()
        self.threshold_input.setMinimum(0)
        self.threshold_input.setMaximum(999999)
        self.threshold_input.setValue(10)
        layout.addRow("预警阈值:", self.threshold_input)
        
        # 描述
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("产品描述（可选）")
        layout.addRow("描述:", self.description_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self.validate_and_accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
    
    def validate_and_accept(self):
        """验证并接受"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入产品名称")
            return
        
        if not self.parent_sku_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入父SKU")
            return
        
        if not self.sku_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入SKU")
            return
        
        self.accept()
    
    def get_product_data(self) -> Dict:
        """获取产品数据"""
        data = {
            'product_name': self.name_input.text().strip(),
            'parent_sku': self.parent_sku_input.text().strip(),
            'sku': self.sku_input.text().strip(),
            'option': self.option_input.text().strip(),
            'warning_threshold': self.threshold_input.value()
        }
        
        # 可选字段
        if self.cost_input.text().strip():
            try:
                data['cost_price'] = float(self.cost_input.text().strip())
            except ValueError:
                pass
        
        if self.description_input.toPlainText().strip():
            data['description'] = self.description_input.toPlainText().strip()
        
        return data
