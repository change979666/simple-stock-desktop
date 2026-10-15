"""
统一的样式定义模块
"""

MAIN_STYLE = """
QMainWindow {
    background-color: #f8f9fa;
}

QTabWidget::pane {
    border: 1px solid #dee2e6;
    background: white;
    border-radius: 6px;
    margin-top: -1px;
}

QTabWidget::tab-bar {
    alignment: left;
    background: transparent;
}

QTabBar::tab {
    background: #e9ecef;
    color: #495057;
    padding: 12px 20px;
    border: 1px solid #dee2e6;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 80px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #0d6efd;
    border-bottom-color: white;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background: #f1f3f5;
    color: #0d6efd;
}

QStatusBar {
    background: #ffffff;
    color: #6c757d;
    padding: 8px;
    border-top: 1px solid #dee2e6;
}

QTreeWidget, QTableWidget {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background-color: white;
    alternate-background-color: #f8f9fa;
    gridline-color: #e9ecef;
    outline: none;
}

QTreeWidget::item, QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f3f5;
}

QTreeWidget::item:selected, QTableWidget::item:selected {
    background-color: #e7f3ff;
    color: #0d6efd;
}

QTreeWidget::item:hover, QTableWidget::item:hover {
    background-color: #f8f9fa;
}

QHeaderView::section {
    background-color: #f8f9fa;
    color: #495057;
    font-weight: bold;
    padding: 10px;
    border: none;
    border-right: 1px solid #dee2e6;
    border-bottom: 2px solid #dee2e6;
}

QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
    border: none;
    min-width: 80px;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);
}

QPushButton:pressed {
    background-color: #dee2e6;
}

QPushButton[primary="true"] {
    background-color: #0d6efd;
    color: white;
}

QPushButton[primary="true"]:hover {
    background-color: #0b5ed7;
}

QPushButton[danger="true"] {
    background-color: #dc3545;
    color: white;
}

QPushButton[danger="true"]:hover {
    background-color: #bb2d3b;
}

QPushButton[success="true"] {
    background-color: #198754;
    color: white;
}

QPushButton[success="true"]:hover {
    background-color: #157347;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    padding: 8px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    background: white;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #86b7fe;
    outline: 0;
}

QLabel {
    color: #212529;
}

QFrame[dashboard="true"] {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 16px;
}

QFrame[warning="true"] {
    background: #fff3cd;
    border: 1px solid #ffecb5;
    color: #664d03;
}

/* 产品管理特定样式 */
QTreeWidget[productTree="true"] QTreeWidget::item:has-children {
    background: #f8f9fa;
    font-weight: bold;
    border-bottom: 2px solid #dee2e6;
    color: #212529;
}

QTreeWidget[productTree="true"] QTreeWidget::item:has-children:selected {
    background: #e7f3ff;
    color: #0d6efd;
}

QTreeWidget[productTree="true"] QTreeWidget::item:!has-children {
    background: white;
    margin-left: 20px;
}
"""

DASHBOARD_STYLE = """
QLabel[dashboardTitle="true"] {
    font-size: 18px;
    font-weight: bold;
    color: #212529;
    margin-bottom: 16px;
}

QLabel[statsLabel="true"] {
    font-size: 24px;
    color: #0d6efd;
    margin: 8px 0;
}

QFrame[warningPanel="true"] {
    background: #fff3cd;
    border: 1px solid #ffecb5;
    border-radius: 8px;
    padding: 16px;
}

QLabel[warningTitle="true"] {
    color: #664d03;
    font-weight: bold;
}
"""

INVENTORY_STYLE = """
QTableWidget[inventoryTable="true"] {
    background-color: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
}

QTableWidget[inventoryTable="true"]::item[warning="true"] {
    color: #dc3545;
    font-weight: bold;
}

QTableWidget[inventoryTable="true"]::item[alert="true"] {
    color: #fd7e14;
    font-weight: bold;
}

QTableWidget[inventoryTable="true"]::item[normal="true"] {
    color: #198754;
}
"""

DIALOG_STYLE = """
QDialog {
    background-color: white;
}

QDialog QLabel[title="true"] {
    font-size: 16px;
    font-weight: bold;
    color: #212529;
    padding: 16px 0;
}

QDialog QFrame {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

QDialog QPushButton {
    min-width: 100px;
}
"""