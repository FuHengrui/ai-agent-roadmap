@echo off
chcp 65001 >nul
setlocal
set "PY=C:\Users\35799\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
cd /d "%~dp0.."
echo 用这个解释器跑：%PY%
echo.
"%PY%" -c "import torch; print('torch', torch.__version__)" || (echo [错误] 这个解释器加载不了 torch & pause & exit /b 1)
echo.
"%PY%" tools\run_gpu_batch.py --json gpu_report.json > gpu_report.txt 2>&1
echo.
echo ============================================
type gpu_report.txt | more +0
echo ============================================
echo 结果已写入 gpu_report.txt 和 gpu_report.json
pause
