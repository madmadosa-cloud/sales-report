# 사회복지시설 매출분석 웹 프로그램

급여관리 시스템과 **분리된 독립 프로그램**입니다. Django + HTMX 기반으로 매출자료 업로드, 집계, Excel/PDF 보고서 생성을 수행합니다.

## 기능

- 매출자료 CSV 복수 업로드 (UTF-8 BOM)
- 연/월별 DB 저장, 동일 연월 재업로드 시 확인 후 교체
- 거래처분류 × 품목분류 × 월 집계 (건수 = 해당 그룹 데이터 행 수)
- 상반기/하반기/연간/직접 기간 보고서 미리보기
- Excel(.xlsx) · PDF 다운로드
- 보고서 생성 시 **집계 검증** 자동 실행 (통과 시에만 다운로드 가능)

## 설치 및 실행

```bash
cd 실적보고프로그램개발
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

브라우저에서 http://127.0.0.1:8000/ 접속

## 테스트

```bash
python manage.py test sales_analysis
```

## PDF (WeasyPrint)

Windows에서는 GTK 런타임이 필요할 수 있습니다. 오류 시 [WeasyPrint 문서](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)를 참고하세요.

## 데이터 저장

SQLite DB(`db.sqlite3`)에 매출 원자료가 저장됩니다. 급여 프로그램과 DB·코드는 공유하지 않습니다.
