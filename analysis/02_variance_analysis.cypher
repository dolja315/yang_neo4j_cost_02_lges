// ============================================================
// Neo4j 원가차이 분석 쿼리 (실제 데이터 구조 반영)
// ============================================================

// ------------------------------------------------------------
// 1. 특정 생산오더의 원가차이 분석
// ------------------------------------------------------------
MATCH (po:ProductionOrder {id: 'PO-2024-001'})-[:HAS_VARIANCE]->(v:Variance)
MATCH (v)-[:CAUSED_BY]->(c:Cause)
RETURN 
  po.id as 생산오더,
  v.cost_element as 원가요소,
  v.variance_type as 차이유형,
  v.variance_amount as 차이금액,
  v.variance_percent as 차이율,
  v.severity as 심각도,
  c.code as 원인코드,
  c.description as 원인상세
ORDER BY abs(v.variance_amount) DESC;

// ------------------------------------------------------------
// 2. 원인코드별 원가차이 집계
// ------------------------------------------------------------
MATCH (v:Variance)-[:CAUSED_BY]->(c:Cause)
RETURN 
  c.code as 원인코드,
  c.category as 분류,
  c.description as 설명,
  c.responsible_dept as 책임부서,
  count(v) as 발생건수,
  sum(v.variance_amount) as 총차이금액,
  avg(v.variance_amount) as 평균차이금액,
  avg(v.variance_percent) as 평균차이율
ORDER BY abs(sum(v.variance_amount)) DESC;

// ------------------------------------------------------------
// 3. 원가요소별 차이 분석
// ------------------------------------------------------------
MATCH (v:Variance)
RETURN 
  v.cost_element as 원가요소,
  count(v) as 발생건수,
  sum(v.variance_amount) as 총차이금액,
  avg(v.variance_amount) as 평균차이금액,
  min(v.variance_amount) as 최소차이,
  max(v.variance_amount) as 최대차이
ORDER BY abs(sum(v.variance_amount)) DESC;

// ------------------------------------------------------------
// 4. 심각도별 차이 분석
// ------------------------------------------------------------
MATCH (v:Variance)
RETURN 
  v.severity as 심각도,
  count(v) as 발생건수,
  sum(v.variance_amount) as 총차이금액,
  avg(v.variance_percent) as 평균차이율
ORDER BY 
  CASE v.severity
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 4
    ELSE 5
  END;

// ------------------------------------------------------------
// 5. TOP 10 차이가 큰 생산오더
// ------------------------------------------------------------
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
WITH po, sum(v.variance_amount) as 총차이금액, count(v) as 차이건수
RETURN 
  po.id as 생산오더,
  po.product_id as 제품코드,
  po.quantity as 생산수량,
  po.status as 상태,
  총차이금액,
  차이건수
ORDER BY abs(총차이금액) DESC
LIMIT 10;

// ------------------------------------------------------------
// 6. 자재소비 vs 차이금액 연관 분석
// ------------------------------------------------------------
MATCH (po:ProductionOrder)-[:CONSUMES]->(m:Material)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance {cost_element: 'MATERIAL'})
RETURN 
  po.id as 생산오더,
  m.name as 자재명,
  m.type as 자재타입,
  v.variance_amount as 자재비차이,
  v.cause_code as 원인코드
ORDER BY abs(v.variance_amount) DESC
LIMIT 20;

// ------------------------------------------------------------
// 7. 작업장별 차이 분석
// ------------------------------------------------------------
MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
WHERE v.cost_element IN ['LABOR', 'OVERHEAD']
WITH wc, v
RETURN 
  wc.name as 작업장,
  wc.type as 작업장타입,
  count(v) as 차이건수,
  sum(v.variance_amount) as 총차이금액,
  avg(v.variance_percent) as 평균차이율
ORDER BY abs(sum(v.variance_amount)) DESC;

// ------------------------------------------------------------
// 8. 시계열 차이 추이 (월별)
// ------------------------------------------------------------
MATCH (v:Variance)
WITH 
  date(v.analysis_date).year as 연도,
  date(v.analysis_date).month as 월,
  v
RETURN 
  연도,
  월,
  count(v) as 차이건수,
  sum(v.variance_amount) as 총차이금액,
  avg(v.variance_amount) as 평균차이금액
ORDER BY 연도, 월;

// ------------------------------------------------------------
// 9. 복합 원인 분석 (같은 오더에서 여러 원인)
// ------------------------------------------------------------
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
WITH po, collect(DISTINCT c.code) as 원인들, sum(v.variance_amount) as 총차이
WHERE size(원인들) > 1
RETURN 
  po.id as 생산오더,
  원인들,
  size(원인들) as 원인개수,
  총차이
ORDER BY 원인개수 DESC, abs(총차이) DESC
LIMIT 20;

// ------------------------------------------------------------
// 10. 전체 요약 대시보드
// ------------------------------------------------------------
MATCH (po:ProductionOrder)
WITH count(po) as 총오더수
MATCH (v:Variance)
WITH 총오더수, count(v) as 총차이건수, sum(v.variance_amount) as 총차이금액
MATCH (v2:Variance)
WHERE v2.variance_amount > 0
WITH 총오더수, 총차이건수, 총차이금액, 
     count(v2) as 불리한차이건수, sum(v2.variance_amount) as 불리한차이금액
MATCH (v3:Variance)
WHERE v3.variance_amount < 0
RETURN 
  총오더수,
  총차이건수,
  총차이금액,
  불리한차이건수,
  불리한차이금액,
  count(v3) as 유리한차이건수,
  sum(v3.variance_amount) as 유리한차이금액;
