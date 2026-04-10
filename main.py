import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import uvicorn

# 기존에 생성한 모듈들을 불러옵니다.
import models, database, utils, schemas

# 서버 시작 시 데이터베이스 테이블 자동 생성
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Global URL Gateway Service")

# --- [SECTION 1] 메인 UI (웹 화면) ---
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <html>
        <head>
            <title>URL Gateway</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }
                .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 90%; max-width: 400px; }
                h1 { color: #1a73e8; }
                input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
                button { background: #1a73e8; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; }
                button:hover { background: #1557b0; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🔗 URL Gateway</h1>
                <p>외부 접속이 가능한 중간 주소를 생성합니다.</p>
                <form action="/web_shorten" method="post">
                    <input type="url" name="target_url" placeholder="https://www.weshareart.com/..." required>
                    <button type="submit">주소 생성하기</button>
                </form>
            </div>
        </body>
    </html>
    """

# --- [SECTION 2] 대량 처리용 API (remote_bulk.py 전용) ---
@app.post("/shorten", response_model=schemas.URLResponse)
def api_shorten(payload: schemas.URLBase, db: Session = Depends(database.get_db), request: Request = None):
    url_str = str(payload.original_url).strip()
    
    # [핵심] 외부 접속을 위해 현재 서버의 실제 도메인 주소를 가져옵니다.
    # 이 로직이 있어야 localhost가 아닌 onrender.com 주소로 결과가 나옵니다.
    base_url = str(request.base_url) if request else "https://your-service.onrender.com/"
    
    # 중복 확인
    existing = db.query(models.URL).filter(models.URL.original_url == url_str).first()
    if existing:
        return {"short_url": f"{base_url}{existing.short_key}", "original_url": url_str}

    # 데이터 저장
    new_url = models.URL(original_url=url_str)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    # 고유 키 생성 및 업데이트
    short_key = utils.encode_base62(new_url.id)
    new_url.short_key = short_key
    db.commit()

    return {"short_url": f"{base_url}{short_key}", "original_url": url_str}

# --- [SECTION 3] 웹 결과 화면 ---
@app.post("/web_shorten", response_class=HTMLResponse)
def web_shorten(target_url: str = Form(...), db: Session = Depends(database.get_db), request: Request = None):
    base_url = str(request.base_url)
    existing = db.query(models.URL).filter(models.URL.original_url == target_url).first()
    
    if existing:
        final_url = f"{base_url}{existing.short_key}"
    else:
        new_url = models.URL(original_url=target_url)
        db.add(new_url); db.commit(); db.refresh(new_url)
        short_key = utils.encode_base62(new_url.id); new_url.short_key = short_key; db.commit()
        final_url = f"{base_url}{short_key}"

    return f"""
    <div style="text-align:center; padding-top:100px; font-family:sans-serif;">
        <h2>생성 완료!</h2>
        <input value="{final_url}" style="width:300px; padding:10px; text-align:center;" readonly>
        <br><br><a href="/">돌아가기</a>
    </div>
    """

# --- [SECTION 4] 리다이렉트 (실제 연결) ---
@app.get("/{short_key}")
def gateway_redirect(short_key: str, db: Session = Depends(database.get_db)):
    target = db.query(models.URL).filter(models.URL.short_key == short_key).first()
    if not target:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    
    # 클릭 카운트 증가
    target.clicks += 1
    db.commit()
    
    return RedirectResponse(url=target.original_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
