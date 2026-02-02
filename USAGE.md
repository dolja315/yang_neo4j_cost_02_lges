# Neo4j 원가차이 분석 시스템 사용 가이드

## 🚀 빠른 시작

### 1. 서버 실행
```bash
python visualization/graph_api_server.py
```

### 2. 브라우저 접속
```
http://localhost:5000
```

## 📁 핵심 파일

### HTML 화면 (3개)
- **`dashboard.html`** - 첫 화면 (대시보드 홈)
- **`variance_graph_dashboard_v3.html`** - 상세 분석 (메인 그래프 화면)
- **`comparison.html`** - 비교 분석

### 백엔드
- **`visualization/graph_api_server.py`** - Flask API 서버

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

---
**마지막 업데이트**: 2026-02-03
