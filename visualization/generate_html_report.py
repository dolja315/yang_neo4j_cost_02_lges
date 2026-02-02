"""
Neo4j 원가차이 분석 - 인터랙티브 HTML 리포트 생성

실행: python visualization/generate_html_report.py
결과: variance_analysis_report.html 파일 생성 (브라우저로 열기!)
"""
import os
import ssl
from dotenv import load_dotenv
from neo4j import GraphDatabase
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

# .env 파일 로드
load_dotenv()

class VarianceVisualizer:
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
    
    def get_variance_by_cause(self):
        """원인코드별 차이 집계"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Variance)-[:CAUSED_BY]->(c:Cause)
                RETURN 
                  c.code as code,
                  c.category as category,
                  c.description as description,
                  count(v) as count,
                  sum(v.variance_amount) as total_variance
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return pd.DataFrame([dict(record) for record in result])
    
    def get_variance_by_element(self):
        """원가요소별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Variance)
                RETURN 
                  v.cost_element as element,
                  count(v) as count,
                  sum(v.variance_amount) as total_variance,
                  avg(v.variance_amount) as avg_variance
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return pd.DataFrame([dict(record) for record in result])
    
    def get_variance_by_severity(self):
        """심각도별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Variance)
                RETURN 
                  v.severity as severity,
                  count(v) as count,
                  sum(v.variance_amount) as total_variance,
                  avg(v.variance_percent) as avg_percent
                ORDER BY 
                  CASE v.severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                  END
            """)
            return pd.DataFrame([dict(record) for record in result])
    
    def get_top_variance_orders(self, limit=20):
        """차이가 큰 TOP 생산오더"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                WITH po, sum(v.variance_amount) as total_variance, count(v) as variance_count
                RETURN 
                  po.id as order_id,
                  po.product_cd as product,
                  total_variance,
                  variance_count
                ORDER BY abs(total_variance) DESC
                LIMIT $limit
            """, limit=limit)
            return pd.DataFrame([dict(record) for record in result])
    
    def get_workcenter_analysis(self):
        """작업장별 차이 분석"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
                MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
                WHERE v.cost_element IN ['LABOR', 'OVERHEAD']
                WITH wc, v
                RETURN 
                  wc.name as workcenter,
                  wc.process_type as type,
                  count(v) as count,
                  sum(v.variance_amount) as total_variance
                ORDER BY abs(sum(v.variance_amount)) DESC
            """)
            return pd.DataFrame([dict(record) for record in result])
    
    def get_summary(self):
        """전체 요약 통계"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (po:ProductionOrder)
                WITH count(po) as total_orders
                MATCH (v:Variance)
                WITH total_orders, count(v) as total_variances, sum(v.variance_amount) as total_amount
                MATCH (v2:Variance)
                WHERE v2.variance_amount > 0
                WITH total_orders, total_variances, total_amount, 
                     count(v2) as unfavorable_count, sum(v2.variance_amount) as unfavorable_amount
                MATCH (v3:Variance)
                WHERE v3.variance_amount < 0
                RETURN 
                  total_orders,
                  total_variances,
                  total_amount,
                  unfavorable_count,
                  unfavorable_amount,
                  count(v3) as favorable_count,
                  sum(v3.variance_amount) as favorable_amount
            """)
            return result.single()

def create_html_report():
    print("=" * 60)
    print("  Neo4j 원가차이 분석 - HTML 리포트 생성")
    print("=" * 60)
    
    viz = VarianceVisualizer()
    
    try:
        # 데이터 수집
        print("\n데이터 수집 중...")
        summary = viz.get_summary()
        df_cause = viz.get_variance_by_cause()
        df_element = viz.get_variance_by_element()
        df_severity = viz.get_variance_by_severity()
        df_orders = viz.get_top_variance_orders(20)
        df_wc = viz.get_workcenter_analysis()
        
        # 1. 원인코드별 바 차트
        fig_cause = go.Figure()
        fig_cause.add_trace(go.Bar(
            x=df_cause['description'],
            y=df_cause['total_variance'],
            text=df_cause['total_variance'].apply(lambda x: f'{x:,.0f}원'),
            textposition='auto',
            marker_color=df_cause['total_variance'].apply(
                lambda x: 'red' if x > 0 else 'green'
            )
        ))
        fig_cause.update_layout(
            title='원인코드별 원가차이',
            xaxis_title='원인',
            yaxis_title='차이 금액 (원)',
            height=500
        )
        
        # 2. 원가요소별 파이 차트
        fig_element = go.Figure()
        fig_element.add_trace(go.Pie(
            labels=df_element['element'],
            values=df_element['total_variance'].abs(),
            hole=0.3,
            text=df_element['element'],
            textposition='inside',
            textinfo='label+percent'
        ))
        fig_element.update_layout(
            title='원가요소별 차이 비중 (절대값)',
            height=500
        )
        
        # 3. TOP 20 오더 바 차트
        fig_orders = go.Figure()
        colors = ['red' if x > 0 else 'green' for x in df_orders['total_variance']]
        fig_orders.add_trace(go.Bar(
            y=df_orders['order_id'],
            x=df_orders['total_variance'],
            orientation='h',
            text=df_orders['total_variance'].apply(lambda x: f'{x:,.0f}원'),
            textposition='auto',
            marker_color=colors
        ))
        fig_orders.update_layout(
            title='TOP 20 차이가 큰 생산오더',
            xaxis_title='차이 금액 (원)',
            yaxis_title='생산오더',
            height=700,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        # 4. 작업장별 차트
        fig_wc = go.Figure()
        fig_wc.add_trace(go.Bar(
            x=df_wc['workcenter'],
            y=df_wc['total_variance'],
            text=df_wc['total_variance'].apply(lambda x: f'{x:,.0f}원'),
            textposition='auto',
            marker_color=df_wc['total_variance'].apply(
                lambda x: 'red' if x > 0 else 'green'
            )
        ))
        fig_wc.update_layout(
            title='작업장별 노무비/경비 차이',
            xaxis_title='작업장',
            yaxis_title='차이 금액 (원)',
            height=500,
            xaxis_tickangle=-45
        )
        
        # 5. 심각도별 도넛 차트
        fig_severity = go.Figure()
        fig_severity.add_trace(go.Pie(
            labels=df_severity['severity'],
            values=df_severity['count'],
            hole=0.4,
            marker_colors=['#ff4444', '#ff8844', '#ffbb44', '#88ff44']
        ))
        fig_severity.update_layout(
            title='심각도별 차이 건수',
            height=500
        )
        
        # HTML 리포트 생성
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Neo4j 원가차이 분석 리포트</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #333;
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
        }}
        .header-info {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card .subvalue {{
            font-size: 14px;
            opacity: 0.8;
        }}
        .chart-container {{
            margin: 40px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 10px;
        }}
        .chart-title {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Neo4j 원가차이 분석 리포트</h1>
        <div class="header-info">
            <p>생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
            <p>데이터 소스: Neo4j Aura Cloud</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>총 생산오더</h3>
                <div class="value">{summary['total_orders']:,}</div>
                <div class="subvalue">개</div>
            </div>
            <div class="summary-card">
                <h3>총 차이 건수</h3>
                <div class="value">{summary['total_variances']:,}</div>
                <div class="subvalue">건</div>
            </div>
            <div class="summary-card">
                <h3>순차이 금액</h3>
                <div class="value">{summary['total_amount']:,.0f}</div>
                <div class="subvalue">원</div>
            </div>
            <div class="summary-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h3>불리한 차이</h3>
                <div class="value">{summary['unfavorable_count']:,}</div>
                <div class="subvalue">{summary['unfavorable_amount']:,.0f} 원</div>
            </div>
            <div class="summary-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <h3>유리한 차이</h3>
                <div class="value">{summary['favorable_count']:,}</div>
                <div class="subvalue">{summary['favorable_amount']:,.0f} 원</div>
            </div>
        </div>
        
        <div class="chart-container">
            {fig_cause.to_html(full_html=False, include_plotlyjs='cdn')}
        </div>
        
        <div class="chart-container">
            {fig_element.to_html(full_html=False, include_plotlyjs=False)}
        </div>
        
        <div class="chart-container">
            {fig_severity.to_html(full_html=False, include_plotlyjs=False)}
        </div>
        
        <div class="chart-container">
            {fig_orders.to_html(full_html=False, include_plotlyjs=False)}
        </div>
        
        <div class="chart-container">
            {fig_wc.to_html(full_html=False, include_plotlyjs=False)}
        </div>
        
        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
            <p>Made with ❤️ using Neo4j + Python + Plotly</p>
            <p>Powered by Graph Database Technology</p>
        </footer>
    </div>
</body>
</html>
        """
        
        # 파일 저장
        output_file = 'variance_analysis_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ HTML 리포트 생성 완료!")
        print(f"📄 파일: {output_file}")
        print(f"🌐 브라우저로 파일을 열어보세요!")
        
        # Windows에서 자동으로 브라우저 열기
        import webbrowser
        import os
        file_path = os.path.abspath(output_file)
        webbrowser.open('file://' + file_path)
        print(f"🚀 브라우저에서 자동으로 열었습니다!")
        
    finally:
        viz.close()
        print("\n" + "=" * 60)

if __name__ == "__main__":
    create_html_report()
