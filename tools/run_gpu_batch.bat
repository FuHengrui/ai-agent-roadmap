@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=C:\Users\35799\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
echo ============================================
echo  torch check
echo ============================================
"%PY%" -c "import torch; print('torch OK', torch.__version__)"
echo.
if errorlevel 1 goto failed
echo ============================================
echo  running chapters...
echo ============================================
"%PY%" tools\run_gpu_batch.py --json gpu_report.json
echo.
echo done. results in gpu_report.json
goto end

:failed
echo.
echo [ERROR] this python cannot load torch.
echo.

:end
echo.
pause
