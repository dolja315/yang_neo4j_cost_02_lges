"""
원가차이 그래프 탐색 API 서버

Flask 기반 REST API로 Neo4j 그래프 데이터를 동적으로 제공
클라이언트에서 요청 시 실시간으로 Neo4j 쿼리 실행

실행: python visualization/graph_api_server.py
"""

import os
import ssl
import json
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from neo4j import GraphDatabase
from neo4j.time import DateTime, Date
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 활성화


def serialize_neo4j_types(obj):
    """Neo4j 타입을 JSON 직렬화 가능한 형태로 변환"""
    if isinstance(obj, (DateTime, Date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_neo4j_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_neo4j_types(item) for item in obj]
    return obj


def variance_color(amount):
    """차이 금액 크기에 따른 색상"""
    try:
        value = abs(float(amount))
    except (TypeError, ValueError):
        return '#98D8C8'
    if value >= 1_000_000_000:
        return '#FF6B6B'
    if value >= 100_000_000:
        return '#FFA94D'
    if value >= 10_000_000:
        return '#FFD43B'
    return '#98D8C8'


def get_node_color(node_type):
    color_map = {
        'Variance': '#98D8C8',
        'ProductionOrder': '#45B7D1',
        'Product': '#FF6B6B',
        'Material': '#4ECDC4',
        'WorkCenter': '#F7DC6F',
        'Cause': '#F8B739'
    }
    return color_map.get(node_type, '#95A5A6')


class Neo4jConnection:
    def __init__(self):
        self.driver = None
        uri = os.getenv('NEO4J_URI')
        username = os.getenv('NEO4J_USERNAME')
        password = os.getenv('NEO4J_PASSWORD')
        if not uri or not password:
            print("Warning: NEO4J_URI or NEO4J_PASSWORD not set. API will return empty data.")
            return
        try:
            print(f"Connecting to Neo4j: {uri}")
            print(f"Username: {username}")
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
        except Exception as e:
            print(f"Warning: Neo4j driver init failed: {e}. API will return empty data.")
            self.driver = None

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass
            self.driver = None


# 전역 연결 객체 (연결 실패해도 서버는 기동)
neo4j_conn = Neo4jConnection()


@app.route('/api/variance/<variance_id>/graph', methods=['GET'])
def get_variance_graph(variance_id):
    """특정 Variance 중심 그래프 데이터"""
    depth = request.args.get('depth', 2, type=int)
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (v:Variance {id: $variance_id})
        OPTIONAL MATCH path1 = (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)
        OPTIONAL MATCH path2 = (po)-[:CONSUMES]->(m:Material)
        OPTIONAL MATCH path3 = (po)-[:WORKS_AT]->(wc:WorkCenter)
        OPTIONAL MATCH path4 = (v)-[:CAUSED_BY]->(c:Cause)
        OPTIONAL MATCH path5 = (po)-[:PRODUCES]->(p:Product)
        
        WITH v, 
             collect(DISTINCT po) as orders,
             collect(DISTINCT m) as materials,
             collect(DISTINCT wc) as workcenters,
             collect(DISTINCT c) as causes,
             collect(DISTINCT p) as products
        
        RETURN v, orders, materials, workcenters, causes, products
        """
        
        result = session.run(query, variance_id=variance_id).single()
        
        if not result:
            return jsonify({'error': 'Variance not found'}), 404
        
        nodes = []
        edges = []
        
        # Variance 노드
        v = result['v']
        nodes.append({
            'id': v.element_id,
            'label': v.get('variance_name', v['id']),
            'type': 'Variance',
            'color': variance_color(v.get('variance_amount')),
            'size': 30,
            'properties': serialize_neo4j_types(dict(v))
        })
        
        # ProductionOrder 노드들
        for po in result['orders']:
            if po:
                nodes.append({
                    'id': po.element_id,
                    'label': po['id'],
                    'type': 'ProductionOrder',
                    'color': '#45B7D1',
                    'size': 35,
                    'properties': serialize_neo4j_types(dict(po))
                })
                edges.append({
                    'from': po.element_id,
                    'to': v.element_id,
                    'label': 'HAS_VARIANCE',
                    'color': variance_color(v.get('variance_amount'))
                })
        
        # Material 노드들
        for m in result['materials']:
            if m:
                nodes.append({
                    'id': m.element_id,
                    'label': m['id'],
                    'type': 'Material',
                    'color': '#4ECDC4',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(m))
                })
                # 연결은 PO를 통해
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': m.element_id,
                            'label': 'CONSUMES',
                            'color': '#45B7D1'
                        })
        
        # WorkCenter 노드들
        for wc in result['workcenters']:
            if wc:
                nodes.append({
                    'id': wc.element_id,
                    'label': wc['id'],
                    'type': 'WorkCenter',
                    'color': '#FFA07A',
                    'size': 28,
                    'properties': serialize_neo4j_types(dict(wc))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': wc.element_id,
                            'label': 'WORKS_AT',
                            'color': '#FFA07A'
                        })
        
        # Cause 노드들
        for c in result['causes']:
            if c:
                nodes.append({
                    'id': c.element_id,
                    'label': c['description'],
                    'type': 'Cause',
                    'color': '#F7DC6F',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(c))
                })
                edges.append({
                    'from': v.element_id,
                    'to': c.element_id,
                    'label': 'CAUSED_BY',
                    'color': '#F7DC6F'
                })
        
        # Product 노드들
        for p in result['products']:
            if p:
                nodes.append({
                    'id': p.element_id,
                    'label': p['name'],
                    'type': 'Product',
                    'color': '#FF6B6B',
                    'size': 30,
                    'properties': serialize_neo4j_types(dict(p))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': p.element_id,
                            'label': 'PRODUCES',
                            'color': '#FF6B6B'
                        })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': v['id']
        })


@app.route('/api/cause/<cause_code>/graph', methods=['GET'])
def get_cause_graph(cause_code):
    """특정 Cause 중심 그래프 데이터"""
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (c:Cause {code: $cause_code})
        MATCH (v:Variance)-[:CAUSED_BY]->(c)
        OPTIONAL MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v)
        
        RETURN c, 
               collect(DISTINCT v) as variances,
               collect(DISTINCT po) as orders
        LIMIT 50
        """
        
        result = session.run(query, cause_code=cause_code).single()
        
        if not result:
            return jsonify({'error': 'Cause not found'}), 404
        
        nodes = []
        edges = []
        
        # Cause 노드
        c = result['c']
        nodes.append({
            'id': c.element_id,
            'label': c['description'],
            'type': 'Cause',
            'color': '#F7DC6F',
            'size': 35,
            'properties': serialize_neo4j_types(dict(c))
        })
        
        # Variance 노드들
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v.get('variance_name', v['id']),
                    'type': 'Variance',
                    'color': variance_color(v.get('variance_amount')),
                    'size': 20,
                    'properties': serialize_neo4j_types(dict(v))
                })
                edges.append({
                    'from': v.element_id,
                    'to': c.element_id,
                    'label': 'CAUSED_BY',
                    'color': '#F7DC6F'
                })
        
        # ProductionOrder 노드들
        for po in result['orders']:
            if po:
                # 중복 체크
                if not any(n['id'] == po.element_id for n in nodes):
                    nodes.append({
                        'id': po.element_id,
                        'label': po['id'],
                        'type': 'ProductionOrder',
                        'color': '#45B7D1',
                        'size': 30,
                        'properties': serialize_neo4j_types(dict(po))
                    })
                
                # PO -> Variance 연결
                for v in result['variances']:
                    if v:
                        edges.append({
                            'from': po.element_id,
                            'to': v.element_id,
                            'label': 'HAS_VARIANCE',
                            'color': variance_color(v.get('variance_amount'))
                        })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': cause_code
        })


@app.route('/api/variances/by-type', methods=['GET'])
def get_variances_by_type():
    """차이 유형별 생산오더 목록"""
    variance_type = request.args.get('type', '')
    cost_element = request.args.get('element', '')
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
        WHERE v.variance_type = $variance_type
        AND ($cost_element = '' OR v.cost_element = $cost_element)
        WITH po, wc,
             SUM(v.variance_amount) as total_variance,
             COUNT(v) as variance_count
        RETURN elementId(po) as po_id,
               po.id as order_no,
               po.product_cd as product,
               wc.id as work_center,
               total_variance,
               variance_count
        ORDER BY ABS(total_variance) DESC
        LIMIT 20
        """
        
        results = session.run(query, 
                            variance_type=variance_type,
                            cost_element=cost_element).data()
        
        return jsonify(results)


@app.route('/api/variances/by-element', methods=['GET'])
def get_variances_by_element():
    """원가요소별 생산오더 목록 (MATERIAL, LABOR, OVERHEAD)"""
    cost_element = request.args.get('element', '')
    if not neo4j_conn.driver:
        return jsonify([])
    try:
        with neo4j_conn.driver.session() as session:
            query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
            WHERE v.cost_element = $cost_element
            WITH po, wc,
                 SUM(v.variance_amount) as total_variance,
                 COUNT(v) as variance_count
            RETURN elementId(po) as po_id,
                   po.id as order_no,
                   po.product_cd as product,
                   wc.id as work_center,
                   total_variance,
                   variance_count
            ORDER BY ABS(total_variance) DESC
            LIMIT 30
            """
            results = session.run(query, cost_element=cost_element).data()
            return jsonify(results or [])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([])


@app.route('/api/product/<product_cd>/graph', methods=['GET'])
def get_product_graph(product_cd):
    """제품 중심 그래프"""
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (p:Product {id: $product_cd})
        OPTIONAL MATCH (po:ProductionOrder)-[:PRODUCES]->(p)
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (po)-[:CONSUMES]->(m:Material)
        OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
        OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
        
        WITH p, 
             collect(DISTINCT po) as orders,
             collect(DISTINCT v) as variances,
             collect(DISTINCT m) as materials,
             collect(DISTINCT wc) as workcenters,
             collect(DISTINCT c) as causes
        
        RETURN p, orders, variances, materials, workcenters, causes
        LIMIT 1
        """
        
        result = session.run(query, product_cd=product_cd).single()
        
        if not result:
            # Product 노드가 없으면 product_cd로 검색
            query_by_cd = """
            MATCH (po:ProductionOrder {product_cd: $product_cd})
            OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            OPTIONAL MATCH (po)-[:CONSUMES]->(m:Material)
            OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
            OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
            
            WITH collect(DISTINCT po) as orders,
                 collect(DISTINCT v) as variances,
                 collect(DISTINCT m) as materials,
                 collect(DISTINCT wc) as workcenters,
                 collect(DISTINCT c) as causes
            
            RETURN null as p, orders, variances, materials, workcenters, causes
            LIMIT 1
            """
            result = session.run(query_by_cd, product_cd=product_cd).single()
            
            if not result or not result['orders']:
                return jsonify({'error': 'Product not found'}), 404
        
        nodes = []
        edges = []
        order_ids = [po['id'] for po in (result['orders'] or []) if po and po.get('id')]
        cause_pairs = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v)-[:CAUSED_BY]->(c)
            WHERE po.id IN $order_ids
            RETURN DISTINCT elementId(v) as v_id, elementId(c) as c_id
        """, order_ids=order_ids).data() if order_ids else []
        
        # Product 노드 (중심)
        if result['p']:
            p = result['p']
            nodes.append({
                'id': p.element_id,
                'label': p.get('name', p.get('id', product_cd)),
                'type': 'Product',
                'color': '#FF6B6B',
                'size': 45,
                'properties': serialize_neo4j_types(dict(p))
            })
            product_id = p.element_id
        else:
            # Product 노드가 없으면 가상 노드 생성
            product_id = f"product_{product_cd}"
            nodes.append({
                'id': product_id,
                'label': product_cd,
                'type': 'Product',
                'color': '#FF6B6B',
                'size': 45,
                'properties': {
                    'id': product_cd,
                    'name': product_cd,
                    'note': 'Virtual node - Product not in Neo4j'
                }
            })
        
        # ProductionOrder 노드들
        for po in result['orders']:
            if po:
                nodes.append({
                    'id': po.element_id,
                    'label': po['id'],
                    'type': 'ProductionOrder',
                    'color': '#45B7D1',
                    'size': 35,
                    'properties': serialize_neo4j_types(dict(po))
                })
                edges.append({
                    'from': po.element_id,
                    'to': product_id,
                    'label': 'PRODUCES',
                    'color': '#FF6B6B'
                })
        
        # Variance 노드들 (각 Variance는 자신의 PO에만 연결)
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v.get('variance_name', v['id']),
                    'type': 'Variance',
                    'color': variance_color(v.get('variance_amount')),
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                v_order_no = v.get('order_no')
                for po in result['orders']:
                    if po and v_order_no == po.get('id'):
                        edges.append({
                            'from': po.element_id,
                            'to': v.element_id,
                            'label': 'HAS_VARIANCE',
                            'color': variance_color(v.get('variance_amount'))
                        })
        
        # Material 노드들
        for m in result['materials']:
            if m:
                nodes.append({
                    'id': m.element_id,
                    'label': m.get('name', m.get('id', 'Material')),
                    'type': 'Material',
                    'color': '#4ECDC4',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(m))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': m.element_id,
                            'label': 'CONSUMES',
                            'color': '#45B7D1'
                        })
        
        # WorkCenter 노드들
        for wc in result['workcenters']:
            if wc:
                nodes.append({
                    'id': wc.element_id,
                    'label': wc.get('name', wc.get('id', 'WorkCenter')),
                    'type': 'WorkCenter',
                    'color': '#FFA07A',
                    'size': 28,
                    'properties': serialize_neo4j_types(dict(wc))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': wc.element_id,
                            'label': 'WORKS_AT',
                            'color': '#FFA07A'
                        })
        
        # Cause 노드들
        for c in result['causes']:
            if c and not any(n['id'] == c.element_id for n in nodes):
                nodes.append({
                    'id': c.element_id,
                    'label': c.get('description', c.get('code', 'Cause')),
                    'type': 'Cause',
                    'color': '#F7DC6F',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(c))
                })
        # Variance -> Cause 실제 관계만 연결
        for pair in cause_pairs:
            v_id = pair.get('v_id')
            c_id = pair.get('c_id')
            if v_id and c_id:
                edges.append({
                    'from': v_id,
                    'to': c_id,
                    'label': 'CAUSED_BY',
                    'color': '#F7DC6F'
                })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': product_cd
        })


@app.route('/api/material/<material_id>/graph', methods=['GET'])
def get_material_graph(material_id):
    """원자재 중심 그래프 - 차이가 큰 상위 5개만 간단하게 표시"""
    
    with neo4j_conn.driver.session() as session:
        # 차이가 큰 상위 5개 생산오더만 선택하고, WorkCenter/Cause는 제외
        query = """
        MATCH (m:Material {id: $material_id})
        MATCH (po:ProductionOrder)-[:CONSUMES]->(m)
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH m, po, SUM(COALESCE(v.variance_amount, 0)) as total_variance
        ORDER BY ABS(total_variance) DESC
        LIMIT 5
        
        WITH m, collect(po) as top_orders
        
        UNWIND top_orders as po
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (po)-[:PRODUCES]->(p:Product)
        
        WITH m,
             collect(DISTINCT po) as orders,
             collect(DISTINCT v) as variances,
             collect(DISTINCT p) as products
        
        RETURN m, orders, variances, [] as workcenters, products, [] as causes
        """
        
        result = session.run(query, material_id=material_id).single()
        
        if not result or not result['m']:
            return jsonify({'error': 'Material not found'}), 404
        
        nodes = []
        edges = []
        order_ids = [po['id'] for po in (result['orders'] or []) if po and po.get('id')]
        cause_pairs = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v)-[:CAUSED_BY]->(c)
            WHERE po.id IN $order_ids
            RETURN DISTINCT elementId(v) as v_id, elementId(c) as c_id
        """, order_ids=order_ids).data() if order_ids else []
        
        # Material 노드 (중심)
        m = result['m']
        nodes.append({
            'id': m.element_id,
            'label': m.get('name', m.get('id', material_id)),
            'type': 'Material',
            'color': '#4ECDC4',
            'size': 45,
            'properties': serialize_neo4j_types(dict(m))
        })
        
        # ProductionOrder 노드들
        for po in result['orders']:
            if po:
                nodes.append({
                    'id': po.element_id,
                    'label': po['id'],
                    'type': 'ProductionOrder',
                    'color': '#45B7D1',
                    'size': 35,
                    'properties': serialize_neo4j_types(dict(po))
                })
                edges.append({
                    'from': po.element_id,
                    'to': m.element_id,
                    'label': 'CONSUMES',
                    'color': '#4ECDC4'
                })
        
        # Variance 노드들 (각 Variance는 자신의 PO에만 연결)
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v.get('variance_name', v['id']),
                    'type': 'Variance',
                    'color': variance_color(v.get('variance_amount')),
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                v_order_no = v.get('order_no')
                for po in result['orders']:
                    if po and v_order_no == po.get('id'):
                        edges.append({
                            'from': po.element_id,
                            'to': v.element_id,
                            'label': 'HAS_VARIANCE',
                            'color': variance_color(v.get('variance_amount'))
                        })
        
        # WorkCenter 노드들
        for wc in result['workcenters']:
            if wc:
                nodes.append({
                    'id': wc.element_id,
                    'label': wc.get('name', wc.get('id', 'WorkCenter')),
                    'type': 'WorkCenter',
                    'color': '#FFA07A',
                    'size': 28,
                    'properties': serialize_neo4j_types(dict(wc))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': wc.element_id,
                            'label': 'WORKS_AT',
                            'color': '#FFA07A'
                        })
        
        # Product 노드들
        for p in result['products']:
            if p:
                nodes.append({
                    'id': p.element_id,
                    'label': p.get('name', p.get('id', 'Product')),
                    'type': 'Product',
                    'color': '#FF6B6B',
                    'size': 30,
                    'properties': serialize_neo4j_types(dict(p))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': p.element_id,
                            'label': 'PRODUCES',
                            'color': '#FF6B6B'
                        })
        
        # Cause 노드들
        for c in result['causes']:
            if c and not any(n['id'] == c.element_id for n in nodes):
                nodes.append({
                    'id': c.element_id,
                    'label': c.get('description', c.get('code', 'Cause')),
                    'type': 'Cause',
                    'color': '#F7DC6F',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(c))
                })
        # Variance -> Cause 실제 관계만 연결
        for pair in cause_pairs:
            v_id = pair.get('v_id')
            c_id = pair.get('c_id')
            if v_id and c_id:
                edges.append({
                    'from': v_id,
                    'to': c_id,
                    'label': 'CAUSED_BY',
                    'color': '#F7DC6F'
                })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': material_id
        })


@app.route('/api/workcenter/<workcenter_id>/graph', methods=['GET'])
def get_workcenter_graph(workcenter_id):
    """공정(WorkCenter) 중심 그래프 - 차이가 큰 상위 5개만 간단하게 표시"""
    
    with neo4j_conn.driver.session() as session:
        # 차이가 큰 상위 5개 생산오더만 선택하고, Material은 제외
        query = """
        MATCH (wc:WorkCenter {id: $workcenter_id})
        MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc)
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH wc, po, SUM(COALESCE(v.variance_amount, 0)) as total_variance
        ORDER BY ABS(total_variance) DESC
        LIMIT 5
        
        WITH wc, collect(po) as top_orders
        
        UNWIND top_orders as po
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (po)-[:PRODUCES]->(p:Product)
        
        WITH wc,
             collect(DISTINCT po) as orders,
             collect(DISTINCT v) as variances,
             collect(DISTINCT p) as products
        
        RETURN wc, orders, variances, [] as materials, products, [] as causes
        """
        
        result = session.run(query, workcenter_id=workcenter_id).single()
        
        if not result or not result['wc']:
            return jsonify({'error': 'WorkCenter not found'}), 404
        
        nodes = []
        edges = []
        order_ids = [po['id'] for po in (result['orders'] or []) if po and po.get('id')]
        cause_pairs = session.run("""
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v)-[:CAUSED_BY]->(c)
            WHERE po.id IN $order_ids
            RETURN DISTINCT elementId(v) as v_id, elementId(c) as c_id
        """, order_ids=order_ids).data() if order_ids else []
        
        # WorkCenter 노드 (중심)
        wc = result['wc']
        nodes.append({
            'id': wc.element_id,
            'label': wc.get('name', wc.get('id', workcenter_id)),
            'type': 'WorkCenter',
            'color': '#FFA07A',
            'size': 45,
            'properties': serialize_neo4j_types(dict(wc))
        })
        
        # ProductionOrder 노드들
        for po in result['orders']:
            if po:
                nodes.append({
                    'id': po.element_id,
                    'label': po['id'],
                    'type': 'ProductionOrder',
                    'color': '#45B7D1',
                    'size': 35,
                    'properties': serialize_neo4j_types(dict(po))
                })
                edges.append({
                    'from': po.element_id,
                    'to': wc.element_id,
                    'label': 'WORKS_AT',
                    'color': '#FFA07A'
                })
        
        # Variance 노드들 (각 Variance는 자신의 PO에만 연결)
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v.get('variance_name', v['id']),
                    'type': 'Variance',
                    'color': variance_color(v.get('variance_amount')),
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                v_order_no = v.get('order_no')
                for po in result['orders']:
                    if po and v_order_no == po.get('id'):
                        edges.append({
                            'from': po.element_id,
                            'to': v.element_id,
                            'label': 'HAS_VARIANCE',
                            'color': '#98D8C8'
                        })
        
        # Material 노드들
        for m in result['materials']:
            if m:
                nodes.append({
                    'id': m.element_id,
                    'label': m.get('name', m.get('id', 'Material')),
                    'type': 'Material',
                    'color': '#4ECDC4',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(m))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': m.element_id,
                            'label': 'CONSUMES',
                            'color': '#4ECDC4'
                        })
        
        # Product 노드들
        for p in result['products']:
            if p:
                nodes.append({
                    'id': p.element_id,
                    'label': p.get('name', p.get('id', 'Product')),
                    'type': 'Product',
                    'color': '#FF6B6B',
                    'size': 30,
                    'properties': serialize_neo4j_types(dict(p))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': p.element_id,
                            'label': 'PRODUCES',
                            'color': '#FF6B6B'
                        })
        
        # Cause 노드들
        for c in result['causes']:
            if c:
                if not any(n['id'] == c.element_id for n in nodes):
                    nodes.append({
                        'id': c.element_id,
                        'label': c.get('description', c.get('code', 'Cause')),
                        'type': 'Cause',
                        'color': '#F7DC6F',
                        'size': 25,
                        'properties': serialize_neo4j_types(dict(c))
                    })
                
                for v in result['variances']:
                    if v:
                        edges.append({
                            'from': v.element_id,
                            'to': c.element_id,
                            'label': 'CAUSED_BY',
                            'color': '#F7DC6F'
                        })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': workcenter_id
        })


@app.route('/api/production-order/<order_no>/graph', methods=['GET'])
def get_production_order_graph(order_no):
    """생산오더 중심 그래프"""
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (po:ProductionOrder {id: $order_no})
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        OPTIONAL MATCH (po)-[:CONSUMES]->(m:Material)
        OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
        OPTIONAL MATCH (po)-[:PRODUCES]->(p:Product)
        OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
        
        RETURN po,
               collect(DISTINCT v) as variances,
               collect(DISTINCT m) as materials,
               collect(DISTINCT wc) as workcenters,
               collect(DISTINCT p) as products,
               collect(DISTINCT c) as causes
        """
        
        result = session.run(query, order_no=order_no).single()
        
        if not result:
            return jsonify({'error': 'Production order not found'}), 404
        
        nodes = []
        edges = []
        cause_pairs = session.run("""
            MATCH (po:ProductionOrder {id: $order_no})-[:HAS_VARIANCE]->(v)-[:CAUSED_BY]->(c)
            RETURN elementId(v) as v_id, elementId(c) as c_id
        """, order_no=order_no).data()
        
        # ProductionOrder 노드 (중심)
        po = result['po']
        nodes.append({
            'id': po.element_id,
            'label': po['id'],
            'type': 'ProductionOrder',
            'color': '#45B7D1',
            'size': 40,
            'properties': serialize_neo4j_types(dict(po))
        })
        
        # Product 노드가 없으면 product_cd로 가상 노드 생성
        if po.get('product_cd') and not result['products']:
            product_id = f"product_{po['product_cd']}"
            nodes.append({
                'id': product_id,
                'label': po['product_cd'],
                'type': 'Product',
                'color': '#FF6B6B',
                'size': 30,
                'properties': {
                    'id': po['product_cd'],
                    'name': po['product_cd'],
                    'note': 'Virtual node - Product not loaded in Neo4j'
                }
            })
            edges.append({
                'from': po.element_id,
                'to': product_id,
                'label': 'PRODUCES',
                'color': '#FF6B6B'
            })
        
        # Variance 노드들
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v.get('variance_name', v['id']),
                    'type': 'Variance',
                    'color': variance_color(v.get('variance_amount')),
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                edges.append({
                    'from': po.element_id,
                    'to': v.element_id,
                    'label': 'HAS_VARIANCE',
                    'color': variance_color(v.get('variance_amount'))
                })
        
        # Material 노드들
        for m in result['materials']:
            if m:
                nodes.append({
                    'id': m.element_id,
                    'label': m.get('name', m.get('id', 'Material')),
                    'type': 'Material',
                    'color': '#4ECDC4',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(m))
                })
                edges.append({
                    'from': po.element_id,
                    'to': m.element_id,
                    'label': 'CONSUMES',
                    'color': '#45B7D1'
                })
        
        # WorkCenter 노드들
        for wc in result['workcenters']:
            if wc:
                nodes.append({
                    'id': wc.element_id,
                    'label': wc.get('name', wc.get('id', 'WorkCenter')),
                    'type': 'WorkCenter',
                    'color': '#FFA07A',
                    'size': 28,
                    'properties': serialize_neo4j_types(dict(wc))
                })
                edges.append({
                    'from': po.element_id,
                    'to': wc.element_id,
                    'label': 'WORKS_AT',
                    'color': '#FFA07A'
                })
        
        # Product 노드들
        for p in result['products']:
            if p:
                nodes.append({
                    'id': p.element_id,
                    'label': p.get('name', p.get('id', 'Product')),
                    'type': 'Product',
                    'color': '#FF6B6B',
                    'size': 30,
                    'properties': serialize_neo4j_types(dict(p))
                })
                edges.append({
                    'from': po.element_id,
                    'to': p.element_id,
                    'label': 'PRODUCES',
                    'color': '#FF6B6B'
                })
        
        # Cause 노드들
        for c in result['causes']:
            if c and not any(n['id'] == c.element_id for n in nodes):
                nodes.append({
                    'id': c.element_id,
                    'label': c.get('description', c.get('code', 'Cause')),
                    'type': 'Cause',
                    'color': '#F7DC6F',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(c))
                })
        # Variance -> Cause 실제 관계만 연결
        for pair in cause_pairs:
            v_id = pair.get('v_id')
            c_id = pair.get('c_id')
            if v_id and c_id:
                edges.append({
                    'from': v_id,
                    'to': c_id,
                    'label': 'CAUSED_BY',
                    'color': '#F7DC6F'
                })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'center': order_no
        })


@app.route('/api/node/<node_id>/expand', methods=['GET'])
def expand_node(node_id):
    """노드 확장 - 연결된 노드들 가져오기"""
    if not neo4j_conn.driver:
        return jsonify({'nodes': [], 'edges': []})
    try:
        with neo4j_conn.driver.session() as session:
            query = """
            MATCH (n)
            WHERE elementId(n) = $node_id
            MATCH (n)-[r]-(connected)
            RETURN n, 
                   connected,
                   r,
                   type(r) as rel_type,
                   CASE 
                       WHEN startNode(r) = n THEN 'out'
                       ELSE 'in'
                   END as direction
            LIMIT 50
            """
            results = session.run(query, node_id=node_id)
            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()
            first_result = None
            for record in results:
                if first_result is None:
                    first_result = record
                    center = record['n']
                    center_type = list(center.labels)[0]
                    center_id = center.element_id
                    if center_id not in seen_nodes:
                        if center_type == 'Variance':
                            center_label = center.get('variance_name', center.get('id'))
                            center_color = variance_color(center.get('variance_amount'))
                        else:
                            center_label = center.get('id') or center.get('name') or center.get('description')
                            center_color = get_node_color(center_type)
                        nodes.append({
                            'id': center_id,
                            'label': center_label,
                            'type': center_type,
                            'color': center_color,
                            'size': 30,
                            'properties': serialize_neo4j_types(dict(center))
                        })
                        seen_nodes.add(center_id)
                connected = record['connected']
                node_type = list(connected.labels)[0]
                node_id = connected.element_id
                color_map = {
                    'Variance': '#98D8C8',
                    'ProductionOrder': '#45B7D1',
                    'Product': '#FF6B6B',
                    'Material': '#4ECDC4',
                    'WorkCenter': '#F7DC6F',
                    'Cause': '#F8B739'
                }
                if node_id not in seen_nodes:
                    if node_type == 'Variance':
                        node_label = connected.get('variance_name', connected.get('id'))
                        node_color = variance_color(connected.get('variance_amount'))
                    else:
                        node_label = connected.get('id') or connected.get('name') or connected.get('description')
                        node_color = color_map.get(node_type, '#95A5A6')
                    nodes.append({
                        'id': node_id,
                        'label': node_label,
                        'type': node_type,
                        'color': node_color,
                        'size': 25,
                        'properties': serialize_neo4j_types(dict(connected))
                    })
                    seen_nodes.add(node_id)
                rel_type = record['rel_type']
                direction = record['direction']
                edge_id = f"{center.element_id}-{node_id}-{rel_type}"
                if edge_id not in seen_edges:
                    if direction == 'out':
                        edges.append({
                            'id': edge_id,
                            'from': center.element_id,
                            'to': node_id,
                            'label': rel_type,
                            'arrows': 'to'
                        })
                    else:
                        edges.append({
                            'id': edge_id,
                            'from': node_id,
                            'to': center.element_id,
                            'label': rel_type,
                            'arrows': 'to'
                        })
                    seen_edges.add(edge_id)
            if not first_result:
                return jsonify({'nodes': [], 'edges': []})
            return jsonify({'nodes': nodes, 'edges': edges})
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({'nodes': [], 'edges': []})


@app.route('/api/overview', methods=['GET'])
def get_overview():
    """전체 개요 그래프 (연결 확인용으로도 사용됨)"""
    if not neo4j_conn.driver:
        return jsonify({'nodes': [], 'edges': []})
    try:
        with neo4j_conn.driver.session() as session:
            query = """
            MATCH (v:Variance)
            WITH v.cost_element as element,
                 v.variance_type as type,
                 collect(v)[..5] as sample_variances
            UNWIND sample_variances as v
            OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
            RETURN element, type,
                   collect(DISTINCT {
                       id: elementId(v),
                       label: v.id,
                       props: properties(v)
                   }) as variances,
                   collect(DISTINCT {
                       id: elementId(c),
                       label: c.description,
                       props: properties(c)
                   }) as causes
            """
            results = session.run(query).data()
            nodes = []
            edges = []
            element_nodes = {}
            added_node_ids = set()
            for row in results:
                element = row['element']
                if element not in element_nodes:
                    elem_id = f"element_{element}"
                    element_nodes[element] = elem_id
                    nodes.append({
                        'id': elem_id, 'label': element, 'type': 'CostElement',
                        'color': '#3498db', 'size': 40, 'properties': {'name': element}
                    })
                for v in (row.get('variances') or []):
                    if v and v.get('id') and v['id'] not in added_node_ids:
                        added_node_ids.add(v['id'])
                        nodes.append({
                            'id': v['id'], 'label': v.get('label', ''), 'type': 'Variance',
                            'color': '#98D8C8', 'size': 20, 'properties': v.get('props') or {}
                        })
                        edges.append({
                            'from': element_nodes[element], 'to': v['id'],
                            'label': row.get('type', ''), 'color': '#98D8C8'
                        })
                for c in (row.get('causes') or []):
                    if c and c.get('id') and c['id'] not in added_node_ids:
                        added_node_ids.add(c['id'])
                        nodes.append({
                            'id': c['id'], 'label': c.get('label', ''),
                            'type': 'Cause', 'color': '#F7DC6F', 'size': 25,
                            'properties': c.get('props') or {}
                        })
            return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'nodes': [], 'edges': []})


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """요약 통계"""
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (v:Variance)
        RETURN 
            v.cost_element as element,
            v.variance_type as type,
            SUM(v.variance_amount) as total,
            COUNT(v) as count
        ORDER BY element, type
        """
        
        results = session.run(query).data()
        return jsonify(results)


def _safe_month(fd):
    """날짜 값에서 YYYY-MM 추출 (Neo4j Date/문자열 모두 처리)"""
    if fd is None:
        return None
    s = str(fd) if not isinstance(fd, str) else fd
    return s[:7] if len(s) >= 7 else s


def _empty_filters():
    return jsonify({'products': [], 'work_centers': [], 'materials': [], 'months': []})


@app.route('/api/filters', methods=['GET'])
def get_filters():
    """필터 옵션 - 제품, 공정, 기간, 원자재"""
    if not neo4j_conn.driver:
        return _empty_filters()
    try:
        with neo4j_conn.driver.session() as session:
            # 제품 목록
            products_query = """
            MATCH (po:ProductionOrder)
            WHERE po.product_cd IS NOT NULL
            RETURN DISTINCT po.product_cd as product
            ORDER BY product
            """
            products = [row['product'] for row in session.run(products_query).data() if row.get('product')]
            
            # 공정 목록 (관계를 통해)
            wc_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            RETURN DISTINCT wc.id as work_center
            ORDER BY work_center
            """
            work_centers = [row['work_center'] for row in session.run(wc_query).data() if row.get('work_center')]
            
            # 원자재 목록
            material_query = """
            MATCH (m:Material)
            RETURN DISTINCT m.id as material_id, m.name as material_name
            ORDER BY material_id
            LIMIT 100
            """
            materials = [{'id': row['material_id'], 'name': row.get('material_name') or row['material_id']} 
                        for row in session.run(material_query).data() if row.get('material_id')]
            
            # 기간 목록 (월별 - finish_date 사용, 문자열/날짜 모두 처리)
            month_query = """
            MATCH (po:ProductionOrder)
            WHERE po.finish_date IS NOT NULL
            RETURN DISTINCT po.finish_date as fd
            ORDER BY fd DESC
            """
            months_raw = session.run(month_query).data()
            months = sorted({_safe_month(row.get('fd')) for row in months_raw if row.get('fd')} - {None}, reverse=True)
            
            return jsonify({
                'products': products or [],
                'work_centers': work_centers or [],
                'materials': materials or [],
                'months': months or []
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _empty_filters()


def _empty_filtered_summary():
    return jsonify({'total_variance': 0, 'total_count': 0, 'by_type': []})


@app.route('/api/filtered_summary', methods=['POST'])
def get_filtered_summary():
    """필터 적용된 요약 통계"""
    filters = request.json or {}
    product = filters.get('product', '')
    work_center = filters.get('work_center', '')
    month = filters.get('month', '')
    if not neo4j_conn.driver:
        return _empty_filtered_summary()
    try:
        with neo4j_conn.driver.session() as session:
            type_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            """
            if work_center:
                type_query += """
                AND EXISTS {
                    MATCH (po)-[:WORKS_AT]->(wc:WorkCenter {id: $work_center})
                }
                """
            type_query += """
            RETURN
                v.cost_element as cost_element,
                v.variance_type as variance_type,
                SUM(v.variance_amount) as total_variance,
                COUNT(v) as count
            ORDER BY cost_element
            """
            by_type = session.run(type_query, product=product, work_center=work_center, month=month).data()
            total_variance = sum([row.get('total_variance') or 0 for row in by_type])
            total_count = sum([row.get('count') or 0 for row in by_type])
            return jsonify({
                'total_variance': total_variance,
                'total_count': total_count,
                'by_type': by_type or []
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _empty_filtered_summary()


@app.route('/api/test/produces/<order_no>', methods=['GET'])
def test_produces(order_no):
    """PRODUCES 관계 테스트"""
    
    with neo4j_conn.driver.session() as session:
        result = session.run("""
            MATCH (po:ProductionOrder {id: $order_no})-[:PRODUCES]->(p:Product)
            RETURN p.id as product_id, p.name as product_name
        """, order_no=order_no).data()
        
        if result:
            return jsonify({'found': True, 'product': result[0]})
        else:
            # Product 노드 개수 확인
            count_result = session.run("MATCH (p:Product) RETURN COUNT(p) as count").single()
            po_result = session.run("""
                MATCH (po:ProductionOrder {id: $order_no})
                RETURN po.product_cd as product_cd
            """, order_no=order_no).single()
            
            return jsonify({
                'found': False,
                'product_node_count': count_result['count'] if count_result else 0,
                'po_product_cd': po_result['product_cd'] if po_result else None
            })


@app.route('/test')
def test_route():
    """테스트 라우트"""
    return jsonify({'status': 'ok', 'message': 'API is working!'})

@app.route('/')
def new_dashboard():
    """새로운 통합 대시보드"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, 'new_dashboard.html')
    if not os.path.exists(html_path):
        return f"File not found: {html_path}", 404
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    from flask import Response
    return Response(content, mimetype='text/html')

@app.route('/dashboard.html')
def index():
    """기존 대시보드 (Tab 1용 iframe)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, 'dashboard.html')
    if not os.path.exists(html_path):
        return f"File not found: {html_path}", 404
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    from flask import Response
    return Response(content, mimetype='text/html')

@app.route('/api/process-status', methods=['GET'])
def get_process_status():
    """공정별 Variance 상태 조회 (Heatmap용)"""
    if not neo4j_conn.driver:
        return jsonify([])

    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (wc:WorkCenter)
        OPTIONAL MATCH (wc)<-[:WORKS_AT]-(po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
        WITH wc, count(v) as risk_level
        RETURN wc.id as id, wc.name as label, risk_level
        ORDER BY wc.id
        """
        results = session.run(query).data()
        return jsonify(results)

@app.route('/api/order-costs/<order_id>', methods=['GET'])
def get_order_costs(order_id):
    """생산오더 비용 분석 (Waterfall Chart용)"""
    if not neo4j_conn.driver:
        return jsonify({'error': 'No DB connection'}), 500

    with neo4j_conn.driver.session() as session:
        # 1. Planned Cost 계산 (Product Standard Cost * Order Actual Qty)
        # 2. Variance 조회
        query = """
        MATCH (po:ProductionOrder {id: $order_id})
        OPTIONAL MATCH (po)-[:PRODUCES]->(p:Product)
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH po, p, collect({element: v.cost_element, amount: v.variance_amount}) as variances

        RETURN
            COALESCE(p.standard_cost, 0) * po.actual_qty as total_planned,
            variances
        """
        result = session.run(query, order_id=order_id).single()

        if not result:
            return jsonify({'error': 'Order not found'}), 404

        total_planned = result['total_planned'] or 0
        variances = [v for v in result['variances'] if v['amount'] is not None]

        total_variance = sum(v['amount'] for v in variances)
        total_actual = total_planned + total_variance

        return jsonify({
            'total_planned': total_planned,
            'total_actual': total_actual,
            'variances': variances
        })

@app.route('/api/graph-data', methods=['GET'])
def get_graph_data():
    """Graph Explorer용 데이터 (Generic)"""
    node_id = request.args.get('id')
    if not node_id:
        return jsonify({'error': 'Missing id parameter'}), 400

    # 기존 expand_node 로직 재사용 (이미 "Spider Legs" 확장을 지원함)
    return expand_node(node_id)

@app.route('/analysis.html')
def analysis():
    """상세 분석 페이지 - 리다이렉트"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_file(os.path.join(base_dir, 'variance_graph_dashboard_v3.html'))

@app.route('/variance_graph_dashboard_v3.html')
def variance_graph_v3():
    """상세 분석 페이지 v3"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    response = send_file(os.path.join(base_dir, 'variance_graph_dashboard_v3.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/comparison.html')
def comparison():
    """비교 분석 페이지"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_file(os.path.join(base_dir, 'comparison.html'))


def _default_summary():
    return {
        'total_variance': 0, 'variance_count': 0,
        'quantity_variance': 0, 'quantity_count': 0,
        'price_variance': 0, 'price_count': 0,
        'production_variance': 0, 'production_count': 0
    }


def _empty_dashboard_response():
    return jsonify({
        'summary': _default_summary(),
        'monthly_trend': [], 'by_type': [], 'by_product': [], 'by_process': [], 'top_orders': []
    })


@app.route('/api/dashboard-data', methods=['POST'])
def get_dashboard_data():
    """대시보드 데이터 제공"""
    data = request.json or {}
    product = data.get('product', '')
    work_center = data.get('work_center', '')
    month = data.get('month', '')
    if not neo4j_conn.driver:
        return _empty_dashboard_response()
    try:
        with neo4j_conn.driver.session() as session:
            # 요약 데이터
            if work_center:
                summary_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND wc.id = $work_center
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            RETURN 
                sum(v.variance_amount) as total_variance,
                count(v) as variance_count,
                sum(CASE WHEN v.cost_element = 'MATERIAL' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                sum(CASE WHEN v.cost_element = 'MATERIAL' THEN 1 ELSE 0 END) as quantity_count,
                sum(CASE WHEN v.cost_element = 'LABOR' THEN v.variance_amount ELSE 0 END) as price_variance,
                sum(CASE WHEN v.cost_element = 'LABOR' THEN 1 ELSE 0 END) as price_count,
                sum(CASE WHEN v.cost_element = 'OVERHEAD' THEN v.variance_amount ELSE 0 END) as production_variance,
                sum(CASE WHEN v.cost_element = 'OVERHEAD' THEN 1 ELSE 0 END) as production_count
            """
            else:
                summary_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            RETURN 
                sum(v.variance_amount) as total_variance,
                count(v) as variance_count,
                sum(CASE WHEN v.cost_element = 'MATERIAL' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                sum(CASE WHEN v.cost_element = 'MATERIAL' THEN 1 ELSE 0 END) as quantity_count,
                sum(CASE WHEN v.cost_element = 'LABOR' THEN v.variance_amount ELSE 0 END) as price_variance,
                sum(CASE WHEN v.cost_element = 'LABOR' THEN 1 ELSE 0 END) as price_count,
                sum(CASE WHEN v.cost_element = 'OVERHEAD' THEN v.variance_amount ELSE 0 END) as production_variance,
                sum(CASE WHEN v.cost_element = 'OVERHEAD' THEN 1 ELSE 0 END) as production_count
            """
            summary_row = session.run(summary_query, product=product, work_center=work_center, month=month).single()
            summary = summary_row if summary_row else _default_summary()
            
            # 월별 트렌드
            if work_center:
                trend_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND wc.id = $work_center
            WITH substring(toString(po.finish_date), 0, 7) as month, sum(v.variance_amount) as total
            RETURN month, total
            ORDER BY month
            """
            else:
                trend_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            WITH substring(toString(po.finish_date), 0, 7) as month, sum(v.variance_amount) as total
            RETURN month, total
            ORDER BY month
            """
            trend = session.run(trend_query, product=product, work_center=work_center).data()
            
            # 차이 유형별
            if work_center:
                type_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND wc.id = $work_center
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH v.cost_element as element, sum(v.variance_amount) as amount
            RETURN element, amount
            """
            else:
                type_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH v.cost_element as element, sum(v.variance_amount) as amount
            RETURN element, amount
            """
            by_type = session.run(type_query, product=product, work_center=work_center, month=month).data()
            
            # 제품별
            if work_center:
                product_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            WHERE wc.id = $work_center
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH po.product_cd as product, sum(v.variance_amount) as amount
            RETURN product, amount
            ORDER BY abs(amount) DESC
            """
            else:
                product_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH po.product_cd as product, sum(v.variance_amount) as amount
            RETURN product, amount
            ORDER BY abs(amount) DESC
            """
            by_product = session.run(product_query, work_center=work_center, month=month).data()
            
            # 공정별
            process_query = """
        MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
        MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WHERE ($product = '' OR po.product_cd = $product)
        AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
        WITH wc.id as work_center, sum(v.variance_amount) as amount
        RETURN work_center, amount
        ORDER BY abs(amount) DESC
        """
            by_process = session.run(process_query, product=product, month=month).data()
            
            # 상위 오더
            if work_center:
                top_orders_query = """
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND wc.id = $work_center
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH po, wc, sum(v.variance_amount) as total_variance
            ORDER BY abs(total_variance) DESC
            LIMIT 20
            RETURN po.id as order_no, po.product_cd as product, wc.id as work_center, total_variance
            """
            else:
                top_orders_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            OPTIONAL MATCH (po)-[:WORKS_AT]->(wc:WorkCenter)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH po, wc, sum(v.variance_amount) as total_variance
            ORDER BY abs(total_variance) DESC
            LIMIT 20
            RETURN po.id as order_no, po.product_cd as product, wc.id as work_center, total_variance
            """
            top_orders = session.run(top_orders_query, product=product, work_center=work_center, month=month).data()
            
            return jsonify({
                'summary': {
                    'total_variance': (summary.get('total_variance') or 0),
                    'variance_count': (summary.get('variance_count') or 0),
                    'quantity_variance': (summary.get('quantity_variance') or 0),
                    'quantity_count': (summary.get('quantity_count') or 0),
                    'price_variance': (summary.get('price_variance') or 0),
                    'price_count': (summary.get('price_count') or 0),
                    'production_variance': (summary.get('production_variance') or 0),
                    'production_count': (summary.get('production_count') or 0)
                },
                'monthly_trend': trend or [],
                'by_type': by_type or [],
                'by_product': by_product or [],
                'by_process': by_process or [],
                'top_orders': top_orders or []
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _empty_dashboard_response()


@app.route('/api/comparison-data', methods=['POST'])
def get_comparison_data():
    """비교 분석 데이터 제공"""
    data = request.json or {}
    targets = data.get('targets', [])
    
    summaries = []
    trends = []
    
    with neo4j_conn.driver.session() as session:
        for target in targets:
            # 요약 데이터
            if target['type'] == 'product':
                summary_query = """
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                WHERE po.product_cd = $value
                RETURN 
                    sum(v.variance_amount) as total_variance,
                    count(v) as variance_count,
                    sum(CASE WHEN v.variance_type = 'QUANTITY' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                    sum(CASE WHEN v.variance_type = 'PRICE' THEN v.variance_amount ELSE 0 END) as price_variance,
                    sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN v.variance_amount ELSE 0 END) as production_variance
                """
            elif target['type'] == 'work_center':
                summary_query = """
                MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
                MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
                WHERE wc.id = $value
                RETURN 
                    sum(v.variance_amount) as total_variance,
                    count(v) as variance_count,
                    sum(CASE WHEN v.variance_type = 'QUANTITY' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                    sum(CASE WHEN v.variance_type = 'PRICE' THEN v.variance_amount ELSE 0 END) as price_variance,
                    sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN v.variance_amount ELSE 0 END) as production_variance
                """
            elif target['type'] == 'month':
                summary_query = """
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                WHERE substring(toString(po.finish_date), 0, 7) = $value
                RETURN 
                    sum(v.variance_amount) as total_variance,
                    count(v) as variance_count,
                    sum(CASE WHEN v.variance_type = 'QUANTITY' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                    sum(CASE WHEN v.variance_type = 'PRICE' THEN v.variance_amount ELSE 0 END) as price_variance,
                    sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN v.variance_amount ELSE 0 END) as production_variance
                """
            else:
                continue
            
            summary = session.run(summary_query, value=target['value']).single()
            
            summaries.append({
                'total_variance': summary['total_variance'] or 0,
                'variance_count': summary['variance_count'] or 0,
                'quantity_variance': summary['quantity_variance'] or 0,
                'price_variance': summary['price_variance'] or 0,
                'production_variance': summary['production_variance'] or 0
            })
            
            # 월별 트렌드 (기간 비교가 아닌 경우에만)
            if target['type'] == 'product':
                trend_query = """
                MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
                WHERE po.product_cd = $value
                WITH substring(toString(po.finish_date), 0, 7) as month, sum(v.variance_amount) as total
                RETURN month, total
                ORDER BY month
                """
                trend = session.run(trend_query, value=target['value']).data()
                trends.append(trend)
            elif target['type'] == 'work_center':
                trend_query = """
                MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
                MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
                WHERE wc.id = $value
                WITH substring(toString(po.finish_date), 0, 7) as month, sum(v.variance_amount) as total
                RETURN month, total
                ORDER BY month
                """
                trend = session.run(trend_query, value=target['value']).data()
                trends.append(trend)
    
    return jsonify({
        'summaries': summaries,
        'trends': trends if trends else []
    })


if __name__ == '__main__':
    print("=" * 80)
    print("  Variance Graph API Server")
    print("=" * 80)
    print("\nServer starting...")
    print("Address: http://localhost:8000")
    print("\nAvailable APIs:")
    print("  GET /api/variance/<id>/graph")
    print("  GET /api/cause/<code>/graph")
    print("  GET /api/product/<product_cd>/graph")
    print("  GET /api/material/<material_id>/graph")
    print("  GET /api/workcenter/<workcenter_id>/graph")
    print("  GET /api/production-order/<order_no>/graph")
    print("  GET /api/node/<id>/expand")
    print("  GET /api/overview")
    print("  GET /api/summary")
    print("  GET /api/filters")
    print("  POST /api/filtered_summary")
    print("  GET /api/variances/by-type")
    print("\nOpen http://localhost:8000 in browser")
    print("=" * 80 + "\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=8000)
    finally:
        neo4j_conn.close()
