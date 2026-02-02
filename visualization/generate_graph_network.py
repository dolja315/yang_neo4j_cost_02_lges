"""
Neo4j 그래프 네트워크 시각화 - 자동 실행 버전

실행: python visualization/generate_graph_network.py [옵션]

옵션:
  - all: 전체 그래프 샘플 (기본)
  - order: ProductionOrder 중심
  - variance: Variance 원인 추적
  - material: Material 소비 그래프
"""
import os
import ssl
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network

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
    
    def get_sample_subgraph(self, node_type=None, depth=2):
        """특정 노드를 중심으로 한 서브그래프 가져오기"""
        with self.driver.session() as session:
            if node_type:
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

def create_network_visualization(nodes, edges, output_file='neo4j_graph_network.html', title='Neo4j 그래프'):
    """PyVis로 인터랙티브 네트워크 그래프 생성"""
    
    # PyVis 네트워크 생성
    net = Network(
        height='900px',
        width='100%',
        bgcolor='#1a1a1a',
        font_color='white',
        directed=True,
        heading=title
    )
    
    # 물리 엔진 설정
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.001,
        damping=0.09,
        overlap=0
    )
    
    # 노드 타입별 색상 및 크기
    node_config = {
        'Product': {'color': '#FF6B6B', 'size': 30},
        'Material': {'color': '#4ECDC4', 'size': 25},
        'ProductionOrder': {'color': '#45B7D1', 'size': 35},
        'WorkCenter': {'color': '#FFA07A', 'size': 28},
        'Variance': {'color': '#98D8C8', 'size': 20},
        'Cause': {'color': '#F7DC6F', 'size': 25}
    }
    
    # 노드 추가
    for node in nodes:
        node_id = node['id']
        node_label = node['label']
        props = node['properties']
        
        # 노드 표시 텍스트
        display_text = ""
        if 'id' in props:
            display_text = props['id']
        elif 'name' in props:
            display_text = props['name']
        elif 'code' in props:
            display_text = props['code']
        else:
            display_text = node_label
        
        # 짧게 표시
        if len(str(display_text)) > 15:
            display_text = str(display_text)[:12] + "..."
        
        # hover 정보
        hover_text = f"<h3>{node_label}</h3>"
        for key, value in list(props.items())[:8]:
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            hover_text += f"<b>{key}:</b> {value_str}<br>"
        
        # 노드 설정
        config = node_config.get(node_label, {'color': '#95A5A6', 'size': 20})
        
        net.add_node(
            node_id,
            label=f"{node_label}\n{display_text}",
            title=hover_text,
            color=config['color'],
            size=config['size'],
            shape='dot',
            font={'size': 12, 'color': 'white', 'face': 'arial'}
        )
    
    # 엣지 추가
    edge_colors = {
        'USES_MATERIAL': '#FF6B6B',
        'PRODUCES': '#4ECDC4',
        'CONSUMES': '#45B7D1',
        'WORKS_AT': '#FFA07A',
        'HAS_VARIANCE': '#98D8C8',
        'CAUSED_BY': '#F7DC6F'
    }
    
    for edge in edges:
        label = edge['type']
        
        # hover 정보
        hover_text = f"<h3>{label}</h3>"
        if edge['properties']:
            for key, value in list(edge['properties'].items())[:5]:
                hover_text += f"<b>{key}:</b> {value}<br>"
        
        color = edge_colors.get(label, '#888888')
        
        net.add_edge(
            edge['from'],
            edge['to'],
            title=hover_text,
            label=label,
            color=color,
            arrows={'to': {'enabled': True, 'scaleFactor': 0.8}},
            width=2,
            font={'size': 10, 'color': 'white', 'align': 'middle'}
        )
    
    # 옵션 설정
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 3,
        "borderWidthSelected": 5,
        "shadow": {
          "enabled": true,
          "color": "rgba(0,0,0,0.5)",
          "size": 10,
          "x": 5,
          "y": 5
        }
      },
      "edges": {
        "smooth": {
          "type": "continuous"
        },
        "shadow": {
          "enabled": true
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
        "keyboard": {
          "enabled": true
        },
        "multiselect": true,
        "tooltipDelay": 100,
        "zoomView": true,
        "dragView": true
      }
    }
    """)
    
    # HTML 저장 (UTF-8 인코딩 명시)
    html_content = net.generate_html()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file

def main():
    print("=" * 80)
    print("  Neo4j 그래프 네트워크 시각화")
    print("=" * 80)
    
    # 명령줄 인자로 옵션 받기
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    viz = Neo4jGraphVisualizer()
    
    try:
        if mode == 'order':
            print("\n📊 ProductionOrder 중심 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='ProductionOrder', depth=2)
            title = "생산오더 중심 그래프"
        elif mode == 'variance':
            print("\n🔍 Variance 원인 추적 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='Variance', depth=2)
            title = "원가차이 원인 추적 그래프"
        elif mode == 'material':
            print("\n🏭 Material 소비 그래프 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type='Material', depth=2)
            title = "자재 소비 그래프"
        else:
            print("\n📈 전체 그래프 샘플 생성 중...")
            nodes, edges = viz.get_sample_subgraph(node_type=None, depth=2)
            title = "Neo4j 전체 그래프 샘플"
        
        print(f"\n✅ 데이터 로드 완료!")
        print(f"   노드: {len(nodes)}개")
        print(f"   엣지: {len(edges)}개")
        
        print("\n🎨 네트워크 그래프 생성 중...")
        output_file = create_network_visualization(nodes, edges, title=title)
        
        print(f"\n✅ 그래프 생성 완료!")
        print(f"📄 파일: {output_file}")
        print(f"🌐 브라우저에서 열립니다...")
        
        # 브라우저에서 자동 열기
        import webbrowser
        file_path = os.path.abspath(output_file)
        webbrowser.open('file://' + file_path)
        
        print("\n💡 사용 방법:")
        print("   🖱️  마우스 드래그: 노드 이동")
        print("   🔍 마우스 휠: 확대/축소")
        print("   👆 노드 클릭: 선택/고정")
        print("   📋 노드 호버: 상세 정보 표시")
        print("   🎮 우측 버튼: 네비게이션 컨트롤")
        print("   ⌨️  키보드: 화살표 키로 이동")
        
        print("\n🎨 노드 색상:")
        print("   🔴 Product (제품)")
        print("   🔵 Material (자재)")
        print("   🟢 ProductionOrder (생산오더)")
        print("   🟠 WorkCenter (작업장)")
        print("   🟡 Variance (차이)")
        print("   🟢 Cause (원인)")
        
        print("\n📝 다른 그래프 보기:")
        print("   python visualization/generate_graph_network.py order")
        print("   python visualization/generate_graph_network.py variance")
        print("   python visualization/generate_graph_network.py material")
        
    finally:
        viz.close()
        print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
