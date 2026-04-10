import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import uvicorn

import models, database, utils, schemas

# DB 초기화
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Global URL Shortener")

@app.get("/")
def read_root():
    return {"message": "URL Shortener is running. Use /docs for API testing."}

@app.post("/shorten", response_model=schemas.URLResponse)
def create_url(payload: schemas.URLBase, db: Session = Depends(database.get_db), request: Request = None):
    url_str = str(payload.original_url)
    existing = db.query(models.URL).filter(models.URL.original_url == url_str).first()
    
    # 배포 환경의 호스트 주소를 자동으로 감지하기 위한 설정
    host_url = str(request.base_url) if request else "http://localhost:8000/"

    if existing:
        return {"short_url": f"{host_url}{existing.short_key}", "original_url": url_str}

    new_url = models.URL(original_url=url_str)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    short_key = utils.encode_base62(new_url.id)
    new_url.short_key = short_key
    db.commit()

    return {"short_url": f"{host_url}{short_key}", "original_url": url_str}

@app.get("/{short_key}")
def redirect_url(short_key: str, db: Session = Depends(database.get_db)):
    target = db.query(models.URL).filter(models.URL.short_key == short_key).first()
    if not target:
        raise HTTPException(status_code=404, detail="URL not found")
    
    target.clicks += 1
    db.commit()
    return RedirectResponse(url=target.original_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)