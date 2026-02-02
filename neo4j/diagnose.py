"""
Neo4j 데이터 진단 스크립트 (SSL 검증 비활성화)
"""
import os
import ssl
from dotenv import load_dotenv
from neo4j import GraphDatabase

# .env 파일 로드
load_dotenv()

# Neo4j 연결 정보
uri = os.getenv('NEO4J_URI')
username = os.getenv('NEO4J_USERNAME')
password = os.getenv('NEO4J_PASSWORD')

print("=" * 60)
print("Neo4j 데이터 진단 시작")
print("=" * 60)

try:
    # neo4j+s:// 를 bolt:// 로 변경 (SSL 컨텍스트 적용을 위해)
    uri = uri.replace('neo4j+s://', 'bolt://')
    uri = uri.replace('neo4j+ssc://', 'bolt://')
    
    # SSL 컨텍스트 생성 (인증서 검증 비활성화)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Neo4j 드라이버 생성
    driver = GraphDatabase.driver(
        uri, 
        auth=(username, password),
        ssl_context=ssl_context
    )
    
    print(f"✓ 연결 성공! (SSL 검증 비활성화)")
    print(f"  URI: {uri}")
    
    with driver.session() as session:
        # 1. 전체 노드 개수 확인
        print("\n📊 1. 노드 타입별 개수:")
        print("-" * 60)
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as NodeType, count(n) as Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  {record['NodeType']:20s}: {record['Count']:5d}개")
        
        # 2. 전체 관계 개수 확인
        print("\n🔗 2. 관계 타입별 개수:")
        print("-" * 60)
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as RelationType, count(r) as Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  {record['RelationType']:20s}: {record['Count']:5d}개")
        
        # 3. Variance 노드 샘플 확인
        print("\n📋 3. Variance 노드 샘플 (첫 3개):")
        print("-" * 60)
        result = session.run("""
            MATCH (v:Variance)
            RETURN v
            LIMIT 3
        """)
        for i, record in enumerate(result, 1):
            variance = record['v']
            print(f"\n  [{i}] Variance 노드:")
            for key, value in variance.items():
                print(f"      {key}: {value}")
        
        # 4. Variance 노드의 프로퍼티 키 확인
        print("\n🔑 4. Variance 노드의 프로퍼티 키:")
        print("-" * 60)
        result = session.run("""
            MATCH (v:Variance)
            RETURN keys(v) as Properties
            LIMIT 1
        """)
        for record in result:
            props = record['Properties']
            print(f"  프로퍼티 목록: {', '.join(props)}")
        
        # 5. 관계 연결 상태 확인
        print("\n🔗 5. 생산오더 -> Variance -> Cause 관계 확인:")
        print("-" * 60)
        result = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
            RETURN count(*) as Count
        """)
        for record in result:
            print(f"  연결된 경로 개수: {record['Count']}개")
        
        # 6. 샘플 차이 분석 데이터
        print("\n💰 6. 샘플 원가차이 데이터 (첫 5개):")
        print("-" * 60)
        result = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
            MATCH (po)-[:PRODUCES]->(p:Product)
            RETURN 
                po.id as order_id,
                p.name as product_name,
                v.id as variance_id,
                c.code as cause_code,
                c.description as cause_desc
            LIMIT 5
        """)
        for i, record in enumerate(result, 1):
            print(f"\n  [{i}] {record['order_id']} -> {record['product_name']}")
            print(f"      차이ID: {record['variance_id']}")
            print(f"      원인: {record['cause_code']} - {record['cause_desc']}")
    
    driver.close()
    print("\n" + "=" * 60)
    print("✅ 진단 완료!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
