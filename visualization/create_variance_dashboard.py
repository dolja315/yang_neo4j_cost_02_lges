"""
원가차이 분석 대시보드 생성기

계층적 드릴다운 분석이 가능한 인터랙티브 대시보드를 생성합니다.
- 전체 원가차이 요약
- 원가요소별 집계 (MATERIAL, LABOR, OVERHEAD)
- 차이유형별 분석 (QUANTITY, PRICE, EFFICIENCY, RATE, VOLUME)
- 상세 내역 조회

실행: python visualization/create_variance_dashboard.py
"""

import os
import ssl
import json
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class VarianceDashboardCreator:
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
        """원가차이 집계 데이터 가져오기"""
        with self.driver.session() as session:
            query = """
            MATCH (v:Variance)
            OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
            WITH v, collect(DISTINCT c.code) as causes
            RETURN 
                v.cost_element as cost_element,
                v.variance_type as variance_type,
                v.severity as severity,
                SUM(v.variance_amount) as total_amount,
                AVG(v.variance_percent) as avg_percent,
                COUNT(v) as count,
                causes,
                collect({
                    id: v.id,
                    order_no: v.order_no,
                    amount: v.variance_amount,
                    percent: v.variance_percent,
                    date: toString(v.analysis_date)
                }) as details
            ORDER BY cost_element, variance_type
            """
            
            results = session.run(query).data()
            
            # 계층적 구조 생성
            hierarchy = {
                'name': '전체 원가차이',
                'children': []
            }
            
            # 원가 요소별로 그룹화
            elements_dict = {}
            total_sum = 0
            
            for row in results:
                element = row['cost_element']
                if element not in elements_dict:
                    elements_dict[element] = {
                        'name': element,
                        'children': [],
                        'total': 0
                    }
                
                amount = row['total_amount']
                total_sum += amount
                elements_dict[element]['total'] += amount
                
                elements_dict[element]['children'].append({
                    'name': row['variance_type'],
                    'value': amount,
                    'count': row['count'],
                    'avg_percent': round(row['avg_percent'], 2),
                    'severity': row['severity'],
                    'causes': row['causes'],
                    'details': row['details'][:10]  # 상위 10개만
                })
            
            # 계층 구조에 추가
            for element_name, element_data in elements_dict.items():
                hierarchy['children'].append({
                    'name': element_name,
                    'value': element_data['total'],
                    'children': element_data['children']
                })
            
            hierarchy['value'] = total_sum
            
            return hierarchy
    
    def get_top_variances(self, limit=10):
        """가장 큰 차이 항목 조회"""
        with self.driver.session() as session:
            query = """
            MATCH (v:Variance)
            OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
            WITH v, collect(c.description) as causes
            RETURN 
                v.id as id,
                v.order_no as order_no,
                v.cost_element as cost_element,
                v.variance_type as variance_type,
                v.variance_amount as amount,
                v.variance_percent as percent,
                v.severity as severity,
                toString(v.analysis_date) as date,
                causes
            ORDER BY ABS(v.variance_amount) DESC
            LIMIT $limit
            """
            
            results = session.run(query, limit=limit).data()
            return results
    
    def get_cause_analysis(self):
        """원인별 차이 분석"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Cause)<-[:CAUSED_BY]-(v:Variance)
            RETURN 
                c.code as cause_code,
                c.description as cause_desc,
                c.category as category,
                c.responsible_dept as dept,
                COUNT(v) as occurrence_count,
                SUM(v.variance_amount) as total_impact,
                AVG(v.variance_amount) as avg_impact
            ORDER BY ABS(total_impact) DESC
            """
            
            results = session.run(query).data()
            return results

    def generate_html(self, data, top_variances, cause_analysis, output_file='variance_dashboard.html'):
        """HTML 대시보드 생성"""
        
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>원가차이 분석 대시보드</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
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
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 32px;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.2);
        }}
        
        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }}
        
        .card h3 {{
            color: #7f8c8d;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 15px;
        }}
        
        .card .value {{
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .card .change {{
            font-size: 13px;
            color: #95a5a6;
        }}
        
        .card .positive {{ 
            color: #e74c3c;
        }}
        
        .card .negative {{ 
            color: #27ae60;
        }}
        
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .chart-container h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 22px;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        
        @media (max-width: 1024px) {{
            .grid-2 {{
                grid-template-columns: 1fr;
            }}
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        table th {{
            background: #f8f9fa;
            color: #495057;
            font-weight: 600;
            text-align: left;
            padding: 15px;
            border-bottom: 2px solid #dee2e6;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        table td {{
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            color: #495057;
        }}
        
        table tr:hover {{
            background: #f8f9fa;
        }}
        
        .severity-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .severity-HIGH {{
            background: #fee;
            color: #c00;
        }}
        
        .severity-MEDIUM {{
            background: #ffeaa7;
            color: #d63031;
        }}
        
        .severity-LOW {{
            background: #dfe6e9;
            color: #636e72;
        }}
        
        .loading {{
            text-align: center;
            padding: 50px;
            color: #95a5a6;
        }}
        
        .tooltip {{
            position: absolute;
            background: rgba(0,0,0,0.9);
            color: white;
            padding: 10px;
            border-radius: 6px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 원가차이 분석 대시보드</h1>
            <div class="subtitle">생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="summary-cards">
            <div class="card">
                <h3>전체 원가차이</h3>
                <div class="value" id="total-variance">계산 중...</div>
                <div class="change" id="total-count">-</div>
            </div>
            <div class="card">
                <h3>MATERIAL 차이</h3>
                <div class="value" id="material-variance">계산 중...</div>
                <div class="change" id="material-count">-</div>
            </div>
            <div class="card">
                <h3>LABOR 차이</h3>
                <div class="value" id="labor-variance">계산 중...</div>
                <div class="change" id="labor-count">-</div>
            </div>
            <div class="card">
                <h3>OVERHEAD 차이</h3>
                <div class="value" id="overhead-variance">계산 중...</div>
                <div class="change" id="overhead-count">-</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="chart-container">
                <h2>원가 요소별 차이 분포</h2>
                <div id="sunburst-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>차이 유형별 분석</h2>
                <div id="treemap-chart"></div>
            </div>
        </div>

        <div class="chart-container">
            <h2>원가 요소별 차이 추이</h2>
            <div id="bar-chart"></div>
        </div>

        <div class="chart-container">
            <h2>주요 차이 항목 TOP 10</h2>
            <div id="top-variances-table"></div>
        </div>

        <div class="chart-container">
            <h2>원인별 차이 분석</h2>
            <div id="cause-analysis-chart"></div>
        </div>
    </div>

    <script>
        // 데이터
        const varianceData = {json.dumps(data, ensure_ascii=False, indent=2)};
        const topVariances = {json.dumps(top_variances, ensure_ascii=False, indent=2)};
        const causeAnalysis = {json.dumps(cause_analysis, ensure_ascii=False, indent=2)};

        // 금액 포맷팅
        function formatCurrency(value) {{
            const abs = Math.abs(value);
            const formatted = abs.toLocaleString('ko-KR', {{maximumFractionDigits: 0}});
            const sign = value >= 0 ? '+' : '-';
            return `${{sign}}₩${{formatted}}`;
        }}

        // 요약 카드 업데이트
        function updateSummaryCards() {{
            const elements = {{ MATERIAL: 0, LABOR: 0, OVERHEAD: 0 }};
            const counts = {{ MATERIAL: 0, LABOR: 0, OVERHEAD: 0 }};
            let total = varianceData.value || 0;
            
            varianceData.children.forEach(element => {{
                let elementSum = element.value || 0;
                let elementCount = 0;
                
                element.children.forEach(type => {{
                    elementCount += type.count || 0;
                }});
                
                elements[element.name] = elementSum;
                counts[element.name] = elementCount;
            }});

            // 전체
            document.getElementById('total-variance').textContent = formatCurrency(total);
            document.getElementById('total-variance').className = `value ${{total >= 0 ? 'positive' : 'negative'}}`;
            const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
            document.getElementById('total-count').textContent = `${{totalCount}}건의 차이`;
            
            // 개별 요소
            Object.keys(elements).forEach(key => {{
                const el = document.getElementById(`${{key.toLowerCase()}}-variance`);
                if (el) {{
                    el.textContent = formatCurrency(elements[key]);
                    el.className = `value ${{elements[key] >= 0 ? 'positive' : 'negative'}}`;
                    
                    const countEl = document.getElementById(`${{key.toLowerCase()}}-count`);
                    if (countEl) {{
                        countEl.textContent = `${{counts[key]}}건의 차이`;
                    }}
                }}
            }});
        }}

        // Sunburst 차트
        function createSunburstChart() {{
            const labels = [];
            const parents = [];
            const values = [];
            const colors = [];

            // 루트
            labels.push('전체');
            parents.push('');
            values.push(varianceData.value);
            
            // 색상 팔레트
            const colorPalette = {{
                'MATERIAL': '#3498db',
                'LABOR': '#e74c3c',
                'OVERHEAD': '#f39c12'
            }};

            varianceData.children.forEach(element => {{
                labels.push(element.name);
                parents.push('전체');
                values.push(Math.abs(element.value));
                
                element.children.forEach(type => {{
                    labels.push(`${{element.name}}-${{type.name}}`);
                    parents.push(element.name);
                    values.push(Math.abs(type.value));
                }});
            }});

            const data = [{{
                type: "sunburst",
                labels: labels,
                parents: parents,
                values: values,
                branchvalues: "total",
                marker: {{ line: {{ width: 2 }} }},
                textinfo: "label+percent parent",
                hovertemplate: '<b>%{{label}}</b><br>금액: ₩%{{value:,.0f}}<br>비율: %{{percentParent}}<extra></extra>'
            }}];

            const layout = {{
                height: 400,
                margin: {{ l: 0, r: 0, b: 0, t: 0 }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                sunburstcolorway: ["#3498db", "#e74c3c", "#f39c12", "#9b59b6", "#1abc9c"]
            }};

            Plotly.newPlot('sunburst-chart', data, layout, {{responsive: true}});
        }}

        // TreeMap 차트
        function createTreemapChart() {{
            const labels = [];
            const parents = [];
            const values = [];
            const texts = [];
            const colors = [];

            varianceData.children.forEach(element => {{
                element.children.forEach(type => {{
                    labels.push(`${{element.name}}<br>${{type.name}}`);
                    parents.push('');
                    values.push(Math.abs(type.value));
                    texts.push(`${{type.count}}건<br>${{formatCurrency(type.value)}}`);
                    colors.push(type.value);
                }});
            }});

            const data = [{{
                type: "treemap",
                labels: labels,
                parents: parents,
                values: values,
                text: texts,
                textposition: "middle center",
                marker: {{
                    colors: colors,
                    colorscale: [
                        [0, '#27ae60'],
                        [0.5, '#f39c12'],
                        [1, '#e74c3c']
                    ],
                    line: {{ width: 2, color: 'white' }}
                }},
                hovertemplate: '<b>%{{label}}</b><br>%{{text}}<extra></extra>'
            }}];

            const layout = {{
                height: 400,
                margin: {{ l: 0, r: 0, b: 20, t: 0 }},
                paper_bgcolor: 'rgba(0,0,0,0)'
            }};

            Plotly.newPlot('treemap-chart', data, layout, {{responsive: true}});
        }}

        // Bar 차트
        function createBarChart() {{
            const traces = [];
            
            varianceData.children.forEach(element => {{
                const x = [];
                const y = [];
                const colors = [];
                
                element.children.forEach(type => {{
                    x.push(type.name);
                    y.push(type.value);
                    colors.push(type.value >= 0 ? '#e74c3c' : '#27ae60');
                }});
                
                traces.push({{
                    type: 'bar',
                    name: element.name,
                    x: x,
                    y: y,
                    marker: {{ color: colors }},
                    text: y.map(v => formatCurrency(v)),
                    textposition: 'outside',
                    hovertemplate: '<b>%{{x}}</b><br>금액: %{{text}}<extra></extra>'
                }});
            }});

            const layout = {{
                height: 400,
                barmode: 'group',
                xaxis: {{ title: '차이 유형' }},
                yaxis: {{ title: '차이 금액 (원)', tickformat: ',.0f' }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                legend: {{ orientation: 'h', y: -0.2 }}
            }};

            Plotly.newPlot('bar-chart', traces, layout, {{responsive: true}});
        }}

        // TOP 10 테이블
        function createTopVariancesTable() {{
            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>차이ID</th>
                            <th>오더번호</th>
                            <th>원가요소</th>
                            <th>차이유형</th>
                            <th>차이금액</th>
                            <th>차이율</th>
                            <th>심각도</th>
                            <th>분석일자</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            topVariances.forEach((v, i) => {{
                const amountClass = v.amount >= 0 ? 'positive' : 'negative';
                html += `
                    <tr>
                        <td><strong>${{i + 1}}</strong></td>
                        <td>${{v.id}}</td>
                        <td>${{v.order_no}}</td>
                        <td>${{v.cost_element}}</td>
                        <td>${{v.variance_type}}</td>
                        <td class="${{amountClass}}">${{formatCurrency(v.amount)}}</td>
                        <td>${{v.percent.toFixed(2)}}%</td>
                        <td><span class="severity-badge severity-${{v.severity}}">${{v.severity}}</span></td>
                        <td>${{v.date}}</td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            document.getElementById('top-variances-table').innerHTML = html;
        }}

        // 원인 분석 차트
        function createCauseAnalysisChart() {{
            const x = causeAnalysis.map(c => c.cause_desc);
            const y = causeAnalysis.map(c => Math.abs(c.total_impact));
            const colors = causeAnalysis.map(c => c.total_impact >= 0 ? '#e74c3c' : '#27ae60');
            const counts = causeAnalysis.map(c => c.occurrence_count);
            
            const data = [{{
                type: 'bar',
                x: x,
                y: y,
                marker: {{ color: colors }},
                text: y.map((v, i) => `${{formatCurrency(causeAnalysis[i].total_impact)}}<br>${{counts[i]}}건`),
                textposition: 'outside',
                hovertemplate: '<b>%{{x}}</b><br>영향: %{{text}}<br>담당: ' + 
                    causeAnalysis.map(c => c.dept).join('<br>') + '<extra></extra>'
            }}];
            
            const layout = {{
                height: 400,
                xaxis: {{ title: '원인' }},
                yaxis: {{ title: '총 영향액 (원)', tickformat: ',.0f' }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                margin: {{ b: 150 }}
            }};
            
            Plotly.newPlot('cause-analysis-chart', data, layout, {{responsive: true}});
        }}

        // 초기화
        document.addEventListener('DOMContentLoaded', function() {{
            updateSummaryCards();
            createSunburstChart();
            createTreemapChart();
            createBarChart();
            createTopVariancesTable();
            createCauseAnalysisChart();
        }});
    </script>
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        return output_file


def main():
    print("=" * 80)
    print("  원가차이 분석 대시보드 생성")
    print("=" * 80)
    
    creator = VarianceDashboardCreator()
    
    try:
        print("\n📊 데이터 수집 중...")
        
        print("  - 원가차이 집계...")
        variance_data = creator.get_variance_summary()
        
        print("  - 주요 차이 항목 조회...")
        top_variances = creator.get_top_variances(10)
        
        print("  - 원인별 분석...")
        cause_analysis = creator.get_cause_analysis()
        
        print(f"\n✅ 데이터 수집 완료!")
        print(f"   원가 요소: {len(variance_data.get('children', []))}개")
        print(f"   차이 항목: {sum(child.get('count', 0) for child in variance_data.get('children', []) for child in child.get('children', []))}건")
        print(f"   전체 금액: {variance_data.get('value', 0):,.0f}원")
        
        print("\n🎨 대시보드 생성 중...")
        output_file = creator.generate_html(variance_data, top_variances, cause_analysis)
        
        print(f"\n✅ 대시보드 생성 완료!")
        print(f"📄 파일: {output_file}")
        print(f"🌐 브라우저에서 열립니다...")
        
        # 브라우저에서 자동 열기
        import webbrowser
        file_path = os.path.abspath(output_file)
        webbrowser.open('file://' + file_path)
        
        print("\n💡 주요 기능:")
        print("   📊 전체 원가차이 요약")
        print("   🔍 원가요소별 계층 분석")
        print("   📈 차이 유형별 시각화")
        print("   🎯 주요 차이 항목 TOP 10")
        print("   🔎 원인별 영향 분석")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        creator.close()
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
