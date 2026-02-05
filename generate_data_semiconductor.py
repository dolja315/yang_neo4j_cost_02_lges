"""
반도체 패키징 원가 데이터 생성기

반도체 후공정(Packaging) 원가차이 분석을 위한 데이터 생성:
- 제품: BGA, QFP, SOP 등 패키지 타입
- 원부재료: Wafer, Lead Frame, Gold Wire, EMC, PCB Substrate
- 공정: Die Attach, Wire Bonding, Molding, Marking, Singulation
- 시나리오: 금 가격 급등, 에폭시 과다 사용, 다이 불량률 증가 등
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import random
import os

# 시드 설정
random.seed(42)
np.random.seed(42)
fake = Faker('ko_KR')

# 출력 디렉토리
RDB_DIR = 'data/rdb_tables'
NEO4J_DIR = 'data/neo4j_import'

os.makedirs(RDB_DIR, exist_ok=True)
os.makedirs(NEO4J_DIR, exist_ok=True)

# ============================================================
# 1. 마스터 데이터 생성
# ============================================================

def generate_products():
    """반도체 제품 마스터 생성"""
    products = [
        ('PKG-BGA-256', '256-ball BGA Package', 'BGA', 'Gold', 256.0, 15000),
        ('PKG-BGA-144', '144-ball BGA Package', 'BGA', 'Gold', 144.0, 12000),
        ('PKG-QFP-100', '100-pin QFP Package', 'QFP', 'Copper', 100.0, 5000),
        ('PKG-QFP-64', '64-pin QFP Package', 'QFP', 'Copper', 64.0, 3500),
        ('PKG-SOP-28', '28-pin SOP Package', 'SOP', 'Copper', 28.0, 1200),
        ('PKG-SOP-16', '16-pin SOP Package', 'SOP', 'Copper', 16.0, 800),
    ]

    product_list = []
    for p_cd, p_name, p_type, wire_type, pin_cnt, std_cost in products:
        product_list.append({
            'product_cd': p_cd,
            'product_name': p_name,
            'product_type': p_type,
            'battery_chemistry': wire_type, # 스키마 호환 (Wire 재질)
            'capacity_kwh': pin_cnt,        # 스키마 호환 (Pin 수)
            'standard_cost': std_cost,
            'active_flag': 'Y',
            'created_date': '2024-01-01'
        })

    df = pd.DataFrame(product_list)
    print(f"[OK] 반도체 제품 생성: {len(df)}개")
    return df

def generate_materials():
    """반도체 자재 마스터 생성"""
    materials = [
        ('MAT-WAFER-01', 'Silicon Wafer 12inch', 'WAFER', 'EA', 500000, 'SUP-WAF-KR', '한국'),
        ('MAT-LF-QFP', 'Lead Frame for QFP', 'LEADFRAME', 'PNL', 5000, 'SUP-LF-JP', '일본'),
        ('MAT-SUB-BGA', 'PCB Substrate for BGA', 'SUBSTRATE', 'PNL', 15000, 'SUP-SUB-KR', '한국'),
        ('MAT-WIRE-AU', 'Gold Wire (99.99%)', 'WIRE', 'M', 200, 'SUP-WIR-DE', '독일'),
        ('MAT-WIRE-CU', 'Copper Wire', 'WIRE', 'M', 20, 'SUP-WIR-CN', '중국'),
        ('MAT-EMC-01', 'Epoxy Molding Compound', 'EMC', 'KG', 45000, 'SUP-EMC-JP', '일본'),
    ]

    mat_list = []
    for m_cd, m_name, m_type, unit, price, sup, origin in materials:
        mat_list.append({
            'material_cd': m_cd,
            'material_name': m_name,
            'material_type': m_type,
            'unit': unit,
            'standard_price': price,
            'price_unit': 'KRW',
            'supplier_cd': sup,
            'origin_country': origin,
            'active_flag': 'Y'
        })

    df = pd.DataFrame(mat_list)
    print(f"[OK] 반도체 자재 생성: {len(df)}개")
    return df

def generate_bom(products_df, materials_df):
    """BOM 생성"""
    boms = []
    bom_id = 1

    for _, prod in products_df.iterrows():
        p_cd = prod['product_cd']
        p_type = prod['product_type']
        wire_type = prod['battery_chemistry'] # Wire 재질
        pin_cnt = prod['capacity_kwh']        # Pin 수

        # 1. Wafer (공통)
        boms.append({
            'bom_id': bom_id,
            'product_cd': p_cd,
            'material_cd': 'MAT-WAFER-01',
            'quantity': 0.002,
            'unit': 'EA',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1

        # 2. Substrate or LeadFrame
        if p_type == 'BGA':
            mat_cd = 'MAT-SUB-BGA'
        else:
            mat_cd = 'MAT-LF-QFP'

        boms.append({
            'bom_id': bom_id,
            'product_cd': p_cd,
            'material_cd': mat_cd,
            'quantity': 0.1,
            'unit': 'PNL',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1

        # 3. Wire
        wire_mat = 'MAT-WIRE-AU' if wire_type == 'Gold' else 'MAT-WIRE-CU'
        wire_len = pin_cnt * 0.005 # 핀당 5mm 가정

        boms.append({
            'bom_id': bom_id,
            'product_cd': p_cd,
            'material_cd': wire_mat,
            'quantity': wire_len,
            'unit': 'M',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1

        # 4. EMC (Molding)
        boms.append({
            'bom_id': bom_id,
            'product_cd': p_cd,
            'material_cd': 'MAT-EMC-01',
            'quantity': 0.005,
            'unit': 'KG',
            'valid_from': '2024-01-01',
            'valid_to': None,
            'bom_level': 1
        })
        bom_id += 1

    return pd.DataFrame(boms)

def generate_work_centers():
    """반도체 공정 작업장"""
    wcs = [
        ('WC-DA-01', 'Die Attach Line', 'DIE_ATTACH', 35000, 70000, 500, 'CleanRoom-A'),
        ('WC-WB-01', 'Wire Bonding Line', 'WIRE_BOND', 40000, 80000, 400, 'CleanRoom-A'),
        ('WC-MD-01', 'Molding Line', 'MOLDING', 38000, 75000, 300, 'CleanRoom-B'),
        ('WC-MK-01', 'Marking & Singulation', 'MARKING', 30000, 60000, 600, 'CleanRoom-B'),
    ]
    wc_list = []
    for w_cd, name, p_type, labor, overhead, capa, loc in wcs:
        wc_list.append({
            'workcenter_cd': w_cd,
            'workcenter_name': name,
            'process_type': p_type,
            'labor_rate_per_hour': labor,
            'overhead_rate_per_hour': overhead,
            'capacity_per_hour': capa,
            'location': loc,
            'active_flag': 'Y'
        })
    return pd.DataFrame(wc_list)

def generate_routing(products_df, work_centers_df):
    """라우팅 생성"""
    routings = []
    rid = 1
    # 공정 순서: Die Attach -> Wire Bond -> Molding -> Marking
    procs = [('DIE_ATTACH', 10, 15.0), ('WIRE_BOND', 20, 30.0), ('MOLDING', 30, 20.0), ('MARKING', 40, 5.0)]

    for _, prod in products_df.iterrows():
        for p_type, seq, base_time in procs:
            # Wire Bonding은 핀 수에 따라 시간 증가
            if p_type == 'WIRE_BOND':
                std_time = base_time + (prod['capacity_kwh'] * 0.1)
            else:
                std_time = base_time

            wc_cd = work_centers_df[work_centers_df['process_type'] == p_type]['workcenter_cd'].values[0]
            routings.append({
                'routing_id': rid,
                'product_cd': prod['product_cd'],
                'operation_seq': seq,
                'workcenter_cd': wc_cd,
                'standard_time_sec': std_time,
                'setup_time_min': 30,
                'valid_from': '2024-01-01',
                'valid_to': None
            })
            rid += 1
    return pd.DataFrame(routings)

def generate_cause_code():
    """반도체 전용 원인 코드"""
    causes = [
        ('WAFER_CRACK', 'MATERIAL', 'DIFF', '웨이퍼 크랙', '품질팀', '입고 웨이퍼 미세 크랙'),
        ('WIRE_BREAK', 'MATERIAL', 'DIFF', '와이어 단선', '생산팀', '본딩 중 금선 끊어짐'),
        ('MOLD_VOID', 'QUALITY', 'DIFF', '몰딩 기포(Void)', '기술팀', 'EMC 충진 불량으로 내부 기포 발생'),
        ('EPOXY_EXP', 'MATERIAL', 'DIFF', '에폭시 유효기간 경과', '자재팀', '보관 기간 초과된 접착제 사용'),
        ('MC_ERROR_WB', 'OVERHEAD', 'DIFF', '본더 설비 오작동', '설비팀', 'Wire Bonder 좌표 인식 오류'),
        ('GOLD_PRICE_HIKE', 'MATERIAL', 'PRICE', '금 가격 급등', '구매팀', '국제 금 시세 상승으로 인한 재료비 증가'),
        ('EPOXY_OVERUSE', 'MATERIAL', 'QTY', '에폭시 과다 사용', '생산팀', '몰딩 공정 수지 주입량 조절 실패'),
        ('DIE_YIELD_LOW', 'MATERIAL', 'YIELD', '다이 수율 저하', '품질팀', '웨이퍼 공정 불량으로 양품 다이 감소'),
        ('WORKER_INEFFICIENCY', 'LABOR', 'EFFICIENCY', '작업 효율 저하', '생산팀', '신규 작업자 투입으로 숙련도 부족'),
        ('POWER_COST_HIKE', 'OVERHEAD', 'PRICE', '전력비 급등', '설비팀', '전기요금 누진제 적용으로 경비 증가'),
        ('VOLUME_LOSS', 'OVERHEAD', 'VOLUME', '조업도 손실', '기획팀', '수주 감소로 인한 설비 가동률 저하'),
    ]
    clist = []
    for c, cat, vtype, desc, dept, det in causes:
        clist.append({
            'cause_code': c,
            'cause_category': cat,
            'variance_type': vtype,
            'cause_description': desc,
            'responsible_dept': dept,
            'detail_description': det
        })
    return pd.DataFrame(clist)

# ============================================================
# 2. 트랜잭션 데이터 생성
# ============================================================

def generate_production_orders(products_df):
    """생산오더 생성"""
    orders = []
    start_date = datetime(2024, 1, 1)
    order_id = 1

    # 3개월치 데이터 (Jan - Mar)
    for idx, product in products_df.iterrows():
        product_cd = product['product_cd']

        # 제품당 월 3-4개 오더
        for i in range(10):
            # 날짜 생성 (1월~3월 분산)
            days_offset = random.randint(0, 85)
            order_date = start_date + timedelta(days=days_offset)
            month = order_date.month

            # 계획 수량 (BGA는 적게, QFP는 많게)
            if product['product_type'] == 'BGA':
                planned_qty = random.choice([500, 800, 1000])
            else:
                planned_qty = random.choice([1000, 2000, 3000])

            # 2월은 생산량 감소 시나리오
            if month == 2:
                planned_qty = int(planned_qty * 0.7)

            # 실적 수량
            actual_qty = int(planned_qty * random.uniform(0.95, 1.05))

            # 수율
            yield_rate = random.uniform(0.96, 0.995)
            good_qty = int(actual_qty * yield_rate)
            scrap_qty = actual_qty - good_qty

            # 완료일
            finish_date = order_date + timedelta(days=random.randint(2, 5))

            orders.append({
                'order_no': f'PO-SEMI-{order_id:04d}',
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
            order_id += 1

    return pd.DataFrame(orders)

def generate_material_consumption(production_orders_df, bom_df, materials_df):
    """자재 투입 실적 생성"""
    consumptions = []
    consumption_id = 1

    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        planned_qty = order['planned_qty']

        # BOM 조회
        product_bom = bom_df[bom_df['product_cd'] == product_cd]

        for _, bom_item in product_bom.iterrows():
            material_cd = bom_item['material_cd']
            planned_qty_per_unit = bom_item['quantity']
            unit = bom_item['unit']

            # 계획 소요량
            planned_total = planned_qty_per_unit * planned_qty

            # 실제 투입량 계산
            actual_total = planned_total

            # 시나리오: 에폭시 과다 사용 (Molding 공정)
            if material_cd == 'MAT-EMC-01' and random.random() < 0.2:
                actual_total *= 1.2 # 20% 과다 사용

            # 시나리오: 와이어 끊김으로 인한 손실
            if 'WIRE' in material_cd and random.random() < 0.1:
                actual_total *= 1.05

            consumptions.append({
                'consumption_id': consumption_id,
                'order_no': order_no,
                'material_cd': material_cd,
                'actual_material_cd': material_cd,
                'planned_qty': round(planned_total, 4),
                'actual_qty': round(actual_total, 4),
                'unit': unit,
                'is_alternative': 'N',
                'consumption_date': order['finish_date']
            })
            consumption_id += 1

    return pd.DataFrame(consumptions)

def generate_operation_actual(production_orders_df, routing_df, work_centers_df):
    """작업 실적 생성"""
    actuals = []
    actual_id = 1

    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        actual_qty = order['actual_qty']
        order_date_str = order['order_date']
        order_date = datetime.strptime(order_date_str, '%Y-%m-%d')

        product_routing = routing_df[routing_df['product_cd'] == product_cd].sort_values('operation_seq')

        for _, routing_item in product_routing.iterrows():
            workcenter_cd = routing_item['workcenter_cd']
            standard_time_sec = routing_item['standard_time_sec']

            # 시나리오: 2월 설 연휴 이후 신규 작업자 투입으로 효율 저하
            efficiency = 1.0
            if order_date.month == 2 and random.random() < 0.3:
                efficiency = 0.8 # 80% 효율
            else:
                efficiency = random.uniform(0.95, 1.05)

            actual_time_sec = (standard_time_sec * actual_qty) / efficiency
            actual_time_min = actual_time_sec / 60.0
            standard_time_min = (standard_time_sec * actual_qty) / 60.0

            actuals.append({
                'actual_id': actual_id,
                'order_no': order_no,
                'workcenter_cd': workcenter_cd,
                'operation_seq': routing_item['operation_seq'],
                'standard_time_min': round(standard_time_min, 2),
                'actual_time_min': round(actual_time_min, 2),
                'actual_qty': actual_qty,
                'efficiency_rate': round(efficiency * 100, 2),
                'work_date': order_date_str,
                'worker_count': 1
            })
            actual_id += 1

    return pd.DataFrame(actuals)

def calculate_cost_accumulation(production_orders_df, material_consumption_df, materials_df,
                                operation_actual_df, work_centers_df, bom_df, routing_df):
    """원가 집계"""
    costs = []
    cost_id = 1

    for idx, order in production_orders_df.iterrows():
        order_no = order['order_no']
        product_cd = order['product_cd']
        planned_qty = order['planned_qty']

        # 1. Material Cost
        product_bom = bom_df[bom_df['product_cd'] == product_cd]
        planned_mat_cost = 0
        actual_mat_cost = 0

        # Planned
        for _, bom_item in product_bom.iterrows():
            mat_cd = bom_item['material_cd']
            price = materials_df[materials_df['material_cd'] == mat_cd]['standard_price'].values[0]
            planned_mat_cost += bom_item['quantity'] * planned_qty * price

        # Actual
        order_cons = material_consumption_df[material_consumption_df['order_no'] == order_no]
        for _, cons in order_cons.iterrows():
            mat_cd = cons['actual_material_cd']
            price = materials_df[materials_df['material_cd'] == mat_cd]['standard_price'].values[0]

            # 시나리오: 금 가격 급등 (3월)
            order_month = int(order['order_date'].split('-')[1])
            if 'WIRE-AU' in mat_cd and order_month == 3:
                price *= 1.2 # 20% 인상

            actual_mat_cost += cons['actual_qty'] * price

        costs.append({
            'cost_id': cost_id,
            'order_no': order_no,
            'cost_element': 'MATERIAL',
            'cost_type': None,
            'planned_cost': round(planned_mat_cost, 2),
            'actual_cost': round(actual_mat_cost, 2),
            'variance': round(actual_mat_cost - planned_mat_cost, 2),
            'calculation_date': order['finish_date']
        })
        cost_id += 1

        # 2. Labor Cost
        planned_labor_cost = 0
        actual_labor_cost = 0

        # Planned
        product_routing = routing_df[routing_df['product_cd'] == product_cd]
        for _, route in product_routing.iterrows():
            wc_cd = route['workcenter_cd']
            rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['labor_rate_per_hour'].values[0]
            time_hour = (route['standard_time_sec'] * planned_qty) / 3600.0
            planned_labor_cost += time_hour * rate

        # Actual
        order_ops = operation_actual_df[operation_actual_df['order_no'] == order_no]
        for _, op in order_ops.iterrows():
            wc_cd = op['workcenter_cd']
            rate = work_centers_df[work_centers_df['workcenter_cd'] == wc_cd]['labor_rate_per_hour'].values[0]
            time_hour = op['actual_time_min'] / 60.0
            actual_labor_cost += time_hour * rate

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

        # 3. Overhead Cost (Simplified)
        planned_overhead = planned_labor_cost * 1.5 # 150% of labor
        actual_overhead = actual_labor_cost * 1.5

        # 시나리오: 1월 전력비 급등
        if int(order['order_date'].split('-')[1]) == 1:
            actual_overhead *= 1.1

        costs.append({
            'cost_id': cost_id,
            'order_no': order_no,
            'cost_element': 'OVERHEAD',
            'cost_type': None,
            'planned_cost': round(planned_overhead, 2),
            'actual_cost': round(actual_overhead, 2),
            'variance': round(actual_overhead - planned_overhead, 2),
            'calculation_date': order['finish_date']
        })
        cost_id += 1

    return pd.DataFrame(costs)

def generate_variance_analysis(cost_accumulation_df, material_consumption_df, operation_actual_df):
    """원가차이 분석 및 원인 할당, 직접 연결 정보 추가"""
    variances = []
    var_id = 1

    for _, cost in cost_accumulation_df.iterrows():
        order_no = cost['order_no']
        element = cost['cost_element']
        amount = cost['variance']
        planned = cost['planned_cost']

        if planned == 0: continue

        percent = (amount / planned) * 100
        severity = 'LOW'
        if abs(amount) > 1000000: severity = 'MEDIUM'
        if abs(amount) > 5000000: severity = 'HIGH'

        cause_code = None
        material_cd = None
        workcenter_cd = None
        defect_id = None
        failure_id = None

        # 원인 할당 및 관계 설정 로직
        if element == 'MATERIAL':
            variance_name = '재료비차이'
            variance_type = 'DIFF'

            # 소비 실적 확인
            cons = material_consumption_df[material_consumption_df['order_no'] == order_no]

            # 자재 식별 (가장 금액이 큰 자재 또는 특정 시나리오 자재)
            if not cons.empty:
                # 간단히 첫번째 또는 특정 조건 자재 선택
                # 시나리오: 에폭시 또는 골드 와이어
                epoxy_cons = cons[cons['actual_material_cd'] == 'MAT-EMC-01']
                wire_cons = cons[cons['actual_material_cd'].str.contains('WIRE')]

                if not epoxy_cons.empty and amount > 0: # 과다 사용 등
                    material_cd = 'MAT-EMC-01'
                elif not wire_cons.empty:
                    material_cd = wire_cons.iloc[0]['actual_material_cd']
                else:
                    material_cd = cons.iloc[0]['actual_material_cd']

            # 골드 와이어 사용 제품인지 확인
            has_gold = cons['actual_material_cd'].str.contains('WIRE-AU').any()
            # 에폭시 사용량 확인
            epoxy_cons = cons[cons['actual_material_cd'] == 'MAT-EMC-01']

            if has_gold and cost['calculation_date'].startswith('2024-03'):
                cause_code = 'GOLD_PRICE_HIKE'
            elif not epoxy_cons.empty:
                 plan = epoxy_cons['planned_qty'].sum()
                 act = epoxy_cons['actual_qty'].sum()
                 if act > plan * 1.1:
                     cause_code = 'EPOXY_OVERUSE'

            if not cause_code:
                if amount > 0:
                    cause_code = 'DIE_YIELD_LOW'
                    # 품질 불량 연결 (가상의 불량 ID 할당)
                    defect_id = 'QD-001'
                else:
                    cause_code = 'WAFER_CRACK'
                    defect_id = 'QD-001'

        elif element == 'LABOR':
            variance_name = '노무비차이'
            variance_type = 'DIFF'
            ops = operation_actual_df[operation_actual_df['order_no'] == order_no]

            if not ops.empty:
                workcenter_cd = ops.iloc[0]['workcenter_cd']

            avg_eff = ops['efficiency_rate'].mean()

            if avg_eff < 90:
                cause_code = 'WORKER_INEFFICIENCY'
            else:
                cause_code = 'WIRE_BREAK' # 재작업

        else: # OVERHEAD
            variance_name = '경비차이'
            variance_type = 'DIFF'

            # WorkCenter 연결 (LABOR와 공유하거나 임의 지정)
            ops = operation_actual_df[operation_actual_df['order_no'] == order_no]
            if not ops.empty:
                workcenter_cd = ops.iloc[0]['workcenter_cd']

            if cost['calculation_date'].startswith('2024-01'):
                cause_code = 'POWER_COST_HIKE'
            else:
                cause_code = 'MC_ERROR_WB'
                failure_id = 'EF-001' # 설비 고장 연결

        variances.append({
            'variance_id': var_id,
            'order_no': order_no,
            'variance_name': variance_name,
            'cost_element': element,
            'variance_type': variance_type,
            'variance_amount': amount,
            'variance_percent': round(percent, 2),
            'cause_code': cause_code,
            'severity': severity,
            'analysis_date': cost['calculation_date'],
            'material_cd': material_cd,
            'workcenter_cd': workcenter_cd,
            'defect_id': defect_id,
            'failure_id': failure_id
        })
        var_id += 1

    return pd.DataFrame(variances)

def generate_quality_defects():
    """품질 불량 (플레이스홀더)"""
    return pd.DataFrame([{
        'defect_id': 'QD-001', 'defect_type': 'CRACK', 'cause_code': 'WAFER_CRACK',
        'material_name': 'Wafer', 'defect_description': 'Edge Crack', 'severity': 'HIGH',
        'detection_date': '2024-01-15', 'supplier_cd': 'SUP-WAF-KR', 'detail': 'N/A'
    }])

def generate_equipment_failures():
    """설비 고장 (플레이스홀더)"""
    return pd.DataFrame([{
        'failure_id': 'EF-001', 'workcenter_cd': 'WC-WB-01', 'cause_code': 'MC_ERROR_WB',
        'failure_type': 'STOP', 'failure_start': '2024-02-01', 'failure_end': '2024-02-01',
        'downtime_hours': 2.0, 'severity': 'MEDIUM', 'description': 'Sensor Error'
    }])

def generate_material_market_prices():
    """자재 시황 (플레이스홀더)"""
    return pd.DataFrame([{
        'market_id': 'MP-001', 'material_cd': 'MAT-WIRE-AU', 'material_name': 'Gold Wire',
        'price_date': '2024-03-01', 'market_price': 240, 'price_trend': 'INCREASE',
        'market_condition': 'BAD', 'note': 'Gold Price Hike'
    }])

# ============================================================
# 메인 실행
# ============================================================

def main():
    print("="*60)
    print("반도체 패키징 데이터 생성 시작 (Full Version)")
    print("="*60)

    # 1. 마스터 데이터
    products_df = generate_products()
    materials_df = generate_materials()
    bom_df = generate_bom(products_df, materials_df)
    wcs_df = generate_work_centers()
    routing_df = generate_routing(products_df, wcs_df)
    cause_df = generate_cause_code()

    # 2. 트랜잭션 데이터
    print("\n[Transaction] 생성 중...")
    orders_df = generate_production_orders(products_df)
    cons_df = generate_material_consumption(orders_df, bom_df, materials_df)
    ops_df = generate_operation_actual(orders_df, routing_df, wcs_df)
    costs_df = calculate_cost_accumulation(orders_df, cons_df, materials_df, ops_df, wcs_df, bom_df, routing_df)
    vars_df = generate_variance_analysis(costs_df, cons_df, ops_df)

    # 추가 데이터 (플레이스홀더)
    qd_df = generate_quality_defects()
    ef_df = generate_equipment_failures()
    mp_df = generate_material_market_prices()

    # 3. RDB 포맷 저장
    print(f"\n[RDB] CSV 저장 중... ({RDB_DIR})")
    products_df.to_csv(f'{RDB_DIR}/product_master.csv', index=False, encoding='utf-8-sig')
    materials_df.to_csv(f'{RDB_DIR}/material_master.csv', index=False, encoding='utf-8-sig')
    bom_df.to_csv(f'{RDB_DIR}/bom.csv', index=False, encoding='utf-8-sig')
    wcs_df.to_csv(f'{RDB_DIR}/work_center.csv', index=False, encoding='utf-8-sig')
    routing_df.to_csv(f'{RDB_DIR}/routing.csv', index=False, encoding='utf-8-sig')
    orders_df.to_csv(f'{RDB_DIR}/production_order.csv', index=False, encoding='utf-8-sig')
    cause_df.to_csv(f'{RDB_DIR}/cause_code.csv', index=False, encoding='utf-8-sig')
    costs_df.to_csv(f'{RDB_DIR}/cost_accumulation.csv', index=False, encoding='utf-8-sig')
    vars_df.to_csv(f'{RDB_DIR}/variance_analysis.csv', index=False, encoding='utf-8-sig')

    # 4. Neo4j Import 포맷 변환 및 저장
    print(f"\n[Neo4j] Import CSV 저장 중... ({NEO4J_DIR})")

    # Product
    products_neo = products_df.copy()
    products_neo.rename(columns={
        'product_cd': 'id', 'product_name': 'name', 'product_type': 'type',
        'battery_chemistry': 'chemistry', 'capacity_kwh': 'capacity'
    }, inplace=True)
    products_neo['active'] = products_neo['active_flag'] == 'Y'
    products_neo[['id', 'name', 'type', 'chemistry', 'capacity', 'standard_cost', 'active']].to_csv(f'{NEO4J_DIR}/products.csv', index=False)

    # Material
    materials_neo = materials_df.copy()
    materials_neo.rename(columns={'material_cd': 'id', 'material_name': 'name', 'material_type': 'type', 'origin_country': 'origin'}, inplace=True)
    materials_neo['active'] = materials_neo['active_flag'] == 'Y'
    materials_neo[['id', 'name', 'type', 'unit', 'standard_price', 'supplier_cd', 'origin', 'active']].to_csv(f'{NEO4J_DIR}/materials.csv', index=False)

    # WorkCenter
    wc_neo = wcs_df.copy()
    wc_neo.rename(columns={'workcenter_cd': 'id', 'workcenter_name': 'name'}, inplace=True)
    wc_neo['active'] = wc_neo['active_flag'] == 'Y'
    wc_neo[['id', 'name', 'process_type', 'labor_rate_per_hour', 'overhead_rate_per_hour', 'capacity_per_hour', 'location', 'active']].to_csv(f'{NEO4J_DIR}/work_centers.csv', index=False)

    # ProductionOrder
    po_neo = orders_df.copy()
    po_neo.rename(columns={'order_no': 'id'}, inplace=True)
    po_neo['yield_rate'] = (po_neo['good_qty'] / po_neo['actual_qty'] * 100).round(2)
    po_neo.to_csv(f'{NEO4J_DIR}/production_orders.csv', index=False)

    # Variance
    var_neo = vars_df.copy()
    var_neo['id'] = var_neo['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    var_neo[['id', 'variance_name', 'order_no', 'cost_element', 'variance_type', 'variance_amount',
             'variance_percent', 'severity', 'cause_code', 'analysis_date']].to_csv(f'{NEO4J_DIR}/variances.csv', index=False)

    # Cause
    cause_neo = cause_df.copy()
    cause_neo.rename(columns={'cause_code': 'code', 'cause_category': 'category', 'cause_description': 'description', 'detail_description': 'detail'}, inplace=True)
    cause_neo.to_csv(f'{NEO4J_DIR}/causes.csv', index=False)

    # QualityDefect & EquipmentFailure & Market (Placeholder)
    qd_df.rename(columns={'defect_id': 'id'}, inplace=True)
    qd_df.to_csv(f'{NEO4J_DIR}/quality_defects.csv', index=False)

    ef_df.rename(columns={'failure_id': 'id'}, inplace=True)
    ef_df.to_csv(f'{NEO4J_DIR}/equipment_failures.csv', index=False)

    mp_df.rename(columns={'market_id': 'id'}, inplace=True)
    mp_df.to_csv(f'{NEO4J_DIR}/material_markets.csv', index=False)

    # Relationships

    # USES_MATERIAL (BOM)
    uses_mat = bom_df[['product_cd', 'material_cd', 'quantity', 'unit']].copy()
    uses_mat.rename(columns={'product_cd': 'from', 'material_cd': 'to'}, inplace=True)
    uses_mat.to_csv(f'{NEO4J_DIR}/rel_uses_material.csv', index=False)

    # PRODUCES (Order -> Product)
    produces = orders_df[['order_no', 'product_cd']].copy()
    produces.rename(columns={'order_no': 'from', 'product_cd': 'to'}, inplace=True)
    produces.to_csv(f'{NEO4J_DIR}/rel_produces.csv', index=False)

    # HAS_VARIANCE (Order -> Variance)
    has_var = vars_df[['order_no', 'variance_id']].copy()
    has_var['variance_id'] = has_var['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    has_var.rename(columns={'order_no': 'from', 'variance_id': 'to'}, inplace=True)
    has_var.to_csv(f'{NEO4J_DIR}/rel_has_variance.csv', index=False)

    # CAUSED_BY (Variance -> Cause)
    caused = vars_df[['variance_id', 'cause_code']].dropna().copy()
    caused['variance_id'] = caused['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    caused.rename(columns={'variance_id': 'from', 'cause_code': 'to'}, inplace=True)
    caused.to_csv(f'{NEO4J_DIR}/rel_caused_by.csv', index=False)

    # CONSUMES (Order -> Material)
    consumes = cons_df[['order_no', 'actual_material_cd', 'planned_qty', 'actual_qty', 'unit']].copy()
    consumes['is_alternative'] = 'N'
    consumes.rename(columns={'order_no': 'from', 'actual_material_cd': 'to'}, inplace=True)
    consumes.to_csv(f'{NEO4J_DIR}/rel_consumes.csv', index=False)

    # WORKS_AT (Order -> WorkCenter)
    works = ops_df[['order_no', 'workcenter_cd', 'standard_time_min', 'actual_time_min', 'efficiency_rate', 'worker_count']].copy()
    works.rename(columns={'order_no': 'from', 'workcenter_cd': 'to'}, inplace=True)
    works.to_csv(f'{NEO4J_DIR}/rel_works_at.csv', index=False)

    # === [NEW] "Spider Legs" Relationships for Variance ===

    # RELATED_TO_MATERIAL (Variance -> Material)
    rel_mat = vars_df[['variance_id', 'material_cd']].dropna().copy()
    rel_mat['variance_id'] = rel_mat['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    rel_mat.rename(columns={'variance_id': 'from', 'material_cd': 'to'}, inplace=True)
    rel_mat.to_csv(f'{NEO4J_DIR}/rel_variance_material.csv', index=False)

    # OCCURRED_AT (Variance -> WorkCenter)
    rel_wc = vars_df[['variance_id', 'workcenter_cd']].dropna().copy()
    rel_wc['variance_id'] = rel_wc['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    rel_wc.rename(columns={'variance_id': 'from', 'workcenter_cd': 'to'}, inplace=True)
    rel_wc.to_csv(f'{NEO4J_DIR}/rel_variance_workcenter.csv', index=False)

    # HAS_DEFECT (Variance -> QualityDefect)
    # Note: Using Variance as source instead of Cause for direct analysis, or as supplementary
    rel_defect = vars_df[['variance_id', 'defect_id']].dropna().copy()
    rel_defect['variance_id'] = rel_defect['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    rel_defect.rename(columns={'variance_id': 'from', 'defect_id': 'to'}, inplace=True)
    rel_defect.to_csv(f'{NEO4J_DIR}/rel_variance_defect.csv', index=False)

    # HAS_FAILURE (Variance -> EquipmentFailure)
    rel_fail = vars_df[['variance_id', 'failure_id']].dropna().copy()
    rel_fail['variance_id'] = rel_fail['variance_id'].apply(lambda x: f'VAR-{x:05d}')
    rel_fail.rename(columns={'variance_id': 'from', 'failure_id': 'to'}, inplace=True)
    rel_fail.to_csv(f'{NEO4J_DIR}/rel_variance_failure.csv', index=False)


    # Empty Placeholders for other rels to avoid file not found errors in loader
    pd.DataFrame(columns=['from', 'to']).to_csv(f'{NEO4J_DIR}/rel_has_defect.csv', index=False)
    pd.DataFrame(columns=['from', 'to']).to_csv(f'{NEO4J_DIR}/rel_has_failure.csv', index=False)
    pd.DataFrame(columns=['from', 'to']).to_csv(f'{NEO4J_DIR}/rel_market_price.csv', index=False)

    print(f"[OK] 데이터 준비 완료.")

if __name__ == "__main__":
    main()
