# File Guide: scripts/start_dev.ps1
# - Purpose: Quick local Windows PowerShell startup script with virtualenv bootstrapping.
# - Usage: ./scripts/start_dev.ps1 -Port 8000
param(
  [int]$Port = 8000
)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $Port --reload
