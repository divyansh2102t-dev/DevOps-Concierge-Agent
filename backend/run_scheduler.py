import uvicorn
from backend.key_optimizer.main import app

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="info")
