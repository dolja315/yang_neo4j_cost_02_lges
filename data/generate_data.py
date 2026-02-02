"""
반도체 패키징 원가 데이터 생성기

중규모 예제 데이터를 생성합니다:
- 제품: 20개
- 자재: 50개
- 생산오더: 100개
- 작업장: 10개
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import random
import os

# 시드 설정 (재현성)
random.seed(42)
np.random.seed(42)
fake = Faker('ko_KR')
Faker.seed(42)

# 출력 디렉토리
RDB_DIR = 'data/rdb_tables'
NEO4J_DIR = 'data/neo4j_import'

os.makedirs(RDB_DIR, exist_ok=True)
os.makedirs(NEO4J_DIR, exist_ok=True)

# ============================================================
# 1. 마스터 데이터 생성
# ============================================================

def generate_products():
    """제품 마스터 생성 (20개)"""
    package_types = {
        'QFP': {'pins': [32, 44, 64, 80, 100], 'base_cost': 8000},
        'BGA': {'pins': [144, 256, 324, 484], 'base_cost': 35000},
        'SOP': {'pins': [8, 14, 16, 20], 'base_cost': 3000},
        'TSOP': {'pins': [28, 32, 48, 56], 'base_cost': 4500},
        'PLCC': {'pins': [20, 28, 44, 52], 'base_cost': 5000}
    }
    
    products = []
    product_id = 1
    
    for pkg_type, config in package_types.items():
        for pins in config['pins']:
            # 표준 원가 계산 (핀수에 비례)
            standard_cost = config['base_cost'] + (pins * 50)
            # 약간의 변동
            standard_cost *= random.uniform(0.9, 1.1)
            
            products.append({
                'product_cd': f'{pkg_type}{pins}-{product_id:03d}',
                'product_name': f'{pkg_type}-{pins} Package',
                'product_type': pkg_type,
                'package_pins': pins,
                'standard_cost': round(standard_cost, 2),
                'active_flag': 'Y',
                'created_date': '2024-01-01'
            })
            product_id += 1
    
    df = pd.DataFrame(products)
    print(f"✓ 제품 마스터 생성: {len(df)}개")
    return df

def generate_materials():
    """자재 마스터 생성 (50개)"""
    materials = []
    
    # 다이 (20개 - 각 제품에 대응)
    for i in range(1, 21):
        materials.append({
            'material_cd': f'DIE-{i:03d}',
            'material_name': f'Silicon Die Type-{i}',
            'material_type': 'DIE',
            'unit': 'EA',
            'standard_price': round(random.uniform(5000, 50000), 2),
            'price_unit': 'KRW',
            'supplier_cd': f'SUP-DIE-{(i-1)%5+1:02d}',
            'active_flag': 'Y'
        })
    
    # 기판/리드프레임 (10개)
    for i in range(1, 11):
        materials.append({
            'material_cd': f'SUBSTRATE-{i:03d}',
            'material_name': f'Lead Frame/Substrate Type-{i}',
            'material_type': 'SUBSTRATE',
            'unit': 'EA',
            'standard_price': round(random.uniform(80, 600), 2),
            'price_unit': 'KRW',
            'supplier_cd': f'SUP-SUB-{(i-1)%3+1:02d}',
            'active_flag': 'Y'
        })
    
    # 금선 (5개 - 다양한 직경)
    wire_types = [
        ('25UM', 25, 60.0),
        ('30UM', 30, 72.0),
        ('20UM', 20, 50.0),
        ('18UM', 18, 45.0),
        ('35UM', 35, 85.0)
    ]
    for i, (code, diameter, price) in enumerate(wire_types, 1):
        materials.append({
            'material_cd': f'GOLDWIRE-{code}',
            'material_name': f'Gold Wire {diameter}um',
            'material_type': 'WIRE',
            'unit': 'MG',
            'standard_price': price * random.uniform(0.95, 1.05),
            'price_unit': 'KRW',
            'supplier_cd': 'SUP-WIRE-01',
            'active_flag': 'Y'
        })
    
    # 에폭시 수지 (5개)
    for i in range(1, 6):
        materials.append({
            'material_cd': f'EPOXY-{i:03d}',
            'material_name': f'Molding Compound Type-{i}',
            'material_type': 'RESIN',
            'unit': 'G',
            'standard_price': round(random.uniform(80, 120), 2),
            'price_unit': 'KRW',
            'supplier_cd': f'SUP-EPOXY-{(i-1)%2+1:02d}',
            'active_flag': 'Y'
        })
    
    # 기타 자재 (10개)
    other_materials = [
        ('ADHESIVE', 'Die Attach Adhesive', 'CHEMICAL', 'G', 50),
        ('INK-BLACK', 'Marking Ink Black', 'INK', 'ML', 5),
        ('INK-WHITE', 'Marking Ink White', 'INK', 'ML', 5),
        ('CLEANSER', 'Cleaning Solution', 'CHEMICAL', 'ML', 3),
        ('TAPE', 'Dicing Tape', 'CONSUMABLE', 'M', 100),
        ('SOCKET', 'Test Socket', 'CONSUMABLE', 'EA', 5000),
        ('TRAY', 'Shipping Tray', 'PACKAGE', 'EA', 500),
        ('LABEL', 'Product Label', 'PACKAGE', 'EA', 10),
        ('BAG', 'Anti-static Bag', 'PACKAGE', 'EA', 50),
        ('BOX', 'Shipping Box', 'PACKAGE', 'EA', 300)
    ]
    
    for i, (code, name, mat_type, unit, price) in enumerate(other_materials, 1):
        materials.append({
            'material_cd': code,
            'material_name': name,
            'material_type': mat_type,
            'unit': unit,
            'standard_price': price,
            'price_unit': 'KRW',
            'supplier_cd': f'SUP-OTHER-{(i-1)%3+1:02d}',
            'active_flag': 'Y'
        })
    
    df = pd.DataFrame(materials)
    print(f"✓ 자재 마스터 생성: {len(df)}개")
    return df

def generate_bom(products_df, materials_df):
    """BOM 생성"""
    boms = []
    bom_id = 1
    
    # DIE 자재 매핑
    die_materials = materials_df[materials_df['material_type'] == 'DIE']['material_cd'].tolist()
    # SUBSTRATE 자재
    substrate_materials = materials_df[materials_df['material_type'] == 'SUBSTRATE']['material_cd'].tolist()
    # WIRE 자재
    wire_materials = materials_df[materials_df['material_type'] == 'WIRE']['material_cd'].tolist()
    # RESIN 자재
    resin_materials = materials_df[materials_df['material_type'] == 'RESIN']['material_cd'].tolist()
    
    for idx, product in products_df.iterrows():
        product_cd = product['product_cd']
        pkg_type = product['product_type']
        pins = product['package_pins']
        
        # 각 제품에 DIE 할당 (1:1 매핑)
        die_idx = idx % len(die_materials)
        boms.append({
            'bom_id': bom_id,
            'product_cd': product_cd,
            'material_cd': die_materials[die_idx],
            'quantity': 1.0,
            'unit': 'EA',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1
        
        # SUBSTRATE
        substrate_idx = idx % len(substrate_materials)
        boms.append({
            'bom_id': bom_id,
            'product_cd': product_cd,
            'material_cd': substrate_materials[substrate_idx],
            'quantity': 1.0,
            'unit': 'EA',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1
        
        # WIRE (핀수에 비례)
        wire_idx = random.randint(0, len(wire_materials)-1)
        wire_qty = round(pins * 0.15, 1)  # 핀수 x 0.15mg
        boms.append({
            'bom_id': bom_id,
            'product_cd': product_cd,
            'material_cd': wire_materials[wire_idx],
            'quantity': wire_qty,
            'unit': 'MG',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1
        
        # RESIN (패키지 크기에 비례)
        resin_idx = random.randint(0, len(resin_materials)-1)
        if pkg_type == 'BGA':
            resin_qty = round(random.uniform(1.5, 2.5), 2)
        elif pkg_type == 'QFP':
            resin_qty = round(random.uniform(0.8, 1.5), 2)
        else:
            resin_qty = round(random.uniform(0.4, 1.0), 2)
        
        boms.append({
            'bom_id': bom_id,
            'product_cd': product_cd,
            'material_cd': resin_materials[resin_idx],
            'quantity': resin_qty,
            'unit': 'G',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1
        
        # ADHESIVE
        boms.append({
            'bom_id': bom_id,
            'product_cd': product_cd,
            'material_cd': 'ADHESIVE',
            'quantity': 0.1,
            'unit': 'G',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1
    
    df = pd.DataFrame(boms)
    print(f"✓ BOM 생성: {len(df)}개")
    return df

def generate_work_centers():
    """작업장 마스터 생성 (10개)"""
    work_centers = [
        ('WC-DIEBOND-01', 'Die Bonding Line 1', 'DIE_BONDING', 30000, 65000, 240),
        ('WC-DIEBOND-02', 'Die Bonding Line 2', 'DIE_BONDING', 30000, 65000, 240),
        ('WC-WIREBOND-01', 'Wire Bonding Line 1', 'WIRE_BONDING', 30000, 65000, 120),
        ('WC-WIREBOND-02', 'Wire Bonding Line 2', 'WIRE_BONDING', 30000, 65000, 120),
        ('WC-MOLDING-01', 'Molding Press 1', 'MOLDING', 30000, 65000, 180),
        ('WC-MOLDING-02', 'Molding Press 2', 'MOLDING', 30000, 65000, 180),
        ('WC-MARKING-01', 'Marking Line 1', 'MARKING', 30000, 65000, 720),
        ('WC-MARKING-02', 'Marking Line 2', 'MARKING', 30000, 65000, 720),
        ('WC-TEST-01', 'Final Test Line 1', 'TESTING', 30000, 65000, 360),
        ('WC-TEST-02', 'Final Test Line 2', 'TESTING', 30000, 65000, 360)
    ]
    
    wc_list = []
    for wc_cd, name, proc_type, labor, overhead, capacity in work_centers:
        wc_list.append({
            'workcenter_cd': wc_cd,
            'workcenter_name': name,
            'process_type': proc_type,
            'labor_rate_per_hour': labor,
            'overhead_rate_per_hour': overhead,
            'capacity_per_hour': capacity,
            'active_flag': 'Y'
        })
    
    df = pd.DataFrame(wc_list)
    print(f"✓ 작업장 마스터 생성: {len(df)}개")
    return df

def generate_routing(products_df, work_centers_df):
    """라우팅 생성"""
    routings = []
    routing_id = 1
    
    # 공정 순서 정의
    process_sequence = [
        ('DIE_BONDING', 10, 15.0, 30.0),
        ('WIRE_BONDING', 20, 30.0, 45.0),
        ('MOLDING', 30, 20.0, 60.0),
        ('MARKING', 40, 5.0, 10.0),
        ('TESTING', 50, 10.0, 15.0)
    ]
    
    for idx, product in products_df.iterrows():
        product_cd = product['product_cd']
        pins = product['package_pins']
        
        for proc_type, seq, base_time, setup_time in process_sequence:
            # 작업장 선택 (라인 1 또는 2)
            wc_candidates = work_centers_df[work_centers_df['process_type'] == proc_type]
            wc_cd = wc_candidates.sample(1)['workcenter_cd'].values[0]
            
            # 표준시간 계산 (핀수에 비례)
            if proc_type == 'WIRE_BONDING':
                std_time = base_time * (pins / 64)  # 64핀 기준
            else:
                std_time = base_time
            
            routings.append({
                'routing_id': routing_id,
                'product_cd': product_cd,
                'operation_seq': seq,
                'workcenter_cd': wc_cd,
                'standard_time_sec': round(std_time, 1),
                'setup_time_min': setup_time,
                'valid_from': '2024-01-01',
                'valid_to': None
            })
            routing_id += 1
    
    df = pd.DataFrame(routings)
    print(f"✓ 라우팅 생성: {len(df)}개")
    return df

# ============================================================
# 2. 트랜잭션 데이터 생성
# ============================================================

def generate_production_orders(products_df):
    """생산오더 생성 (100개, 3개월)"""
    orders = []
    start_date = datetime(2024, 1, 1)
    
    # 월별 가중치 (1월 많음, 2월 적음, 3월 보통)
    monthly_weights = {1: 1.3, 2: 0.7, 3: 1.0}
    
    for order_id in range(1, 101):
        # 날짜 생성 (1월~3월)
        days_offset = random.randint(0, 89)
        order_date = start_date + timedelta(days=days_offset)
        month = order_date.month
        
        # 제품 선택
        product = products_df.sample(1).iloc[0]
        product_cd = product['product_cd']
        
        # 계획 수량 (월별 가중치 적용)
        base_qty = random.choice([500, 1000, 1500, 2000, 2500])
        planned_qty = int(base_qty * monthly_weights[month])
        
        # 실적 수량 (계획 대비 ±5%)
        actual_qty = int(planned_qty * random.uniform(0.95, 1.05))
        
        # 수율 (95% ~ 99%)
        yield_rate = random.uniform(0.95, 0.99)
        
        # 양품/불량 수량
        good_qty = int(actual_qty * yield_rate)
        scrap_qty = actual_qty - good_qty
        
        # 완료일 (오더일 + 1~3일)
        finish_date = order_date + timedelta(days=random.randint(1, 3))
        
        orders.append({
            'order_no': f'PO-2024-{order_id:03d}',
            'product_cd': product_cd,
            'order_type': 'NORMAL',
            'planned_qty': planned_qty,
            'actual_qty': actual_qty,
            'good_qty': good_qty,
            'scrap_qty': scrap_qty,
            'order_date': order_date.strftime('%Y-%m-%d'),
            'start_date': order_date.strftime('%Y-%m-%d'),
            'finish_date': finish_date.strftime('%Y-%m-%d'),
            'status': 'CLOSED'
        })
    
    df = pd.DataFrame(orders)
    print(f"✓ 생산오더 생성: {len(df)}개")
    return df

def generate_material_consumption(production_orders_df, bom_df, materials_df):
    """자재 투입 실적 생성"""
    consumptions = []
    consumption_id = 1
    
    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        actual_qty = order['actual_qty']
        scrap_qty = order['scrap_qty']
        
        # 해당 제품의 BOM 조회
        product_bom = bom_df[bom_df['product_cd'] == product_cd]
        
        for _, bom_item in product_bom.iterrows():
            material_cd = bom_item['material_cd']
            planned_qty_per_unit = bom_item['quantity']
            unit = bom_item['unit']
            
            # 계획 소요량
            planned_qty = planned_qty_per_unit * order['planned_qty']
            
            # 실제 투입량 (불량률 반영 + 약간의 오차)
            # 불량이 발생하면 재투입 필요
            actual_multiplier = (actual_qty + scrap_qty * 0.5) / order['planned_qty']
            actual_qty_consumed = planned_qty_per_unit * order['planned_qty'] * actual_multiplier
            
            # 추가 변동 (±3%)
            actual_qty_consumed *= random.uniform(0.97, 1.03)
            
            consumptions.append({
                'consumption_id': consumption_id,
                'order_no': order_no,
                'material_cd': material_cd,
                'planned_qty': round(planned_qty, 4),
                'actual_qty': round(actual_qty_consumed, 4),
                'unit': unit,
                'consumption_date': order['finish_date']
            })
            consumption_id += 1
    
    df = pd.DataFrame(consumptions)
    print(f"✓ 자재 투입 실적 생성: {len(df)}개")
    return df

def generate_operation_actual(production_orders_df, routing_df):
    """작업 실적 생성"""
    actuals = []
    actual_id = 1
    
    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        actual_qty = order['actual_qty']
        order_date = order['order_date']
        
        # 해당 제품의 라우팅 조회
        product_routing = routing_df[routing_df['product_cd'] == product_cd].sort_values('operation_seq')
        
        current_date = datetime.strptime(order_date, '%Y-%m-%d')
        
        for _, routing_item in product_routing.iterrows():
            workcenter_cd = routing_item['workcenter_cd']
            operation_seq = routing_item['operation_seq']
            standard_time_sec = routing_item['standard_time_sec']
            
            # 실제 작업시간 (표준시간 대비 ±10%)
            efficiency_factor = random.uniform(0.90, 1.10)
            actual_time_per_unit = standard_time_sec * efficiency_factor
            total_time_min = (actual_time_per_unit * actual_qty) / 60.0
            
            actuals.append({
                'actual_id': actual_id,
                'order_no': order_no,
                'workcenter_cd': workcenter_cd,
                'operation_seq': operation_seq,
                'actual_time_min': round(total_time_min, 2),
                'actual_qty': actual_qty,
                'work_date': current_date.strftime('%Y-%m-%d'),
                'worker_count': 1
            })
            actual_id += 1
            
            # 다음 공정은 다음 날 (간소화)
            current_date += timedelta(hours=6)
    
    df = pd.DataFrame(actuals)
    print(f"✓ 작업 실적 생성: {len(df)}개")
    return df

def calculate_cost_accumulation(production_orders_df, material_consumption_df, materials_df, 
                                operation_actual_df, work_centers_df, bom_df, routing_df):
    """원가 집계 계산"""
    costs = []
    cost_id = 1
    
    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        planned_qty = order['planned_qty']
        
        # === 재료비 계산 ===
        # 계획 재료비
        product_bom = bom_df[bom_df['product_cd'] == product_cd]
        planned_material_cost = 0
        for _, bom_item in product_bom.iterrows():
            material_cd = bom_item['material_cd']
            material_price = materials_df[materials_df['material_cd'] == material_cd]['standard_price'].values[0]
            planned_material_cost += bom_item['quantity'] * material_price * planned_qty
        
        # 실적 재료비
        order_consumption = material_consumption_df[material_consumption_df['order_no'] == order_no]
        actual_material_cost = 0
        for _, cons in order_consumption.iterrows():
            material_cd = cons['material_cd']
            material_price = materials_df[materials_df['material_cd'] == material_cd]['standard_price'].values[0]
            # 가격 변동 시뮬레이션 (±5%)
            actual_price = material_price * random.uniform(0.95, 1.05)
            actual_material_cost += cons['actual_qty'] * actual_price
        
        costs.append({
            'cost_id': cost_id,
            'order_no': order_no,
            'cost_element': 'MATERIAL',
            'cost_type': None,
            'planned_cost': round(planned_material_cost, 2),
            'actual_cost': round(actual_material_cost, 2),
            'variance': round(actual_material_cost - planned_material_cost, 2),
            'calculation_date': order['finish_date']
        })
        cost_id += 1
        
        # === 노무비 계산 ===
        # 계획 노무비
        product_routing = routing_df[routing_df['product_cd'] == product_cd]
        planned_labor_cost = 0
        for _, routing_item in product_routing.iterrows():
            wc_cd = routing_item['workcenter_cd']
            labor_rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['labor_rate_per_hour'].values[0]
            std_time_hour = routing_item['standard_time_sec'] / 3600.0
            planned_labor_cost += std_time_hour * labor_rate * planned_qty
        
        # 실적 노무비
        order_actual = operation_actual_df[operation_actual_df['order_no'] == order_no]
        actual_labor_cost = 0
        for _, oper in order_actual.iterrows():
            wc_cd = oper['workcenter_cd']
            labor_rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['labor_rate_per_hour'].values[0]
            actual_time_hour = oper['actual_time_min'] / 60.0
            actual_labor_cost += actual_time_hour * labor_rate
        
        costs.append({
            'cost_id': cost_id,
            'order_no': order_no,
            'cost_element': 'LABOR',
            'cost_type': None,
            'planned_cost': round(planned_labor_cost, 2),
            'actual_cost': round(actual_labor_cost, 2),
            'variance': round(actual_labor_cost - planned_labor_cost, 2),
            'calculation_date': order['finish_date']
        })
        cost_id += 1
        
        # === 경비 계산 ===
        # 계획 경비
        planned_overhead_cost = 0
        for _, routing_item in product_routing.iterrows():
            wc_cd = routing_item['workcenter_cd']
            overhead_rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['overhead_rate_per_hour'].values[0]
            std_time_hour = routing_item['standard_time_sec'] / 3600.0
            planned_overhead_cost += std_time_hour * overhead_rate * planned_qty
        
        # 실적 경비
        actual_overhead_cost = 0
        for _, oper in order_actual.iterrows():
            wc_cd = oper['workcenter_cd']
            overhead_rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['overhead_rate_per_hour'].values[0]
            actual_time_hour = oper['actual_time_min'] / 60.0
            actual_overhead_cost += actual_time_hour * overhead_rate
        
        costs.append({
            'cost_id': cost_id,
            'order_no': order_no,
            'cost_element': 'OVERHEAD',
            'cost_type': None,
            'planned_cost': round(planned_overhead_cost, 2),
            'actual_cost': round(actual_overhead_cost, 2),
            'variance': round(actual_overhead_cost - planned_overhead_cost, 2),
            'calculation_date': order['finish_date']
        })
        cost_id += 1
    
    df = pd.DataFrame(costs)
    print(f"✓ 원가 집계 생성: {len(df)}개")
    return df

def generate_variance_analysis(cost_accumulation_df, production_orders_df):
    """원가차이 분석 생성"""
    variances = []
    variance_id = 1
    
    # 원인 코드 목록
    cause_codes = {
        'MATERIAL': ['GOLD_PRICE_UP', 'SUPPLIER_ISSUE', 'OVERUSE'],
        'LABOR': ['NEW_WORKER', 'EQUIPMENT_OLD'],
        'OVERHEAD': ['LOW_VOLUME', 'EQUIPMENT_OLD']
    }
    
    for idx, cost in cost_accumulation_df.iterrows():
        if abs(cost['variance']) > 100:  # 차이가 100원 이상인 경우만
            order_no = cost['order_no']
            cost_element = cost['cost_element']
            variance_amount = cost['variance']
            
            # 차이 유형 결정
            if cost_element == 'MATERIAL':
                if variance_amount > 0:
                    variance_type = random.choice(['PRICE', 'QUANTITY'])
                else:
                    variance_type = 'QUANTITY'
            elif cost_element == 'LABOR':
                variance_type = random.choice(['RATE', 'EFFICIENCY'])
            else:  # OVERHEAD
                variance_type = random.choice(['VOLUME', 'SPENDING'])
            
            # 원인 코드 할당
            cause_code = random.choice(cause_codes.get(cost_element, ['OTHER']))
            
            # 차이율 계산
            if cost['planned_cost'] != 0:
                variance_percent = (variance_amount / cost['planned_cost']) * 100
            else:
                variance_percent = 0
            
            # 심각도
            if abs(variance_percent) > 20:
                severity = 'HIGH'
            elif abs(variance_percent) > 10:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            variances.append({
                'variance_id': variance_id,
                'order_no': order_no,
                'cost_element': cost_element,
                'variance_type': variance_type,
                'variance_amount': round(variance_amount, 2),
                'variance_percent': round(variance_percent, 4),
                'cause_code': cause_code,
                'cause_description': f'{variance_type} 차이 발생',
                'analysis_date': cost['calculation_date']
            })
            variance_id += 1
    
    df = pd.DataFrame(variances)
    print(f"✓ 원가차이 분석 생성: {len(df)}개")
    return df

def generate_cause_code():
    """원인 코드 마스터 생성"""
    causes = [
        ('GOLD_PRICE_UP', 'MATERIAL', '금 시세 상승', '구매팀'),
        ('SUPPLIER_ISSUE', 'MATERIAL', '공급업체 품질 이슈', '구매팀'),
        ('OVERUSE', 'MATERIAL', '자재 과다 사용', '생산팀'),
        ('NEW_WORKER', 'LABOR', '신규 작업자 투입', '생산팀'),
        ('EQUIPMENT_OLD', 'OVERHEAD', '장비 노후화', '설비팀'),
        ('LOW_VOLUME', 'OVERHEAD', '조업도 저하', '생산관리팀'),
        ('YIELD_LOSS', 'YIELD', '수율 저하', '품질팀')
    ]
    
    cause_list = []
    for code, category, desc, dept in causes:
        cause_list.append({
            'cause_code': code,
            'cause_category': category,
            'cause_description': desc,
            'responsible_dept': dept
        })
    
    df = pd.DataFrame(cause_list)
    print(f"✓ 원인 코드 생성: {len(df)}개")
    return df

# ============================================================
# 3. 메인 실행
# ============================================================

def main():
    print("=" * 60)
    print("반도체 패키징 원가 데이터 생성")
    print("=" * 60)
    
    # 마스터 데이터 생성
    print("\n[1단계] 마스터 데이터 생성")
    products_df = generate_products()
    materials_df = generate_materials()
    bom_df = generate_bom(products_df, materials_df)
    work_centers_df = generate_work_centers()
    routing_df = generate_routing(products_df, work_centers_df)
    cause_code_df = generate_cause_code()
    
    # 트랜잭션 데이터 생성
    print("\n[2단계] 트랜잭션 데이터 생성")
    production_orders_df = generate_production_orders(products_df)
    material_consumption_df = generate_material_consumption(production_orders_df, bom_df, materials_df)
    operation_actual_df = generate_operation_actual(production_orders_df, routing_df)
    
    # 원가 데이터 생성
    print("\n[3단계] 원가 데이터 생성")
    cost_accumulation_df = calculate_cost_accumulation(
        production_orders_df, material_consumption_df, materials_df,
        operation_actual_df, work_centers_df, bom_df, routing_df
    )
    variance_analysis_df = generate_variance_analysis(cost_accumulation_df, production_orders_df)
    
    # RDB 테이블 형식으로 저장
    print("\n[4단계] RDB 테이블 CSV 저장")
    products_df.to_csv(f'{RDB_DIR}/product_master.csv', index=False, encoding='utf-8-sig')
    materials_df.to_csv(f'{RDB_DIR}/material_master.csv', index=False, encoding='utf-8-sig')
    bom_df.to_csv(f'{RDB_DIR}/bom.csv', index=False, encoding='utf-8-sig')
    work_centers_df.to_csv(f'{RDB_DIR}/work_center.csv', index=False, encoding='utf-8-sig')
    routing_df.to_csv(f'{RDB_DIR}/routing.csv', index=False, encoding='utf-8-sig')
    production_orders_df.to_csv(f'{RDB_DIR}/production_order.csv', index=False, encoding='utf-8-sig')
    material_consumption_df.to_csv(f'{RDB_DIR}/material_consumption.csv', index=False, encoding='utf-8-sig')
    operation_actual_df.to_csv(f'{RDB_DIR}/operation_actual.csv', index=False, encoding='utf-8-sig')
    cost_accumulation_df.to_csv(f'{RDB_DIR}/cost_accumulation.csv', index=False, encoding='utf-8-sig')
    variance_analysis_df.to_csv(f'{RDB_DIR}/variance_analysis.csv', index=False, encoding='utf-8-sig')
    cause_code_df.to_csv(f'{RDB_DIR}/cause_code.csv', index=False, encoding='utf-8-sig')
    
    print(f"✓ RDB 테이블 저장 완료: {RDB_DIR}/")
    
    # Neo4j 임포트용 데이터 저장 (노드별)
    print("\n[5단계] Neo4j 임포트 CSV 저장")
    
    # Product 노드
    products_neo = products_df.copy()
    products_neo.rename(columns={'product_cd': 'id', 'product_name': 'name', 
                                  'product_type': 'type', 'package_pins': 'pins'}, inplace=True)
    products_neo['active'] = products_neo['active_flag'] == 'Y'
    products_neo = products_neo[['id', 'name', 'type', 'pins', 'standard_cost', 'active']]
    products_neo.to_csv(f'{NEO4J_DIR}/products.csv', index=False)
    
    # Material 노드
    materials_neo = materials_df.copy()
    materials_neo.rename(columns={'material_cd': 'id', 'material_name': 'name',
                                   'material_type': 'type'}, inplace=True)
    materials_neo['active'] = materials_neo['active_flag'] == 'Y'
    materials_neo = materials_neo[['id', 'name', 'type', 'unit', 'standard_price', 'supplier_cd', 'active']]
    materials_neo.to_csv(f'{NEO4J_DIR}/materials.csv', index=False)
    
    # WorkCenter 노드
    work_centers_neo = work_centers_df.copy()
    work_centers_neo.rename(columns={'workcenter_cd': 'id', 'workcenter_name': 'name'}, inplace=True)
    work_centers_neo['active'] = work_centers_neo['active_flag'] == 'Y'
    work_centers_neo = work_centers_neo[['id', 'name', 'process_type', 'labor_rate_per_hour', 
                                          'overhead_rate_per_hour', 'capacity_per_hour', 'active']]
    work_centers_neo.to_csv(f'{NEO4J_DIR}/work_centers.csv', index=False)
    
    # ProductionOrder 노드
    po_neo = production_orders_df.copy()
    po_neo.rename(columns={'order_no': 'id'}, inplace=True)
    po_neo['yield_rate'] = (po_neo['good_qty'] / po_neo['planned_qty'] * 100).round(2)
    po_neo.to_csv(f'{NEO4J_DIR}/production_orders.csv', index=False)
    
    # Variance 노드
    var_neo = variance_analysis_df.copy()
    var_neo['id'] = var_neo['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    var_neo['severity'] = var_neo['variance_percent'].abs().apply(
        lambda x: 'HIGH' if x > 20 else ('MEDIUM' if x > 10 else 'LOW')
    )
    var_neo = var_neo[['id', 'order_no', 'cost_element', 'variance_type', 'variance_amount', 
                       'variance_percent', 'severity', 'cause_code', 'analysis_date']]
    var_neo.to_csv(f'{NEO4J_DIR}/variances.csv', index=False)
    
    # Cause 노드
    cause_neo = cause_code_df.copy()
    cause_neo.rename(columns={'cause_code': 'code', 'cause_category': 'category',
                              'cause_description': 'description'}, inplace=True)
    cause_neo.to_csv(f'{NEO4J_DIR}/causes.csv', index=False)
    
    # 관계 데이터
    # USES_MATERIAL 관계
    uses_material = bom_df[['product_cd', 'material_cd', 'quantity', 'unit']].copy()
    uses_material.rename(columns={'product_cd': 'from', 'material_cd': 'to'}, inplace=True)
    uses_material.to_csv(f'{NEO4J_DIR}/rel_uses_material.csv', index=False)
    
    # PRODUCES 관계
    produces = production_orders_df[['order_no', 'product_cd']].copy()
    produces.rename(columns={'order_no': 'from', 'product_cd': 'to'}, inplace=True)
    produces.to_csv(f'{NEO4J_DIR}/rel_produces.csv', index=False)
    
    # HAS_VARIANCE 관계
    has_variance = variance_analysis_df[['order_no', 'variance_id']].copy()
    has_variance['variance_id'] = has_variance['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    has_variance.rename(columns={'order_no': 'from', 'variance_id': 'to'}, inplace=True)
    has_variance.to_csv(f'{NEO4J_DIR}/rel_has_variance.csv', index=False)
    
    # CAUSED_BY 관계
    caused_by = variance_analysis_df[['variance_id', 'cause_code']].dropna().copy()
    caused_by['variance_id'] = caused_by['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    caused_by.rename(columns={'variance_id': 'from', 'cause_code': 'to'}, inplace=True)
    caused_by.to_csv(f'{NEO4J_DIR}/rel_caused_by.csv', index=False)
    
    # CONSUMES 관계
    consumes = material_consumption_df[['order_no', 'material_cd', 'planned_qty', 'actual_qty', 'unit']].copy()
    consumes.rename(columns={'order_no': 'from', 'material_cd': 'to'}, inplace=True)
    consumes.to_csv(f'{NEO4J_DIR}/rel_consumes.csv', index=False)
    
    # WORKS_AT 관계
    works_at = operation_actual_df[['order_no', 'workcenter_cd', 'actual_time_min', 'actual_qty']].copy()
    works_at.rename(columns={'order_no': 'from', 'workcenter_cd': 'to'}, inplace=True)
    works_at.to_csv(f'{NEO4J_DIR}/rel_works_at.csv', index=False)
    
    print(f"✓ Neo4j 임포트 파일 저장 완료: {NEO4J_DIR}/")
    
    # 요약 통계
    print("\n" + "=" * 60)
    print("데이터 생성 완료 - 요약")
    print("=" * 60)
    print(f"제품: {len(products_df)}개")
    print(f"자재: {len(materials_df)}개")
    print(f"BOM: {len(bom_df)}개")
    print(f"작업장: {len(work_centers_df)}개")
    print(f"라우팅: {len(routing_df)}개")
    print(f"생산오더: {len(production_orders_df)}개")
    print(f"자재 투입: {len(material_consumption_df)}개")
    print(f"작업 실적: {len(operation_actual_df)}개")
    print(f"원가 집계: {len(cost_accumulation_df)}개")
    print(f"원가차이: {len(variance_analysis_df)}개")
    print("\n총 차이 금액:", variance_analysis_df['variance_amount'].sum().round(2), "원")
    print("평균 차이율:", variance_analysis_df['variance_percent'].abs().mean().round(2), "%")
    print("=" * 60)

if __name__ == "__main__":
    main()
