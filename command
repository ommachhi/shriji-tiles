# Backend (run in terminal 1) - fastest local mode
cd project/backend; $env:ENABLE_CATALOG_AUTO_RELOAD='false'; $env:ENABLE_IMAGE_VALIDATION='false'; $env:ENABLE_IMAGE_VERSIONING='false'; e:/Tejeshkp/.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001

# Backend (optional dev autoreload, slower startup)
# cd project/backend; $env:ENABLE_CATALOG_AUTO_RELOAD='false'; $env:ENABLE_IMAGE_VALIDATION='false'; $env:ENABLE_IMAGE_VERSIONING='false'; e:/Tejeshkp/.venv/Scripts/python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8001

# Frontend (run in terminal 2)
cd project/frontend; npm start
