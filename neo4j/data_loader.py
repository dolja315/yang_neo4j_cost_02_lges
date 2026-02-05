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
            print(f"[OK] Neo4j 연결 성공: {uri}")
            return True
        except Exception as e:
            print(f"[X] Neo4j 연결 실패: {str(e)}")
            return False
    
    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
            print("[OK] 연결 종료")
    
    def clear_database(self):
        """데이터베이스 초기화 (주의!)"""
        print("\n[!]  데이터베이스 초기화 중...")
        with self.driver.session(database=self.database) as session:
            # 모든 노드와 관계 삭제
            session.run("MATCH (n) DETACH DELETE n")
        print("[OK] 데이터베이스 초기화 완료")
    
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
                "CREATE CONSTRAINT cause_code IF NOT EXISTS FOR (c:Cause) REQUIRE c.code IS UNIQUE",
                "CREATE CONSTRAINT quality_defect_id IF NOT EXISTS FOR (qd:QualityDefect) REQUIRE qd.id IS UNIQUE",
                "CREATE CONSTRAINT equipment_failure_id IF NOT EXISTS FOR (ef:EquipmentFailure) REQUIRE ef.id IS UNIQUE",
                "CREATE CONSTRAINT material_market_id IF NOT EXISTS FOR (mm:MaterialMarket) REQUIRE mm.id IS UNIQUE",
                "CREATE CONSTRAINT cost_pool_id IF NOT EXISTS FOR (cp:CostPool) REQUIRE cp.id IS UNIQUE",
                "CREATE CONSTRAINT monthly_state_id IF NOT EXISTS FOR (ms:MonthlyProductState) REQUIRE ms.id IS UNIQUE",
                "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT factor_id IF NOT EXISTS FOR (f:Factor) REQUIRE f.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"  [OK] {constraint.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  [X] 제약조건 생성 실패: {str(e)}")
            
            # 인덱스
            indexes = [
                "CREATE INDEX product_type IF NOT EXISTS FOR (p:Product) ON (p.type)",
                "CREATE INDEX material_type IF NOT EXISTS FOR (m:Material) ON (m.type)",
                "CREATE INDEX workcenter_process IF NOT EXISTS FOR (wc:WorkCenter) ON (wc.process_type)",
                "CREATE INDEX po_order_date IF NOT EXISTS FOR (po:ProductionOrder) ON (po.order_date)",
                "CREATE INDEX variance_element IF NOT EXISTS FOR (v:Variance) ON (v.cost_element)",
                "CREATE INDEX variance_type IF NOT EXISTS FOR (v:Variance) ON (v.variance_type)",
                "CREATE INDEX variance_severity IF NOT EXISTS FOR (v:Variance) ON (v.severity)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    print(f"  [OK] {index.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  [X] 인덱스 생성 실패: {str(e)}")
        
        # 인덱스가 생성될 때까지 대기
        time.sleep(2)
        print("[OK] 스키마 생성 완료")
    
    def load_products(self):
        """Product 노드 로드"""
        csv_file = f'{self.data_dir}/products.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Products"):
                # 배터리 데이터 구조 확인
                params = {
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'standard_cost': float(row['standard_cost']),
                    'active': bool(row['active'])
                }
                # 선택적 필드 추가
                if 'chemistry' in row and pd.notna(row['chemistry']):
                    params['chemistry'] = row['chemistry']
                if 'capacity' in row and pd.notna(row['capacity']):
                    params['capacity'] = float(row['capacity'])
                
                session.run("""
                    CREATE (p:Product)
                    SET p = $params
                """, params=params)
        
        print(f"  [OK] Product 노드: {len(df)}개")
    
    def load_materials(self):
        """Material 노드 로드"""
        csv_file = f'{self.data_dir}/materials.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Materials"):
                params = {
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'unit': row['unit'],
                    'standard_price': float(row['standard_price']),
                    'supplier_cd': row['supplier_cd'],
                    'active': bool(row['active'])
                }
                # 선택적 필드
                if 'origin' in row and pd.notna(row['origin']):
                    params['origin'] = row['origin']
                
                session.run("""
                    CREATE (m:Material)
                    SET m = $params
                """, params=params)
        
        print(f"  [OK] Material 노드: {len(df)}개")
    
    def load_work_centers(self):
        """WorkCenter 노드 로드"""
        csv_file = f'{self.data_dir}/work_centers.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  WorkCenters"):
                params = {
                    'id': row['id'],
                    'name': row['name'],
                    'process_type': row['process_type'],
                    'labor_rate_per_hour': float(row['labor_rate_per_hour']),
                    'overhead_rate_per_hour': float(row['overhead_rate_per_hour']),
                    'capacity_per_hour': int(row['capacity_per_hour']),
                    'active': bool(row['active'])
                }
                # 선택적 필드
                if 'location' in row and pd.notna(row['location']):
                    params['location'] = row['location']
                
                session.run("""
                    CREATE (wc:WorkCenter)
                    SET wc = $params
                """, params=params)
        
        print(f"  [OK] WorkCenter 노드: {len(df)}개")
    
    def load_production_orders(self):
        """ProductionOrder 노드 로드"""
        csv_file = f'{self.data_dir}/production_orders.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
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
        
        print(f"  [OK] ProductionOrder 노드: {len(df)}개")
    
    def load_variances(self):
        """Variance 노드 로드"""
        csv_file = f'{self.data_dir}/variances.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Variances"):
                params = {
                    'id': row['id'],
                    'order_no': row['order_no'],
                    'cost_element': row['cost_element'],
                    'variance_type': row['variance_type'],
                    'variance_amount': float(row['variance_amount']),
                    'variance_percent': float(row['variance_percent']),
                    'severity': row['severity'],
                    'cause_code': row['cause_code'],
                    'analysis_date': row['analysis_date']
                }
                # variance_name 필드 추가
                if 'variance_name' in row and pd.notna(row['variance_name']):
                    params['variance_name'] = row['variance_name']
                
                session.run("""
                    CREATE (v:Variance)
                    SET v = $params
                """, params=params)
        
        print(f"  [OK] Variance 노드: {len(df)}개")
    
    def load_causes(self):
        """Cause 노드 로드"""
        csv_file = f'{self.data_dir}/causes.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Causes"):
                params = {
                    'code': row['code'],
                    'category': row['category'],
                    'description': row['description'],
                    'responsible_dept': row['responsible_dept']
                }
                # 선택적 필드
                if 'variance_type' in row and pd.notna(row['variance_type']):
                    params['variance_type'] = row['variance_type']
                if 'detail' in row and pd.notna(row['detail']):
                    params['detail'] = row['detail']
                
                session.run("""
                    CREATE (c:Cause)
                    SET c = $params
                """, params=params)
        
        print(f"  [OK] Cause 노드: {len(df)}개")

    def load_cost_pools(self):
        """CostPool 노드 로드"""
        csv_file = f'{self.data_dir}/cost_pools.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return

        df = pd.read_csv(csv_file)

        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  CostPools"):
                params = dict(row)
                session.run("""
                    CREATE (cp:CostPool)
                    SET cp = $params
                """, params=params)

        print(f"  [OK] CostPool 노드: {len(df)}개")

    def load_monthly_states(self):
        """MonthlyProductState 노드 로드"""
        csv_file = f'{self.data_dir}/monthly_states.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return

        df = pd.read_csv(csv_file)

        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  MonthlyStates"):
                params = dict(row)
                session.run("""
                    CREATE (ms:MonthlyProductState)
                    SET ms = $params
                """, params=params)

        print(f"  [OK] MonthlyProductState 노드: {len(df)}개")

    def load_symptoms(self):
        """Symptom 노드 로드"""
        csv_file = f'{self.data_dir}/symptoms.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return

        df = pd.read_csv(csv_file)

        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Symptoms"):
                params = dict(row)
                session.run("""
                    CREATE (s:Symptom)
                    SET s = $params
                """, params=params)

        print(f"  [OK] Symptom 노드: {len(df)}개")

    def load_factors(self):
        """Factor 노드 로드"""
        csv_file = f'{self.data_dir}/factors.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return

        df = pd.read_csv(csv_file)

        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  Factors"):
                params = dict(row)
                session.run("""
                    CREATE (f:Factor)
                    SET f = $params
                """, params=params)

        print(f"  [OK] Factor 노드: {len(df)}개")
    
    def load_quality_defects(self):
        """QualityDefect 노드 로드"""
        csv_file = f'{self.data_dir}/quality_defects.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  QualityDefects"):
                params = dict(row)
                session.run("""
                    CREATE (qd:QualityDefect)
                    SET qd = $params
                """, params=params)
        
        print(f"  [OK] QualityDefect 노드: {len(df)}개")
    
    def load_equipment_failures(self):
        """EquipmentFailure 노드 로드"""
        csv_file = f'{self.data_dir}/equipment_failures.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  EquipmentFailures"):
                params = dict(row)
                session.run("""
                    CREATE (ef:EquipmentFailure)
                    SET ef = $params
                """, params=params)
        
        print(f"  [OK] EquipmentFailure 노드: {len(df)}개")
    
    def load_material_markets(self):
        """MaterialMarket 노드 로드"""
        csv_file = f'{self.data_dir}/material_markets.csv'
        if not os.path.exists(csv_file):
            print(f"  [X] 파일 없음: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        with self.driver.session(database=self.database) as session:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="  MaterialMarkets"):
                params = dict(row)
                session.run("""
                    CREATE (mm:MaterialMarket)
                    SET mm = $params
                """, params=params)
        
        print(f"  [OK] MaterialMarket 노드: {len(df)}개")
    
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
            print(f"  [OK] USES_MATERIAL: {len(df)}개")
        
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
            print(f"  [OK] PRODUCES: {len(df)}개")
        
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
            print(f"  [OK] HAS_VARIANCE: {len(df)}개")
        
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
            print(f"  [OK] CAUSED_BY: {len(df)}개")
        
        # CONSUMES 관계
        csv_file = f'{self.data_dir}/rel_consumes.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  CONSUMES"):
                    params = {
                        'from': row['from'],
                        'to': row['to'],
                        'planned_qty': float(row['planned_qty']),
                        'actual_qty': float(row['actual_qty']),
                        'unit': row['unit']
                    }
                    # 선택적 필드
                    if 'is_alternative' in row and pd.notna(row['is_alternative']):
                        params['is_alternative'] = row['is_alternative']
                    if 'batch_no' in row and pd.notna(row['batch_no']):
                        params['batch_no'] = row['batch_no']
                    
                    query = """
                        MATCH (po:ProductionOrder {id: $from})
                        MATCH (m:Material {id: $to})
                        CREATE (po)-[:CONSUMES {
                            planned_qty: $planned_qty,
                            actual_qty: $actual_qty,
                            unit: $unit,
                            is_alternative: COALESCE($is_alternative, 'N'),
                            batch_no: $batch_no
                        }]->(m)
                    """
                    session.run(query, params)
            print(f"  [OK] CONSUMES: {len(df)}개")
        
        # WORKS_AT 관계
        csv_file = f'{self.data_dir}/rel_works_at.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  WORKS_AT"):
                    params = {
                        'from': row['from'],
                        'to': row['to']
                    }
                    # 선택적 필드
                    if 'standard_time_min' in row and pd.notna(row['standard_time_min']):
                        params['standard_time_min'] = float(row['standard_time_min'])
                    if 'actual_time_min' in row and pd.notna(row['actual_time_min']):
                        params['actual_time_min'] = float(row['actual_time_min'])
                    if 'efficiency_rate' in row and pd.notna(row['efficiency_rate']):
                        params['efficiency_rate'] = float(row['efficiency_rate'])
                    if 'worker_count' in row and pd.notna(row['worker_count']):
                        params['worker_count'] = int(row['worker_count'])
                    if 'actual_qty' in row and pd.notna(row['actual_qty']):
                        params['actual_qty'] = int(row['actual_qty'])
                    if 'step_yield' in row and pd.notna(row['step_yield']):
                        params['step_yield'] = float(row['step_yield'])
                    if 'step_loss_qty' in row and pd.notna(row['step_loss_qty']):
                        params['step_loss_qty'] = int(row['step_loss_qty'])
                    
                    # CREATE 문 동적 생성
                    props = []
                    for key in params.keys():
                        if key not in ['from', 'to']:
                            props.append(f"{key}: $params.{key}")
                    props_str = ', '.join(props) if props else ''
                    
                    query = f"""
                        MATCH (po:ProductionOrder {{id: $params.from}})
                        MATCH (wc:WorkCenter {{id: $params.to}})
                        CREATE (po)-[:WORKS_AT {{{props_str}}}]->(wc)
                    """
                    session.run(query, params={'params': params})
            print(f"  [OK] WORKS_AT: {len(df)}개")
        
        # HAS_DEFECT 관계
        csv_file = f'{self.data_dir}/rel_has_defect.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_DEFECT"):
                    session.run("""
                        MATCH (c:Cause {code: $from})
                        MATCH (qd:QualityDefect {id: $to})
                        CREATE (c)-[:HAS_DEFECT]->(qd)
                    """, dict(row))
            print(f"  [OK] HAS_DEFECT: {len(df)}개")
        
        # HAS_FAILURE 관계
        csv_file = f'{self.data_dir}/rel_has_failure.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_FAILURE"):
                    session.run("""
                        MATCH (c:Cause {code: $from})
                        MATCH (ef:EquipmentFailure {id: $to})
                        CREATE (c)-[:HAS_FAILURE]->(ef)
                    """, dict(row))
            print(f"  [OK] HAS_FAILURE: {len(df)}개")
        
        # MARKET_PRICE 관계
        csv_file = f'{self.data_dir}/rel_market_price.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  MARKET_PRICE"):
                    session.run("""
                        MATCH (m:Material {id: $from})
                        MATCH (mm:MaterialMarket {id: $to})
                        CREATE (m)-[:MARKET_PRICE]->(mm)
                    """, dict(row))
            print(f"  [OK] MARKET_PRICE: {len(df)}개")

        # === [NEW] New Relationships ===

        # INCURRED_COST (WorkCenter -> CostPool)
        csv_file = f'{self.data_dir}/rel_incurred_cost.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  INCURRED_COST"):
                    session.run("""
                        MATCH (wc:WorkCenter {id: $from})
                        MATCH (cp:CostPool {id: $to})
                        CREATE (wc)-[:INCURRED_COST]->(cp)
                    """, dict(row))
            print(f"  [OK] INCURRED_COST: {len(df)}개")

        # ALLOCATES (CostPool -> ProductionOrder)
        csv_file = f'{self.data_dir}/rel_allocates.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  ALLOCATES"):
                    session.run("""
                        MATCH (cp:CostPool {id: $from})
                        MATCH (po:ProductionOrder {id: $to})
                        CREATE (cp)-[:ALLOCATES {
                            amount: $amount,
                            hours_used: $hours_used
                        }]->(po)
                    """, dict(row))
            print(f"  [OK] ALLOCATES: {len(df)}개")

        # HAS_MONTHLY_STATE (Product -> MonthlyProductState)
        csv_file = f'{self.data_dir}/rel_has_monthly_state.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_MONTHLY_STATE"):
                    session.run("""
                        MATCH (p:Product {id: $from})
                        MATCH (ms:MonthlyProductState {id: $to})
                        CREATE (p)-[:HAS_MONTHLY_STATE]->(ms)
                    """, dict(row))
            print(f"  [OK] HAS_MONTHLY_STATE: {len(df)}개")

        # NEXT_MONTH (MonthlyProductState -> MonthlyProductState)
        csv_file = f'{self.data_dir}/rel_next_month.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  NEXT_MONTH"):
                    session.run("""
                        MATCH (ms1:MonthlyProductState {id: $from})
                        MATCH (ms2:MonthlyProductState {id: $to})
                        CREATE (ms1)-[:NEXT_MONTH]->(ms2)
                    """, dict(row))
            print(f"  [OK] NEXT_MONTH: {len(df)}개")

        # LINKED_TO_SYMPTOM (Variance -> Symptom)
        csv_file = f'{self.data_dir}/rel_linked_to_symptom.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  LINKED_TO_SYMPTOM"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (s:Symptom {id: $to})
                        CREATE (v)-[:LINKED_TO_SYMPTOM]->(s)
                    """, dict(row))
            print(f"  [OK] LINKED_TO_SYMPTOM: {len(df)}개")

        # CAUSED_BY_FACTOR (Symptom -> Factor)
        csv_file = f'{self.data_dir}/rel_caused_by_factor.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  CAUSED_BY_FACTOR"):
                    session.run("""
                        MATCH (s:Symptom {id: $from})
                        MATCH (f:Factor {id: $to})
                        CREATE (s)-[:CAUSED_BY_FACTOR]->(f)
                    """, dict(row))
            print(f"  [OK] CAUSED_BY_FACTOR: {len(df)}개")

        # TRACED_TO_ROOT (Factor -> Cause)
        csv_file = f'{self.data_dir}/rel_traced_to_root.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  TRACED_TO_ROOT"):
                    session.run("""
                        MATCH (f:Factor {id: $from})
                        MATCH (c:Cause {code: $to})
                        CREATE (f)-[:TRACED_TO_ROOT]->(c)
                    """, dict(row))
            print(f"  [OK] TRACED_TO_ROOT: {len(df)}개")

        # === "Spider Legs" Relationships for Variance ===

        # RELATED_TO_MATERIAL (Variance -> Material)
        csv_file = f'{self.data_dir}/rel_variance_material.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  RELATED_TO_MATERIAL (Direct)"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (m:Material {id: $to})
                        CREATE (v)-[:RELATED_TO_MATERIAL]->(m)
                    """, dict(row))
            print(f"  [OK] RELATED_TO_MATERIAL (Direct): {len(df)}개")

        # OCCURRED_AT (Variance -> WorkCenter)
        csv_file = f'{self.data_dir}/rel_variance_workcenter.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  OCCURRED_AT"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (wc:WorkCenter {id: $to})
                        CREATE (v)-[:OCCURRED_AT]->(wc)
                    """, dict(row))
            print(f"  [OK] OCCURRED_AT: {len(df)}개")

        # HAS_DEFECT (Variance -> QualityDefect)
        csv_file = f'{self.data_dir}/rel_variance_defect.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_DEFECT (Direct)"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (qd:QualityDefect {id: $to})
                        CREATE (v)-[:HAS_DEFECT]->(qd)
                    """, dict(row))
            print(f"  [OK] HAS_DEFECT (Direct): {len(df)}개")

        # HAS_FAILURE (Variance -> EquipmentFailure)
        csv_file = f'{self.data_dir}/rel_variance_failure.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            with self.driver.session(database=self.database) as session:
                for _, row in tqdm(df.iterrows(), total=len(df), desc="  HAS_FAILURE (Direct)"):
                    session.run("""
                        MATCH (v:Variance {id: $from})
                        MATCH (ef:EquipmentFailure {id: $to})
                        CREATE (v)-[:HAS_FAILURE]->(ef)
                    """, dict(row))
            print(f"  [OK] HAS_FAILURE (Direct): {len(df)}개")
    
    def create_additional_relationships(self):
        """추가 관계 생성 (분석 최적화용)"""
        print("\n[4단계] 추가 관계 생성")
        
        with self.driver.session(database=self.database) as session:
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
            print(f"  [OK] NEXT_ORDER: {count}개")
            
            # SAME_PRODUCT: 동일 제품 생산 오더 연결
            print("  - SAME_PRODUCT 관계 생성 중...")
            result = session.run("""
                MATCH (po1:ProductionOrder)-[:PRODUCES]->(p:Product)<-[:PRODUCES]-(po2:ProductionOrder)
                WHERE po1.id < po2.id
                CREATE (po1)-[:SAME_PRODUCT]->(po2)
                RETURN COUNT(*) as count
            """)
            count = result.single()['count']
            print(f"  [OK] SAME_PRODUCT: {count}개")
    
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
            self.load_cost_pools()
            self.load_monthly_states()
            self.load_symptoms()
            self.load_factors()
            self.load_quality_defects()
            self.load_equipment_failures()
            self.load_material_markets()
            
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
            print(f"\n[X] 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.close()

def main():
    # 데이터 파일 존재 확인
    data_dir = 'data/neo4j_import'
    if not os.path.exists(data_dir):
        print(f"[X] 데이터 디렉토리가 없습니다: {data_dir}")
        print("먼저 'python data/generate_data.py'를 실행하세요.")
        return
    
    loader = Neo4jDataLoader()
    
    # 데이터베이스 초기화 여부 확인
    print("\n[!]  기존 데이터를 삭제하고 새로 로드하시겠습니까?")
    print("   이 작업은 되돌릴 수 없습니다!")
    response = input("   계속하려면 'yes'를 입력하세요: ")
    
    if response.lower() == 'yes':
        loader.load_all(clear_first=True)
    else:
        print("작업이 취소되었습니다.")

if __name__ == "__main__":
    main()
