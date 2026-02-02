"""
Neo4j 원가차이 자동 분석 리포트 생성
"""
import os
import ssl
from dotenv import load_dotenv
from neo4j import GraphDatabase
from datetime import datetime

# .env 파일 로드
load_dotenv()

class VarianceAnalyzer:
    def __init__(self):
        uri = os.getenv('NEO4J_URI')
        username = os.getenv('NEO4J_USERNAME')
        password = os.getenv('NEO4J_PASSWORD')
        
        # URI 변경 및 SSL 설정
        uri = uri.replace('neo4j+s://', 'bolt://')
        uri = uri.replace('neo4j+ssc://', 'bolt://')
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            ssl_context=ssl_context
        )
    
    def close(self):
        self.driver.close()
    
    def get_summary(self):
        """전체 요약 통계"""
        with self.driver.session() as session:
            result = session.run("""
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
                  sum(v3.variance_amount) as 유리한차이금액
            """)
            return result.single()
    
    def get_variance_by_cause(self):
        """원인코드별 차이 집계"""
        with self.driver.session() as session:
            result = session.run("""
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
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return list(result)
    
    def get_variance_by_element(self):
        """원가요소별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Variance)
                RETURN 
                  v.cost_element as 원가요소,
                  count(v) as 발생건수,
                  sum(v.variance_amount) as 총차이금액,
                  avg(v.variance_amount) as 평균차이금액,
                  min(v.variance_amount) as 최소차이,
                  max(v.variance_amount) as 최대차이
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return list(result)
    
    def get_variance_by_severity(self):
        """심각도별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
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
                  END
            """)
            return list(result)
    
    def get_top_variance_orders(self, limit=10):
        """차이가 큰 TOP 생산오더"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                WITH po, sum(v.variance_amount) as 총차이금액, count(v) as 차이건수
                RETURN 
                  po.id as 생산오더,
                  po.product_cd as 제품코드,
                  po.planned_qty as 생산수량,
                  po.status as 상태,
                  총차이금액,
                  차이건수
                ORDER BY abs(총차이금액) DESC
                LIMIT $limit
            """, limit=limit)
            return list(result)
    
    def get_workcenter_analysis(self):
        """작업장별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
                MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
                WHERE v.cost_element IN ['LABOR', 'OVERHEAD']
                WITH wc, v
                RETURN 
                  wc.name as 작업장,
                  wc.process_type as 작업장타입,
                  count(v) as 차이건수,
                  sum(v.variance_amount) as 총차이금액,
                  avg(v.variance_percent) as 평균차이율
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return list(result)

def print_section(title):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def format_amount(amount):
    """금액 포맷팅"""
    if amount is None:
        return "N/A"
    return f"{amount:,.2f} 원"

def format_percent(percent):
    """퍼센트 포맷팅"""
    if percent is None:
        return "N/A"
    return f"{percent:.2f}%"

def main():
    print("=" * 80)
    print("  Neo4j 원가차이 분석 리포트")
    print(f"  생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    analyzer = VarianceAnalyzer()
    
    try:
        # 1. 전체 요약
        print_section("1. 전체 요약")
        summary = analyzer.get_summary()
        print(f"\n  총 생산오더 수:     {summary['총오더수']:,}개")
        print(f"  총 차이 건수:       {summary['총차이건수']:,}건")
        print(f"  총 차이 금액:       {format_amount(summary['총차이금액'])}")
        print(f"\n  불리한 차이:        {summary['불리한차이건수']:,}건 / {format_amount(summary['불리한차이금액'])}")
        print(f"  유리한 차이:        {summary['유리한차이건수']:,}건 / {format_amount(summary['유리한차이금액'])}")
        
        # 2. 원인코드별 분석
        print_section("2. 원인코드별 차이 분석")
        causes = analyzer.get_variance_by_cause()
        print(f"\n  {'원인코드':<20} {'분류':<15} {'발생건수':<10} {'총차이금액':<20} {'평균차이율':<12}")
        print("  " + "-" * 95)
        for record in causes:
            print(f"  {record['원인코드']:<20} {record['분류']:<15} "
                  f"{record['발생건수']:<10} {record['총차이금액']:>18,.0f}원 "
                  f"{format_percent(record['평균차이율']):<12}")
        
        # 3. 원가요소별 분석
        print_section("3. 원가요소별 차이 분석")
        elements = analyzer.get_variance_by_element()
        print(f"\n  {'원가요소':<15} {'발생건수':<10} {'총차이금액':<20} {'평균차이금액':<20}")
        print("  " + "-" * 75)
        for record in elements:
            print(f"  {record['원가요소']:<15} {record['발생건수']:<10} "
                  f"{record['총차이금액']:>18,.0f}원 {record['평균차이금액']:>18,.0f}원")
        
        # 4. 심각도별 분석
        print_section("4. 심각도별 차이 분석")
        severities = analyzer.get_variance_by_severity()
        print(f"\n  {'심각도':<15} {'발생건수':<10} {'총차이금액':<20} {'평균차이율':<12}")
        print("  " + "-" * 65)
        for record in severities:
            print(f"  {record['심각도']:<15} {record['발생건수']:<10} "
                  f"{record['총차이금액']:>18,.0f}원 {format_percent(record['평균차이율']):<12}")
        
        # 5. TOP 10 차이 큰 오더
        print_section("5. TOP 10 차이가 큰 생산오더")
        top_orders = analyzer.get_top_variance_orders(10)
        print(f"\n  {'생산오더':<15} {'제품코드':<15} {'생산수량':<10} {'차이건수':<10} {'총차이금액':<20}")
        print("  " + "-" * 80)
        for record in top_orders:
            print(f"  {record['생산오더']:<15} {record['제품코드']:<15} "
                  f"{record['생산수량']:<10} {record['차이건수']:<10} "
                  f"{record['총차이금액']:>18,.0f}원")
        
        # 6. 작업장별 분석
        print_section("6. 작업장별 차이 분석 (노무비/경비)")
        workcenters = analyzer.get_workcenter_analysis()
        print(f"\n  {'작업장':<25} {'타입':<15} {'차이건수':<10} {'총차이금액':<20}")
        print("  " + "-" * 80)
        for record in workcenters:
            print(f"  {record['작업장']:<25} {record['작업장타입']:<15} "
                  f"{record['차이건수']:<10} {record['총차이금액']:>18,.0f}원")
        
        print("\n" + "=" * 80)
        print("  분석 완료!")
        print("=" * 80)
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
