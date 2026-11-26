
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.search import router as search_router
from api.routes.discovery import router as discovery_router
from api.routes.documents import router as documents_router
from api.routes.downloads import router as downloads_router
from api.routes.processing import router as processing_router


app = FastAPI(
    title="TopicDoc Finder API",
    description="Research paper discovery and semantic retrieval API.",
    version="1.0.0",
)


# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Semantic Search API
app.include_router(
    search_router,
    prefix="/api/search",
    tags=["Research Search"],
)


# Multi-source Discovery API
app.include_router(
    discovery_router,
    prefix="/api/discovery",
    tags=["Research Paper Discovery"],
)


# Document Management API
app.include_router(
    documents_router,
    prefix="/api/documents",
    tags=["Document Management"],
)


# PDF Downloads API
app.include_router(
    downloads_router,
    prefix="/api/downloads",
    tags=["PDF Downloads"],
)


# Document Processing API
app.include_router(
    processing_router,
    prefix="/api/processing",
    tags=["Document Processing"],
)


# Root endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to TopicDoc Finder API",
        "status": "running",
        "docs": "/docs",
    }


# Health Check
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
