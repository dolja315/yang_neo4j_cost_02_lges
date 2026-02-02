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


class Neo4jConnection:
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
        if self.driver:
            self.driver.close()


# 전역 연결 객체
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
            'label': v['id'],
            'type': 'Variance',
            'color': '#98D8C8',
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
                    'color': '#98D8C8'
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
                    'label': v['id'],
                    'type': 'Variance',
                    'color': '#98D8C8',
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
                            'color': '#98D8C8'
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
        
        # Variance 노드들
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v['id'],
                    'type': 'Variance',
                    'color': '#98D8C8',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                # PO를 통해 연결
                for po in result['orders']:
                    if po:
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
        
        # Variance 노드들
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v['id'],
                    'type': 'Variance',
                    'color': '#98D8C8',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                for po in result['orders']:
                    if po:
                        edges.append({
                            'from': po.element_id,
                            'to': v.element_id,
                            'label': 'HAS_VARIANCE',
                            'color': '#98D8C8'
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
        
        # Variance 노드들
        for v in result['variances']:
            if v:
                nodes.append({
                    'id': v.element_id,
                    'label': v['id'],
                    'type': 'Variance',
                    'color': '#98D8C8',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
                for po in result['orders']:
                    if po:
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
                    'label': v['id'],
                    'type': 'Variance',
                    'color': '#98D8C8',
                    'size': 25,
                    'properties': serialize_neo4j_types(dict(v))
                })
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
            if c:
                # 중복 체크
                if not any(n['id'] == c.element_id for n in nodes):
                    nodes.append({
                        'id': c.element_id,
                        'label': c.get('description', c.get('code', 'Cause')),
                        'type': 'Cause',
                        'color': '#F7DC6F',
                        'size': 25,
                        'properties': serialize_neo4j_types(dict(c))
                    })
                
                # Variance -> Cause 연결
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
            'center': order_no
        })


@app.route('/api/node/<node_id>/expand', methods=['GET'])
def expand_node(node_id):
    """노드 확장 - 연결된 노드들 가져오기"""
    
    with neo4j_conn.driver.session() as session:
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        MATCH (n)-[r]-(connected)
        RETURN n, 
               type(r) as rel_type,
               collect(DISTINCT {
                   node: connected,
                   rel: r,
                   direction: CASE 
                       WHEN startNode(r) = n THEN 'out'
                       ELSE 'in'
                   END
               }) as connections
        LIMIT 50
        """
        
        result = session.run(query, node_id=node_id).single()
        
        if not result:
            return jsonify({'error': 'Node not found'}), 404
        
        nodes = []
        edges = []
        
        # 중심 노드
        center = result['n']
        center_type = list(center.labels)[0]
        nodes.append({
            'id': center.element_id,
            'label': center.get('id') or center.get('name') or center.get('description'),
            'type': center_type,
            'properties': serialize_neo4j_types(dict(center))
        })
        
        # 연결된 노드들
        for conn in result['connections']:
            node = conn['node']
            rel = conn['rel']
            direction = conn['direction']
            
            node_type = list(node.labels)[0]
            nodes.append({
                'id': node.element_id,
                'label': node.get('id') or node.get('name') or node.get('description'),
                'type': node_type,
                'properties': serialize_neo4j_types(dict(node))
            })
            
            if direction == 'out':
                edges.append({
                    'from': center.element_id,
                    'to': node.element_id,
                    'label': rel.type
                })
            else:
                edges.append({
                    'from': node.element_id,
                    'to': center.element_id,
                    'label': rel.type
                })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges
        })


@app.route('/api/overview', methods=['GET'])
def get_overview():
    """전체 개요 그래프"""
    
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
        
        # 원가 요소 노드 생성
        for row in results:
            element = row['element']
            if element not in element_nodes:
                elem_id = f"element_{element}"
                element_nodes[element] = elem_id
                nodes.append({
                    'id': elem_id,
                    'label': element,
                    'type': 'CostElement',
                    'color': '#3498db',
                    'size': 40,
                    'properties': {'name': element}
                })
            
            # Variance 노드들
            for v in row['variances']:
                if v and v['id'] not in added_node_ids:
                    added_node_ids.add(v['id'])
                    nodes.append({
                        'id': v['id'],
                        'label': v['label'],
                        'type': 'Variance',
                        'color': '#98D8C8',
                        'size': 20,
                        'properties': v['props']
                    })
                    edges.append({
                        'from': element_nodes[element],
                        'to': v['id'],
                        'label': row['type'],
                        'color': '#98D8C8'
                    })
            
            # Cause 노드들
            for c in row['causes']:
                if c and c['id'] and c['id'] not in added_node_ids:
                    added_node_ids.add(c['id'])
                    nodes.append({
                        'id': c['id'],
                        'label': c['label'],
                        'type': 'Cause',
                        'color': '#F7DC6F',
                        'size': 25,
                        'properties': c['props'] if c['props'] else {}
                    })
        
        return jsonify({
            'nodes': nodes,
            'edges': edges
        })


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


@app.route('/api/filters', methods=['GET'])
def get_filters():
    """필터 옵션 - 제품, 공정, 기간, 원자재"""
    
    with neo4j_conn.driver.session() as session:
        # 제품 목록
        products_query = """
        MATCH (po:ProductionOrder)
        RETURN DISTINCT po.product_cd as product
        ORDER BY product
        """
        products = [row['product'] for row in session.run(products_query).data() if row['product']]
        
        # 공정 목록 (관계를 통해)
        wc_query = """
        MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
        RETURN DISTINCT wc.id as work_center
        ORDER BY work_center
        """
        work_centers = [row['work_center'] for row in session.run(wc_query).data() if row['work_center']]
        
        # 원자재 목록
        material_query = """
        MATCH (m:Material)
        RETURN DISTINCT m.id as material_id, m.name as material_name
        ORDER BY material_id
        LIMIT 100
        """
        materials = [{'id': row['material_id'], 'name': row['material_name'] or row['material_id']} 
                    for row in session.run(material_query).data() if row['material_id']]
        
        # 기간 목록 (월별 - finish_date 사용)
        month_query = """
        MATCH (po:ProductionOrder)
        WHERE po.finish_date IS NOT NULL
        WITH substring(toString(po.finish_date), 0, 7) as month
        RETURN DISTINCT month
        ORDER BY month DESC
        """
        months = [row['month'] for row in session.run(month_query).data() if row['month']]
        
        return jsonify({
            'products': products,
            'work_centers': work_centers,
            'materials': materials,
            'months': months
        })


@app.route('/api/filtered_summary', methods=['POST'])
def get_filtered_summary():
    """필터 적용된 요약 통계"""
    
    filters = request.json or {}
    product = filters.get('product', '')
    work_center = filters.get('work_center', '')
    month = filters.get('month', '')
    
    with neo4j_conn.driver.session() as session:
        # 타입별로 집계
        type_query = """
        MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
        WHERE ($product = '' OR po.product_cd = $product)
        AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
        """
        
        # work_center 필터 추가 (관계를 통해)
        if work_center:
            type_query += """
            AND EXISTS {
                MATCH (po)-[:WORKS_AT]->(wc:WorkCenter {id: $work_center})
            }
            """
        
        type_query += """
        RETURN 
            v.variance_type as variance_type,
            SUM(v.variance_amount) as total_variance,
            COUNT(v) as count
        ORDER BY variance_type
        """
        
        by_type = session.run(type_query,
                            product=product,
                            work_center=work_center,
                            month=month).data()
        
        total_variance = sum([row['total_variance'] for row in by_type if row['total_variance']])
        total_count = sum([row['count'] for row in by_type if row['count']])
        
        return jsonify({
            'total_variance': total_variance,
            'total_count': total_count,
            'by_type': by_type
        })


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


@app.route('/')
def index():
    """메인 페이지 - 대시보드 홈"""
    return send_file('../dashboard.html')

@app.route('/analysis.html')
def analysis():
    """상세 분석 페이지 - 리다이렉트"""
    return send_file('../variance_graph_dashboard_v3.html')

@app.route('/variance_graph_dashboard_v3.html')
def variance_graph_v3():
    """상세 분석 페이지 v3"""
    return send_file('../variance_graph_dashboard_v3.html')

@app.route('/comparison.html')
def comparison():
    """비교 분석 페이지"""
    return send_file('../comparison.html')


@app.route('/api/dashboard-data', methods=['POST'])
def get_dashboard_data():
    """대시보드 데이터 제공"""
    data = request.json
    product = data.get('product', '')
    work_center = data.get('work_center', '')
    month = data.get('month', '')
    
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
                sum(CASE WHEN v.variance_type = 'QUANTITY' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                sum(CASE WHEN v.variance_type = 'QUANTITY' THEN 1 ELSE 0 END) as quantity_count,
                sum(CASE WHEN v.variance_type = 'PRICE' THEN v.variance_amount ELSE 0 END) as price_variance,
                sum(CASE WHEN v.variance_type = 'PRICE' THEN 1 ELSE 0 END) as price_count,
                sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN v.variance_amount ELSE 0 END) as production_variance,
                sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN 1 ELSE 0 END) as production_count
            """
        else:
            summary_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            RETURN 
                sum(v.variance_amount) as total_variance,
                count(v) as variance_count,
                sum(CASE WHEN v.variance_type = 'QUANTITY' THEN v.variance_amount ELSE 0 END) as quantity_variance,
                sum(CASE WHEN v.variance_type = 'QUANTITY' THEN 1 ELSE 0 END) as quantity_count,
                sum(CASE WHEN v.variance_type = 'PRICE' THEN v.variance_amount ELSE 0 END) as price_variance,
                sum(CASE WHEN v.variance_type = 'PRICE' THEN 1 ELSE 0 END) as price_count,
                sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN v.variance_amount ELSE 0 END) as production_variance,
                sum(CASE WHEN v.variance_type = 'PRODUCTION' THEN 1 ELSE 0 END) as production_count
            """
        summary = session.run(summary_query, product=product, work_center=work_center, month=month).single()
        
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
            WITH v.variance_type as type, sum(v.variance_amount) as amount
            RETURN type, amount
            """
        else:
            type_query = """
            MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
            WHERE ($product = '' OR po.product_cd = $product)
            AND ($month = '' OR substring(toString(po.finish_date), 0, 7) = $month)
            WITH v.variance_type as type, sum(v.variance_amount) as amount
            RETURN type, amount
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
                'total_variance': summary['total_variance'] or 0,
                'variance_count': summary['variance_count'] or 0,
                'quantity_variance': summary['quantity_variance'] or 0,
                'quantity_count': summary['quantity_count'] or 0,
                'price_variance': summary['price_variance'] or 0,
                'price_count': summary['price_count'] or 0,
                'production_variance': summary['production_variance'] or 0,
                'production_count': summary['production_count'] or 0
            },
            'monthly_trend': trend,
            'by_type': by_type,
            'by_product': by_product,
            'by_process': by_process,
            'top_orders': top_orders
        })


@app.route('/api/comparison-data', methods=['POST'])
def get_comparison_data():
    """비교 분석 데이터 제공"""
    data = request.json
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
    print("Address: http://localhost:5000")
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
    print("\nOpen http://localhost:5000 in browser")
    print("=" * 80 + "\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        neo4j_conn.close()
