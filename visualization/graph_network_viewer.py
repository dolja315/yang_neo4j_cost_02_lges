"""
Neo4j 그래프 네트워크 시각화 도구

Neo4j의 노드와 엣지를 인터랙티브하게 탐색할 수 있는 도구입니다.
실행: python visualization/graph_network_viewer.py
"""
import os
import ssl
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network
import networkx as nx

load_dotenv()

class Neo4jGraphVisualizer:
    def __init__(self):
        uri = os.getenv('NEO4J_URI')
        username = os.getenv('NEO4J_USERNAME')
        password = os.getenv('NEO4J_PASSWORD')
        
        uri = uri.replace('neo4j+s://', 'bolt://')
        uri = uri.replace('neo4j+ssc://', 'bolt://')
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password), ssl_context=ssl_context)
    
    def close(self):
        self.driver.close()
    
    def get_graph_data(self, limit=100):
        """Neo4j에서 노드와 관계 데이터 가져오기"""
        with self.driver.session() as session:
            # 전체 그래프 구조 가져오기 (제한적으로)
            result = session.run("""
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
            """, limit=limit)
            
            nodes = {}
            edges = []
            
            for record in result:
                # 시작 노드
                start_node = record['n']
                start_id = start_node.element_id
                start_labels = list(start_node.labels)[0] if start_node.labels else 'Node'
                
                if start_id not in nodes:
                    nodes[start_id] = {
                        'id': start_id,
                        'label': start_labels,
                        'properties': dict(start_node)
                    }
                
                # 끝 노드
                end_node = record['m']
                end_id = end_node.element_id
                end_labels = list(end_node.labels)[0] if end_node.labels else 'Node'
                
                if end_id not in nodes:
                    nodes[end_id] = {
                        'id': end_id,
                        'label': end_labels,
                        'properties': dict(end_node)
                    }
                
                # 관계
                relationship = record['r']
                edges.append({
                    'from': start_id,
                    'to': end_id,
                    'type': relationship.type,
                    'properties': dict(relationship)
                })
            
            return list(nodes.values()), edges
    
    def get_sample_subgraph(self, node_type=None, center_id=None, depth=2):
        """특정 노드를 중심으로 한 서브그래프 가져오기"""
        with self.driver.session() as session:
            if center_id:
                # 특정 노드 중심
                query = """
                    MATCH path = (center)-[*1..2]-(n)
                    WHERE center.id = $center_id
                    UNWIND relationships(path) as r
                    RETURN startNode(r) as n1, r, endNode(r) as n2
                    LIMIT 200
                """
                result = session.run(query, center_id=center_id)
            elif node_type:
                # 특정 노드 타입
                query = f"""
                    MATCH (center:{node_type})
                    WITH center LIMIT 5
                    MATCH path = (center)-[*1..{depth}]-(n)
                    UNWIND relationships(path) as r
                    RETURN startNode(r) as n1, r, endNode(r) as n2
                    LIMIT 200
                """
                result = session.run(query)
            else:
                # 샘플 데이터
                result = session.run("""
                    MATCH (n)-[r]->(m)
                    RETURN n as n1, r, m as n2
                    LIMIT 200
                """)
            
            nodes = {}
            edges = []
            
            for record in result:
                # 시작 노드
                start_node = record['n1']
                start_id = start_node.element_id
                start_labels = list(start_node.labels)[0] if start_node.labels else 'Node'
                
                if start_id not in nodes:
                    nodes[start_id] = {
                        'id': start_id,
                        'label': start_labels,
                        'properties': dict(start_node)
                    }
                
                # 끝 노드
                end_node = record['n2']
                end_id = end_node.element_id
                end_labels = list(end_node.labels)[0] if end_node.labels else 'Node'
                
                if end_id not in nodes:
                    nodes[end_id] = {
                        'id': end_id,
                        'label': end_labels,
                        'properties': dict(end_node)
                    }
                
                # 관계
                relationship = record['r']
                edges.append({
                    'from': start_id,
                    'to': end_id,
                    'type': relationship.type,
                    'properties': dict(relationship)
                })
            
            return list(nodes.values()), edges

def create_network_visualization(nodes, edges, output_file='neo4j_graph_network.html'):
    """PyVis로 인터랙티브 네트워크 그래프 생성"""
    
    # PyVis 네트워크 생성
    net = Network(
        height='900px',
        width='100%',
        bgcolor='#222222',
        font_color='white',
        directed=True
    )
    
    # 물리 엔진 설정 (부드러운 애니메이션)
    net.barnes_hut(
        gravity=-80000,
        central_gravity=0.3,
        spring_length=250,
        spring_strength=0.001,
        damping=0.09,
        overlap=0
    )
    
    # 노드 타입별 색상
    color_map = {
        'Product': '#FF6B6B',
        'Material': '#4ECDC4',
        'ProductionOrder': '#45B7D1',
        'WorkCenter': '#FFA07A',
        'Variance': '#98D8C8',
        'Cause': '#F7DC6F'
    }
    
    # 노드 추가
    for node in nodes:
        node_id = node['id']
        node_label = node['label']
        props = node['properties']
        
        # 노드 표시 텍스트
        if 'id' in props:
            title = f"{node_label}: {props['id']}"
        elif 'name' in props:
            title = f"{node_label}: {props['name']}"
        elif 'code' in props:
            title = f"{node_label}: {props['code']}"
        else:
            title = node_label
        
        # hover 정보
        hover_text = f"<b>{node_label}</b><br>"
        for key, value in list(props.items())[:5]:  # 처음 5개 속성만
            hover_text += f"{key}: {value}<br>"
        
        # 노드 색상
        color = color_map.get(node_label, '#95A5A6')
        
        net.add_node(
            node_id,
            label=title,
            title=hover_text,
            color=color,
            size=25,
            shape='dot'
        )
    
    # 엣지 추가
    for edge in edges:
        label = edge['type']
        
        # hover 정보
        hover_text = f"<b>{label}</b><br>"
        if edge['properties']:
            for key, value in list(edge['properties'].items())[:3]:
                hover_text += f"{key}: {value}<br>"
        
        net.add_edge(
            edge['from'],
            edge['to'],
            title=hover_text,
            label=label,
            color='#888888',
            arrows='to',
            width=2
        )
    
    # 옵션 설정
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "font": {
          "size": 14,
          "face": "arial"
        }
      },
      "edges": {
        "color": {
          "inherit": false
        },
        "smooth": {
          "type": "continuous"
        },
        "font": {
          "size": 11,
          "align": "middle"
        }
      },
      "physics": {
        "enabled": true,
        "stabilization": {
          "enabled": true,
          "iterations": 200
        }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true,
        "multiselect": true,
        "tooltipDelay": 100
      }
    }
    """)
    
    # HTML 저장
    net.save_graph(output_file)
    
    return output_file

def main():
    print("=" * 80)
    print("  Neo4j 그래프 네트워크 시각화")
    print("=" * 80)
    
    viz = Neo4jGraphVisualizer()
    
    try:
        print("\n어떤 그래프를 시각화하시겠습니까?")
        print("1. 전체 그래프 샘플 (200개 관계)")
        print("2. ProductionOrder 중심 그래프")
        print("3. Variance 원인 추적 그래프")
        print("4. Material 소비 그래프")
        
        choice = input("\n선택 (1-4, 엔터=1): ").strip() or "1"
        
        if choice == "2":
            print("\n📊 ProductionOrder 중심 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='ProductionOrder', depth=2)
        elif choice == "3":
            print("\n🔍 Variance 원인 추적 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='Variance', depth=2)
        elif choice == "4":
            print("\n🏭 Material 소비 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='Material', depth=2)
        else:
            print("\n📈 전체 그래프 샘플 생성 중...")
            nodes, edges = viz.get_graph_data(limit=200)
        
        print(f"\n✅ 데이터 로드 완료!")
        print(f"   노드: {len(nodes)}개")
        print(f"   엣지: {len(edges)}개")
        
        print("\n🎨 네트워크 그래프 생성 중...")
        output_file = create_network_visualization(nodes, edges)
        
        print(f"\n✅ 그래프 생성 완료!")
        print(f"📄 파일: {output_file}")
        print(f"🌐 브라우저에서 열립니다...")
        
        # 브라우저에서 자동 열기
        import webbrowser
        file_path = os.path.abspath(output_file)
        webbrowser.open('file://' + file_path)
        
        print("\n💡 사용 방법:")
        print("   - 마우스로 드래그: 노드 이동")
        print("   - 마우스 휠: 확대/축소")
        print("   - 노드 클릭: 선택")
        print("   - 노드 호버: 상세 정보")
        print("   - 우측 하단 버튼: 네비게이션")
        
    finally:
        viz.close()
        print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
