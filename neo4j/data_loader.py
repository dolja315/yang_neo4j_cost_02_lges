"""
Neo4j 데이터 로더

생성된 CSV 파일을 Neo4j 데이터베이스에 로드합니다.
"""

import os
import ssl
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm
import time

# 환경 변수 로드
load_dotenv()

class Neo4jDataLoader:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        self.database = os.getenv('NEO4J_DATABASE', 'neo4j')
        self.driver = None
        self.data_dir = 'data/neo4j_import'
        
    def connect(self):
        """Neo4j 데이터베이스에 연결"""
        try:
            # URI 변환 (API 서버와 동일)
            uri = self.uri.replace('neo4j+s://', 'bolt://')
            uri = uri.replace('neo4j+ssc://', 'bolt://')
            
            # SSL 설정 (인증서 검증 비활성화)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.driver = GraphDatabase.driver(
                uri,
                auth=(self.username, self.password),
                ssl_context=ssl_context
            )
            # 연결 테스트
            self.driver.verify_connectivity()
            print(f"✓ Neo4j 연결 성공: {uri}")
            return True
        except Exception as e:
            print(f"✗ Neo4j 연결 실패: {str(e)}")
            return False
    
    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
            print("✓ 연결 종료")
    
    def clear_database(self):
        """데이터베이스 초기화 (주의!)"""
        print("\n⚠️  데이터베이스 초기화 중...")
        with self.driver.session(database=self.database) as session:
            # 모든 노드와 관계 삭제
            session.run("MATCH (n) DETACH DELETE n")
        print("✓ 데이터베이스 초기화 완료")
    
    def create_schema(self):
        """스키마 (제약조건, 인덱스) 생성"""
        print("\n[1단계] 스키마 생성")
        
        with self.driver.session(database=self.database) as session:
            # 제약조건
            constraints = [
                "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT material_id IF NOT EXISTS FOR (m:Material) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT workcenter_id IF NOT EXISTS FOR (wc:WorkCenter) REQUIRE wc.id IS UNIQUE",
                "CREATE CONSTRAINT production_order_id IF NOT EXISTS FOR (po:ProductionOrder) REQUIRE po.id IS UNIQUE",
                "CREATE CONSTRAINT variance_id IF NOT EXISTS FOR (v:Variance) REQUIRE v.id IS UNIQUE",
                "CREATE CONSTRAINT cause_code IF NOT EXISTS FOR (c:Cause) REQUIRE c.code IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"  ✓ {constraint.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  ✗ 제약조건 생성 실패: {str(e)}")
            
            # 인덱스
            indexes = [
                "CREATE INDEX product_type IF NOT EXISTS FOR (p:Product) ON (p.type)",
                "CREATE INDEX material_type IF NOT EXISTS FOR (m:Material) ON (m.type)",
                "CREATE INDEX workcenter_process IF NOT EXISTS FOR (wc:WorkCenter) ON (wc.process_type)",
                "CREATE INDEX po_order_date IF NOT EXISTS FOR (po:ProductionOrder) ON (po.order_date)",
                "CREATE INDEX variance_element IF NOT EXISTS FOR (v:Variance) ON (v.cost_element)",
                "CREATE INDEX variance_severity IF NOT EXISTS FOR (v:Variance) ON (v.severity)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    print(f"  ✓ {index.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  ✗ 인덱스 생성 실패: {str(e)}")
        
        # 인덱스가 생성될 때까지 대기
        time.sleep(2)
        print("✓ 스키마 생성 완료")
    
    def load_products(self):
        """Product 노드 로드"""
        csv_file = f'{self.data_dir}/products.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Products"):
                session.run("""
                    CREATE (p:Product {
                        id: $id,
                        name: $name,
                        type: $type,
                        pins: $pins,
                        standard_cost: $standard_cost,
                        active: $active
                    })
                """, dict(row))
        
        print(f"  ✓ Product 노드: {len(df)}개")
    
    def load_materials(self):
        """Material 노드 로드"""
        csv_file = f'{self.data_dir}/materials.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Materials"):
                session.run("""
                    CREATE (m:Material {
                        id: $id,
                        name: $name,
                        type: $type,
                        unit: $unit,
                        standard_price: $standard_price,
                        supplier_cd: $supplier_cd,
                        active: $active
                    })
                """, dict(row))
        
        print(f"  ✓ Material 노드: {len(df)}개")
    
    def load_work_centers(self):
        """WorkCenter 노드 로드"""
        csv_file = f'{self.data_dir}/work_centers.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  WorkCenters"):
                session.run("""
                    CREATE (wc:WorkCenter {
                        id: $id,
                        name: $name,
                        process_type: $process_type,
                        labor_rate_per_hour: $labor_rate_per_hour,
                        overhead_rate_per_hour: $overhead_rate_per_hour,
                        capacity_per_hour: $capacity_per_hour,
                        active: $active
                    })
                """, dict(row))
        
        print(f"  ✓ WorkCenter 노드: {len(df)}개")
    
    def load_production_orders(self):
        """ProductionOrder 노드 로드"""
        csv_file = f'{self.data_dir}/production_orders.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  ProductionOrders"):
                session.run("""
                    CREATE (po:ProductionOrder {
                        id: $id,
                        product_cd: $product_cd,
                        order_type: $order_type,
                        planned_qty: $planned_qty,
                        actual_qty: $actual_qty,
                        good_qty: $good_qty,
                        scrap_qty: $scrap_qty,
                        order_date: date($order_date),
                        start_date: date($start_date),
                        finish_date: date($finish_date),
                        status: $status,
                        yield_rate: $yield_rate
                    })
                """, dict(row))
        
        print(f"  ✓ ProductionOrder 노드: {len(df)}개")
    
    def load_variances(self):
        """Variance 노드 로드"""
        csv_file = f'{self.data_dir}/variances.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Variances"):
                session.run("""
                    CREATE (v:Variance {
                        id: $id,
                        order_no: $order_no,
                        cost_element: $cost_element,
                        variance_type: $variance_type,
                        variance_amount: $variance_amount,
                        variance_percent: $variance_percent,
                        severity: $severity,
                        cause_code: $cause_code,
                        analysis_date: date($analysis_date)
                    })
                """, dict(row))
        
        print(f"  ✓ Variance 노드: {len(df)}개")
    
    def load_causes(self):
        """Cause 노드 로드"""
        csv_file = f'{self.data_dir}/causes.csv'
        if not os.path.exists(csv_file):
            print(f"  ✗ 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Causes"):
                session.run("""
                    CREATE (c:Cause {
                        code: $code,
                        category: $category,
                        description: $description,
                        responsible_dept: $responsible_dept
                    })
                """, dict(row))
        
        print(f"  ✓ Cause 노드: {len(df)}개")
    
    def load_relationships(self):
        """관계 로드"""
        print("\n[3단계] 관계 생성")
        
        # USES_MATERIAL 관계
        csv_file = f'{self.data_dir}/rel_uses_material.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  USES_MATERIAL"):
                    session.run("""
                        MATCH (p:Product {id: $from})
                        MATCH (m:Material {id: $to})
                        CREATE (p)-[:USES_MATERIAL {
                            quantity: $quantity,
                            unit: $unit
                        }]->(m)
                    """, dict(row))
            print(f"  ✓ USES_MATERIAL: {len(df)}개")
        
        # PRODUCES 관계
        csv_file = f'{self.data_dir}/rel_produces.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  PRODUCES"):
                    session.run("""
                        MATCH (po:ProductionOrder {id: $from})
                        MATCH (p:Product {id: $to})
                        CREATE (po)-[:PRODUCES]->(p)
                    """, dict(row))
            print(f"  ✓ PRODUCES: {len(df)}개")
        
        # HAS_VARIANCE 관계
        csv_file = f'{self.data_dir}/rel_has_variance.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_VARIANCE"):
                    session.run("""
                        MATCH (po:ProductionOrder {id: $from})
                        MATCH (v:Variance {id: $to})
                        CREATE (po)-[:HAS_VARIANCE]->(v)
                    """, dict(row))
            print(f"  ✓ HAS_VARIANCE: {len(df)}개")
        
        # CAUSED_BY 관계
        csv_file = f'{self.data_dir}/rel_caused_by.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  CAUSED_BY"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (c:Cause {code: $to})
                        CREATE (v)-[:CAUSED_BY]->(c)
                    """, dict(row))
            print(f"  ✓ CAUSED_BY: {len(df)}개")
        
        # CONSUMES 관계
        csv_file = f'{self.data_dir}/rel_consumes.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  CONSUMES"):
                    session.run("""
                        MATCH (po:ProductionOrder {id: $from})
                        MATCH (m:Material {id: $to})
                        CREATE (po)-[:CONSUMES {
                            planned_qty: $planned_qty,
                            actual_qty: $actual_qty,
                            unit: $unit
                        }]->(m)
                    """, dict(row))
            print(f"  ✓ CONSUMES: {len(df)}개")
        
        # WORKS_AT 관계
        csv_file = f'{self.data_dir}/rel_works_at.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  WORKS_AT"):
                    session.run("""
                        MATCH (po:ProductionOrder {id: $from})
                        MATCH (wc:WorkCenter {id: $to})
                        CREATE (po)-[:WORKS_AT {
                            actual_time_min: $actual_time_min,
                            actual_qty: $actual_qty
                        }]->(wc)
                    """, dict(row))
            print(f"  ✓ WORKS_AT: {len(df)}개")
    
    def create_additional_relationships(self):
        """추가 관계 생성 (분석 최적화용)"""
        print("\n[4단계] 추가 관계 생성")
        
        with self.driver.session(database=self.database) as session:
            # RELATED_TO_MATERIAL: Variance -> Material 관계
            # (Variance가 어떤 자재와 관련있는지 직접 연결)
            print("  - RELATED_TO_MATERIAL 관계 생성 중...")
            result = session.run("""
                MATCH (v:Variance)<-[:HAS_VARIANCE]-(po:ProductionOrder)-[:CONSUMES]->(m:Material)
                WHERE v.cost_element = 'MATERIAL'
                WITH v, m, COUNT(*) as strength
                CREATE (v)-[:RELATED_TO_MATERIAL {strength: strength}]->(m)
                RETURN COUNT(*) as count
            """)
            count = result.single()['count']
            print(f"  ✓ RELATED_TO_MATERIAL: {count}개")
            
            # NEXT_ORDER: 시계열 순서 관계
            print("  - NEXT_ORDER 관계 생성 중...")
            result = session.run("""
                MATCH (po1:ProductionOrder), (po2:ProductionOrder)
                WHERE po1.order_date < po2.order_date
                WITH po1, po2, duration.between(po1.order_date, po2.order_date).days as days
                WHERE days <= 7
                ORDER BY po1.order_date, po2.order_date
                WITH po1, MIN(days) as min_days, COLLECT(po2)[0] as next_po
                CREATE (po1)-[:NEXT_ORDER {days_diff: min_days}]->(next_po)
                RETURN COUNT(*) as count
            """)
            count = result.single()['count']
            print(f"  ✓ NEXT_ORDER: {count}개")
            
            # SAME_PRODUCT: 동일 제품 생산 오더 연결
            print("  - SAME_PRODUCT 관계 생성 중...")
            result = session.run("""
                MATCH (po1:ProductionOrder)-[:PRODUCES]->(p:Product)<-[:PRODUCES]-(po2:ProductionOrder)
                WHERE po1.id < po2.id
                CREATE (po1)-[:SAME_PRODUCT]->(po2)
                RETURN COUNT(*) as count
            """)
            count = result.single()['count']
            print(f"  ✓ SAME_PRODUCT: {count}개")
    
    def verify_data(self):
        """데이터 로드 검증"""
        print("\n[5단계] 데이터 검증")
        
        with self.driver.session(database=self.database) as session:
            # 노드 개수 확인
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, COUNT(n) as count
                ORDER BY label
            """)
            
            print("\n노드 개수:")
            for record in result:
                print(f"  {record['label']}: {record['count']}개")
            
            # 관계 개수 확인
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, COUNT(r) as count
                ORDER BY type
            """)
            
            print("\n관계 개수:")
            for record in result:
                print(f"  {record['type']}: {record['count']}개")
            
            # 샘플 데이터 확인
            result = session.run("""
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                RETURN po.id, v.variance_amount
                ORDER BY ABS(v.variance_amount) DESC
                LIMIT 3
            """)
            
            print("\n최대 차이 발생 오더 (Top 3):")
            for record in result:
                print(f"  {record['po.id']}: {record['v.variance_amount']:,.0f}원")
    
    def load_all(self, clear_first=False):
        """전체 데이터 로드"""
        print("=" * 60)
        print("Neo4j 데이터 로드 시작")
        print("=" * 60)
        
        if not self.connect():
            return False
        
        try:
            if clear_first:
                self.clear_database()
            
            # 스키마 생성
            self.create_schema()
            
            # 노드 로드
            print("\n[2단계] 노드 생성")
            self.load_products()
            self.load_materials()
            self.load_work_centers()
            self.load_production_orders()
            self.load_variances()
            self.load_causes()
            
            # 관계 로드
            self.load_relationships()
            
            # 추가 관계 생성
            self.create_additional_relationships()
            
            # 검증
            self.verify_data()
            
            print("\n" + "=" * 60)
            print("데이터 로드 완료!")
            print("=" * 60)
            
            return True
        
        except Exception as e:
            print(f"\n✗ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.close()

def main():
    # 데이터 파일 존재 확인
    data_dir = 'data/neo4j_import'
    if not os.path.exists(data_dir):
        print(f"✗ 데이터 디렉토리가 없습니다: {data_dir}")
        print("먼저 'python data/generate_data.py'를 실행하세요.")
        return
    
    loader = Neo4jDataLoader()
    
    # 데이터베이스 초기화 여부 확인
    print("\n⚠️  기존 데이터를 삭제하고 새로 로드하시겠습니까?")
    print("   이 작업은 되돌릴 수 없습니다!")
    response = input("   계속하려면 'yes'를 입력하세요: ")
    
    if response.lower() == 'yes':
        loader.load_all(clear_first=True)
    else:
        print("작업이 취소되었습니다.")

if __name__ == "__main__":
    main()
