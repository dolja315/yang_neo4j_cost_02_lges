"""
Neo4j Aura 연결 테스트 스크립트

Neo4j Aura 인스턴스와의 연결을 확인하고 기본 정보를 출력합니다.
"""

import os
import ssl
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class Neo4jConnection:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        self.database = os.getenv('NEO4J_DATABASE', 'neo4j')
        self.driver = None
        
    def connect(self):
        """Neo4j 데이터베이스에 연결 (SSL 검증 비활성화)"""
        try:
            # neo4j+s:// 를 bolt:// 로 변경 (SSL 컨텍스트 적용을 위해)
            uri = self.uri.replace('neo4j+s://', 'bolt://')
            uri = uri.replace('neo4j+ssc://', 'bolt://')
            
            # SSL 컨텍스트 생성 (인증서 검증 비활성화)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.driver = GraphDatabase.driver(
                uri,
                auth=(self.username, self.password),
                ssl_context=ssl_context
            )
            print(f"✓ Neo4j 연결 성공! (SSL 검증 비활성화)")
            print(f"  URI: {uri}")
            print(f"  Database: {self.database}")
            return True
        except Exception as e:
            print(f"✗ Neo4j 연결 실패: {str(e)}")
            return False
    
    def test_query(self):
        """간단한 테스트 쿼리 실행"""
        if not self.driver:
            print("✗ 연결이 되어있지 않습니다.")
            return False
        
        try:
            with self.driver.session(database=self.database) as session:
                # Neo4j 버전 확인
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                record = result.single()
                print(f"\n✓ 테스트 쿼리 성공!")
                print(f"  Neo4j 버전: {record['versions'][0]}")
                print(f"  Edition: {record['edition']}")
                
                # 노드 개수 확인
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()['count']
                print(f"  현재 노드 개수: {count}")
                
                return True
        except Exception as e:
            print(f"✗ 테스트 쿼리 실패: {str(e)}")
            return False
    
    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
            print("\n✓ 연결 종료")

def main():
    print("=" * 60)
    print("Neo4j Aura 연결 테스트")
    print("=" * 60)
    
    # 환경 변수 확인
    if not os.path.exists('.env'):
        print("\n✗ .env 파일이 없습니다!")
        print("  .env.example 파일을 .env로 복사하고 연결 정보를 입력하세요.")
        return
    
    neo4j = Neo4jConnection()
    
    # 연결 테스트
    if neo4j.connect():
        neo4j.test_query()
    
    neo4j.close()
    print("=" * 60)

if __name__ == "__main__":
    main()
