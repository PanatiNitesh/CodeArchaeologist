import uvicorn
import os
import sys

# Ensure current dir is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"=== Starting CodeArchaeologist Backend Server on http://localhost:{port} ===")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, reload=False)
