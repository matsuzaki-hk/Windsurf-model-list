@echo off
REM パスにスペースがあるためスクリプトをフルパス指定
python "C:\Users\avalo\.vscode\projects\Windsurf model list\fetch_models.py" > models.json
echo Done. Output: models_output.json / models_table.md