$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
python automation\lnwshop\prepare_assets.py
