# 批量替换 operator_info 导入为 operator
$files = @(
    "gui\inventory_view.py",
    "gui\product_view.py",
    "gui\sales_view.py",
    "test_delete_order.py",
    "test_inventory_operations.py",
    "test_product_operations.py",
    "test_sales_operations.py",
    "test_shipment_operations.py"
)

$oldImport = "from utils.operator_info import get_operator_info"
$newImport = "from utils.operator import get_operator_info"

$totalReplaced = 0

foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw -Encoding UTF8
        $originalContent = $content
        $content = $content -replace [regex]::Escape($oldImport), $newImport
        
        if ($content -ne $originalContent) {
            [System.IO.File]::WriteAllText((Resolve-Path $file).Path, $content, (New-Object System.Text.UTF8Encoding $false))
            $count = ([regex]::Matches($originalContent, [regex]::Escape($oldImport))).Count
            $totalReplaced += $count
            Write-Host "✓ $file - 替换了 $count 处" -ForegroundColor Green
        }
    } else {
        Write-Host "✗ $file - 文件不存在" -ForegroundColor Red
    }
}

Write-Host "`n总共替换了 $totalReplaced 处导入语句" -ForegroundColor Cyan
