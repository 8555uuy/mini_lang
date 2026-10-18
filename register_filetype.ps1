# Associate .hx with HX Language Editor (current user only, no admin needed)
# Usage: powershell -ExecutionPolicy Bypass -File register_filetype.ps1

$ErrorActionPreference = "Stop"

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "hx.py"
$icon   = Join-Path $here "hx.ico"

if (-not (Test-Path $script)) { Write-Error "hx.py not found: $script"; exit 1 }

# Prefer pythonw.exe so double-click shows no console window
$pyw = $null
try {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $exe = & py -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2>$null
    if ($exe -and (Test-Path $exe.Trim())) { $pyw = $exe.Trim() }
  }
} catch {}
if (-not $pyw) {
  $cand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
  if ($cand) { $pyw = $cand.Source }
}
if (-not $pyw) { Write-Error "pythonw.exe not found"; exit 1 }

$cmd = '"' + $pyw + '" "' + $script + '" --edit "%1"'

# 1) ProgId
$progId = "HX.SourceFile"
$base = "HKCU:\Software\Classes\" + $progId
New-Item -Path $base -Force | Out-Null
Set-ItemProperty -Path $base -Name "(Default)" -Value "HX Source File"
New-Item -Path "$base\DefaultIcon" -Force | Out-Null
Set-ItemProperty -Path "$base\DefaultIcon" -Name "(Default)" -Value ($icon + ",0")
New-Item -Path "$base\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "$base\shell\open\command" -Name "(Default)" -Value $cmd

# 2) Extension
$ext = "HKCU:\Software\Classes\.hx"
New-Item -Path $ext -Force | Out-Null
Set-ItemProperty -Path $ext -Name "(Default)" -Value $progId
$owp = "HKCU:\Software\Classes\.hx\OpenWithProgids"
New-Item -Path $owp -Force | Out-Null
New-ItemProperty -Path $owp -Name $progId -PropertyType None -Value ([byte[]]@()) -Force | Out-Null

# 3) Refresh explorer icon cache
try {
  Add-Type -Namespace Win32 -Name Shell -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, int flags, System.IntPtr item1, System.IntPtr item2);
'@
  [Win32.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}

Write-Host "Done."
Write-Host ("  python : " + $pyw)
Write-Host ("  script : " + $script)
Write-Host ("  icon   : " + $icon)
Write-Host "Double-click any .hx file to open it in HX Language Editor."
Write-Host "To undo: run unregister_filetype.ps1"
