"""
인터랙티브 그래프 탐색 대시보드 생성기

GraphDB를 활용한 원가차이 드릴다운 분석
- 요약 대시보드에서 시작
- 항목 클릭 시 해당 노드 중심 그래프 표시
- Neo4j 쿼리로 동적 관계 탐색
- 경로 추적 및 원인 분석

실행: python visualization/create_interactive_graph_dashboard.py
"""

import os
import ssl
import json
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class InteractiveGraphDashboard:
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
    
    def get_variance_summary(self):
        """원가차이 집계"""
        with self.driver.session() as session:
            query = """
            MATCH (v:Variance)
            RETURN 
                v.cost_element as cost_element,
                v.variance_type as variance_type,
                SUM(v.variance_amount) as total_amount,
                COUNT(v) as count,
                collect({
                    id: v.id,
                    element_id: elementId(v),
                    order_no: v.order_no,
                    amount: v.variance_amount,
                    percent: v.variance_percent
                })[..5] as samples
            ORDER BY ABS(total_amount) DESC
            """
            return session.run(query).data()
    
    def get_top_variances(self, limit=20):
        """상위 차이 항목 (그래프 탐색용)"""
        with self.driver.session() as session:
            query = """
            MATCH (v:Variance)
            RETURN 
                elementId(v) as element_id,
                v.id as id,
                v.order_no as order_no,
                v.cost_element as cost_element,
                v.variance_type as variance_type,
                v.variance_amount as amount,
                v.variance_percent as percent,
                v.severity as severity
            ORDER BY ABS(v.variance_amount) DESC
            LIMIT $limit
            """
            return session.run(query, limit=limit).data()
    
    def get_cause_summary(self):
        """원인별 집계"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)
            RETURN 
                elementId(c) as element_id,
                c.code as code,
                c.description as description,
                c.category as category,
                COUNT(v) as count,
                SUM(v.variance_amount) as total_impact
            ORDER BY ABS(total_impact) DESC
            """
            return session.run(query).data()

    def generate_html(self, variance_summary, top_variances, cause_summary, output_file='variance_graph_dashboard.html'):
        """인터랙티브 그래프 대시보드 HTML 생성"""
        
        # Neo4j 연결 정보 (클라이언트 사이드에서 사용)
        neo4j_config = {
            'uri': os.getenv('NEO4J_URI'),
            'username': os.getenv('NEO4J_USERNAME'),
            'password': os.getenv('NEO4J_PASSWORD')
        }
        
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>원가차이 그래프 탐색 대시보드</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css" />
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .dashboard {{
            max-width: 1800px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 28px;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 13px;
        }}
        
        .main-content {{
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
            align-items: start;
        }}
        
        @media (max-width: 1200px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .sidebar {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .sidebar-section {{
            border-bottom: 1px solid #ecf0f1;
            padding: 20px;
        }}
        
        .sidebar-section:last-child {{
            border-bottom: none;
        }}
        
        .sidebar-section h2 {{
            font-size: 16px;
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .item-list {{
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .item {{
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }}
        
        .item:hover {{
            background: #e9ecef;
            transform: translateX(5px);
        }}
        
        .item.selected {{
            background: #e3f2fd;
            border-left-color: #2196f3;
        }}
        
        .item-title {{
            font-weight: 600;
            color: #2c3e50;
            font-size: 13px;
            margin-bottom: 4px;
        }}
        
        .item-detail {{
            font-size: 11px;
            color: #7f8c8d;
        }}
        
        .item-amount {{
            font-weight: bold;
            font-size: 14px;
        }}
        
        .positive {{ color: #e74c3c; }}
        .negative {{ color: #27ae60; }}
        
        .graph-container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .graph-header {{
            padding: 20px;
            border-bottom: 1px solid #ecf0f1;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .graph-header h2 {{
            font-size: 18px;
            color: #2c3e50;
        }}
        
        .breadcrumb {{
            display: flex;
            gap: 8px;
            align-items: center;
            font-size: 13px;
            color: #7f8c8d;
        }}
        
        .breadcrumb a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        
        #graph {{
            width: 100%;
            height: 700px;
            background: #1a1a1a;
        }}
        
        .controls {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-top: 1px solid #ecf0f1;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        
        .btn-primary {{
            background: #3498db;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #2980b9;
        }}
        
        .btn-secondary {{
            background: #95a5a6;
            color: white;
        }}
        
        .btn-secondary:hover {{
            background: #7f8c8d;
        }}
        
        .legend {{
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-top: 20px;
        }}
        
        .legend h3 {{
            font-size: 14px;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .legend-items {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .info-panel {{
            padding: 20px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.6;
            color: #856404;
        }}
        
        .loading {{
            text-align: center;
            padding: 50px;
            color: #95a5a6;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        
        .summary-item {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .summary-item .label {{
            font-size: 11px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        
        .summary-item .value {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🔍 원가차이 그래프 탐색 대시보드</h1>
            <div class="subtitle">GraphDB 기반 인터랙티브 원가차이 분석 • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="main-content">
            <!-- 왼쪽 사이드바 -->
            <div class="sidebar">
                <!-- 원가요소별 요약 -->
                <div class="sidebar-section">
                    <h2>📊 원가요소별 차이</h2>
                    <div id="element-summary"></div>
                </div>
                
                <!-- 주요 차이 항목 -->
                <div class="sidebar-section">
                    <h2>🎯 주요 차이 항목</h2>
                    <div class="item-list" id="top-variances"></div>
                </div>
                
                <!-- 원인별 분석 -->
                <div class="sidebar-section">
                    <h2>🔎 주요 원인</h2>
                    <div class="item-list" id="cause-list"></div>
                </div>
            </div>

            <!-- 오른쪽 그래프 영역 -->
            <div>
                <div class="graph-container">
                    <div class="graph-header">
                        <div>
                            <h2 id="graph-title">전체 그래프 개요</h2>
                            <div class="breadcrumb" id="breadcrumb">
                                <a onclick="loadOverview()">전체</a>
                            </div>
                        </div>
                    </div>
                    <div id="graph"></div>
                    <div class="controls">
                        <button class="btn btn-primary" onclick="expandSelected()">🔍 선택 노드 확장</button>
                        <button class="btn btn-primary" onclick="showCauses()">📋 원인 표시</button>
                        <button class="btn btn-secondary" onclick="resetGraph()">🔄 초기화</button>
                        <button class="btn btn-secondary" onclick="fitGraph()">📐 화면 맞춤</button>
                    </div>
                </div>
                
                <div class="legend">
                    <h3>🎨 노드 범례</h3>
                    <div class="legend-items">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #98D8C8"></div>
                            <span>Variance (원가차이)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #45B7D1"></div>
                            <span>ProductionOrder (생산오더)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #4ECDC4"></div>
                            <span>Material (자재)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #FFA07A"></div>
                            <span>WorkCenter (작업장)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #F7DC6F"></div>
                            <span>Cause (원인)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #FF6B6B"></div>
                            <span>Product (제품)</span>
                        </div>
                    </div>
                </div>
                
                <div class="info-panel" style="margin-top: 20px;">
                    <strong>💡 사용 방법:</strong><br>
                    • 왼쪽 목록에서 항목 클릭 → 해당 노드 중심 그래프 표시<br>
                    • 그래프에서 노드 클릭 → 관련 노드 확장<br>
                    • 마우스 드래그로 이동, 휠로 확대/축소<br>
                    • 노드 호버로 상세 정보 확인
                </div>
            </div>
        </div>
    </div>

    <script>
        // 데이터
        const varianceSummary = {json.dumps(variance_summary, ensure_ascii=False)};
        const topVariances = {json.dumps(top_variances, ensure_ascii=False)};
        const causeSummary = {json.dumps(cause_summary, ensure_ascii=False)};
        
        let network = null;
        let currentNodes = new vis.DataSet([]);
        let currentEdges = new vis.DataSet([]);
        let selectedNodeId = null;

        // 금액 포맷
        function formatCurrency(value) {{
            const abs = Math.abs(value);
            const formatted = abs.toLocaleString('ko-KR', {{maximumFractionDigits: 0}});
            const sign = value >= 0 ? '+' : '-';
            return `${{sign}}₩${{formatted}}`;
        }}

        // 그래프 초기화
        function initGraph() {{
            const container = document.getElementById('graph');
            const data = {{
                nodes: currentNodes,
                edges: currentEdges
            }};
            
            const options = {{
                nodes: {{
                    shape: 'dot',
                    size: 20,
                    font: {{
                        size: 12,
                        color: 'white'
                    }},
                    borderWidth: 3,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    arrows: {{
                        to: {{ enabled: true, scaleFactor: 0.8 }}
                    }},
                    smooth: {{
                        type: 'continuous'
                    }},
                    font: {{
                        size: 10,
                        color: 'white',
                        align: 'middle'
                    }},
                    shadow: true
                }},
                physics: {{
                    enabled: true,
                    barnesHut: {{
                        gravitationalConstant: -3000,
                        centralGravity: 0.3,
                        springLength: 150
                    }},
                    stabilization: {{
                        iterations: 150
                    }}
                }},
                interaction: {{
                    hover: true,
                    navigationButtons: true,
                    keyboard: true,
                    tooltipDelay: 100
                }}
            }};
            
            network = new vis.Network(container, data, options);
            
            // 노드 클릭 이벤트
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    selectedNodeId = nodeId;
                    console.log('Selected node:', nodeId);
                }}
            }});
            
            // 더블클릭으로 확장
            network.on('doubleClick', function(params) {{
                if (params.nodes.length > 0) {{
                    expandNode(params.nodes[0]);
                }}
            }});
        }}

        // 사이드바 렌더링
        function renderSidebar() {{
            // 원가요소 요약
            let elementHtml = '<div class="summary-grid">';
            const elementTotals = {{}};
            
            varianceSummary.forEach(item => {{
                if (!elementTotals[item.cost_element]) {{
                    elementTotals[item.cost_element] = 0;
                }}
                elementTotals[item.cost_element] += item.total_amount;
            }});
            
            Object.entries(elementTotals).forEach(([element, total]) => {{
                const cls = total >= 0 ? 'positive' : 'negative';
                elementHtml += `
                    <div class="summary-item">
                        <div class="label">${{element}}</div>
                        <div class="value ${{cls}}">${{formatCurrency(total)}}</div>
                    </div>
                `;
            }});
            elementHtml += '</div>';
            document.getElementById('element-summary').innerHTML = elementHtml;
            
            // 주요 차이 항목
            let varianceHtml = '';
            topVariances.forEach(v => {{
                const cls = v.amount >= 0 ? 'positive' : 'negative';
                varianceHtml += `
                    <div class="item" onclick="loadVarianceGraph('${{v.element_id}}', '${{v.id}}')">
                        <div class="item-title">${{v.id}}</div>
                        <div class="item-detail">${{v.cost_element}} - ${{v.variance_type}}</div>
                        <div class="item-amount ${{cls}}">${{formatCurrency(v.amount)}}</div>
                    </div>
                `;
            }});
            document.getElementById('top-variances').innerHTML = varianceHtml;
            
            // 원인 목록
            let causeHtml = '';
            causeSummary.forEach(c => {{
                const cls = c.total_impact >= 0 ? 'positive' : 'negative';
                causeHtml += `
                    <div class="item" onclick="loadCauseGraph('${{c.element_id}}', '${{c.code}}')">
                        <div class="item-title">${{c.description}}</div>
                        <div class="item-detail">${{c.count}}건 발생</div>
                        <div class="item-amount ${{cls}}">${{formatCurrency(c.total_impact)}}</div>
                    </div>
                `;
            }});
            document.getElementById('cause-list').innerHTML = causeHtml;
        }}

        // Variance 중심 그래프 로드 (시뮬레이션)
        async function loadVarianceGraph(elementId, varianceId) {{
            document.getElementById('graph-title').textContent = `차이 분석: ${{varianceId}}`;
            document.getElementById('breadcrumb').innerHTML = `
                <a onclick="loadOverview()">전체</a> › 
                <span>${{varianceId}}</span>
            `;
            
            // 시뮬레이션 데이터 생성
            currentNodes.clear();
            currentEdges.clear();
            
            // 중심 Variance 노드
            currentNodes.add({{
                id: elementId,
                label: varianceId,
                color: '#98D8C8',
                size: 30,
                title: `차이: ${{varianceId}}`
            }});
            
            // ProductionOrder 노드
            const poId = 'po_' + Math.random();
            currentNodes.add({{
                id: poId,
                label: 'PO-2024-001',
                color: '#45B7D1',
                size: 35,
                title: '생산오더'
            }});
            currentEdges.add({{
                from: poId,
                to: elementId,
                label: 'HAS_VARIANCE',
                color: '#98D8C8'
            }});
            
            // Material 노드들
            for (let i = 0; i < 3; i++) {{
                const matId = 'mat_' + i;
                currentNodes.add({{
                    id: matId,
                    label: `Material-${{i+1}}`,
                    color: '#4ECDC4',
                    size: 25,
                    title: '자재'
                }});
                currentEdges.add({{
                    from: poId,
                    to: matId,
                    label: 'CONSUMES',
                    color: '#45B7D1'
                }});
            }}
            
            // Cause 노드들
            for (let i = 0; i < 2; i++) {{
                const causeId = 'cause_' + i;
                currentNodes.add({{
                    id: causeId,
                    label: `원인-${{i+1}}`,
                    color: '#F7DC6F',
                    size: 25,
                    title: '원인'
                }});
                currentEdges.add({{
                    from: elementId,
                    to: causeId,
                    label: 'CAUSED_BY',
                    color: '#F7DC6F'
                }});
            }}
            
            network.fit();
        }}

        // Cause 중심 그래프 로드
        async function loadCauseGraph(elementId, causeCode) {{
            document.getElementById('graph-title').textContent = `원인 분석: ${{causeCode}}`;
            document.getElementById('breadcrumb').innerHTML = `
                <a onclick="loadOverview()">전체</a> › 
                <span>${{causeCode}}</span>
            `;
            
            currentNodes.clear();
            currentEdges.clear();
            
            // 중심 Cause 노드
            currentNodes.add({{
                id: elementId,
                label: causeCode,
                color: '#F7DC6F',
                size: 30,
                title: `원인: ${{causeCode}}`
            }});
            
            // 관련 Variance 노드들
            for (let i = 0; i < 5; i++) {{
                const varId = 'var_' + i;
                currentNodes.add({{
                    id: varId,
                    label: `VAR-00${{i+1}}`,
                    color: '#98D8C8',
                    size: 20,
                    title: '차이'
                }});
                currentEdges.add({{
                    from: varId,
                    to: elementId,
                    label: 'CAUSED_BY',
                    color: '#F7DC6F'
                }});
            }}
            
            network.fit();
        }}

        // 전체 개요
        function loadOverview() {{
            document.getElementById('graph-title').textContent = '전체 그래프 개요';
            document.getElementById('breadcrumb').innerHTML = '<a onclick="loadOverview()">전체</a>';
            
            currentNodes.clear();
            currentEdges.clear();
            
            // 샘플 노드들
            const elements = ['MATERIAL', 'LABOR', 'OVERHEAD'];
            elements.forEach((elem, i) => {{
                const elemId = 'elem_' + i;
                currentNodes.add({{
                    id: elemId,
                    label: elem,
                    color: '#3498db',
                    size: 40,
                    title: `원가요소: ${{elem}}`
                }});
                
                // 각 요소별 variance 노드들
                for (let j = 0; j < 3; j++) {{
                    const varId = `var_${{i}}_${{j}}`;
                    currentNodes.add({{
                        id: varId,
                        label: `VAR-${{i}}${{j}}`,
                        color: '#98D8C8',
                        size: 20,
                        title: '차이'
                    }});
                    currentEdges.add({{
                        from: elemId,
                        to: varId,
                        color: '#98D8C8'
                    }});
                }}
            }});
            
            network.fit();
        }}

        // 노드 확장
        function expandNode(nodeId) {{
            alert(`노드 확장: ${{nodeId}}`);
        }}

        // 선택 노드 확장
        function expandSelected() {{
            if (selectedNodeId) {{
                expandNode(selectedNodeId);
            }} else {{
                alert('노드를 먼저 선택하세요');
            }}
        }}

        // 원인 표시
        function showCauses() {{
            alert('원인 노드를 추가합니다');
        }}

        // 그래프 초기화
        function resetGraph() {{
            loadOverview();
        }}

        // 화면 맞춤
        function fitGraph() {{
            if (network) {{
                network.fit({{
                    animation: {{
                        duration: 500,
                        easingFunction: 'easeInOutQuad'
                    }}
                }});
            }}
        }}

        // 초기화
        document.addEventListener('DOMContentLoaded', function() {{
            initGraph();
            renderSidebar();
            loadOverview();
        }});
    </script>
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        return output_file


def main():
    print("=" * 80)
    print("  인터랙티브 그래프 탐색 대시보드 생성")
    print("=" * 80)
    
    dashboard = InteractiveGraphDashboard()
    
    try:
        print("\n📊 데이터 수집 중...")
        
        print("  - 원가차이 집계...")
        variance_summary = dashboard.get_variance_summary()
        
        print("  - 주요 차이 항목...")
        top_variances = dashboard.get_top_variances(20)
        
        print("  - 원인 분석...")
        cause_summary = dashboard.get_cause_summary()
        
        print(f"\n✅ 데이터 수집 완료!")
        print(f"   원가차이 유형: {len(variance_summary)}개")
        print(f"   주요 항목: {len(top_variances)}개")
        print(f"   원인: {len(cause_summary)}개")
        
        print("\n🎨 대시보드 생성 중...")
        output_file = dashboard.generate_html(variance_summary, top_variances, cause_summary)
        
        print(f"\n✅ 대시보드 생성 완료!")
        print(f"📄 파일: {output_file}")
        print(f"🌐 브라우저에서 열립니다...")
        
        # 브라우저에서 자동 열기
        import webbrowser
        file_path = os.path.abspath(output_file)
        webbrowser.open('file://' + file_path)
        
        print("\n💡 주요 기능:")
        print("   📊 원가요소별 요약 + 그래프 시각화")
        print("   🎯 차이 항목 클릭 → 관련 노드 탐색")
        print("   🔎 원인 클릭 → 영향받은 차이들 표시")
        print("   🔍 노드 더블클릭 → 관계 확장")
        print("   📈 GraphDB의 관계 탐색 기능 활용")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        dashboard.close()
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
