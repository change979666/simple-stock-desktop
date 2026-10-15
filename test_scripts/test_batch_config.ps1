# Test config update logic
# Simulate the update process in bat file

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Config Update Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Show current config
Write-Host "`n[1] Before update:" -ForegroundColor Yellow
$before = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Keys count: $($before.PSObject.Properties.Count)"
$before.PSObject.Properties.Name | ForEach-Object { Write-Host "  - $_" }

# 2. Simulate bat update logic
Write-Host "`n[2] Updating config..." -ForegroundColor Yellow
$server = '192.168.1.4'

$ErrorActionPreference = 'Stop'
try {
    if (Test-Path 'erp_settings.json') {
        $settings = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
        
        Write-Host "After read: $($settings.PSObject.Properties.Count) keys"
        
        if (-not $settings.PSObject.Properties['server']) {
            Write-Host "Adding server config" -ForegroundColor Green
            $settings | Add-Member -MemberType NoteProperty -Name 'server' -Value @{
                host_ip=$server
                port=8001
                auto_connect=$true
                timeout=30
            } -Force
        } else {
            Write-Host "Updating server config" -ForegroundColor Green
            $settings.server.host_ip = $server
            $settings.server.port = 8001
        }
        
        Write-Host "After update: $($settings.PSObject.Properties.Count) keys"
        
        $json = $settings | ConvertTo-Json -Depth 10 -Compress:$false
        
        Write-Host "JSON length: $($json.Length) chars"
        
        # Verify JSON
        $verify = $json | ConvertFrom-Json
        Write-Host "After JSON conversion: $($verify.PSObject.Properties.Count) keys"
        
        # Write file
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText((Resolve-Path 'erp_settings.json').Path, $json, $utf8NoBom)
        
        Write-Host "File written" -ForegroundColor Green
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. Verify result
Write-Host "`n[3] After update:" -ForegroundColor Yellow
$after = Get-Content 'erp_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Keys count: $($after.PSObject.Properties.Count)"
$after.PSObject.Properties.Name | ForEach-Object { Write-Host "  - $_" }

# 4. Compare
Write-Host "`n[4] Comparison:" -ForegroundColor Yellow
$beforeKeys = $before.PSObject.Properties.Name | Sort-Object
$afterKeys = $after.PSObject.Properties.Name | Sort-Object

$lost = $beforeKeys | Where-Object { $_ -notin $afterKeys }
$added = $afterKeys | Where-Object { $_ -notin $beforeKeys }

if ($lost.Count -gt 0) {
    Write-Host "LOST keys:" -ForegroundColor Red
    $lost | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
} else {
    Write-Host "No keys lost" -ForegroundColor Green
}

if ($added.Count -gt 0) {
    Write-Host "ADDED keys:" -ForegroundColor Green
    $added | ForEach-Object { Write-Host "  - $_" -ForegroundColor Green }
}

Write-Host "`n========================================" -ForegroundColor Cyan
if ($lost.Count -eq 0) {
    Write-Host "TEST PASSED" -ForegroundColor Green
} else {
    Write-Host "TEST FAILED" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
