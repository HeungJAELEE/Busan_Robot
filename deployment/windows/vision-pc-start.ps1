param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("A", "B", "C")]
    [string]$Role,

    [string]$InstallRoot = "C:\Busan_Project"
)

$ErrorActionPreference = "Stop"

$VisionRepo = Join-Path $InstallRoot "factory_mes"
$ScriptByRole = @{
    "A" = "mes\A_Process_pendant.py"
    "B" = "mes\B_Process_pendant.py"
    "C" = "mes\C_Process_pendant.py"
}

Set-Location $VisionRepo
& ".\.venv\Scripts\python.exe" $ScriptByRole[$Role]
