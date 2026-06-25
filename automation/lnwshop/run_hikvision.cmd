@echo off
cd /d C:\365_project\TheCool18e\Dev
powershell -NoProfile -ExecutionPolicy Bypass -File automation\lnwshop\lnwshop.ps1 -Dataset HIKVISION %*
