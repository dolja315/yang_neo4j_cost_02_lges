# 🕸️ Neo4j 그래프 네트워크 시각화 가이드

## 개요

Neo4j Browser처럼 **노드와 엣지를 인터랙티브하게 탐색**할 수 있는 시각화 도구입니다!

---

## 🚀 빠른 시작

### 기본 사용법

```bash
# 가상환경 활성화
venv\Scripts\activate

# 전체 그래프 보기
python visualization/generate_graph_network.py

# 생산오더 중심 그래프
python visualization/generate_graph_network.py order

# 원가차이 원인 추적 그래프
python visualization/generate_graph_network.py variance

# 자재 소비 그래프
python visualization/generate_graph_network.py material
```

---

## 📊 생성되는 그래프 종류

### 1. 전체 그래프 (기본)
```bash
python visualization/generate_graph_network.py
```
- **내용**: 모든 노드 타입과 관계
- **노드 수**: 약 100개
- **엣지 수**: 200개
- **용도**: 전체 구조 파악

### 2. ProductionOrder 중심 그래프
```bash
python visualization/generate_graph_network.py order
```
- **내용**: 생산오더를 중심으로 2홉 이내 연결
- **포함**: ProductionOrder → Product, Material, WorkCenter, Variance
- **용도**: 생산 프로세스 흐름 확인

### 3. Variance 원인 추적 그래프
```bash
python visualization/generate_graph_network.py variance
```
- **내용**: 원가차이를 중심으로 원인 추적
- **포함**: Variance → Cause, ProductionOrder
- **용도**: 차이 원인 분석

### 4. Material 소비 그래프
```bash
python visualization/generate_graph_network.py material
```
- **내용**: 자재를 중심으로 소비 관계
- **포함**: Material → ProductionOrder, Product (BOM)
- **용도**: 자재 흐름 파악

---

## 🎨 그래프 사용법

### 기본 조작

| 동작 | 설명 |
|------|------|
| 🖱️ **마우스 드래그** | 캔버스 이동 (패닝) |
| 🔍 **마우스 휠** | 확대/축소 (줌) |
| 👆 **노드 클릭** | 노드 선택 및 고정 |
| 🖱️ **노드 드래그** | 노드 위치 이동 |
| 📋 **노드 호버** | 상세 정보 표시 |
| ⌨️ **화살표 키** | 캔버스 이동 |

### 우측 하단 네비게이션 버튼

- 🔼 🔽 ◀️ ▶️ : 방향 이동
- 🔍+ : 확대
- 🔍- : 축소
- 🎯 : 전체 보기 (Fit to View)

---

## 🎨 노드 색상 가이드

- 🔴 **Product** (제품) - #FF6B6B
- 🔵 **Material** (자재) - #4ECDC4
- 🟢 **ProductionOrder** (생산오더) - #45B7D1
- 🟠 **WorkCenter** (작업장) - #FFA07A
- 🟡 **Variance** (차이) - #98D8C8
- 🟢 **Cause** (원인) - #F7DC6F

### 엣지 색상

- 🔴 **USES_MATERIAL** (BOM)
- 🔵 **PRODUCES** (생산)
- 🟢 **CONSUMES** (소비)
- 🟠 **WORKS_AT** (작업)
- 🟡 **HAS_VARIANCE** (차이)
- 🟢 **CAUSED_BY** (원인)

---

## 💡 활용 시나리오

### 시나리오 1: 생산 프로세스 이해하기
1. ProductionOrder 중심 그래프 생성
   ```bash
   python visualization/generate_graph_network.py order
   ```
2. 생산오더 노드(파란색) 클릭
3. 연결된 엣지 확인:
   - PRODUCES → Product (어떤 제품?)
   - CONSUMES → Material (어떤 자재?)
   - WORKS_AT → WorkCenter (어떤 작업장?)
   - HAS_VARIANCE → Variance (차이 발생?)

### 시나리오 2: 원가차이 원인 추적
1. Variance 그래프 생성
   ```bash
   python visualization/generate_graph_network.py variance
   ```
2. Variance 노드(연두색) 클릭
3. CAUSED_BY 엣지 따라가기
4. Cause 노드(노란색)에서 원인 확인

### 시나리오 3: 자재 소비 패턴 파악
1. Material 그래프 생성
   ```bash
   python visualization/generate_graph_network.py material
   ```
2. Material 노드(하늘색) 선택
3. CONSUMES 엣지로 연결된 생산오더 확인
4. USES_MATERIAL 엣지로 BOM 관계 확인

---

## 🔍 상세 정보 보기

### 노드 정보
노드 위에 마우스를 올리면 팝업 표시:
```
ProductionOrder
id: PO-2024-001
product_cd: QFP80-004
planned_qty: 2500
actual_qty: 2580
good_qty: 2500
scrap_qty: 80
status: CLOSED
yield_rate: 96.9
```

### 엣지 정보
엣지 위에 마우스를 올리면 관계 정보 표시:
```
CONSUMES
planned_qty: 1000
actual_qty: 1050
unit: EA
```

---

## 🎯 성능 최적화

### 대용량 그래프 처리
현재 기본 제한: 200개 엣지

더 많은 데이터를 보려면 코드 수정:
```python
# visualization/generate_graph_network.py 53번째 줄
LIMIT 200  →  LIMIT 500
```

⚠️ 주의: 너무 많은 노드는 브라우저를 느리게 만들 수 있습니다!

---

## 📸 예상 화면

```
┌─────────────────────────────────────────────┐
│  Neo4j 전체 그래프 샘플           [⚙️설정]  │
├─────────────────────────────────────────────┤
│                                             │
│      🔴(Product)                           │
│         ↓ PRODUCES                         │
│      🟢(ProductionOrder) ─CONSUMES─→ 🔵(Material)
│         ↓ HAS_VARIANCE                     │
│      🟡(Variance)                          │
│         ↓ CAUSED_BY                        │
│      🟢(Cause)                             │
│                                             │
│                     [🔼] [🔽]              │
│                     [◀️] [▶️]              │
│                     [🔍+] [🔍-] [🎯]       │
└─────────────────────────────────────────────┘
```

---

## 🆚 Neo4j Browser vs 이 도구

| 기능 | Neo4j Browser | 이 도구 |
|------|--------------|---------|
| 온라인 필요 | ✅ 필요 | ❌ 오프라인 가능 |
| 커스텀 쿼리 | ✅ 가능 | ⚠️ 코드 수정 필요 |
| 시각화 | ✅ 우수 | ✅ 우수 |
| 공유 | ⚠️ 스크린샷만 | ✅ HTML 파일 |
| 속도 | ⚠️ 네트워크 의존 | ✅ 로컬 빠름 |
| 편의성 | ✅ GUI | ⚠️ CLI |

---

## 🔧 고급 사용법

### 커스텀 쿼리 만들기

`visualization/generate_graph_network.py` 파일 수정:

```python
# 특정 제품의 차이만 보기
query = """
    MATCH (p:Product {id: 'QFP80-004'})
    MATCH path = (p)-[*1..3]-(n)
    UNWIND relationships(path) as r
    RETURN startNode(r) as n1, r, endNode(r) as n2
    LIMIT 200
"""
```

### 다른 파일명으로 저장

```python
output_file = create_network_visualization(
    nodes, edges, 
    output_file='my_custom_graph.html',
    title='커스텀 그래프'
)
```

---

## 📦 생성된 파일

- `neo4j_graph_network.html` - 인터랙티브 HTML
- 파일 크기: 약 500KB ~ 2MB
- 의존성: 없음 (standalone)
- 공유: 이메일/USB로 전달 가능

---

## 💻 시스템 요구사항

- **브라우저**: Chrome, Edge, Firefox (최신 버전)
- **메모리**: 최소 4GB RAM
- **네트워크**: 오프라인 가능 (CDN 제외)

---

## 🐛 문제 해결

### 그래프가 안 보여요
- 브라우저 콘솔 확인 (F12)
- 팝업 차단 해제
- 다른 브라우저로 시도

### 노드가 너무 많아요
- 쿼리 LIMIT 값 줄이기
- 특정 노드 타입만 선택

### 느려요
- 노드 수 < 500개 권장
- Physics 끄기 (코드에서 `"enabled": false`)

---

## 🎓 배운 내용

1. **그래프 DB의 구조**: 노드와 엣지로 연결된 네트워크
2. **관계의 시각화**: 복잡한 관계를 한눈에 파악
3. **탐색적 분석**: 클릭과 호버로 데이터 탐색
4. **오프라인 공유**: HTML 파일로 쉬운 공유

---

## 📚 참고 자료

- **PyVis 문서**: https://pyvis.readthedocs.io/
- **Neo4j Browser**: https://neo4j.com/developer/neo4j-browser/
- **NetworkX**: https://networkx.org/

---

**🎉 이제 Neo4j의 노드와 엣지를 마음껏 탐색하세요! 🕸️**

브라우저에서 `neo4j_graph_network.html` 파일을 열고 확인해보세요!
