from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth
from app.core.config import settings

app = FastAPI(
    title="Auth API",
    description="Authentication API using FastAPI",
    version="1.0.0",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
    }
)

# Security scheme for Swagger UI
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
}

# Add security scheme
security_scheme = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
}
app.openapi_components = {"securitySchemes": security_scheme}
app.openapi_security = [{"Bearer": []}]

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
