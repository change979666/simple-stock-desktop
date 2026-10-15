# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_client.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('erp_settings.json', '.'),  # 配置文件放在根目录
    ],
    hiddenimports=[
        # PyQt6 核心模块
        'PyQt6.QtCore', 
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        
        # PyQtGraph 数据可视化 (v4.0.0+)
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.Qt',
        
        # 数据库相关
        'sqlalchemy',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.orm',
        'sqlalchemy.sql',
        
        # 数据处理
        'pandas',
        'openpyxl',
        'datetime',
        'json',
        
        # 客户端模块 (v2.1.0)
        'client',
        'client.api_client',
        'client.server_config_dialog',
        'client.product_view_client',
        
        # 工具模块 (v2.1.0 性能优化)
        'utils',
        'utils.async_loader',        # ⭐ 异步加载框架
        'utils.data_access',          # ⭐ 统一数据访问层
        'utils.cache',                # ⭐ 缓存管理
        'utils.operator',             # 操作员管理
        'utils.app_mode',             # ⭐ 应用模式管理
        'utils.logging_config',       # ⭐ 日志配置
        'utils.auto_backup',          # 自动备份
        'utils.config_loader',        # 配置加载器
        'utils.exception_handlers',   # 异常处理
        'utils.export',               # 导出功能
        'utils.file_encoding',        # 文件编码
        'utils.import_helper',        # 导入助手
        'utils.port_manager',         # 端口管理
        'utils.resource_path',        # 资源路径
        'utils.sku_processor',        # SKU处理器
        
        # 配置模块
        'config',
        'config.settings',            # ⭐ 设置管理
        'config.unified_config',      # ⭐ 统一配置
        'config.product_options',     # 产品选项
        'config.product_view',        # 产品视图配置
        'config.column_width_manager', # 列宽管理
        
        # CRUD模块 (数据库操作)
        'crud',
        'crud.analytics',             # ⭐ v4.0.0 数据分析查询
        'crud.inventory',
        'crud.operations',
        'crud.sales',
        'crud.settings',
        'crud.shipment_operations',
        'crud.sku_utils',
        'crud.inventory_logs',
        'crud.inventory_analytics',
        
        # API路由模块
        'api',
        'api.routes',
        'api.routes.analytics',       # ⭐ v4.0.0 数据分析API
        'api.routes.dashboard',
        'api.routes.inventory',
        'api.routes.products',
        'api.routes.sales',
        'api.routes.shipment',
        'api.errors',
        'api.errors.handlers',
        
        # GUI模块
        'gui',
        'gui.main_window',
        'gui.dashboard_view',
        'gui.product_view',           # ⭐ 集成异步加载
        'gui.inventory_view',         # ⭐ 集成异步加载+批量API
        'gui.sales_view',             # ⭐ 集成异步加载
        'gui.analytics_view',         # ⭐ v4.0.0 数据分析视图 (PyQtGraph)
        'gui.shipment_view',
        'gui.inventory_log_view',
        'gui.settings_view',
        'gui.database_backup_view',
        'gui.option_settings_dialog',
        'gui.system_settings_dialog',
        'gui.progress_dialog',        # ⭐ v2.1.1 进度对话框
        'gui.sku_sales_stats_view',   # ⭐ v2.1.2 SKU销量统计
        'gui.natural_sort_tree_item', # ⭐ v2.1.2 智能排序
        'gui.styles',
        'gui.utils',
        'gui.models',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # 关键：不将依赖库打包进EXE
    name='库存管理系统_v5.2.0',  # 轻量级询问机制优化：服务端减负+窗口失焦暂停
    debug=False,  # 生产版本关闭调试
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 关闭UPX压缩以提升启动速度
    console=False,  # 生产版本不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='库存管理系统_v5.2.0',  # 输出文件夹名称
)
