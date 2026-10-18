# Remove .hx association (current user only)
$ErrorActionPreference = "Continue"
Remove-Item -Path "HKCU:\Software\Classes\HX.SourceFile" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Classes\.hx" -Recurse -Force -ErrorAction SilentlyContinue
try {
  Add-Type -Namespace Win32 -Name Shell -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, int flags, System.IntPtr item1, System.IntPtr item2);
'@
  [Win32.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}
Write-Host "Removed .hx file association."
