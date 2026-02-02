-- ============================================================
-- 원가 계산 및 차이분석 쿼리
-- ============================================================

-- ============================================================
-- 1. 계획원가 계산
-- ============================================================

-- 1.1 재료비 계획원가 계산
-- BOM과 자재단가를 이용하여 제품별 계획 재료비 계산
SELECT 
    po.order_no,
    po.product_cd,
    pm.product_name,
    SUM(b.quantity * mm.standard_price * po.planned_qty) as planned_material_cost,
    po.planned_qty
FROM PRODUCTION_ORDER po
JOIN PRODUCT_MASTER pm ON po.product_cd = pm.product_cd
JOIN BOM b ON po.product_cd = b.product_cd
JOIN MATERIAL_MASTER mm ON b.material_cd = mm.material_cd
WHERE po.status = 'RELEASED'
  AND b.valid_from <= po.order_date
  AND (b.valid_to IS NULL OR b.valid_to >= po.order_date)
GROUP BY po.order_no, po.product_cd, pm.product_name, po.planned_qty;

-- 1.2 노무비 계획원가 계산
-- 라우팅의 표준시간과 작업장 노무비율 이용
SELECT 
    po.order_no,
    po.product_cd,
    SUM(r.standard_time_sec / 3600.0 * wc.labor_rate_per_hour * po.planned_qty) as planned_labor_cost
FROM PRODUCTION_ORDER po
JOIN ROUTING r ON po.product_cd = r.product_cd
JOIN WORK_CENTER wc ON r.workcenter_cd = wc.workcenter_cd
WHERE po.status = 'RELEASED'
  AND r.valid_from <= po.order_date
  AND (r.valid_to IS NULL OR r.valid_to >= po.order_date)
GROUP BY po.order_no, po.product_cd;

-- 1.3 경비 계획원가 계산
SELECT 
    po.order_no,
    po.product_cd,
    SUM(r.standard_time_sec / 3600.0 * wc.overhead_rate_per_hour * po.planned_qty) as planned_overhead_cost
FROM PRODUCTION_ORDER po
JOIN ROUTING r ON po.product_cd = r.product_cd
JOIN WORK_CENTER wc ON r.workcenter_cd = wc.workcenter_cd
WHERE po.status = 'RELEASED'
  AND r.valid_from <= po.order_date
  AND (r.valid_to IS NULL OR r.valid_to >= po.order_date)
GROUP BY po.order_no, po.product_cd;

-- 1.4 통합 계획원가 계산 및 COST_ACCUMULATION 테이블 적재
INSERT INTO COST_ACCUMULATION (cost_id, order_no, cost_element, planned_cost, calculation_date)
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.order_no) as cost_id,
    po.order_no,
    'MATERIAL' as cost_element,
    SUM(b.quantity * mm.standard_price * po.planned_qty) as planned_cost,
    CURRENT_DATE as calculation_date
FROM PRODUCTION_ORDER po
JOIN BOM b ON po.product_cd = b.product_cd
JOIN MATERIAL_MASTER mm ON b.material_cd = mm.material_cd
WHERE po.status = 'RELEASED'
GROUP BY po.order_no;

-- ============================================================
-- 2. 실적원가 계산
-- ============================================================

-- 2.1 재료비 실적원가 계산
-- 실제 자재 투입량과 투입 시점의 단가 이용
SELECT 
    mc.order_no,
    SUM(mc.actual_qty * mm.standard_price) as actual_material_cost
FROM MATERIAL_CONSUMPTION mc
JOIN MATERIAL_MASTER mm ON mc.material_cd = mm.material_cd
GROUP BY mc.order_no;

-- 2.2 노무비 실적원가 계산
-- 실제 작업시간과 작업장 노무비율 이용
SELECT 
    oa.order_no,
    SUM(oa.actual_time_min / 60.0 * wc.labor_rate_per_hour) as actual_labor_cost
FROM OPERATION_ACTUAL oa
JOIN WORK_CENTER wc ON oa.workcenter_cd = wc.workcenter_cd
GROUP BY oa.order_no;

-- 2.3 경비 실적원가 계산
SELECT 
    oa.order_no,
    SUM(oa.actual_time_min / 60.0 * wc.overhead_rate_per_hour) as actual_overhead_cost
FROM OPERATION_ACTUAL oa
JOIN WORK_CENTER wc ON oa.workcenter_cd = wc.workcenter_cd
GROUP BY oa.order_no;

-- 2.4 실적원가 업데이트
UPDATE COST_ACCUMULATION ca
SET actual_cost = (
    SELECT SUM(mc.actual_qty * mm.standard_price)
    FROM MATERIAL_CONSUMPTION mc
    JOIN MATERIAL_MASTER mm ON mc.material_cd = mm.material_cd
    WHERE mc.order_no = ca.order_no
),
variance = actual_cost - planned_cost
WHERE ca.cost_element = 'MATERIAL';

-- ============================================================
-- 3. 원가차이 계산
-- ============================================================

-- 3.1 재료비 가격차이 (Price Variance)
-- 차이 = (실제단가 - 표준단가) × 실제수량
SELECT 
    mc.order_no,
    mc.material_cd,
    mm.material_name,
    (mm.standard_price - mm.standard_price) * mc.actual_qty as price_variance,
    '가격차이 계산 시 실제단가 테이블 필요' as note
FROM MATERIAL_CONSUMPTION mc
JOIN MATERIAL_MASTER mm ON mc.material_cd = mm.material_cd;

-- 3.2 재료비 수량차이 (Quantity Variance)
-- 차이 = (실제수량 - 표준수량) × 표준단가
SELECT 
    mc.order_no,
    mc.material_cd,
    mm.material_name,
    (mc.actual_qty - mc.planned_qty) * mm.standard_price as quantity_variance
FROM MATERIAL_CONSUMPTION mc
JOIN MATERIAL_MASTER mm ON mc.material_cd = mm.material_cd;

-- 3.3 노무비 임률차이 (Rate Variance)
-- 차이 = (실제임률 - 표준임률) × 실제시간
-- 단순화를 위해 표준임률만 사용 (임률차이 = 0)

-- 3.4 노무비 효율차이 (Efficiency Variance)
-- 차이 = (실제시간 - 표준시간) × 표준임률
SELECT 
    po.order_no,
    po.product_cd,
    (SUM(oa.actual_time_min) - SUM(r.standard_time_sec * po.actual_qty / 60.0)) * 
    AVG(wc.labor_rate_per_hour) / 60.0 as efficiency_variance
FROM PRODUCTION_ORDER po
JOIN OPERATION_ACTUAL oa ON po.order_no = oa.order_no
JOIN ROUTING r ON po.product_cd = r.product_cd AND oa.workcenter_cd = r.workcenter_cd
JOIN WORK_CENTER wc ON oa.workcenter_cd = wc.workcenter_cd
GROUP BY po.order_no, po.product_cd;

-- 3.5 수율차이 (Yield Variance)
-- 차이 = (투입수량 - 산출수량) × 단위당 원가
SELECT 
    po.order_no,
    po.product_cd,
    po.planned_qty as input_qty,
    po.good_qty as output_qty,
    po.scrap_qty,
    (po.planned_qty - po.good_qty) / NULLIF(po.planned_qty, 0) * 100.0 as scrap_rate,
    (po.planned_qty - po.good_qty) * pm.standard_cost as yield_variance
FROM PRODUCTION_ORDER po
JOIN PRODUCT_MASTER pm ON po.product_cd = pm.product_cd
WHERE po.actual_qty IS NOT NULL;

-- ============================================================
-- 4. 복잡한 차이분석 쿼리 (RDB의 문제점 예시)
-- ============================================================

-- 4.1 특정 제품의 재료비 차이 근본 원인 추적
-- 문제: 5개 이상의 테이블 JOIN 필요
SELECT 
    v.variance_id,
    v.order_no,
    po.product_cd,
    pm.product_name,
    v.variance_type,
    v.variance_amount,
    m.material_cd,
    mm.material_name,
    mm.material_type,
    mm.supplier_cd,
    c.cause_description,
    c.responsible_dept
FROM VARIANCE_ANALYSIS v
JOIN PRODUCTION_ORDER po ON v.order_no = po.order_no
JOIN PRODUCT_MASTER pm ON po.product_cd = pm.product_cd
JOIN MATERIAL_CONSUMPTION m ON po.order_no = m.order_no
JOIN MATERIAL_MASTER mm ON m.material_cd = mm.material_cd
LEFT JOIN CAUSE_CODE c ON v.cause_code = c.cause_code
WHERE v.cost_element = 'MATERIAL'
  AND v.variance_amount > 1000
ORDER BY v.variance_amount DESC;

-- 4.2 유사 패턴의 차이 발견 (동일 제품, 동일 차이 유형)
-- 문제: 자기 조인으로 인한 성능 저하
SELECT 
    v1.order_no as order1,
    v2.order_no as order2,
    po1.product_cd,
    v1.variance_type,
    v1.variance_amount as amount1,
    v2.variance_amount as amount2,
    ABS(v1.variance_amount - v2.variance_amount) as diff
FROM VARIANCE_ANALYSIS v1
JOIN VARIANCE_ANALYSIS v2 ON v1.variance_type = v2.variance_type AND v1.order_no < v2.order_no
JOIN PRODUCTION_ORDER po1 ON v1.order_no = po1.order_no
JOIN PRODUCTION_ORDER po2 ON v2.order_no = po2.order_no
WHERE po1.product_cd = po2.product_cd
  AND v1.variance_amount > 1000
ORDER BY diff;

-- 4.3 시계열 차이 분석 (월별 트렌드)
-- 문제: 집계와 윈도우 함수로 복잡도 증가
SELECT 
    TO_CHAR(po.order_date, 'YYYY-MM') as month,
    v.cost_element,
    v.variance_type,
    COUNT(*) as variance_count,
    SUM(v.variance_amount) as total_variance,
    AVG(v.variance_amount) as avg_variance,
    MIN(v.variance_amount) as min_variance,
    MAX(v.variance_amount) as max_variance,
    LAG(SUM(v.variance_amount)) OVER (PARTITION BY v.cost_element ORDER BY TO_CHAR(po.order_date, 'YYYY-MM')) as prev_month_variance,
    SUM(v.variance_amount) - LAG(SUM(v.variance_amount)) OVER (PARTITION BY v.cost_element ORDER BY TO_CHAR(po.order_date, 'YYYY-MM')) as month_on_month_change
FROM VARIANCE_ANALYSIS v
JOIN PRODUCTION_ORDER po ON v.order_no = po.order_no
GROUP BY TO_CHAR(po.order_date, 'YYYY-MM'), v.cost_element, v.variance_type
ORDER BY month, v.cost_element;

-- 4.4 공통 원인이 미치는 영향 분석
-- 문제: 다단계 집계로 쿼리 실행 시간 증가
SELECT 
    c.cause_code,
    c.cause_description,
    COUNT(DISTINCT v.order_no) as affected_orders,
    COUNT(DISTINCT po.product_cd) as affected_products,
    SUM(v.variance_amount) as total_impact,
    STRING_AGG(DISTINCT mm.supplier_cd, ', ') as affected_suppliers
FROM VARIANCE_ANALYSIS v
JOIN CAUSE_CODE c ON v.cause_code = c.cause_code
JOIN PRODUCTION_ORDER po ON v.order_no = po.order_no
LEFT JOIN MATERIAL_CONSUMPTION mc ON po.order_no = mc.order_no
LEFT JOIN MATERIAL_MASTER mm ON mc.material_cd = mm.material_cd
GROUP BY c.cause_code, c.cause_description
HAVING SUM(v.variance_amount) > 10000
ORDER BY total_impact DESC;

-- ============================================================
-- 5. 성능 문제 시뮬레이션
-- ============================================================

-- 5.1 전체 원가 흐름 추적 (최악의 시나리오)
-- 문제: 8개 이상의 테이블 JOIN, 실행 시간 수 분 소요 가능
SELECT 
    po.order_no,
    po.order_date,
    pm.product_name,
    pm.product_type,
    b.material_cd,
    mm.material_name,
    mm.material_type,
    b.quantity as bom_qty,
    mc.actual_qty,
    r.workcenter_cd,
    wc.workcenter_name,
    r.standard_time_sec,
    oa.actual_time_min,
    ca.cost_element,
    ca.planned_cost,
    ca.actual_cost,
    ca.variance,
    v.variance_type,
    v.variance_amount,
    c.cause_description
FROM PRODUCTION_ORDER po
JOIN PRODUCT_MASTER pm ON po.product_cd = pm.product_cd
JOIN BOM b ON po.product_cd = b.product_cd
JOIN MATERIAL_MASTER mm ON b.material_cd = mm.material_cd
LEFT JOIN MATERIAL_CONSUMPTION mc ON po.order_no = mc.order_no AND b.material_cd = mc.material_cd
JOIN ROUTING r ON po.product_cd = r.product_cd
JOIN WORK_CENTER wc ON r.workcenter_cd = wc.workcenter_cd
LEFT JOIN OPERATION_ACTUAL oa ON po.order_no = oa.order_no AND r.workcenter_cd = oa.workcenter_cd
LEFT JOIN COST_ACCUMULATION ca ON po.order_no = ca.order_no
LEFT JOIN VARIANCE_ANALYSIS v ON po.order_no = v.order_no AND ca.cost_element = v.cost_element
LEFT JOIN CAUSE_CODE c ON v.cause_code = c.cause_code
WHERE po.order_date >= '2024-01-01'
  AND po.order_date < '2024-04-01'
ORDER BY po.order_no, b.material_cd, r.operation_seq;

-- ============================================================
-- 6. 차이분석 요약 뷰
-- ============================================================

CREATE VIEW V_VARIANCE_SUMMARY AS
SELECT 
    po.order_no,
    po.order_date,
    pm.product_cd,
    pm.product_name,
    pm.product_type,
    po.planned_qty,
    po.good_qty,
    po.scrap_qty,
    CASE 
        WHEN po.planned_qty > 0 THEN (po.good_qty::DECIMAL / po.planned_qty) * 100 
        ELSE 0 
    END as yield_rate,
    SUM(CASE WHEN ca.cost_element = 'MATERIAL' THEN ca.planned_cost ELSE 0 END) as planned_material,
    SUM(CASE WHEN ca.cost_element = 'MATERIAL' THEN ca.actual_cost ELSE 0 END) as actual_material,
    SUM(CASE WHEN ca.cost_element = 'MATERIAL' THEN ca.variance ELSE 0 END) as material_variance,
    SUM(CASE WHEN ca.cost_element = 'LABOR' THEN ca.planned_cost ELSE 0 END) as planned_labor,
    SUM(CASE WHEN ca.cost_element = 'LABOR' THEN ca.actual_cost ELSE 0 END) as actual_labor,
    SUM(CASE WHEN ca.cost_element = 'LABOR' THEN ca.variance ELSE 0 END) as labor_variance,
    SUM(CASE WHEN ca.cost_element = 'OVERHEAD' THEN ca.planned_cost ELSE 0 END) as planned_overhead,
    SUM(CASE WHEN ca.cost_element = 'OVERHEAD' THEN ca.actual_cost ELSE 0 END) as actual_overhead,
    SUM(CASE WHEN ca.cost_element = 'OVERHEAD' THEN ca.variance ELSE 0 END) as overhead_variance,
    SUM(ca.planned_cost) as total_planned,
    SUM(ca.actual_cost) as total_actual,
    SUM(ca.variance) as total_variance
FROM PRODUCTION_ORDER po
JOIN PRODUCT_MASTER pm ON po.product_cd = pm.product_cd
LEFT JOIN COST_ACCUMULATION ca ON po.order_no = ca.order_no
WHERE po.status IN ('CONFIRMED', 'CLOSED')
GROUP BY po.order_no, po.order_date, pm.product_cd, pm.product_name, pm.product_type,
         po.planned_qty, po.good_qty, po.scrap_qty;

-- 뷰 사용 예시
SELECT * 
FROM V_VARIANCE_SUMMARY 
WHERE ABS(total_variance) > 5000
ORDER BY ABS(total_variance) DESC;
