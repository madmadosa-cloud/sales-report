# 사회복지시설 매출분석 웹 프로그램

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Author:** [madmadosa-cloud](https://github.com/madmadosa-cloud)  
**Year:** 2026  
**License:** MIT

Django + HTMX 기반 매출자료 업로드, 집계, Excel/PDF 보고서 생성 프로그램입니다.  
급여관리 등 다른 시스템과 **분리된 독립 프로그램**으로 동작합니다.

## 기능

- 매출자료 CSV 복수 업로드 (UTF-8 BOM)
- 연/월별 DB 저장, 동일 연월 재업로드 시 확인 후 교체
- 거래처분류 × 품목분류 × 월 집계 (건수 = 해당 그룹 데이터 행 수)
- **분류코드 마스터 관리** (품목/거래처 CRUD, CSV 일괄 업로드)
- 상반기/하반기/연간/직접 기간 보고서, **간편보고서**, **복지부보고서**
- Excel(.xlsx) · PDF 다운로드
- 보고서 생성 시 **집계 검증** (통과 시에만 다운로드)

## 설치

### 요구 사항

- Python 3.11 이상 권장
- Windows / macOS / Linux

### 1. 저장소 받기

```bash
git clone https://github.com/madmadosa-cloud/sales-report.git
cd sales-report/실적보고프로그램개발
```

### 2. 가상환경 및 패키지

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수 (`.env`)

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

`.env` 파일을 열어 `DJANGO_SECRET_KEY`를 변경합니다. 새 키 생성:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| 변수 | 설명 | 예시 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 비밀 키 (필수) | 랜덤 문자열 |
| `DJANGO_DEBUG` | 디버그 모드 (`True`/`False`) | 로컬: `True`, 배포: `False` |
| `DJANGO_ALLOWED_HOSTS` | 허용 호스트 (쉼표 구분) | `localhost,127.0.0.1` |
| `REPORT_FONT_PATH` | PDF 한글 폰트 경로 (선택) | `C:\Windows\Fonts\malgun.ttf` |

### 4. DB 초기화 및 실행

```bash
python manage.py migrate
python manage.py runserver
```

브라우저: http://127.0.0.1:8000/

**Windows:** `run_server.bat` 더블클릭 (`.env` 없으면 `.env.example`을 복사한 뒤 실행)

## 사용 방법

1. **매출자료 업로드** — 월별 전표별품목별매출자료 CSV를 선택해 업로드합니다. 동일 연·월 데이터가 있으면 교체 여부를 확인합니다.
2. **기간 입력** — 연도와 상반기/하반기/연간/직접 기간을 선택합니다.
3. **보고서 생성** — 「보고서 생성」, 「간편보고서」, 「복지부보고서」 중 선택합니다.
4. **검증 확인** — 화면의 집계 검증 결과가 통과하면 Excel/PDF를 다운로드할 수 있습니다.
5. **분류코드 관리** — 상단 메뉴 또는 http://127.0.0.1:8000/master/ 에서 품목·거래처 분류코드를 등록/수정합니다.

## 테스트

```bash
python manage.py test sales_analysis
```

## PDF

PDF 보고서는 **xhtml2pdf**(순수 Python)로 생성합니다. Windows exe 배포에 적합하며 별도 GTK 설치가 필요 없습니다.

## Windows exe 배포 (PyInstaller)

비개발자 PC에 Python 없이 배포할 때:

```bat
build_exe.bat
```

또는:

```bash
.venv\Scripts\pip install -r requirements.txt -r requirements-build.txt
.venv\Scripts\python build_support\build.py
```

결과물:
- `dist/매출분석프로그램/` — exe + `_internal` 폴더
- `dist/매출분석프로그램_배포.zip` — 배포용 압축 파일

직원 PC에서는 zip을 풀고 `매출분석프로그램.exe`를 더블클릭하면 됩니다. 자세한 안내는 `README_설치방법.txt` 참고.

exe 빌드 후 자동 테스트:

```bash
.venv\Scripts\python build_support\test_dist_full.py
```

## 데이터 저장

- SQLite `db.sqlite3`에 매출 원자료가 저장됩니다 (Git에 포함하지 마세요).
- **exe 실행 시** DB·로그·업로드 파일은 exe와 **같은 폴더**에 저장됩니다.
- 실제 시설 데이터는 **저장소에 올리지 않습니다**. `.gitignore`로 제외됩니다.

## Author

**madmadosa-cloud**

- GitHub: https://github.com/madmadosa-cloud
- Repository: https://github.com/madmadosa-cloud/sales-report

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file.

Third-party library notices: [NOTICE.md](NOTICE.md)
