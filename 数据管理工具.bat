@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动数据库备份管理工具...
python backup_manager.py
pause
