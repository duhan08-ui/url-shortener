import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import uvicorn

# 파일명이 다를 수 있으니 확인: models, database, utils, schemas 파일들이 같은 폴더에 있어야 합니다.
import models, database, utils, schemas

# DB 초기화 (실패 방지를 위한 예외 처리)
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"DB 초기화 에러: {e}")

app = FastAPI(title="Professional URL Gateway")

# --- [API] 대량 처리용 (500 에러 해결 버전) ---
@app.post("/shorten", response_model=schemas.URLResponse)
def api_shorten(payload: schemas.URLBase, db: Session = Depends(database.get_db), request: Request = None):
    try:
        url_str = str(payload.original_url).strip()
        
        # 중복 체크
        existing = db.query(models.URL).filter(models.URL.original_url == url_str).first()
        host_url = str(request.base_url) if request else "/"
        
        if existing:
            return {"short_url": f"{host_url}{existing.short_key}", "original_url": url_str}

        # 새 데이터 생성
        new_url = models.URL(original_url=url_str)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)

        # 키 생성 및 업데이트
        short_key = utils.encode_base62(new_url.id)
        new_url.short_key = short_key
        db.commit()

        return {"short_url": f"{host_url}{short_key}", "original_url": url_str}
    except Exception as e:
        db.rollback() # 에러 발생 시 DB 되돌리기
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# --- [UI] 메인 화면 ---
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <html>
        <head><title>URL Gateway</title></head>
        <body style="text-align:center; padding-top:100px; font-family:sans-serif;">
            <h1>🔗 URL Gateway</h1>
            <form action="/web_shorten" method="post">
                <input type="url" name="target_url" placeholder="https://example.com" style="width:300px; padding:10px;" required>
                <button type="submit" style="padding:10px 20px;">줄이기</button>
            </form>
        </body>
    </html>
    """

@app.post("/web_shorten", response_class=HTMLResponse)
def web_shorten(target_url: str = Form(...), db: Session = Depends(database.get_db), request: Request = None):
    host_url = str(request.base_url) if request else "/"
    existing = db.query(models.URL).filter(models.URL.original_url == target_url).first()
    if existing:
        final_url = f"{host_url}{existing.short_key}"
    else:
        new_url = models.URL(original_url=target_url)
        db.add(new_url); db.commit(); db.refresh(new_url)
        short_key = utils.encode_base62(new_url.id); new_url.short_key = short_key; db.commit()
        final_url = f"{host_url}{short_key}"
    return f"<h2>결과: <a href='{final_url}'>{final_url}</a></h2><br><a href='/'>돌아가기</a>"

# --- [Redirect] 리다이렉트 ---
@app.get("/{short_key}")
def gateway_redirect(short_key: str, db: Session = Depends(database.get_db)):
    target = db.query(models.URL).filter(models.URL.short_key == short_key).first()
    if not target: raise HTTPException(status_code=404)
    target.clicks += 1; db.commit()
    return RedirectResponse(url=target.original_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
