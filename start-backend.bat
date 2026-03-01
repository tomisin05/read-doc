@echo off
echo Starting FastAPI backend server...
cd api
python -m uvicorn index:app --reload --port 8000
