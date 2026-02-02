# 🎨 시각화 도구 사용 가이드

## 개요

Neo4j 원가차이 분석 결과를 로컬 PC에서 시각적으로 확인할 수 있는 3가지 방법을 제공합니다.

---

## 🌐 방법 1: HTML 인터랙티브 리포트 (추천!)

### 특징
- ✅ **가장 빠름**: 한 번 생성하면 Neo4j 연결 없이 볼 수 있음
- ✅ **공유 용이**: HTML 파일을 이메일/USB로 공유 가능
- ✅ **인터랙티브**: Plotly 차트로 확대/축소/필터 가능
- ✅ **보고서용**: 인쇄/PDF 저장 가능

### 실행 방법

```bash
# 가상환경 활성화
venv\Scripts\activate

# HTML 리포트 생성
python visualization/generate_html_report.py
```

### 결과
- `variance_analysis_report.html` 파일이 생성됩니다
- 자동으로 기본 브라우저에서 열립니다
- 파일을 더블클릭해도 열 수 있습니다

### 포함된 차트
1. 📊 **원인코드별 원가차이** - 바 차트
2. 🥧 **원가요소별 비중** - 파이 차트
3. 🎯 **TOP 20 차이 큰 오더** - 수평 바 차트
4. 🏭 **작업장별 차이** - 바 차트
5. 🔴 **심각도별 분포** - 도넛 차트

### 장점
- 오프라인에서도 볼 수 있음
- 경영진 보고용으로 적합
- 파일 크기 작음 (~1MB)

---

## 📱 방법 2: Streamlit 대시보드 (최고 UX!)

### 특징
- ✅ **실시간 대화형**: 필터링, 정렬, 탐색 가능
- ✅ **프로페셔널**: 현대적인 UI/UX
- ✅ **데이터 새로고침**: 버튼 클릭으로 최신 데이터 로드
- ✅ **탭 구성**: 원인분석, 원가요소, 생산오더, 작업장

### 실행 방법

```bash
# 가상환경 활성화
venv\Scripts\activate

# Streamlit 대시보드 실행
streamlit run visualization/streamlit_dashboard.py
```

### 결과
- 자동으로 브라우저에서 `http://localhost:8501` 열림
- 실시간 인터랙티브 대시보드 표시
- 종료하려면 터미널에서 `Ctrl+C`

### 기능
- 🔄 **데이터 새로고침** 버튼
- 📊 **5개 요약 메트릭** (오더, 차이, 금액)
- 📑 **4개 탭**:
  1. 🔍 원인 분석 (바 차트 + 테이블)
  2. 📈 원가요소 (파이 + 바 차트)
  3. 🏭 생산오더 (TOP 20 차트 + 테이블)
  4. 👷 작업장 (차트 + 요약 통계)
- 🎨 **인터랙티브 차트**:
  - 확대/축소
  - 데이터 포인트 호버
  - 범례 클릭으로 필터링

### 장점
- 가장 세련된 UI
- 실시간 데이터 탐색
- 필터/정렬 기능
- 대시보드 느낌

### 주의사항
- Neo4j 연결 필요 (실시간 데이터 로드)
- 터미널 창을 닫으면 대시보드도 종료됨

---

## 📊 방법 3: Python 텍스트 리포트

### 특징
- ✅ **가장 단순**: 터미널에서 바로 확인
- ✅ **빠른 확인**: 요약 정보만 필요할 때

### 실행 방법

```bash
# 가상환경 활성화
venv\Scripts\activate

# 텍스트 리포트 출력
python analysis/run_analysis.py
```

### 결과
- 터미널에 텍스트로 출력
- 6개 섹션:
  1. 전체 요약
  2. 원인코드별 분석
  3. 원가요소별 분석
  4. 심각도별 분석
  5. TOP 10 오더
  6. 작업장별 분석

### 장점
- 추가 설치 불필요
- 빠른 실행
- 로그/파일로 저장 가능

---

## 🎯 어떤 방법을 선택할까?

| 상황 | 추천 방법 |
|------|----------|
| 경영진 보고서 작성 | 📄 HTML 리포트 |
| 일상적인 데이터 분석 | 📱 Streamlit 대시보드 |
| 빠른 확인 | 📊 Python 텍스트 |
| 오프라인 프레젠테이션 | 📄 HTML 리포트 |
| 실시간 탐색 | 📱 Streamlit 대시보드 |
| 파일 공유 필요 | 📄 HTML 리포트 |

---

## 💡 사용 팁

### HTML 리포트
```bash
# 여러 개 생성하고 비교
python visualization/generate_html_report.py
# 파일 이름 변경
move variance_analysis_report.html report_2024_02_01.html
```

### Streamlit 대시보드
```bash
# 다른 포트에서 실행 (8501이 사용 중일 때)
streamlit run visualization/streamlit_dashboard.py --server.port 8502

# 자동 새로고침 비활성화
streamlit run visualization/streamlit_dashboard.py --server.runOnSave false
```

### 텍스트 리포트를 파일로 저장
```bash
python analysis/run_analysis.py > report.txt
```

---

## 🔧 문제 해결

### "모듈을 찾을 수 없습니다" 오류
```bash
# 패키지 재설치
pip install -r requirements.txt
```

### Streamlit 실행 안됨
```bash
# Streamlit 설치 확인
pip install streamlit --upgrade
```

### HTML 파일이 안 열림
- 파일 탐색기에서 직접 더블클릭
- 또는 브라우저에 파일을 드래그 앤 드롭

### Neo4j 연결 오류
- `.env` 파일 확인
- `python neo4j/connection_test.py` 실행

---

## 📸 스크린샷

### HTML 리포트
- 아름다운 그라데이션 배경
- 5개 요약 카드
- 인터랙티브 Plotly 차트
- 프린트 친화적 레이아웃

### Streamlit 대시보드
- 현대적인 Material Design
- 사이드바 설정 패널
- 탭으로 구분된 분석
- 반응형 레이아웃

---

## 🚀 다음 단계

1. **Excel 리포트 추가**
   ```bash
   python visualization/generate_excel_report.py
   ```

2. **이메일 자동 발송**
   ```bash
   python visualization/email_report.py --to manager@company.com
   ```

3. **일정 자동 실행** (Windows 작업 스케줄러)
   - 매일 아침 8시 자동 리포트 생성

---

## 📞 지원

문제가 있거나 기능 추가가 필요하면:
1. `docs/PROJECT_COMPLETION.md` 참조
2. GitHub Issue 생성
3. README.md의 문의처 확인

---

**🎊 이제 Neo4j 분석 결과를 아름답게 시각화할 수 있습니다! 🎊**
