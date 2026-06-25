$ErrorActionPreference = "Stop"

$targetPath = "C:\Users\tumsu\Desktop\AMS_Present\ams_source_files\02_Require.xlsx"
$fixedPath = "C:\Users\tumsu\Desktop\AMS_Present\ams_source_files\02_Require_FIXED.xlsx"

$excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
$target = $null
foreach ($wb in $excel.Workbooks) {
    if ($wb.FullName -eq $targetPath) {
        $target = $wb
        break
    }
}

if ($null -eq $target) {
    throw "Target workbook is not open in Excel: $targetPath"
}

$previousDisplayAlerts = $excel.DisplayAlerts
$previousScreenUpdating = $excel.ScreenUpdating
$excel.DisplayAlerts = $false
$excel.ScreenUpdating = $false

try {
    $fixed = $excel.Workbooks.Open($fixedPath, 0, $true)
    $sourceWs = $fixed.Worksheets.Item(1)
    $targetWs = $target.Worksheets.Item(1)

    $targetWs.Range("A1:D80").Value2 = $sourceWs.Range("A1:D80").Value2
    $targetWs.Range("D1:D120").WrapText = $true
    $targetWs.Columns.Item(4).ColumnWidth = 74
    $targetWs.Range("A1:D120").Rows.AutoFit()

    $fixed.Close($false)
    $target.Save()

    Write-Output "Updated open workbook and saved: $targetPath"
}
finally {
    $excel.DisplayAlerts = $previousDisplayAlerts
    $excel.ScreenUpdating = $previousScreenUpdating
}
