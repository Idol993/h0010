import time
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.requests import Request

from server.models import ResumeParseResponse
from server.services import parser as parser_service
from server import db

router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_SIZE = 10 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".doc", ".docx", ".txt", ".md", ".text"}


@router.post("", response_model=ResumeParseResponse)
async def upload_resume(request: Request, file: UploadFile = File(...)):
    start = time.time()
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        return ResumeParseResponse(success=False, error=f"不支持的文件格式: {ext}",
                                   parse_time_ms=(time.time() - start) * 1000)
    try:
        contents = await file.read()
    except Exception as e:
        return ResumeParseResponse(success=False, error=f"文件读取失败: {e}",
                                   parse_time_ms=(time.time() - start) * 1000)
    if len(contents) > MAX_SIZE:
        return ResumeParseResponse(success=False, error="文件大小超过10MB限制",
                                   parse_time_ms=(time.time() - start) * 1000)
    if not contents:
        return ResumeParseResponse(success=False, error="文件为空或已损坏",
                                   parse_time_ms=(time.time() - start) * 1000)
    try:
        resume = parser_service.parse_resume(contents, filename)
    except ValueError as e:
        return ResumeParseResponse(success=False, error=str(e),
                                   parse_time_ms=(time.time() - start) * 1000)
    except Exception as e:
        return ResumeParseResponse(success=False, error=f"解析异常: {e}",
                                   parse_time_ms=(time.time() - start) * 1000)
    saved = db.save_resume(resume)
    elapsed = (time.time() - start) * 1000
    return ResumeParseResponse(success=True, resume=saved, parse_time_ms=round(elapsed, 2))


@router.post("/batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    results = []
    for f in files:
        try:
            resp = await upload_resume(None, f)
            results.append({"filename": f.filename, "result": resp})
        except Exception as e:
            results.append({"filename": f.filename, "success": False, "error": str(e)})
    return {"results": results}


@router.get("/resumes")
def list_all_resumes():
    return {"total": len(db.list_resumes()), "resumes": db.list_resumes()}
