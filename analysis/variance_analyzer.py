"""
Neo4j 기반 원가차이 분석기

그래프 데이터베이스를 활용한 차이분석 및 리포트 생성
"""

import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
from datetime import datetime
import json

# 환경 변수 로드
load_dotenv()

class VarianceAnalyzer:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        self.database = os.getenv('NEO4J_DATABASE', 'neo4j')
        self.driver = None
        
    def connect(self):
        """Neo4j 연결"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"연결 실패: {str(e)}")
            return False
    
    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
    
    def run_query(self, query, parameters=None):
        """Cypher 쿼리 실행 및 DataFrame 반환"""
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return pd.DataFrame([dict(record) for record in result])
    
    # ============================================================
    # 1. 전체 요약 분석
    # ============================================================
    
    def get_variance_summary(self):
        """원가차이 전체 요약"""
        query = """
        MATCH (v:Variance)
        RETURN 
            v.cost_element as cost_element,
            COUNT(v) as variance_count,
            SUM(v.variance_amount) as total_variance,
            AVG(v.variance_amount) as avg_variance,
            AVG(v.variance_percent) as avg_variance_percent,
            SUM(CASE WHEN v.variance_amount > 0 THEN v.variance_amount ELSE 0 END) as unfavorable,
            SUM(CASE WHEN v.variance_amount < 0 THEN ABS(v.variance_amount) ELSE 0 END) as favorable
        ORDER BY total_variance DESC
        """
        return self.run_query(query)
    
    def get_variance_by_type(self):
        """차이 유형별 분석"""
        query = """
        MATCH (v:Variance)
        RETURN 
            v.variance_type as variance_type,
            v.cost_element as cost_element,
            COUNT(v) as count,
            SUM(v.variance_amount) as total_amount,
            AVG(ABS(v.variance_percent)) as avg_percentage
        ORDER BY total_amount DESC
        """
        return self.run_query(query)
    
    def get_variance_by_severity(self):
        """심각도별 차이 분포"""
        query = """
        MATCH (v:Variance)
        RETURN 
            v.severity as severity,
            COUNT(v) as count,
            SUM(v.variance_amount) as total_amount,
            AVG(ABS(v.variance_amount)) as avg_amount
        ORDER BY 
            CASE v.severity
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
            END
        """
        return self.run_query(query)
    
    def get_monthly_variance_trend(self):
        """월별 차이 트렌드"""
        query = """
        MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
        WITH date.truncate('month', po.order_date) as month,
             v.cost_element as cost_element,
             SUM(v.variance_amount) as total_variance,
             COUNT(v) as variance_count
        RETURN 
            toString(month) as month,
            cost_element,
            total_variance,
            variance_count
        ORDER BY month, cost_element
        """
        return self.run_query(query)
    
    # ============================================================
    # 2. 원인 분석
    # ============================================================
    
    def get_top_causes(self, limit=10):
        """주요 차이 원인 Top N"""
        query = """
        MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)<-[:HAS_VARIANCE]-(po:ProductionOrder)
        WITH c, COUNT(DISTINCT po) as affected_orders,
             SUM(v.variance_amount) as total_impact
        RETURN 
            c.code as cause_code,
            c.description as description,
            c.category as category,
            c.responsible_dept as responsible_dept,
            affected_orders,
            total_impact
        ORDER BY total_impact DESC
        LIMIT $limit
        """
        return self.run_query(query, {'limit': limit})
    
    def get_cause_impact_analysis(self, cause_code):
        """특정 원인의 영향 분석"""
        query = """
        MATCH (c:Cause {code: $cause_code})<-[:CAUSED_BY]-(v:Variance)
        MATCH (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)-[:PRODUCES]->(p:Product)
        RETURN 
            po.id as order_no,
            p.name as product_name,
            po.order_date as order_date,
            v.cost_element as cost_element,
            v.variance_type as variance_type,
            v.variance_amount as variance_amount
        ORDER BY v.variance_amount DESC
        """
        return self.run_query(query, {'cause_code': cause_code})
    
    def get_recurring_issues(self, min_frequency=3):
        """반복되는 문제 패턴"""
        query = """
        MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)<-[:HAS_VARIANCE]-(po:ProductionOrder)
        WITH c, COLLECT(DISTINCT po.id) as orders, COUNT(DISTINCT po) as frequency
        WHERE frequency >= $min_frequency
        MATCH (c)<-[:CAUSED_BY]-(v:Variance)
        RETURN 
            c.code as cause_code,
            c.description as description,
            frequency as occurrence_count,
            orders[0..5] as sample_orders,
            SUM(v.variance_amount) as total_impact
        ORDER BY frequency DESC
        """
        return self.run_query(query, {'min_frequency': min_frequency})
    
    # ============================================================
    # 3. 제품/자재 분석
    # ============================================================
    
    def get_product_variance_ranking(self, limit=10):
        """제품별 차이 순위"""
        query = """
        MATCH (po:ProductionOrder)-[:PRODUCES]->(p:Product)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH p, COUNT(po) as order_count,
             SUM(v.variance_amount) as total_variance,
             AVG(ABS(v.variance_amount)) as avg_variance
        RETURN 
            p.id as product_code,
            p.name as product_name,
            p.type as package_type,
            order_count,
            total_variance,
            avg_variance
        ORDER BY total_variance DESC
        LIMIT $limit
        """
        return self.run_query(query, {'limit': limit})
    
    def get_material_impact_analysis(self, material_type):
        """특정 자재 타입의 영향 분석"""
        query = """
        MATCH (m:Material {type: $material_type})<-[:USES_MATERIAL]-(p:Product)
        MATCH (p)<-[:PRODUCES]-(po:ProductionOrder)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance {cost_element: 'MATERIAL'})
        RETURN 
            m.name as material_name,
            COUNT(DISTINCT p) as affected_products,
            COUNT(DISTINCT po) as affected_orders,
            SUM(v.variance_amount) as total_variance
        ORDER BY total_variance DESC
        """
        return self.run_query(query, {'material_type': material_type})
    
    def get_bom_complexity_analysis(self):
        """BOM 복잡도와 차이의 상관관계"""
        query = """
        MATCH (p:Product)
        MATCH (p)<-[:PRODUCES]-(po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
        WITH p, COUNT(po) as order_count, AVG(ABS(v.variance_amount)) as avg_variance
        MATCH (p)-[:USES_MATERIAL]->()
        WITH p, COUNT(*) as material_count, order_count, avg_variance
        RETURN 
            p.type as package_type,
            AVG(p.pins) as avg_pins,
            AVG(material_count) as avg_material_count,
            AVG(avg_variance) as avg_variance_amount
        ORDER BY avg_variance_amount DESC
        """
        return self.run_query(query)
    
    # ============================================================
    # 4. 패턴 분석
    # ============================================================
    
    def find_similar_variances(self, variance_threshold=500, limit=10):
        """유사한 차이 패턴 발견"""
        query = """
        MATCH (po1:ProductionOrder)-[:PRODUCES]->(p:Product)<-[:PRODUCES]-(po2:ProductionOrder)
        MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
        MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
        WHERE po1.id < po2.id
          AND v1.variance_type = v2.variance_type
          AND v1.cost_element = v2.cost_element
          AND ABS(v1.variance_amount - v2.variance_amount) < $threshold
        RETURN 
            po1.id as order1,
            po2.id as order2,
            p.name as product,
            v1.variance_type as variance_type,
            v1.variance_amount as amount1,
            v2.variance_amount as amount2,
            ABS(v1.variance_amount - v2.variance_amount) as difference
        ORDER BY difference
        LIMIT $limit
        """
        return self.run_query(query, {'threshold': variance_threshold, 'limit': limit})
    
    def get_time_series_patterns(self):
        """시계열 차이 패턴"""
        query = """
        MATCH (po1:ProductionOrder)-[:NEXT_ORDER]->(po2:ProductionOrder)
        MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
        MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
        WHERE v1.variance_type = v2.variance_type
          AND v1.cost_element = v2.cost_element
        RETURN 
            po1.id as first_order,
            po2.id as next_order,
            v1.variance_type as variance_type,
            v1.variance_amount as first_amount,
            v2.variance_amount as next_amount,
            CASE 
                WHEN v2.variance_amount > v1.variance_amount THEN '악화'
                WHEN v2.variance_amount < v1.variance_amount THEN '개선'
                ELSE '유지'
            END as trend
        ORDER BY ABS(v2.variance_amount - v1.variance_amount) DESC
        LIMIT 20
        """
        return self.run_query(query)
    
    # ============================================================
    # 5. 예측 및 리스크 분석
    # ============================================================
    
    def get_risk_products(self, min_orders=3):
        """위험 제품 예측"""
        query = """
        MATCH (p:Product)<-[:PRODUCES]-(po:ProductionOrder)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH p, 
             COUNT(po) as total_orders,
             COUNT(v) as variance_count,
             AVG(ABS(v.variance_amount)) as avg_variance
        WHERE total_orders >= $min_orders
        WITH p, total_orders, variance_count, avg_variance,
             100.0 * variance_count / total_orders as variance_rate
        RETURN 
            p.id as product_code,
            p.name as product_name,
            total_orders,
            variance_count,
            ROUND(variance_rate, 2) as variance_rate,
            ROUND(avg_variance, 2) as avg_variance_amount,
            CASE 
                WHEN variance_rate > 80 THEN '높음'
                WHEN variance_rate > 50 THEN '중간'
                ELSE '낮음'
            END as risk_level
        ORDER BY variance_rate DESC, avg_variance DESC
        """
        return self.run_query(query, {'min_orders': min_orders})
    
    def get_supplier_quality_issues(self):
        """공급업체별 품질 이슈"""
        query = """
        MATCH (m:Material)<-[:CONSUMES]-(po:ProductionOrder)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance {cost_element: 'MATERIAL'})
        WITH m.supplier_cd as supplier, 
             COUNT(DISTINCT po) as orders,
             SUM(v.variance_amount) as total_variance
        WHERE total_variance > 0
        RETURN 
            supplier,
            orders,
            total_variance,
            ROUND(total_variance / orders, 2) as avg_variance_per_order
        ORDER BY total_variance DESC
        """
        return self.run_query(query)
    
    # ============================================================
    # 6. 특정 오더 상세 분석
    # ============================================================
    
    def analyze_order(self, order_no):
        """특정 오더의 상세 차이 분석"""
        query = """
        MATCH (po:ProductionOrder {id: $order_no})
        MATCH (po)-[:PRODUCES]->(p:Product)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
        OPTIONAL MATCH (v)-[:RELATED_TO_MATERIAL]->(m:Material)
        RETURN 
            po.id as order_no,
            p.name as product,
            po.order_date as order_date,
            po.planned_qty as planned_qty,
            po.good_qty as good_qty,
            po.yield_rate as yield_rate,
            v.cost_element as cost_element,
            v.variance_type as variance_type,
            v.variance_amount as variance_amount,
            v.variance_percent as variance_percent,
            c.description as cause,
            m.name as related_material
        ORDER BY ABS(v.variance_amount) DESC
        """
        return self.run_query(query, {'order_no': order_no})
    
    # ============================================================
    # 7. 리포트 생성
    # ============================================================
    
    def generate_summary_report(self):
        """요약 리포트 생성"""
        print("=" * 70)
        print("원가차이 분석 리포트")
        print("=" * 70)
        print(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. 전체 요약
        print("[1] 원가요소별 차이 요약")
        print("-" * 70)
        summary = self.get_variance_summary()
        print(summary.to_string(index=False))
        print()
        
        # 2. 차이 유형별
        print("[2] 차이 유형별 분석")
        print("-" * 70)
        by_type = self.get_variance_by_type()
        print(by_type.head(10).to_string(index=False))
        print()
        
        # 3. 주요 원인
        print("[3] 주요 차이 원인 Top 5")
        print("-" * 70)
        causes = self.get_top_causes(5)
        print(causes.to_string(index=False))
        print()
        
        # 4. 위험 제품
        print("[4] 위험 제품 Top 5")
        print("-" * 70)
        risk = self.get_risk_products()
        print(risk.head(5).to_string(index=False))
        print()
        
        # 5. 반복 문제
        print("[5] 반복되는 문제")
        print("-" * 70)
        recurring = self.get_recurring_issues()
        if not recurring.empty:
            print(recurring.to_string(index=False))
        else:
            print("반복되는 문제가 없습니다.")
        print()
        
        print("=" * 70)
        print("리포트 종료")
        print("=" * 70)
    
    def export_to_excel(self, filename='variance_analysis_report.xlsx'):
        """Excel 리포트 출력"""
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            self.get_variance_summary().to_excel(writer, sheet_name='전체요약', index=False)
            self.get_variance_by_type().to_excel(writer, sheet_name='유형별', index=False)
            self.get_variance_by_severity().to_excel(writer, sheet_name='심각도별', index=False)
            self.get_top_causes(20).to_excel(writer, sheet_name='주요원인', index=False)
            self.get_product_variance_ranking(20).to_excel(writer, sheet_name='제품별', index=False)
            self.get_risk_products().to_excel(writer, sheet_name='위험제품', index=False)
            self.get_monthly_variance_trend().to_excel(writer, sheet_name='월별트렌드', index=False)
        
        print(f"✓ Excel 리포트 생성: {filename}")

def main():
    print("=" * 70)
    print("Neo4j 원가차이 분석기")
    print("=" * 70)
    
    analyzer = VarianceAnalyzer()
    
    if not analyzer.connect():
        print("Neo4j 연결 실패. .env 파일을 확인하세요.")
        return
    
    print("✓ Neo4j 연결 성공\n")
    
    try:
        # 요약 리포트 출력
        analyzer.generate_summary_report()
        
        # Excel 리포트 생성
        print("\nExcel 리포트를 생성하시겠습니까? (y/n): ", end='')
        response = input().strip().lower()
        if response == 'y':
            analyzer.export_to_excel()
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
