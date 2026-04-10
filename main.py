import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import uvicorn

import models, database, utils, schemas

# DB 테이블 생성
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Professional URL Redirector")

# 1. 중간자 메인 페이지 (브랜딩 및 입력)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return """
    <html>
        <head>
            <title>Gateway URL Shortener</title>
            <style>
                body { font-family: 'Malgun Gothic', sans-serif; background-color: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; width: 450px; }
                h1 { color: #1a73e8; margin-bottom: 10px; }
                p { color: #5f6368; font-size: 14px; }
                input { width: 100%; padding: 12px; margin: 20px 0; border: 1px solid #dadce0; border-radius: 8px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
                button:hover { background: #1557b0; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🔗 URL Gateway</h1>
                <p>긴 주소를 안전하고 짧은 중간 경로로 변환합니다.</p>
                <form action="/web_shorten" method="post">
                    <input type="url" name="target_url" placeholder="줄이고 싶은 긴 URL 입력" required>
                    <button type="submit">중간 경로 생성하기</button>
                </form>
            </div>
        </body>
    </html>
    """

# 2. 웹 전용 생성 로직 (중간자 결과 화면)
@app.post("/web_shorten", response_class=HTMLResponse)
def web_shorten(target_url: str = Form(...), db: Session = Depends(database.get_db), request: Request = None):
    new_url = models.URL(original_url=target_url)
    db.add(new_url); db.commit(); db.refresh(new_url)
    short_key = utils.encode_base62(new_url.id)
    new_url.short_key = short_key; db.commit()
    
    # 실제 생성된 짧은 주소
    full_short_url = f"{request.base_url}{short_key}"
    
    return f"""
    <div style="text-align:center; padding-top:100px; font-family:sans-serif;">
        <h2 style="color:#1a73e8;">생성된 중간 경로</h2>
        <div style="padding:20px; background:#e8f0fe; display:inline-block; border-radius:10px;">
            <a href="{full_short_url}" id="result" style="font-size:20px; font-weight:bold; color:#1a73e8;">{full_short_url}</a>
        </div>
        <p style="color:#666;">위 주소를 복사해서 사용하세요.</p>
        <a href="/" style="text-decoration:none; color:#999;">새로 만들기</a>
    </div>
    """

# 3. 중간자 핵심 기능: 리다이렉트 (추적 로직 포함 가능)
@app.get("/{short_key}")
def gateway_redirect(short_key: str, request: Request, db: Session = Depends(database.get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_key == short_key).first()
    if not url_entry:
        raise HTTPException(status_code=404, detail="연결된 원본 주소를 찾을 수 없습니다.")
    
    # [실무 엔지니어링] 클릭 수 증가 및 로그 출력
    url_entry.clicks += 1
    db.commit()
    
    print(f"INFO: Gateway Redirect - {short_key} -> {url_entry.original_url} (IP: {request.client.host})")
    
    return RedirectResponse(url=url_entry.original_url)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)