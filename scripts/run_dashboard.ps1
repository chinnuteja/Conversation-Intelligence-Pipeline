# Delegates to repo-root run_dashboard.py (unbuffered Streamlit).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python run_dashboard.py @args
