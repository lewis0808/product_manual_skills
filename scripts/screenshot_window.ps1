# screenshot_window.ps1 — 桌面软件（exe）截图：截取前台窗口或全屏为 PNG。
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File screenshot_window.ps1 out.png            # 倒计时 5 秒后截前台窗口
#   powershell -ExecutionPolicy Bypass -File screenshot_window.ps1 out.png -Delay 8   # 自定义倒计时
#   powershell -ExecutionPolicy Bypass -File screenshot_window.ps1 out.png -Full      # 截全屏（多窗口/开始菜单等场景）
#
# 执行后立刻把目标软件窗口切到前台，等倒计时结束即自动截取。
# 依赖：仅 Windows 自带 PowerShell，无需安装任何包。

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$OutFile,
    [int]$Delay = 5,
    [switch]$Full
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Cap {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    public static int[] ForegroundRect() {
        RECT r;
        GetWindowRect(GetForegroundWindow(), out r);
        return new int[]{ r.Left, r.Top, r.Right, r.Bottom };
    }
}
"@
# 高 DPI 显示器上必须设为 DPI 感知，否则窗口坐标和屏幕像素对不上
[void][Win32Cap]::SetProcessDPIAware()

if ($Delay -gt 0) {
    Write-Host "请在 $Delay 秒内把目标软件窗口切到前台…"
    Start-Sleep -Seconds $Delay
}

if ($Full) {
    $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $x = $b.Left; $y = $b.Top; $w = $b.Width; $h = $b.Height
}
else {
    $r = [Win32Cap]::ForegroundRect()
    $x = $r[0]; $y = $r[1]; $w = $r[2] - $r[0]; $h = $r[3] - $r[1]
    if ($w -le 0 -or $h -le 0) { Write-Error "窗口尺寸异常（窗口是否最小化了？）"; exit 1 }
}

$out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutFile)
$dir = Split-Path $out -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

Write-Host "截图已保存：$out（${w}x${h}）"
