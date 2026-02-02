// ============================================================
// Neo4j 데이터 진단 쿼리 모음
// ============================================================
// Neo4j Browser에서 각 쿼리를 복사해서 실행하세요

// ------------------------------------------------------------
// 1. 전체 노드 개수 확인
// ------------------------------------------------------------
MATCH (n)
RETURN labels(n)[0] as NodeType, count(n) as Count
ORDER BY Count DESC;

// ------------------------------------------------------------
// 2. 전체 관계 개수 확인
// ------------------------------------------------------------
MATCH ()-[r]->()
RETURN type(r) as RelationType, count(r) as Count
ORDER BY Count DESC;

// ------------------------------------------------------------
// 3. Variance 노드 샘플 확인 (프로퍼티 확인)
// ------------------------------------------------------------
MATCH (v:Variance)
RETURN v
LIMIT 3;

// ------------------------------------------------------------
// 4. Variance 노드의 프로퍼티 키 목록
// ------------------------------------------------------------
MATCH (v:Variance)
RETURN keys(v) as Properties
LIMIT 1;

// ------------------------------------------------------------
// 5. 생산오더 -> Variance -> Cause 연결 확인
// ------------------------------------------------------------
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
RETURN count(*) as 연결된경로개수;

// ------------------------------------------------------------
// 6. 샘플 경로 시각화 (첫 번째 생산오더)
// ------------------------------------------------------------
MATCH path = (po:ProductionOrder)-[*1..2]-(n)
WHERE po.id = 'PO-2024-001'
RETURN path
LIMIT 50;

// ------------------------------------------------------------
// 7. 전체 데이터 요약
// ------------------------------------------------------------
MATCH (n)
WITH count(n) as totalNodes
MATCH ()-[r]->()
WITH totalNodes, count(r) as totalRels
MATCH (po:ProductionOrder)
WITH totalNodes, totalRels, count(po) as orders
MATCH (v:Variance)
WITH totalNodes, totalRels, orders, count(v) as variances
MATCH (c:Cause)
RETURN 
  totalNodes as 전체노드수,
  totalRels as 전체관계수,
  orders as 생산오더수,
  variances as 차이건수,
  count(c) as 원인코드수;
