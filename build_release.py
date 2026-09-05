#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
湘大选课·漆黑结界 - Release 打包发布脚本
======================================
使用 PyInstaller 进行独立免安装运行包与分发 Zip 压缩打包。
"""
import os
import sys
import shutil
import zipfile
import subprocess
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTERNAL_NAME = "jwglxt_auto"
DISPLAY_NAME = "湘大选课·漆黑结界"
VERSION = "v1.1.0"
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

RAW_TARGET = os.path.join(DIST_DIR, INTERNAL_NAME)
FINAL_TARGET = os.path.join(DIST_DIR, DISPLAY_NAME)
ZIP_NAME = f"{DISPLAY_NAME}-{VERSION}-Windows-x64.zip"
ZIP_PATH = os.path.join(DIST_DIR, ZIP_NAME)


def clean():
    print("[1/5] 清理旧构建产物...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def build():
    print(f"[2/5] 开始 PyInstaller 构建内部包: {INTERNAL_NAME}...")
    import PyInstaller.__main__

    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    assets_data = f"{os.path.join(BASE_DIR, 'assets')};assets"

    args = [
        os.path.join(BASE_DIR, "gui_app.py"),
        f"--name={INTERNAL_NAME}",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}",
        f"--add-data={assets_data}",
        "--collect-all=customtkinter",
        "--noconfirm",
        "--clean",
    ]
    PyInstaller.__main__.run(args)


def post_process():
    print(f"[3/5] 重命名并注入元数据与分发文档...")
    if not os.path.exists(RAW_TARGET):
        raise RuntimeError(f"构建目录未生成: {RAW_TARGET}")

    # 重命名主程序 exe
    old_exe = os.path.join(RAW_TARGET, f"{INTERNAL_NAME}.exe")
    new_exe = os.path.join(RAW_TARGET, f"{DISPLAY_NAME}.exe")
    if os.path.exists(old_exe):
        if os.path.exists(new_exe):
            os.remove(new_exe)
        os.rename(old_exe, new_exe)

    # 重命名顶层目录
    if os.path.exists(FINAL_TARGET):
        shutil.rmtree(FINAL_TARGET, ignore_errors=True)
    os.rename(RAW_TARGET, FINAL_TARGET)

    # 复制 README.md
    readme_path = os.path.join(BASE_DIR, "README.md")
    if os.path.exists(readme_path):
        shutil.copy2(readme_path, os.path.join(FINAL_TARGET, "README.md"))

    # 生成清晰易读的使用说明文档
    tips_path = os.path.join(FINAL_TARGET, "使用说明.txt")
    with open(tips_path, "w", encoding="utf-8") as f:
        f.write(
            f"=====================================================\n"
            f"   {DISPLAY_NAME} ({VERSION}) 免安装便携发布版\n"
            f"=====================================================\n\n"
            f"【快速上手指南】\n"
            f"1. 双击运行当前目录下的「{DISPLAY_NAME}.exe」；\n"
            f"2. 在左侧面板的【浏览器介质】下拉框中，选择你常用的浏览器：\n"
            f"   - Microsoft Edge (Windows 原生标配)\n"
            f"   - Google Chrome\n"
            f"   - 自动检测 (Auto)\n"
            f"3. 点击「❖ 结下契约 · 连接教务」按钮：\n"
            f"   系统会自动弹出专属沙箱浏览器窗口，进入湘大统一身份认证登录页；\n"
            f"4. 在弹出的浏览器中输入学号与密码登录，并进入教务系统；\n"
            f"5. 登录成功后，主程序会自动捕获已选课程并建立结界连通！\n"
            f"6. 接下来你可以：\n"
            f"   - 点击「📜 扫描全表」拉取当前学期所有课程；\n"
            f"   - 点击「⏳ 时段筛课」按空闲时间找课；\n"
            f"   - 输入课程关键词，点击「启动抢课」全自动秒级抢课！\n\n"
            f"【特性优势】\n"
            f"- 纯本地运行：无需安装 Python 环境，开箱即用；\n"
            f"- 沙箱隔离：浏览器登录环境独立，不影响日常上网；\n"
            f"- 密码记忆：支持浏览器原生保存密码，下次登录一键直达。\n\n"
            f"祝大家都能选到心仪的好课！\n"
        )


def make_zip():
    print(f"[4/5] 打包生成分发压缩包: {ZIP_NAME}...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(FINAL_TARGET):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DIST_DIR)
                zf.write(full_path, rel_path)

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"[+] 压缩包打包完成: {ZIP_PATH} ({size_mb:.2f} MB)")


def verify():
    print(f"[5/5] 验证生成的可执行文件...")
    target_exe = os.path.join(FINAL_TARGET, f"{DISPLAY_NAME}.exe")
    if not os.path.isfile(target_exe):
        raise RuntimeError(f"目标主程序不存在: {target_exe}")
    print(f"[+] 目标主程序就绪: {target_exe} ({os.path.getsize(target_exe) / (1024*1024):.2f} MB)")
    print(f"=== 全部打包流程顺利完成 ===")


if __name__ == "__main__":
    clean()
    build()
    post_process()
    make_zip()
    verify()
