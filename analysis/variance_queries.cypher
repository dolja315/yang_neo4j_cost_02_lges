-- ============================================================
-- Neo4j 차이분석 Cypher 쿼리 모음
-- ============================================================

-- ============================================================
-- 1. 기본 조회 쿼리
-- ============================================================

-- 1.1 전체 데이터 개요
MATCH (n)
RETURN labels(n)[0] as NodeType, COUNT(n) as Count
ORDER BY Count DESC;

-- 1.2 전체 관계 개요
MATCH ()-[r]->()
RETURN type(r) as RelationshipType, COUNT(r) as Count
ORDER BY Count DESC;

-- 1.3 특정 생산오더의 전체 구조 시각화
MATCH path = (po:ProductionOrder {id: 'PO-2024-001'})-[*1..2]-()
RETURN path
LIMIT 50;

-- ============================================================
-- 2. 제품 및 BOM 분석
-- ============================================================

-- 2.1 제품별 자재 구성 (BOM) 조회
MATCH (p:Product {id: 'QFP64-001'})-[r:USES_MATERIAL]->(m:Material)
RETURN p.name as Product,
       m.name as Material,
       m.type as MaterialType,
       r.quantity as Quantity,
       r.unit as Unit,
       m.standard_price as UnitPrice,
       r.quantity * m.standard_price as TotalCost
ORDER BY TotalCost DESC;

-- 2.2 특정 자재를 사용하는 모든 제품
MATCH (p:Product)-[r:USES_MATERIAL]->(m:Material {type: 'WIRE'})
RETURN p.name as Product,
       p.type as PackageType,
       m.name as GoldWire,
       r.quantity as UsageInMg,
       r.quantity * m.standard_price as WireCost
ORDER BY WireCost DESC;

-- 2.3 제품 타입별 평균 원가
MATCH (p:Product)
RETURN p.type as PackageType,
       COUNT(p) as ProductCount,
       AVG(p.standard_cost) as AvgCost,
       MIN(p.standard_cost) as MinCost,
       MAX(p.standard_cost) as MaxCost
ORDER BY AvgCost DESC;

-- ============================================================
-- 3. 생산 실적 분석
-- ============================================================

-- 3.1 월별 생산 현황
MATCH (po:ProductionOrder)
WITH po, date(po.order_date) as order_date
RETURN 
    date.truncate('month', order_date) as Month,
    COUNT(po) as OrderCount,
    SUM(po.planned_qty) as TotalPlannedQty,
    SUM(po.good_qty) as TotalGoodQty,
    SUM(po.scrap_qty) as TotalScrapQty,
    ROUND(100.0 * SUM(po.good_qty) / SUM(po.planned_qty), 2) as AvgYieldRate
ORDER BY Month;

-- 3.2 제품 타입별 수율 분석
MATCH (po:ProductionOrder)-[:PRODUCES]->(p:Product)
RETURN 
    p.type as PackageType,
    COUNT(po) as OrderCount,
    AVG(po.yield_rate) as AvgYield,
    MIN(po.yield_rate) as MinYield,
    MAX(po.yield_rate) as MaxYield
ORDER BY AvgYield DESC;

-- 3.3 수율이 낮은 오더 Top 10
MATCH (po:ProductionOrder)-[:PRODUCES]->(p:Product)
RETURN 
    po.id as OrderNo,
    p.name as Product,
    po.planned_qty as Planned,
    po.good_qty as Good,
    po.scrap_qty as Scrap,
    po.yield_rate as YieldRate
ORDER BY YieldRate ASC
LIMIT 10;

-- ============================================================
-- 4. 원가차이 분석
-- ============================================================

-- 4.1 전체 차이 요약
MATCH (v:Variance)
RETURN 
    v.cost_element as CostElement,
    COUNT(v) as VarianceCount,
    SUM(v.variance_amount) as TotalVariance,
    AVG(v.variance_amount) as AvgVariance,
    AVG(v.variance_percent) as AvgVariancePercent
ORDER BY TotalVariance DESC;

-- 4.2 차이 유형별 분석
MATCH (v:Variance)
RETURN 
    v.variance_type as VarianceType,
    v.cost_element as CostElement,
    COUNT(v) as Count,
    SUM(v.variance_amount) as TotalAmount,
    AVG(ABS(v.variance_percent)) as AvgPercentage
ORDER BY TotalAmount DESC;

-- 4.3 심각도별 차이 분포
MATCH (v:Variance)
RETURN 
    v.severity as Severity,
    COUNT(v) as Count,
    SUM(v.variance_amount) as TotalAmount,
    AVG(ABS(v.variance_amount)) as AvgAmount
ORDER BY 
    CASE v.severity
        WHEN 'HIGH' THEN 1
        WHEN 'MEDIUM' THEN 2
        WHEN 'LOW' THEN 3
    END;

-- 4.4 차이 금액이 큰 오더 Top 10
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
WITH po, SUM(v.variance_amount) as TotalVariance
MATCH (po)-[:PRODUCES]->(p:Product)
RETURN 
    po.id as OrderNo,
    p.name as Product,
    po.order_date as OrderDate,
    TotalVariance as TotalVariance
ORDER BY ABS(TotalVariance) DESC
LIMIT 10;

-- ============================================================
-- 5. 차이 원인 분석 (Neo4j의 강점!)
-- ============================================================

-- 5.1 특정 오더의 차이 원인 추적
MATCH path = (po:ProductionOrder {id: 'PO-2024-001'})
             -[:HAS_VARIANCE]->(v:Variance)
             -[:CAUSED_BY]->(c:Cause)
RETURN 
    po.id as OrderNo,
    v.cost_element as CostElement,
    v.variance_type as VarianceType,
    v.variance_amount as Amount,
    c.description as Cause,
    c.responsible_dept as ResponsibleDept
ORDER BY ABS(v.variance_amount) DESC;

-- 5.2 재료비 차이의 근본 원인 추적 (자재까지)
MATCH (v:Variance {cost_element: 'MATERIAL'})<-[:HAS_VARIANCE]-(po:ProductionOrder)
MATCH (v)-[:CAUSED_BY]->(c:Cause)
MATCH (v)-[:RELATED_TO_MATERIAL]->(m:Material)
WHERE v.variance_amount > 1000
RETURN 
    po.id as OrderNo,
    v.variance_amount as VarianceAmount,
    m.name as Material,
    m.type as MaterialType,
    c.description as Cause
ORDER BY v.variance_amount DESC
LIMIT 20;

-- 5.3 금선 가격 상승의 영향 분석
MATCH (c:Cause {code: 'GOLD_PRICE_UP'})<-[:CAUSED_BY]-(v:Variance)
MATCH (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)-[:PRODUCES]->(p:Product)
RETURN 
    p.name as Product,
    COUNT(po) as AffectedOrders,
    SUM(v.variance_amount) as TotalImpact,
    AVG(v.variance_amount) as AvgImpact
ORDER BY TotalImpact DESC;

-- 5.4 공통 원인이 미치는 영향 범위
MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)<-[:HAS_VARIANCE]-(po:ProductionOrder)
MATCH (po)-[:PRODUCES]->(p:Product)
WITH c, COUNT(DISTINCT po) as AffectedOrders, 
     COUNT(DISTINCT p) as AffectedProducts,
     SUM(v.variance_amount) as TotalImpact
WHERE AffectedOrders >= 3
RETURN 
    c.code as CauseCode,
    c.description as Description,
    c.category as Category,
    AffectedOrders,
    AffectedProducts,
    TotalImpact
ORDER BY TotalImpact DESC;

-- ============================================================
-- 6. 패턴 분석 (그래프의 강력한 기능!)
-- ============================================================

-- 6.1 유사한 차이 패턴 발견 (동일 제품, 유사한 차이)
MATCH (po1:ProductionOrder)-[:PRODUCES]->(p:Product)<-[:PRODUCES]-(po2:ProductionOrder)
MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
WHERE po1.id < po2.id
  AND v1.variance_type = v2.variance_type
  AND v1.cost_element = v2.cost_element
  AND ABS(v1.variance_amount - v2.variance_amount) < 500
RETURN 
    po1.id as Order1,
    po2.id as Order2,
    p.name as Product,
    v1.variance_type as VarianceType,
    v1.variance_amount as Amount1,
    v2.variance_amount as Amount2,
    ABS(v1.variance_amount - v2.variance_amount) as Difference
ORDER BY Difference
LIMIT 10;

-- 6.2 반복되는 문제 패턴 (동일 원인, 여러 오더)
MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)<-[:HAS_VARIANCE]-(po:ProductionOrder)
WITH c, COLLECT(DISTINCT po.id) as Orders, COUNT(DISTINCT po) as Frequency
WHERE Frequency >= 5
MATCH (c)<-[:CAUSED_BY]-(v:Variance)
RETURN 
    c.code as CauseCode,
    c.description as Description,
    Frequency as OccurrenceCount,
    Orders[0..5] as SampleOrders,
    SUM(v.variance_amount) as TotalImpact
ORDER BY Frequency DESC;

-- 6.3 연쇄 문제 발견 (시계열 패턴)
MATCH (po1:ProductionOrder)-[:NEXT_ORDER]->(po2:ProductionOrder)
MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
WHERE v1.variance_type = v2.variance_type
  AND v1.cost_element = v2.cost_element
RETURN 
    po1.id as FirstOrder,
    po2.id as NextOrder,
    v1.variance_type as VarianceType,
    v1.variance_amount as FirstAmount,
    v2.variance_amount as NextAmount,
    CASE 
        WHEN v2.variance_amount > v1.variance_amount THEN '악화'
        WHEN v2.variance_amount < v1.variance_amount THEN '개선'
        ELSE '유지'
    END as Trend
ORDER BY ABS(v2.variance_amount - v1.variance_amount) DESC
LIMIT 20;

-- ============================================================
-- 7. 영향 범위 분석 (다단계 관계 추적)
-- ============================================================

-- 7.1 특정 자재 가격 변동의 전체 영향
MATCH (m:Material {type: 'WIRE'})<-[:USES_MATERIAL]-(p:Product)
MATCH (p)<-[:PRODUCES]-(po:ProductionOrder)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance {cost_element: 'MATERIAL'})
RETURN 
    m.name as Material,
    COUNT(DISTINCT p) as AffectedProducts,
    COUNT(DISTINCT po) as AffectedOrders,
    SUM(v.variance_amount) as TotalVariance
ORDER BY TotalVariance DESC;

-- 7.2 작업장별 차이 분석
MATCH (wc:WorkCenter)<-[:WORKS_AT]-(po:ProductionOrder)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
WHERE v.cost_element IN ['LABOR', 'OVERHEAD']
RETURN 
    wc.name as WorkCenter,
    wc.process_type as ProcessType,
    COUNT(po) as OrderCount,
    SUM(v.variance_amount) as TotalVariance,
    AVG(v.variance_amount) as AvgVariance
ORDER BY TotalVariance DESC;

-- 7.3 제품 복잡도와 차이의 상관관계
MATCH (p:Product)
MATCH (p)<-[:PRODUCES]-(po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
WITH p, COUNT(po) as OrderCount, AVG(ABS(v.variance_amount)) as AvgVariance
MATCH (p)-[:USES_MATERIAL]->()
WITH p, COUNT(*) as MaterialCount, OrderCount, AvgVariance
RETURN 
    p.type as PackageType,
    AVG(p.pins) as AvgPins,
    AVG(MaterialCount) as AvgMaterialCount,
    AVG(AvgVariance) as AvgVarianceAmount
ORDER BY AvgVarianceAmount DESC;

-- ============================================================
-- 8. 예측 및 시뮬레이션
-- ============================================================

-- 8.1 과거 패턴 기반 위험 제품 예측
MATCH (p:Product)<-[:PRODUCES]-(po:ProductionOrder)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
WITH p, 
     COUNT(po) as TotalOrders,
     COUNT(v) as VarianceCount,
     AVG(ABS(v.variance_amount)) as AvgVariance
WHERE TotalOrders >= 3
RETURN 
    p.id as ProductCode,
    p.name as ProductName,
    TotalOrders,
    VarianceCount,
    ROUND(100.0 * VarianceCount / TotalOrders, 2) as VarianceRate,
    ROUND(AvgVariance, 2) as AvgVarianceAmount,
    CASE 
        WHEN 100.0 * VarianceCount / TotalOrders > 80 THEN '높음'
        WHEN 100.0 * VarianceCount / TotalOrders > 50 THEN '중간'
        ELSE '낮음'
    END as RiskLevel
ORDER BY VarianceRate DESC, AvgVariance DESC;

-- 8.2 공급업체별 품질 이슈 분석
MATCH (m:Material)<-[:CONSUMES]-(po:ProductionOrder)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance {cost_element: 'MATERIAL'})
WITH m.supplier_cd as Supplier, 
     COUNT(DISTINCT po) as Orders,
     SUM(v.variance_amount) as TotalVariance
WHERE TotalVariance > 0
RETURN 
    Supplier,
    Orders,
    TotalVariance,
    ROUND(TotalVariance / Orders, 2) as AvgVariancePerOrder
ORDER BY TotalVariance DESC;

-- ============================================================
-- 9. 성능 비교용 복잡 쿼리
-- ============================================================

-- 9.1 전체 원가 흐름 추적 (RDB에서는 8개 테이블 JOIN!)
MATCH (po:ProductionOrder {id: 'PO-2024-001'})
MATCH (po)-[:PRODUCES]->(p:Product)
MATCH (p)-[:USES_MATERIAL]->(m:Material)
OPTIONAL MATCH (po)-[:CONSUMES]->(m)
OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
RETURN 
    po.id as OrderNo,
    p.name as Product,
    m.name as Material,
    m.type as MaterialType,
    m.standard_price as StandardPrice,
    v.variance_type as VarianceType,
    v.variance_amount as VarianceAmount,
    c.description as Cause
ORDER BY m.type, v.variance_amount DESC;

-- 9.2 다차원 집계 (제품타입 x 차이유형 x 월)
MATCH (po:ProductionOrder)-[:PRODUCES]->(p:Product)
MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
WITH date.truncate('month', po.order_date) as Month,
     p.type as ProductType,
     v.variance_type as VarianceType,
     SUM(v.variance_amount) as TotalVariance
RETURN 
    Month,
    ProductType,
    VarianceType,
    TotalVariance
ORDER BY Month, ProductType, TotalVariance DESC;

-- ============================================================
-- 10. 시각화용 쿼리
-- ============================================================

-- 10.1 차이 네트워크 시각화 (Neo4j Browser에서 실행)
MATCH path = (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
WHERE v.severity = 'HIGH'
RETURN path
LIMIT 50;

-- 10.2 제품-자재 의존성 그래프
MATCH path = (p:Product)-[:USES_MATERIAL]->(m:Material {type: 'WIRE'})
RETURN path
LIMIT 30;

-- 10.3 시계열 차이 흐름
MATCH path = (po1:ProductionOrder)-[:NEXT_ORDER*1..5]->(po2:ProductionOrder)
WHERE po1.id = 'PO-2024-001'
OPTIONAL MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
OPTIONAL MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
RETURN path
LIMIT 20;
