@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动数据管理工具...
python -m gui.backup_view
pause
