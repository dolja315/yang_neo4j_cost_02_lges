# Neo4j 원가차이 분석 시스템 사용 가이드

## 🚀 빠른 시작

### 1. 서버 실행
```bash
python visualization/graph_api_server.py
```

### 2. 브라우저 접속
```
http://localhost:8000
```

## 📁 핵심 파일

### HTML 화면
- **`new_dashboard.html`** - **(New)** 통합 대시보드
- **`dashboard.html`** - 기존 대시보드 홈
- **`variance_graph_dashboard_v3.html`** - 상세 분석
- **`comparison.html`** - 비교 분석

### 백엔드
- **`visualization/graph_api_server.py`** - Flask API 서버 (Port 8000)

## 🎯 주요 기능

### 상세 분석 화면 (variance_graph_dashboard_v3.html)

#### 1. 제품/원자재/공정 버튼으로 그래프 탐색
- **제품 탭**: 제품별 버튼 클릭 → 해당 제품 중심 그래프 표시
- **원자재 탭**: 원자재별 버튼 클릭 → 원자재 사용 상위 5개 오더 표시
- **공정 탭**: 공정별 버튼 클릭 → 공정 관련 상위 5개 오더 표시

#### 2. 생산오더별 차이 분석
- 왼쪽 하단: 수량차/단가차/생산량차 카테고리
- 각 카테고리 펼치기 → 생산오더 목록 확인
- 생산오더 클릭 → 오더 중심 그래프 표시

#### 3. 그래프 인터랙션
- **더블클릭**: 노드 확장 (연결된 노드 추가 표시)
- **초기화 버튼**: 처음 상태로 복원
- **포커스 버튼**: 선택한 노드 주변만 표시

## 🔧 성능 최적화

### 노드 수 제한
- 제품: 모든 관련 오더 표시
- 원자재/공정: **차이가 큰 상위 5개 오더만** 표시
- 30개 이상 노드: 물리 엔진 자동 비활성화

## 📊 데이터 구조

```
Product (제품)
  ← PRODUCES ← ProductionOrder (생산오더)
                 → HAS_VARIANCE → Variance (차이)
                 → CONSUMES → Material (원자재)
                 → WORKS_AT → WorkCenter (공정)
```

## ⚡ 문제 해결

### 화면이 느려지는 경우
- 원자재/공정 버튼 대신 **제품 버튼** 사용 권장
- 브라우저 새로고침: `Ctrl + Shift + R` (캐시 삭제)

### 그래프가 안 나오는 경우
1. Flask 서버 재시작
2. 브라우저 콘솔(F12) 확인
3. API 엔드포인트 확인: `http://localhost:5000/api/filters`

## 📝 개발 히스토리

- ~~analysis.html~~ → variance_graph_dashboard_v3.html로 통합
- 드롭박스 방식 → **버튼 방식**으로 개선
- 노드 수 제한으로 성능 최적화

## 🌟 통합 대시보드 (new_dashboard.html)

**주소:** `http://localhost:8000/`

새로운 통합 대시보드는 3개의 탭으로 구성됩니다.

### 1. 📊 Dashboard
기존 `dashboard.html`을 통합하여 보여줍니다.

### 2. 🔥 Process Monitoring
- **Process Status Heatmap**: 공정별 위험도를 시각적으로 표시합니다.
- **Drill-down**: 공정 박스를 클릭하면 우측 Drawer에서 세부 분석을 볼 수 있습니다.
- **Cost Breakdown (Waterfall)**:
    - 우측 Drawer에서 **생산오더를 선택**하여 계획 원가 대비 실제 원가 차이를 Waterfall 차트로 분석할 수 있습니다.
    - 드롭다운 목록에서 상위 차이 발생 오더를 선택하세요.

### 3. 🕸️ Graph Explorer
- 전체 그래프를 탐색할 수 있는 전체 화면 모드입니다.
- 검색 기능을 통해 특정 생산오더나 Variance ID를 찾을 수 있습니다.

## 💾 SK Hynix V2 Data Generation

새로운 데이터셋(V2)을 생성하고 로드하려면 다음 단계를 따르십시오.

### 1. 데이터 생성
```bash
python generate_data_skhynix_v2.py
```
이 스크립트는 `data/neo4j_import/` 디렉토리에 CSV 파일들을 생성합니다. (Master Data, Transaction Data, Relationships)

### 2. Neo4j 데이터 로드
```bash
python upload_skhynix_v2.py
```
이 스크립트는 기존 데이터를 삭제하고, 생성된 CSV 파일을 Neo4j 데이터베이스에 로드합니다.
이 스크립트는 Python Driver를 사용하여 CSV를 직접 읽어 로드하므로, Neo4j 서버의 파일 접근 제한(LOAD CSV)을 우회할 수 있습니다.
**.env 파일 설정이 필요합니다.** (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

### 3. 대시보드 확인
서버를 재시작한 후 `http://localhost:8000/`에서 'Process Monitoring' 탭을 확인하십시오.

---
**마지막 업데이트**: 2026-02-05
