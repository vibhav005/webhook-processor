# app/main.py
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Webhook Processor Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)

# When running locally without uvicorn CLI:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
