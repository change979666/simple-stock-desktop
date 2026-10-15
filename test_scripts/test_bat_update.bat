@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo 测试批处理中的配置更新
echo ========================================
echo.

set server=192.168.1.3

echo [1] 更新前的配置:
python -c "import json; d=json.load(open('erp_settings.json','r',encoding='utf-8')); print(f'配置节数: {len(d)}'); [print(f'  - {k}') for k in d.keys()]"

echo.
echo [2] 执行更新命令...
powershell -Command "$ErrorActionPreference='Stop'; try { if (Test-Path 'erp_settings.json') { $settings = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json; if (-not $settings.PSObject.Properties['server']) { $settings | Add-Member -MemberType NoteProperty -Name 'server' -Value @{host_ip='!server!';port=8001;auto_connect=$true;timeout=30} -Force } else { $settings.server.host_ip = '!server!'; $settings.server.port = 8001 }; $json = $settings | ConvertTo-Json -Depth 10 -Compress:$false; [System.IO.File]::WriteAllText((Resolve-Path 'erp_settings.json').Path, $json, (New-Object System.Text.UTF8Encoding $false)) } else { Write-Error '配置文件不存在' } } catch { Write-Error $_.Exception.Message; exit 1 }"

if errorlevel 1 (
    echo [错误] 更新失败
    pause
    exit /b 1
)

echo.
echo [3] 更新后的配置:
python -c "import json; d=json.load(open('erp_settings.json','r',encoding='utf-8')); print(f'配置节数: {len(d)}'); [print(f'  - {k}') for k in d.keys()]"

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
