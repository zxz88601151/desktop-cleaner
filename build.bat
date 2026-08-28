@echo off
REM ============================================================
REM  Desktop Cleaner - Windows 打包脚本 (PyInstaller one-file)
REM  用法：双击本文件，或在项目根目录执行 build.bat
REM  产物：dist\DesktopCleaner.exe  （单文件，无需安装）
REM
REM  一致性说明（P2-6）：统一调用 build.spec 作为唯一事实源，
REM  spec 已包含 name / onefile / windowed / hiddenimports / 代码签名占位，
REM  不再内联重复参数，避免两条打包路径产物不一致。
REM ============================================================
setlocal

python -m pip install -r requirements.txt

pyinstaller build.spec

REM ---- 可选：代码签名（P1-4 发布阻断项，需外部证书）----
REM  未配置证书时整段跳过，不影响构建。配置方式：设置环境变量
REM  CERT_PFX（pfx 路径）与 CERT_PWD（密码）后取消下方注释：
REM if defined CERT_PFX (
REM     signtool sign /f "%CERT_PFX%" /p "%CERT_PWD%" ^
REM         /tr http://timestamp.digicert.com /td SHA256 ^
REM         /fd SHA256 dist\DesktopCleaner.exe
REM )

echo.
echo 打包完成，exe 位于 dist\DesktopCleaner.exe
pause
