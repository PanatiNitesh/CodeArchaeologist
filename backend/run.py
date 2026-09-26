import uvicorn
import os
import sys

# Ensure current dir is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 7860))
    print(f"=== Starting CodeArchaeologist Backend Server on http://{host}:{port} ===")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)
