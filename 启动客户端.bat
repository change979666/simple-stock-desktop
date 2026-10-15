@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动客户端程序...
python main_client.py
pause
