"""
Neo4j 원가차이 분석 - Streamlit 대시보드

실행: streamlit run visualization/streamlit_dashboard.py
브라우저에서 http://localhost:8501 자동으로 열림!
"""
import os
import ssl
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 페이지 설정
st.set_page_config(
    page_title="Neo4j 원가차이 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일
st.markdown("""
<style>
    .main {
        background: #f0f2f6;
    }
    .stMetric {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Neo4j 연결 클래스
@st.cache_resource
def get_neo4j_connection():
    load_dotenv()
    uri = os.getenv('NEO4J_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    
    uri = uri.replace('neo4j+s://', 'bolt://')
    uri = uri.replace('neo4j+ssc://', 'bolt://')
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    return GraphDatabase.driver(uri, auth=(username, password), ssl_context=ssl_context)

# 데이터 로딩 함수들
@st.cache_data(ttl=300)
def get_summary():
    driver = get_neo4j_connection()
    with driver.session() as session:
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
        return dict(result.single())

@st.cache_data(ttl=300)
def get_variance_by_cause():
    driver = get_neo4j_connection()
    with driver.session() as session:
        result = session.run("""
            MATCH (v:Variance)-[:CAUSED_BY]->(c:Cause)
            RETURN 
              c.code as code,
              c.category as category,
              c.description as description,
              c.responsible_dept as dept,
              count(v) as count,
              sum(v.variance_amount) as total_variance,
              avg(v.variance_percent) as avg_percent
            ORDER BY abs(sum(v.variance_amount)) DESC
        """)
        return pd.DataFrame([dict(record) for record in result])

@st.cache_data(ttl=300)
def get_variance_by_element():
    driver = get_neo4j_connection()
    with driver.session() as session:
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

@st.cache_data(ttl=300)
def get_top_orders(limit=20):
    driver = get_neo4j_connection()
    with driver.session() as session:
        result = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WITH po, sum(v.variance_amount) as total_variance, count(v) as variance_count
            RETURN 
              po.id as order_id,
              po.product_cd as product,
              po.planned_qty as quantity,
              total_variance,
              variance_count
            ORDER BY abs(total_variance) DESC
            LIMIT $limit
        """, limit=limit)
        return pd.DataFrame([dict(record) for record in result])

@st.cache_data(ttl=300)
def get_workcenter_analysis():
    driver = get_neo4j_connection()
    with driver.session() as session:
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

# 메인 앱
def main():
    # 헤더
    st.title("🎯 Neo4j 원가차이 분석 대시보드")
    st.markdown("**실시간 그래프 데이터베이스 분석**")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        st.info("📊 Neo4j Aura Cloud 연결")
        
        # 새로고침 버튼
        if st.button("🔄 데이터 새로고침"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📌 필터")
        
        # 필터 옵션 (추후 확장 가능)
        show_all = st.checkbox("모든 데이터 표시", value=True)
    
    # 데이터 로드
    try:
        summary = get_summary()
        df_cause = get_variance_by_cause()
        df_element = get_variance_by_element()
        df_orders = get_top_orders(20)
        df_wc = get_workcenter_analysis()
    except Exception as e:
        st.error(f"❌ 데이터 로드 실패: {e}")
        st.stop()
    
    if summary['total_orders'] == 0:
        st.warning("⚠️ 데이터가 없습니다. 먼저 데이터 생성 및 업로드를 진행해주세요.")
        st.stop()

    # 요약 메트릭
    st.header("📊 전체 요약")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("총 생산오더", f"{summary['total_orders']:,}개")
    with col2:
        st.metric("총 차이 건수", f"{summary['total_variances']:,}건")
    with col3:
        st.metric("순차이 금액", f"{summary['total_amount']:,.0f}원")
    with col4:
        st.metric("불리한 차이", f"{summary['unfavorable_count']:,}건", 
                  f"{summary['unfavorable_amount']:,.0f}원", delta_color="inverse")
    with col5:
        st.metric("유리한 차이", f"{summary['favorable_count']:,}건",
                  f"{summary['favorable_amount']:,.0f}원", delta_color="normal")
    
    st.markdown("---")
    
    # 탭으로 구성
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 원인 분석", "📈 원가요소", "🏭 생산오더", "👷 작업장"])
    
    with tab1:
        st.header("원인코드별 차이 분석")
        
        if df_cause.empty:
            st.info("데이터가 없습니다.")
        else:
            col1, col2 = st.columns([2, 1])

            with col1:
                # 바 차트
                fig = px.bar(
                    df_cause,
                    x='description',
                    y='total_variance',
                    color='total_variance',
                    color_continuous_scale=['green', 'yellow', 'red'],
                    text='total_variance',
                    title='원인코드별 원가차이'
                )
                fig.update_traces(texttemplate='%{text:,.0f}원', textposition='outside')
                fig.update_layout(height=500, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 테이블
                st.subheader("상세 데이터")
                df_display = df_cause.copy()
                df_display['total_variance'] = df_display['total_variance'].apply(lambda x: f"{x:,.0f}원")
                df_display['avg_percent'] = df_display['avg_percent'].apply(lambda x: f"{x:.2f}%")
                st.dataframe(df_display, use_container_width=True)
    
    with tab2:
        st.header("원가요소별 분석")
        
        if df_element.empty:
            st.info("데이터가 없습니다.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # 파이 차트
                fig = px.pie(
                    df_element,
                    names='element',
                    values=df_element['total_variance'].abs(),
                    title='원가요소별 비중',
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 바 차트
                fig = px.bar(
                    df_element,
                    x='element',
                    y='total_variance',
                    color='total_variance',
                    color_continuous_scale=['green', 'yellow', 'red'],
                    title='원가요소별 차이금액',
                    text='total_variance'
                )
                fig.update_traces(texttemplate='%{text:,.0f}원', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("생산오더 분석")
        
        # TOP 20 오더
        st.subheader("TOP 20 차이가 큰 생산오더")
        
        if df_orders.empty:
            st.info("데이터가 없습니다.")
        else:
            # 수평 바 차트
            fig = px.bar(
                df_orders,
                y='order_id',
                x='total_variance',
                orientation='h',
                color='total_variance',
                color_continuous_scale=['green', 'yellow', 'red'],
                hover_data=['product', 'quantity', 'variance_count'],
                text='total_variance'
            )
            fig.update_traces(texttemplate='%{text:,.0f}원', textposition='outside')
            fig.update_layout(height=700, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # 상세 테이블
            st.subheader("상세 정보")
            df_display = df_orders.copy()
            df_display['total_variance'] = df_display['total_variance'].apply(lambda x: f"{x:,.0f}원")
            st.dataframe(df_display, use_container_width=True)

    with tab4:
        st.header("작업장별 분석")
        
        if df_wc.empty:
            st.info("데이터가 없습니다.")
        else:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 바 차트
                fig = px.bar(
                    df_wc,
                    x='workcenter',
                    y='total_variance',
                    color='total_variance',
                    color_continuous_scale=['green', 'yellow', 'red'],
                    hover_data=['type', 'count'],
                    title='작업장별 노무비/경비 차이',
                    text='total_variance'
                )
                fig.update_traces(texttemplate='%{text:,.0f}원', textposition='outside')
                fig.update_layout(height=500, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("요약")
                st.metric("총 작업장", len(df_wc))
                st.metric("평균 차이", f"{df_wc['total_variance'].mean():,.0f}원")

                # 최고/최저 효율 작업장
                best = df_wc.loc[df_wc['total_variance'].idxmin()]
                worst = df_wc.loc[df_wc['total_variance'].idxmax()]

                st.success(f"✅ 최고 효율\n{best['workcenter']}")
                st.error(f"❌ 개선 필요\n{worst['workcenter']}")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Made with ❤️ using Neo4j + Streamlit + Plotly</p>
        <p>Powered by Graph Database Technology</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
