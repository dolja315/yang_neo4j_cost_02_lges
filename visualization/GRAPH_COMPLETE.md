# 🎉 Neo4j 그래프 네트워크 시각화 완료!

## ✅ 완성!

**Neo4j의 노드와 엣지를 브라우저에서 인터랙티브하게 탐색**할 수 있는 도구가 완성되었습니다!

---

## 🚀 지금 바로 사용하기

### 1. 전체 그래프 보기 (이미 실행됨!)

```bash
python visualization/generate_graph_network.py
```

**결과**: `neo4j_graph_network.html` 파일이 브라우저에서 열렸습니다!

### 2. 다른 관점으로 보기

```bash
# 생산오더 중심
python visualization/generate_graph_network.py order

# 원가차이 원인 추적
python visualization/generate_graph_network.py variance

# 자재 소비 흐름
python visualization/generate_graph_network.py material
```

---

## 🎨 어떻게 보이나요?

브라우저에 열린 화면:

### 노드 (점)
- 🔴 **Product**: 제품 (QFP32, BGA144 등)
- 🔵 **Material**: 자재 (DIE, Substrate, Wire 등)
- 🟢 **ProductionOrder**: 생산오더 (PO-2024-001 등)
- 🟠 **WorkCenter**: 작업장 (Die Bonding Line 등)
- 🟡 **Variance**: 원가차이 (VAR-00001 등)
- 🟢 **Cause**: 원인코드 (OVERUSE, SUPPLIER_ISSUE 등)

### 엣지 (선)
- **PRODUCES**: 생산오더 → 제품
- **CONSUMES**: 생산오더 → 자재 (실제 소비)
- **USES_MATERIAL**: 제품 → 자재 (BOM)
- **WORKS_AT**: 생산오더 → 작업장
- **HAS_VARIANCE**: 생산오더 → 차이
- **CAUSED_BY**: 차이 → 원인

---

## 🖱️ 조작 방법

| 동작 | 효과 |
|------|------|
| **마우스 드래그** | 전체 그래프 이동 |
| **마우스 휠** | 확대/축소 |
| **노드 클릭** | 노드 선택 및 고정 |
| **노드 드래그** | 노드 위치 조정 |
| **노드 호버** | 상세 정보 팝업 |
| **엣지 호버** | 관계 정보 팝업 |
| **우측 버튼** | 네비게이션 컨트롤 |

---

## 💡 활용 예시

### 예시 1: 생산 프로세스 추적
1. **ProductionOrder** 노드(파란색 큰 점) 찾기
2. 클릭하면 연결된 엣지와 노드 확인:
   - PRODUCES → 어떤 제품을 생산?
   - CONSUMES → 어떤 자재를 소비?
   - WORKS_AT → 어떤 작업장에서?
   - HAS_VARIANCE → 차이 발생?

### 예시 2: 원가차이 원인 찾기
1. **Variance** 노드(연두색) 클릭
2. **CAUSED_BY** 엣지 따라가기
3. **Cause** 노드(노란색)에서 원인 확인:
   - OVERUSE (자재 초과 사용)
   - SUPPLIER_ISSUE (공급업체 문제)
   - GOLD_PRICE_UP (금 가격 상승)

### 예시 3: 자재 흐름 파악
1. **Material** 노드(하늘색) 선택
2. 연결 확인:
   - ← USES_MATERIAL: 어떤 제품의 BOM에 포함?
   - ← CONSUMES: 어떤 오더에서 소비?

---

## 📊 실제 데이터

### 현재 그래프
- **노드**: 99개
- **엣지**: 200개
- **관계 타입**: 6가지

### 포함된 데이터
- 생산오더: 100개
- 제품: 22종
- 자재: 50종
- 작업장: 10곳
- 원가차이: 298건
- 원인코드: 7개

---

## 🆚 3가지 시각화 도구 비교

| 도구 | 용도 | 실행 방법 |
|------|------|----------|
| **그래프 네트워크** | 노드-엣지 탐색 | `generate_graph_network.py` |
| **HTML 리포트** | 차트 분석 | `generate_html_report.py` |
| **Streamlit 대시보드** | 실시간 분석 | `streamlit run streamlit_dashboard.py` |

### 언제 어떤 도구를?

**그래프 네트워크 (지금 만든 것!)**
- ✅ 관계 구조 이해하고 싶을 때
- ✅ 특정 노드의 연결 확인
- ✅ 데이터 흐름 추적
- ✅ Neo4j Browser 없이 탐색

**HTML 리포트**
- ✅ 통계와 차트가 필요할 때
- ✅ 경영진 보고서
- ✅ 파일 공유 필요

**Streamlit 대시보드**
- ✅ 실시간 필터링/정렬
- ✅ 일상적인 모니터링
- ✅ 대화형 탐색

---

## 🎯 핵심 가치

### 1. 직관적 이해
- 복잡한 JOIN 쿼리 없이
- 눈으로 관계 확인
- 클릭으로 탐색

### 2. 오프라인 가능
- Neo4j Browser 불필요
- HTML 파일만으로 동작
- 인터넷 연결 불필요 (CDN 제외)

### 3. 쉬운 공유
- HTML 파일 전송
- 이메일 첨부
- USB 복사

---

## 📁 생성된 파일

```
yang_neo4j_cost_01/
├── neo4j_graph_network.html      ← 메인 그래프 (이미 열림!)
├── variance_analysis_report.html ← HTML 리포트
└── visualization/
    ├── generate_graph_network.py     ← 그래프 생성기 ⭐
    ├── generate_html_report.py       ← 리포트 생성기
    ├── streamlit_dashboard.py        ← 대시보드
    ├── GRAPH_NETWORK_GUIDE.md        ← 상세 가이드
    └── README.md                      ← 시각화 개요
```

---

## 🔥 고급 활용

### 커스텀 쿼리
특정 제품만 보고 싶다면 코드 수정:
```python
# generate_graph_network.py에서
query = """
    MATCH (p:Product {id: 'QFP80-004'})
    MATCH path = (p)-[*1..3]-(n)
    ...
"""
```

### 더 많은 노드
LIMIT 값 변경:
```python
LIMIT 200  →  LIMIT 500
```

### 특정 관계만
```python
# CONSUMES 관계만 보기
MATCH (po:ProductionOrder)-[r:CONSUMES]->(m:Material)
```

---

## 🎓 배운 것

1. **그래프 구조**: 노드와 엣지로 데이터 표현
2. **관계 탐색**: 클릭만으로 연결 확인
3. **시각적 분석**: 패턴을 눈으로 발견
4. **오프라인 활용**: HTML 파일로 독립 실행

---

## 📚 도움말

### 더 자세한 사용법
`visualization/GRAPH_NETWORK_GUIDE.md` 참조

### 문제 해결
- 그래프가 안 보이면 브라우저 새로고침
- 너무 느리면 노드 수 줄이기
- 색상 변경은 코드에서 `node_config` 수정

---

## 🎊 완성!

**이제 3가지 방법으로 Neo4j 데이터를 볼 수 있습니다:**

1. ✅ **그래프 네트워크** - 노드-엣지 탐색 (방금 만듦!)
2. ✅ **HTML 리포트** - 차트와 통계
3. ✅ **Streamlit 대시보드** - 실시간 대화형

**브라우저를 확인하세요!**
- `neo4j_graph_network.html` - 그래프 네트워크
- `variance_analysis_report.html` - 분석 리포트
- http://localhost:8501 - Streamlit 대시보드

---

**🎉 축하합니다! Neo4j를 완전히 시각화했습니다! 🎉**
