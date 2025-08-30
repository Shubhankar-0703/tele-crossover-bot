# Activate virtual environment
. .\.venv\Scripts\Activate.ps1

# Stop any running Python bot processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Start bot.py
Start-Process python -ArgumentList "bot.py"

# Start alerts.py
Start-Process python -ArgumentList "alerts.py"
