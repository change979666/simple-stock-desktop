# SKU销量列宽保存问题修复

## 问题描述

用户反馈：SKU销量统计界面的列宽调整后，每次重启程序（特别是打包后的程序）都会恢复到默认值，无法保持用户的自定义列宽。

## 根本原因

### 1. 打包后的配置文件路径问题

**打包前（开发环境）：**
- 配置文件 `erp_settings.json` 位于项目根目录
- 程序可以直接读写配置文件 ✅

**打包后（单目录模式）：**
- `erp_settings.json` 被打包到 `_internal/erp_settings.json`（只读）❌
- 程序尝试写入只读目录失败
- 列宽修改无法保存

### 2. 配置文件位置策略

```
打包前目录结构:
simple-stock-desktop/
├── erp_settings.json        ← 可读写
├── main_client.py
└── config/
    └── column_width_manager.py

打包后目录结构（旧版本问题）:
库存管理系统_v5.0.0/
├── 库存管理系统_v5.0.0.exe
└── _internal/
    ├── erp_settings.json    ← 只读，无法保存修改 ❌
    └── [其他依赖文件]

打包后目录结构（修复后）:
库存管理系统_v5.0.0/
├── 库存管理系统_v5.0.0.exe
├── erp_settings.json        ← 首次运行时创建，可读写 ✅
└── _internal/
    ├── erp_settings.json    ← 配置模板（只读）
    └── [其他依赖文件]
```

## 解决方案

### 修改文件
`config/column_width_manager.py`

### 核心修改

#### 1. 增强的配置文件加载逻辑

```python
def _load_config(self) -> dict:
    """加载配置文件"""
    if os.path.exists(self.config_path):
        # 配置文件存在，直接加载
        return json.load(...)
    else:
        # 配置文件不存在
        if getattr(sys, 'frozen', False):
            # 打包模式：从 _internal 复制模板
            template_path = self._find_template_config()
            if template_path:
                shutil.copy2(template_path, self.config_path)
                return json.load(...)
        
        # 创建默认配置
        default_config = self._get_default_full_config()
        self._save_config_directly(default_config)
        return default_config
```

#### 2. 智能模板查找

```python
def _find_template_config(self) -> str:
    """查找打包资源中的配置模板"""
    if getattr(sys, 'frozen', False):
        # 检查 _MEIPASS（单文件模式）
        if hasattr(sys, '_MEIPASS'):
            template = os.path.join(sys._MEIPASS, 'erp_settings.json')
            if os.path.exists(template):
                return template
        
        # 检查 _internal（单目录模式）
        exe_dir = os.path.dirname(sys.executable)
        template = os.path.join(exe_dir, '_internal', 'erp_settings.json')
        if os.path.exists(template):
            return template
    
    return None
```

#### 3. 增强的保存逻辑

```python
def _save_config(self):
    """保存配置到文件"""
    # 确保目录存在
    config_dir = os.path.dirname(self.config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    # 检查目录是否可写
    if not os.access(config_dir, os.W_OK):
        print(f"❌ 配置目录不可写: {config_dir}")
        return False
    
    # 保存配置
    with open(self.config_path, 'w', encoding='utf-8') as f:
        json.dump(self.full_config, f, indent=4, ensure_ascii=False)
    
    return True
```

## 工作流程

### 首次运行（打包后）

1. 程序启动，检测到是打包模式（`sys.frozen = True`）
2. 配置路径：`exe目录/erp_settings.json`
3. 发现配置文件不存在
4. 从 `_internal/erp_settings.json` 复制模板到 `exe目录/`
5. 用户调整列宽 → 保存到 `exe目录/erp_settings.json` ✅

### 后续运行

1. 程序启动
2. 直接加载 `exe目录/erp_settings.json`
3. 应用保存的列宽配置 ✅

## 测试验证

### 开发环境测试

```bash
python test_column_width_save.py
```

**输出示例：**
```
======================================================================
               测试列宽配置保存功能
======================================================================
[开发模式] 配置目录: 项目根目录
✅ 配置文件路径: ...\erp_settings.json
   文件存在: True
   目录可写: True

----------------------------------------------------------------------
1. 读取当前 SKU销量统计 列宽配置:
----------------------------------------------------------------------
   当前列宽: [200, 150, 150, 100, 100]

----------------------------------------------------------------------
2. 保存测试列宽 [250, 180, 180, 120, 120]:
----------------------------------------------------------------------
💾 保存配置到: ...\erp_settings.json
✅ 配置保存成功
   ✅ 保存成功

----------------------------------------------------------------------
3. 重新读取验证:
----------------------------------------------------------------------
   读取到的列宽: [250, 180, 180, 120, 120]
   ✅ 验证成功！列宽保存和读取一致
```

### 打包后测试步骤

1. 打包程序：`.\打包_v5.0.0.bat`
2. 首次运行可执行文件
3. 打开 SKU销量统计页面
4. 调整列宽（拖动列标题边缘）
5. 关闭程序
6. 检查 `erp_settings.json` 是否在 exe 旁边 ✅
7. 再次运行程序
8. 验证列宽是否保持调整后的值 ✅

## 调试信息

程序启动时会输出详细的配置加载信息：

```
[打包模式] 可执行文件: D:\App\库存管理系统_v5.0.0.exe
[打包模式] 配置目录: D:\App
✅ 配置文件路径: D:\App\erp_settings.json
   文件存在: True
   目录可写: True
📂 加载配置文件: D:\App\erp_settings.json
✅ 配置加载成功，共 11 个配置项
```

## 兼容性

- ✅ 开发环境：直接读写项目根目录的配置文件
- ✅ 打包后（单目录模式）：exe旁边的可写配置文件
- ✅ 打包后（单文件模式）：临时目录的配置文件
- ✅ 升级兼容：自动迁移旧配置到新位置

## 影响范围

### 修改的文件
- `config/column_width_manager.py`

### 受益的界面
- 📈 SKU销量统计（主要修复目标）
- 📦 产品管理
- 📊 库存管理
- 🚚 发货管理
- 💰 销售管理
- 📋 库存日志
- 📊 数据分析

所有使用 `get_column_width_manager()` 的界面都会受益于此修复。

## 注意事项

1. **首次运行时间**：打包后首次运行会稍慢（需复制配置模板）
2. **权限要求**：确保 exe 所在目录有写入权限
3. **配置迁移**：旧版本的配置会自动迁移到新位置
4. **多用户环境**：每个用户目录需独立配置文件

---

**修复日期**: 2025-11-23  
**版本**: v5.0.0  
**问题严重程度**: 中等（用户体验问题）  
**修复优先级**: 高（影响所有打包后的用户）
