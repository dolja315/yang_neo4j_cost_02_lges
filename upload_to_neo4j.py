"""
Neo4j 데이터 로더 - 자동 실행 버전
"""
import sys
sys.path.append('neo4j')
from data_loader import Neo4jDataLoader

if __name__ == "__main__":
    print("\n[Semiconductor] 반도체 원가 데이터를 Neo4j에 업로드합니다...")
    print("=" * 70)
    
    loader = Neo4jDataLoader()
    success = loader.load_all(clear_first=True)
    
    if success:
        print("\n[OK] 성공적으로 업로드되었습니다!")
        print("\n다음 단계:")
        print("  1. Flask API 서버 시작: python visualization/graph_api_server.py")
        print("  2. 브라우저에서 접속: http://localhost:5000")
    else:
        print("\n[FAIL] 업로드 실패")
        sys.exit(1)
