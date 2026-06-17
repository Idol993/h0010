from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from server.routes import upload, match, jd

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(
    title="智能简历解析与岗位匹配 API",
    description="基于 FastAPI + sentence-transformers 的简历解析、岗位匹配服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            length = request.headers.get("content-length")
            if length and int(length) > MAX_UPLOAD_BYTES:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"detail": "上传文件超过 10MB 限制"},
                )
        return await call_next(request)


app.add_middleware(UploadSizeLimitMiddleware)

app.include_router(upload.router)
app.include_router(match.router)
app.include_router(jd.router)


@app.get("/")
def root():
    return {
        "name": "智能简历解析与岗位匹配 API",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
