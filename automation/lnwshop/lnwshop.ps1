param(
    [ValidateSet(
        "Menu",
        "Prepare",
        "CategoryInspect",
        "CategoryOne",
        "CategoryBatch",
        "ProductInspect",
        "ProductOne",
        "ProductBatch",
        "DryCategory",
        "DryProduct",
        "OpenOutput"
    )]
    [string]$Action = "Menu",
    [ValidateSet("IMOU", "HIKFIRE", "HIKVISION", "HIP", "HUAWEI")]
    [string]$Dataset = "HIKVISION",
    [string]$Excel = "",
    [string]$CategoryExcel = "",
    [int]$Row = 2,
    [int]$StartRow = 2,
    [int]$EndRow = 0,
    [switch]$AutoSave,
    [switch]$NoClick,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path "$ScriptDir\..\.."
Set-Location $Root

function Get-DatasetConfig {
    switch ($Dataset) {
        "IMOU" {
            return @{
                PrepareScript = "automation\lnwshop\prepare_assets.py"
                ProductExcel = "output\spreadsheet\IMOU_LnwShop_AI_ready_watermarked.xlsx"
                CategoryExcel = "output\spreadsheet\IMOU_LnwShop_categories.xlsx"
            }
        }
        "HIKFIRE" {
            return @{
                PrepareScript = "automation\lnwshop\prepare_hikfire_assets.py"
                ProductExcel = "output\spreadsheet\HIKFIRE_LnwShop_AI_ready_watermarked.xlsx"
                CategoryExcel = "output\spreadsheet\HIKFIRE_LnwShop_categories.xlsx"
            }
        }
        "HIKVISION" {
            return @{
                PrepareScript = "automation\lnwshop\prepare_hikvision_assets.py"
                ProductExcel = "output\spreadsheet\HIKVISION_LnwShop_AI_ready_watermarked.xlsx"
                CategoryExcel = "output\spreadsheet\HIKVISION_LnwShop_categories.xlsx"
            }
        }
        "HIP" {
            return @{
                PrepareScript = "automation\lnwshop\prepare_lpr_assets.py"
                ProductExcel = "output\spreadsheet\HIP_LnwShop_AI_ready_watermarked.xlsx"
                CategoryExcel = "output\spreadsheet\HIP_LnwShop_categories.xlsx"
            }
        }
        "HUAWEI" {
            return @{
                PrepareScript = "automation\lnwshop\prepare_huawei_assets.py"
                ProductExcel = "output\spreadsheet\HUAWEI_LnwShop_AI_ready_watermarked.xlsx"
                CategoryExcel = "output\spreadsheet\HUAWEI_LnwShop_categories.xlsx"
            }
        }
    }
}

$Config = Get-DatasetConfig
$ProductExcel = if ([string]::IsNullOrWhiteSpace($Excel)) { $Config.ProductExcel } else { $Excel }
$SelectedCategoryExcel = if ([string]::IsNullOrWhiteSpace($CategoryExcel)) { $Config.CategoryExcel } else { $CategoryExcel }
$PrepareScript = $Config.PrepareScript

function Invoke-Python {
    param([string[]]$ArgsList)
    & python @ArgsList
}

function Invoke-Lnw {
    param([string[]]$ArgsList)
    $allArgs = @("automation\lnwshop\lnwshop_fill.py") + $ArgsList + @("--excel", $ProductExcel, "--category-excel", $SelectedCategoryExcel)
    Invoke-Python $allArgs
}

function Invoke-Prepare {
    Invoke-Python @($PrepareScript)
}

function Open-OutputFolder {
    explorer.exe (Resolve-Path "output\spreadsheet")
}

function Add-AutoSaveArg {
    param([string[]]$ArgsList)
    if ($AutoSave) {
        return $ArgsList + @("--auto-save")
    }
    return $ArgsList
}

function Add-NoPauseArg {
    param([string[]]$ArgsList)
    if ($NoPause) {
        return $ArgsList + @("--no-pause")
    }
    return $ArgsList
}

function Invoke-Action {
    param([string]$SelectedAction)

    switch ($SelectedAction) {
        "Prepare" {
            Invoke-Prepare
        }
        "CategoryInspect" {
            $args = @("inspect-category")
            if ($NoClick) { $args += "--no-click-add-category" }
            Invoke-Lnw $args
        }
        "CategoryOne" {
            $args = @("fill-category", "--row", "$Row")
            if ($NoClick) { $args += "--no-click-add-category" }
            $args = Add-AutoSaveArg $args
            Invoke-Lnw $args
        }
        "CategoryBatch" {
            $args = @("fill-categories", "--start-row", "$StartRow")
            if ($EndRow -gt 0) { $args += @("--end-row", "$EndRow") }
            $args = Add-AutoSaveArg $args
            $args = Add-NoPauseArg $args
            Invoke-Lnw $args
        }
        "ProductInspect" {
            $args = @("inspect")
            if ($NoClick) { $args += "--no-click-add-product" }
            Invoke-Lnw $args
        }
        "ProductOne" {
            $args = @("fill", "--row", "$Row")
            if ($NoClick) { $args += "--no-click-add-product" }
            $args = Add-AutoSaveArg $args
            Invoke-Lnw $args
        }
        "ProductBatch" {
            $args = @("fill-products", "--start-row", "$StartRow")
            if ($EndRow -gt 0) { $args += @("--end-row", "$EndRow") }
            $args = Add-AutoSaveArg $args
            $args = Add-NoPauseArg $args
            Invoke-Lnw $args
        }
        "DryCategory" {
            Invoke-Lnw @("dry-run-category", "--row", "$Row")
        }
        "DryProduct" {
            Invoke-Lnw @("dry-run", "--row", "$Row")
        }
        "OpenOutput" {
            Open-OutputFolder
        }
    }
}

function Read-IntOrDefault {
    param([string]$Prompt, [int]$Default)
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return [int]$value
}

function Read-YesNo {
    param([string]$Prompt)
    $value = Read-Host "$Prompt y/N"
    return ($value -match "^(y|Y)")
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "LnwShop Automation" -ForegroundColor Cyan
        Write-Host "Dataset: $Dataset"
        Write-Host "Product Excel: $ProductExcel"
        Write-Host "Category Excel: $SelectedCategoryExcel"
        Write-Host "1. Prepare Excel, watermarked images, categories"
        Write-Host "2. Dry-run one category row"
        Write-Host "3. Inspect add-category form"
        Write-Host "4. Fill one category row"
        Write-Host "5. Fill category rows batch"
        Write-Host "6. Dry-run one product row"
        Write-Host "7. Inspect add-product form"
        Write-Host "8. Fill one product row"
        Write-Host "9. Fill product rows batch"
        Write-Host "10. Open output folder"
        Write-Host "Q. Quit"
        $choice = Read-Host "Choose"

        switch ($choice.ToUpperInvariant()) {
            "1" { Invoke-Prepare }
            "2" {
                $script:Row = Read-IntOrDefault "Category Excel row" 2
                Invoke-Action "DryCategory"
            }
            "3" {
                $script:NoClick = Read-YesNo "Already on add-category page, skip +category click?"
                Invoke-Action "CategoryInspect"
                $script:NoClick = $false
            }
            "4" {
                $script:Row = Read-IntOrDefault "Category Excel row" 2
                $script:AutoSave = Read-YesNo "Click Save automatically?"
                $script:NoClick = Read-YesNo "Already on add-category page, skip +category click?"
                Invoke-Action "CategoryOne"
                $script:AutoSave = $false
                $script:NoClick = $false
            }
            "5" {
                $script:StartRow = Read-IntOrDefault "Start category row" 2
                $script:EndRow = Read-IntOrDefault "End category row, use 0 for last row" 0
                $script:AutoSave = Read-YesNo "Click Save automatically?"
                $script:NoPause = $false
                if ($script:AutoSave) { $script:NoPause = Read-YesNo "Run continuously without pause after each save?" }
                Invoke-Action "CategoryBatch"
                $script:AutoSave = $false
                $script:NoPause = $false
                $script:EndRow = 0
            }
            "6" {
                $script:Row = Read-IntOrDefault "Product Excel row" 2
                Invoke-Action "DryProduct"
            }
            "7" {
                $script:NoClick = Read-YesNo "Already on add-product page, skip +product click?"
                Invoke-Action "ProductInspect"
                $script:NoClick = $false
            }
            "8" {
                $script:Row = Read-IntOrDefault "Product Excel row" 2
                $script:AutoSave = Read-YesNo "Click Save automatically?"
                $script:NoClick = Read-YesNo "Already on add-product page, skip +product click?"
                Invoke-Action "ProductOne"
                $script:AutoSave = $false
                $script:NoClick = $false
            }
            "9" {
                $script:StartRow = Read-IntOrDefault "Start product row" 2
                $script:EndRow = Read-IntOrDefault "End product row, use 0 for last row" 0
                $script:AutoSave = Read-YesNo "Click Save automatically?"
                $script:NoPause = $false
                if ($script:AutoSave) { $script:NoPause = Read-YesNo "Run continuously without pause after each save?" }
                Invoke-Action "ProductBatch"
                $script:AutoSave = $false
                $script:NoPause = $false
                $script:EndRow = 0
            }
            "10" { Open-OutputFolder }
            "Q" { return }
            default { Write-Host "Invalid choice" -ForegroundColor Yellow }
        }
    }
}

if ($Action -eq "Menu") {
    Show-Menu
} else {
    Invoke-Action $Action
}
