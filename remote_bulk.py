import requests
import csv
import time

# [중요] 본인의 Render 서버 주소로 수정하세요 (끝에 /는 빼주세요)
API_HOST = "https://my-short-url-service.onrender.com" 
API_URL = f"{API_HOST.rstrip('/')}/shorten"

INPUT_FILE = "urls.txt"        # 원본 URL 200개가 들어있는 파일
OUTPUT_FILE = "short_results.csv" # 결과가 저장될 파일

def run_bulk():
    try:
        # urls.txt 읽기
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        
        print(f"🚀 총 {len(urls)}개의 URL 작업을 시작합니다...")
        results = []

        for i, original_url in enumerate(urls, 1):
            try:
                # 서버에 요청 (JSON 형식)
                response = requests.post(
                    API_URL, 
                    json={"original_url": original_url}, 
                    timeout=15
                )
                
                if response.status_code == 200:
                    short_url = response.json()["short_url"]
                    results.append([original_url, short_url])
                    print(f"[{i}/{len(urls)}] 성공: {short_url}")
                else:
                    # 여기서 404가 난다면 서버 주소나 API 경로(/shorten) 문제임
                    print(f"[{i}/{len(urls)}] 실패: 코드 {response.status_code}")
                
                time.sleep(0.1) # 서버 과부하 방지
                
            except Exception as e:
                print(f"[{i}] 에러 발생: {str(e)}")

        # CSV 파일로 저장
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Original URL", "Short URL (Gateway)"])
            writer.writerows(results)

        print(f"\n✅ 완료! {OUTPUT_FILE} 파일을 확인하세요.")

    except FileNotFoundError:
        print(f"❌ {INPUT_FILE} 파일이 없습니다. URL 목록을 먼저 만드세요.")

if __name__ == "__main__":
    run_bulk()