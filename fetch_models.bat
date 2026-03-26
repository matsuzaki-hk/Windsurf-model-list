@echo off
REM Windsurfモデルリスト取得スクリプト
python "%~dp0fetch_models.py"
echo Done. Output: models_output.json / models_table.md