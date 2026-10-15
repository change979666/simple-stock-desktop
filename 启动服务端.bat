@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 API 服务端...
python api_server.py
pause
