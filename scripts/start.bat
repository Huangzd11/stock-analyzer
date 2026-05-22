@echo off
REM Stock Analyzer Web 服务启动脚本（双击或 cmd 运行）
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境 .venv
    echo.
    echo 请先执行:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev]"
    echo   .venv\Scripts\pip install -e ".[ml]"   REM 可选：深度学习预测
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [提示] 已从 .env.example 创建 .env
    )
)

echo.
echo  Stock Analyzer 正在启动...
echo  控制台: http://127.0.0.1:8000/
echo  API 文档: http://127.0.0.1:8000/docs
echo  按 Ctrl+C 停止服务
echo.

".venv\Scripts\python.exe" -m uvicorn stock_analyzer.interface.api.app:app --host 127.0.0.1 --port 8000

echo.
echo 服务已停止。
pause
