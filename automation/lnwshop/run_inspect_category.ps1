$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
python automation\lnwshop\lnwshop_fill.py inspect-category
