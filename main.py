import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import uvicorn

import models, database, utils, schemas

# DB 테이블 자동 생성
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Professional URL Gateway")

# --- [SECTION 1] 중간자 메인 화면 (UI) ---
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <html>
        <head>
            <title>URL Gateway Service</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; width: 500px; }
                h1 { color: #2c3e50; margin-bottom: 20px; }
                input { width: 80%; padding: 15px; border: 2px solid #ddd; border-radius: 8px; margin-bottom: 20px; font-size: 16px; }
                button { background-color: #3498db; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; }
                button:hover { background-color: #2980b9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔗 URL Gateway</h1>
                <p>긴 원본 주소를 중간 경로 주소로 변환합니다.</p>
                <form action="/web_shorten" method="post">
                    <input type="url" name="target_url" placeholder="https://example.com" required>
                    <br>
                    <button type="submit">중간 주소 생성</button>
                </form>
            </div>
        </body>
    </html>
    """

# --- [SECTION 2] 대량 처리용 API (remote_bulk.py와 통신) ---
@app.post("/shorten", response_model=schemas.URLResponse)
def api_shorten(payload: schemas.URLBase, db: Session = Depends(database.get_db), request: Request = None):
    url_str = str(payload.original_url).strip()
    
    # 중복 체크: 이미 존재하는 URL이면 기존 정보를 반환 (성능 최적화)
    existing = db.query(models.URL).filter(models.URL.original_url == url_str).first()
    
    host_url = str(request.base_url) if request else "/"
    
    if existing:
        return {"short_url": f"{host_url}{existing.short_key}", "original_url": url_str}

    # 새 데이터 생성
    new_url = models.URL(original_url=url_str)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    # 고유 키 생성 및 저장
    short_key = utils.encode_base62(new_url.id)
    new_url.short_key = short_key
    db.commit()

    return {"short_url": f"{host_url}{short_key}", "original_url": url_str}

# --- [SECTION 3] 웹 화면 전용 생성 처리 ---
@app.post("/web_shorten", response_class=HTMLResponse)
def web_shorten(target_url: str = Form(...), db: Session = Depends(database.get_db), request: Request = None):
    # API 로직과 동일하게 작동하도록 내부 호출
    host_url = str(request.base_url) if request else "/"
    existing = db.query(models.URL).filter(models.URL.original_url == target_url).first()
    
    if existing:
        final_url = f"{host_url}{existing.short_key}"
    else:
        new_url = models.URL(original_url=target_url)
        db.add(new_url); db.commit(); db.refresh(new_url)
        short_key = utils.encode_base62(new_url.id)
        new_url.short_key = short_key; db.commit()
        final_url = f"{host_url}{short_key}"

    return f"""
    <div style="text-align:center; padding-top:100px; font-family:sans-serif;">
        <h2 style="color:#2c3e50;">생성 성공!</h2>
        <p>아래 주소를 복사해서 공유하세요:</p>
        <div style="background:#f1f1f1; padding:20px; display:inline-block; border-radius:10px; font-size:1.2rem;">
            <a href="{final_url}" target="_blank">{final_url}</a>
        </div>
        <br><br><a href="/">메인으로 돌아가기</a>
    </div>
    """

# --- [SECTION 4] 중간자 핵심: 리다이렉트 기능 ---
@app.get("/{short_key}")
def gateway_redirect(short_key: str, db: Session = Depends(database.get_db)):
    target = db.query(models.URL).filter(models.URL.short_key == short_key).first()
    if not target:
        raise HTTPException(status_code=404, detail="연결된 원본 주소를 찾을 수 없습니다.")
    
    # 클릭 수 집계 (통계용)
    target.clicks += 1
    db.commit()
    
    return RedirectResponse(url=target.original_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
