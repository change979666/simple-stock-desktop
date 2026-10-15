$ErrorActionPreference = 'Stop'

try {
    if (Test-Path 'erp_settings.json') {
        # 读取现有配置
        $settings = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
        
        Write-Host "修改前的配置节:" -ForegroundColor Yellow
        $settings.PSObject.Properties.Name | ForEach-Object { Write-Host "  - $_" }
        
        # 更新或添加 server 配置
        if (-not $settings.PSObject.Properties['server']) {
            Write-Host "`n添加 server 配置节" -ForegroundColor Green
            $settings | Add-Member -MemberType NoteProperty -Name 'server' -Value @{
                host_ip = '192.168.1.4'
                port = 8001
                auto_connect = $true
                timeout = 30
            } -Force
        } else {
            Write-Host "`n更新 server 配置节" -ForegroundColor Green
            $settings.server.host_ip = '192.168.1.4'
            $settings.server.port = 8001
        }
        
        # 保存配置
        $json = $settings | ConvertTo-Json -Depth 10 -Compress:$false
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText((Resolve-Path 'erp_settings.json').Path, $json, $utf8NoBom)
        
        # 验证保存结果
        $verify = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
        
        Write-Host "`n修改后的配置节:" -ForegroundColor Yellow
        $verify.PSObject.Properties.Name | ForEach-Object { Write-Host "  - $_" }
        
        Write-Host "`n配置检查:" -ForegroundColor Cyan
        Write-Host "  ✓ server: $($verify.PSObject.Properties['server'] -ne $null)"
        Write-Host "  ✓ user_info: $($verify.PSObject.Properties['user_info'] -ne $null)"
        Write-Host "  ✓ inventory: $($verify.PSObject.Properties['inventory'] -ne $null)"
        Write-Host "  ✓ database: $($verify.PSObject.Properties['database'] -ne $null)"
        
        Write-Host "`n✅ 配置更新成功！" -ForegroundColor Green
    } else {
        Write-Error '配置文件不存在'
    }
} catch {
    Write-Error "Error: $($_.Exception.Message)"
    exit 1
}
