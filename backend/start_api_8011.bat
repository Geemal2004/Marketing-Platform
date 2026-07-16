@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
  if not "%%A"=="" set "%%A=%%B"
)
echo HF_VIDEO_REPO_ID=%HF_VIDEO_REPO_ID%
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --timeout-keep-alive 75
pause
