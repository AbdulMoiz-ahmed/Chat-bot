import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting Webhook Backend Server on {settings.HOST}:{settings.PORT} in {settings.ENVIRONMENT} mode...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True if settings.ENVIRONMENT == "development" else False
    )
