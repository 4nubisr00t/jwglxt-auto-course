"""
create_shortcut.py - 为「湘大选课·漆黑结界」创建无黑窗直接启动的桌面快捷方式
"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_ICON = os.path.join(BASE_DIR, "assets", "icon.ico")


def find_pythonw():
    """探测 pythonw.exe 路径，优先同目录，找不到则退回 python.exe"""
    python_dir = os.path.dirname(sys.executable)
    pythonw_candidate = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw_candidate):
        return pythonw_candidate

    # 尝试在 PATH 中查找
    try:
        res = subprocess.run(["where", "pythonw"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
            if lines and os.path.exists(lines[0]):
                return lines[0]
    except Exception:
        pass

    return sys.executable


def get_desktop_dir():
    """获取用户桌面路径"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        desktop, _ = winreg.QueryValueEx(key, "Desktop")
        desktop = os.path.expandvars(desktop)
        if os.path.exists(desktop):
            return desktop
    except Exception:
        pass

    user_profile = os.environ.get("USERPROFILE", "")
    desktop = os.path.join(user_profile, "Desktop")
    if os.path.exists(desktop):
        return desktop
    return os.path.expanduser("~/Desktop")


def create_desktop_shortcut():
    """使用 PowerShell WScript.Shell 创建或更新桌面快捷方式"""
    desktop_dir = get_desktop_dir()
    shortcut_path = os.path.join(desktop_dir, "湘大选课·漆黑结界.lnk")
    pythonw_path = find_pythonw()

    print(f"[*] 快捷方式目标路径: {shortcut_path}")
    print(f"[*] 启动执行体 (无黑窗): {pythonw_path}")
    print(f"[*] 工作目录: {BASE_DIR}")
    print(f"[*] 绑定图标: {ASSET_ICON}")

    # 用 PowerShell WScript.Shell 创建快捷方式，避免第三方库依赖
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{pythonw_path}'
$Shortcut.Arguments = 'gui_app.py'
$Shortcut.WorkingDirectory = '{BASE_DIR}'
$Shortcut.IconLocation = '{ASSET_ICON},0'
$Shortcut.Description = '湘潭大学教务选课自动化工具·漆黑结界'
$Shortcut.Save()
"""
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] 创建快捷方式失败: {res.stderr}")
        return False

    if os.path.exists(shortcut_path):
        print(f"[OK] 桌面快捷方式已成功创建/更新: {shortcut_path}")
        verify_desktop_shortcut(shortcut_path)
        return True
    else:
        print("[!] 快捷方式文件未找到！")
        return False


def verify_desktop_shortcut(shortcut_path):
    """读取并验证快捷方式详细属性"""
    inspect_ps = f"""
$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut('{shortcut_path}')
Write-Output ("TargetPath: " + $sc.TargetPath)
Write-Output ("Arguments: " + $sc.Arguments)
Write-Output ("WorkingDirectory: " + $sc.WorkingDirectory)
Write-Output ("IconLocation: " + $sc.IconLocation)
Write-Output ("Description: " + $sc.Description)
"""
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", inspect_ps]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("[*] 快捷方式属性检验:")
        for line in res.stdout.strip().splitlines():
            print("   ", line.strip())
    else:
        print("[!] 检验读取失败:", res.stderr)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    create_desktop_shortcut()
