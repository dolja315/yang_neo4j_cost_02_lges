# 원가차이 그래프 탐색 대시보드

Neo4j GraphDB를 활용한 인터랙티브 원가차이 분석 시스템

## 🎯 주요 기능

### 1. 정적 대시보드 (variance_dashboard.html)
- ✅ 원가차이 요약 및 통계
- ✅ Plotly 기반 인터랙티브 차트
- ✅ TreeMap, Sunburst, Bar 차트
- ✅ 브라우저만으로 즉시 사용 가능

### 2. 그래프 탐색 대시보드 (variance_graph_dashboard.html)
- ✅ vis.js 기반 네트워크 그래프
- ✅ 노드 클릭 & 드릴다운
- ✅ 시뮬레이션 데이터로 즉시 체험
- ✅ 오프라인 사용 가능

### 3. **실시간 GraphDB 탐색 시스템** ⭐ (API 기반)
- ✅ Neo4j 실시간 쿼리
- ✅ 동적 노드 확장
- ✅ 관계 기반 드릴다운
- ✅ 원인 추적 및 영향 분석

---

## 🚀 빠른 시작

### 방법 1: 정적 대시보드 (가장 간단)

```bash
# 1. 대시보드 생성
$env:PYTHONIOENCODING="utf-8"
python visualization/create_variance_dashboard.py

# 2. 브라우저에서 variance_dashboard.html 열기
```

### 방법 2: GraphDB 실시간 탐색 (추천!)

#### Step 1: API 서버 실행

```bash
# 터미널 1
cd c:\Users\jaehoyang\github\yang_neo4j_cost_01
.\venv\Scripts\activate
$env:PYTHONIOENCODING="utf-8"
python visualization/graph_api_server.py
```

서버가 실행되면:
```
🚀 서버 시작...
📍 주소: http://localhost:5000

📡 사용 가능한 API:
  GET /api/variance/<id>/graph - Variance 중심 그래프
  GET /api/cause/<code>/graph - Cause 중심 그래프
  GET /api/node/<id>/expand - 노드 확장
  GET /api/overview - 전체 개요
  GET /api/summary - 요약 통계

💡 브라우저에서 http://localhost:5000 접속
```

#### Step 2: 브라우저에서 접속

```
http://localhost:5000
```

또는 HTML 파일 직접 열기:
```
variance_graph_dashboard_api.html
```

---

## 📊 사용 방법

### 1. 전체 개요에서 시작

- **왼쪽 사이드바**: 원가요소별 요약
- **그래프 영역**: 전체 구조 시각화
- **범례**: 노드 타입 확인

### 2. 드릴다운 분석

#### 방법 A: 사이드바에서 선택
```
왼쪽 "주요 차이 항목" → 항목 클릭
→ Neo4j에서 실시간으로 관련 그래프 조회
```

#### 방법 B: 그래프에서 탐색
```
노드 클릭 → "선택 노드 확장" 버튼
→ 연결된 모든 노드 표시
```

#### 방법 C: 빠른 확장
```
노드 더블클릭 → 즉시 확장
```

### 3. 원인 추적

```
"주요 원인" 섹션 → 원인 클릭
→ 해당 원인으로 발생한 모든 차이 표시
→ 영향 범위 파악
```

---

## 🔍 API 엔드포인트

### GET /api/variance/{variance_id}/graph
특정 Variance를 중심으로 관련 노드들 조회

**응답 예시:**
```json
{
  "nodes": [
    {
      "id": "4:...:160",
      "label": "VAR-00001",
      "type": "Variance",
      "color": "#98D8C8",
      "properties": {...}
    }
  ],
  "edges": [...]
}
```

### GET /api/cause/{cause_code}/graph
특정 Cause와 관련된 Variance들 조회

### GET /api/node/{element_id}/expand
노드를 확장하여 직접 연결된 노드들 조회

### GET /api/overview
전체 그래프 개요 (샘플링)

### GET /api/summary
원가차이 요약 통계

---

## 🎨 노드 타입 및 색상

| 타입 | 색상 | 설명 |
|------|------|------|
| **Variance** | 🟢 #98D8C8 | 원가차이 |
| **ProductionOrder** | 🔵 #45B7D1 | 생산오더 |
| **Material** | 🟦 #4ECDC4 | 자재 |
| **WorkCenter** | 🟠 #FFA07A | 작업장 |
| **Cause** | 🟡 #F7DC6F | 원인 |
| **Product** | 🔴 #FF6B6B | 제품 |

---

## 💡 분석 시나리오

### 시나리오 1: 자재 가격 차이 분석

1. 사이드바에서 **MATERIAL - PRICE** 차이 클릭
2. 그래프에서 차이가 큰 항목 확인
3. ProductionOrder 노드 더블클릭 → 사용된 자재 확인
4. Material 노드 더블클릭 → 어떤 오더들이 사용했는지 확인
5. Cause 노드 확인 → "공급업체 이슈" 등의 원인 파악

### 시나리오 2: 원인별 영향 분석

1. "주요 원인" 섹션에서 **SUPPLIER_ISSUE** 클릭
2. 해당 원인으로 발생한 모든 Variance 표시
3. 영향받은 ProductionOrder 확인
4. 총 영향액 계산 (차이 금액 합계)

### 시나리오 3: 생산오더 추적

1. 특정 차이 항목 선택
2. ProductionOrder 노드 확장
3. 해당 오더의 자재 소비 (CONSUMES) 확인
4. 작업장 사용 (WORKS_AT) 확인
5. 생산된 제품 (PRODUCES) 확인
6. 전체 원가 흐름 이해

---

## 🛠️ 트러블슈팅

### 문제 1: API 서버 연결 안 됨

**증상:** 상단에 "연결 끊김" 표시

**해결:**
```bash
# 1. API 서버가 실행 중인지 확인
# 터미널에 "Running on http://0.0.0.0:5000" 메시지 있는지 확인

# 2. 포트 충돌 확인
netstat -ano | findstr :5000

# 3. 서버 재시작
python visualization/graph_api_server.py
```

### 문제 2: 그래프가 표시되지 않음

**해결:**
1. 브라우저 콘솔 확인 (F12)
2. CORS 오류 → Flask-CORS 설치 확인
3. 네트워크 오류 → Neo4j 연결 확인

### 문제 3: 노드 확장이 느림

**원인:** Neo4j 쿼리 성능

**해결:**
1. Neo4j 인덱스 확인
2. 쿼리에 LIMIT 적용
3. 샘플링 범위 조정

---

## 📦 파일 구조

```
visualization/
├── create_variance_dashboard.py          # 정적 대시보드 생성기
├── create_interactive_graph_dashboard.py # 그래프 탐색 생성기
├── graph_api_server.py                   # Flask API 서버 ⭐
├── variance_dashboard.html               # 정적 차트 대시보드
├── variance_graph_dashboard.html         # 시뮬레이션 그래프
└── variance_graph_dashboard_api.html     # API 연동 그래프 ⭐
```

---

## 🎓 GraphDB 활용 포인트

### 전통적인 분석 vs GraphDB 분석

**전통적인 방법 (SQL)**
```sql
-- 여러 번의 JOIN 필요
SELECT v.*, po.*, m.*, c.*
FROM variances v
JOIN production_orders po ON v.order_no = po.id
JOIN material_consumption mc ON po.id = mc.order_id
JOIN materials m ON mc.material_id = m.id
JOIN variance_causes vc ON v.id = vc.variance_id
JOIN causes c ON vc.cause_id = c.id
WHERE v.id = 'VAR-00001'
```

**GraphDB 방법 (Cypher)**
```cypher
-- 관계를 따라가기만 하면 됨!
MATCH (v:Variance {id: 'VAR-00001'})
MATCH path = (v)-[*1..3]-(related)
RETURN path
```

### GraphDB의 장점

1. **직관적 탐색**: 클릭만으로 관계 추적
2. **유연한 깊이**: 필요한 만큼 확장
3. **패턴 발견**: 숨겨진 관계 발견
4. **빠른 조회**: 인접 노드 조회가 O(1)

---

## 🚀 다음 단계

### 추가 기능 아이디어

1. **경로 분석**
   - 차이 → 원인까지의 최단 경로
   - 영향도가 큰 경로 하이라이트

2. **패턴 인식**
   - 비슷한 패턴의 차이 그룹화
   - 반복되는 원인 탐지

3. **시계열 분석**
   - 시간에 따른 그래프 변화
   - 트렌드 시각화

4. **추천 시스템**
   - "이 차이를 분석한 사용자는 다음도 봤습니다"
   - GraphDB 기반 협업 필터링

---

## 📞 지원

문제가 있거나 개선 아이디어가 있으면:
1. GitHub Issues
2. 프로젝트 문서 참조
3. Neo4j 커뮤니티 포럼

---

**Happy Graph Exploring! 🚀**
