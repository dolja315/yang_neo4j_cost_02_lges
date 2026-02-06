import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

# Configuration
NEO4J_DIR = 'data/neo4j_import'
os.makedirs(NEO4J_DIR, exist_ok=True)

# Random Seed
random.seed(2025)
np.random.seed(2025)

# Date Range
DATES = pd.date_range(start='2025-01-01', end='2026-01-01', freq='MS')
MONTHS = [d.strftime('%Y-%m') for d in DATES]

# ==========================================
# 1. Master Data Generation
# ==========================================

def generate_master_data():
    # Company & Factories
    companies = [{'id': 'SK-HYNIX', 'name': 'SK Hynix'}]
    factories = [
        {'id': 'FAC-M16', 'name': 'M16 Plant (Icheon)', 'type': 'Fab', 'company_id': 'SK-HYNIX'},
        {'id': 'FAC-M15', 'name': 'M15 Plant (Cheongju)', 'type': 'Fab', 'company_id': 'SK-HYNIX'}
    ]
    areas = [{'id': 'AREA-FAB-CLEAN', 'name': 'Clean Room Zone', 'factory_id': 'FAC-M16'}] # Simplified assignment

    # VFAreas (Process Steps)
    vf_areas = [
        # Wafer Fab
        {'id': 'VF-PHOTO', 'name': 'Photolithography', 'type': 'Wafer Fab', 'area_id': 'AREA-FAB-CLEAN'},
        {'id': 'VF-ETCH', 'name': 'Etching', 'type': 'Wafer Fab', 'area_id': 'AREA-FAB-CLEAN'},
        {'id': 'VF-DEPO', 'name': 'Deposition', 'type': 'Wafer Fab', 'area_id': 'AREA-FAB-CLEAN'},
        # Packaging
        {'id': 'VF-TSV', 'name': 'Through Silicon Via', 'type': 'Packaging', 'area_id': 'AREA-FAB-CLEAN'},
        {'id': 'VF-MR-MUF', 'name': 'MR-MUF Reflow', 'type': 'Packaging', 'area_id': 'AREA-FAB-CLEAN'},
        {'id': 'VF-TEST-PKG', 'name': 'Final Test', 'type': 'Packaging', 'area_id': 'AREA-FAB-CLEAN'}
    ]

    # Products
    families = [
        {'id': 'FAM-DRAM', 'name': 'DRAM'},
        {'id': 'FAM-NAND', 'name': 'NAND Flash'}
    ]
    products = [
        {'id': 'PROD-HBM3E', 'name': 'HBM3E 8-Hi', 'family_id': 'FAM-DRAM'},
        {'id': 'PROD-DDR5', 'name': 'DDR5 32GB', 'family_id': 'FAM-DRAM'},
        {'id': 'PROD-NAND-238L', 'name': '238-Layer 4D NAND', 'family_id': 'FAM-NAND'}
    ]

    # Cost Hierarchy
    accounts = [
        {'id': 'ACC-MAT', 'name': 'Direct Material'},
        {'id': 'ACC-MFG', 'name': 'Overhead'}
    ]
    sub_accounts = [
        {'id': 'SUB-WAFER', 'name': 'Wafer', 'account_id': 'ACC-MAT'},
        {'id': 'SUB-CHEM', 'name': 'Chemicals', 'account_id': 'ACC-MAT'},
        {'id': 'SUB-PKG-MAT', 'name': 'Packaging Materials', 'account_id': 'ACC-MAT'}
    ]

    # Material Items
    items = [
        {'id': 'ITEM-WAFER-12', 'name': '12-inch Polished Wafer', 'unit': 'EA', 'sub_account_id': 'SUB-WAFER', 'base_price': 500},
        {'id': 'ITEM-PR-EUV', 'name': 'EUV Photoresist', 'unit': 'L', 'sub_account_id': 'SUB-CHEM', 'base_price': 2000},
        {'id': 'ITEM-LMC-H', 'name': 'Liquid Molding Compound (High Grade)', 'unit': 'KG', 'sub_account_id': 'SUB-PKG-MAT', 'base_price': 150},
        {'id': 'ITEM-HBM-BASE', 'name': 'Base Die', 'unit': 'EA', 'sub_account_id': 'SUB-WAFER', 'base_price': 50}
    ]

    # Symptoms & Factors
    symptoms = [{'id': 'SYMP-VOID', 'name': 'Micro Voids'}]
    factors = [{'id': 'FACT-MAT-BATCH', 'name': 'Bad Batch Issue', 'type': 'Material'}]

    return {
        'companies': pd.DataFrame(companies),
        'factories': pd.DataFrame(factories),
        'areas': pd.DataFrame(areas),
        'vf_areas': pd.DataFrame(vf_areas),
        'families': pd.DataFrame(families),
        'products': pd.DataFrame(products),
        'accounts': pd.DataFrame(accounts),
        'sub_accounts': pd.DataFrame(sub_accounts),
        'items': pd.DataFrame(items),
        'symptoms': pd.DataFrame(symptoms),
        'factors': pd.DataFrame(factors)
    }

# ==========================================
# 2. Transactional Data Generation
# ==========================================

def generate_transactions(master_data):
    vf_states = []
    prod_states = []

    # Relationships
    rel_contributes = [] # Item -> VFState
    rel_allocates = []   # VFState -> ProdState
    rel_next_vf = []
    rel_next_prod = []
    rel_has_symptom = []
    rel_caused_by = [] # Symptom -> Factor
    rel_impacts = []   # Event -> Item/VF

    external_events = []

    # Unpack Master Data
    vf_df = master_data['vf_areas']
    prod_df = master_data['products']
    items_df = master_data['items']

    # --- Configuration per Product ---
    # Simplified BOM/Routing simulation
    # Product -> [VF Steps]
    # Each VF Step uses certain Items

    prod_routing = {
        'PROD-HBM3E': ['VF-PHOTO', 'VF-ETCH', 'VF-TSV', 'VF-MR-MUF', 'VF-TEST-PKG'],
        'PROD-DDR5': ['VF-PHOTO', 'VF-ETCH', 'VF-DEPO', 'VF-TEST-PKG'],
        'PROD-NAND-238L': ['VF-PHOTO', 'VF-ETCH', 'VF-DEPO', 'VF-TEST-PKG']
    }

    # VF -> Items (Base Usage)
    vf_item_usage = {
        'VF-PHOTO': {'ITEM-PR-EUV': 0.005}, # 0.005 L per unit
        'VF-ETCH': {'ITEM-WAFER-12': 0.001}, # Fractional wafer per unit? Simplification: Consume wafer at first step or spread. Let's put Wafer at Etch for simplicity of cost flow.
        'VF-TSV': {'ITEM-HBM-BASE': 1.0},
        'VF-MR-MUF': {'ITEM-LMC-H': 0.02},
        'VF-DEPO': {},
        'VF-TEST-PKG': {}
    }

    # Initial Volumes
    base_volumes = {
        'PROD-HBM3E': 5000,
        'PROD-DDR5': 20000,
        'PROD-NAND-238L': 15000
    }

    prev_vf_states = {}   # Key: vf_id, Value: state_id
    prev_prod_states = {} # Key: prod_id, Value: state_id

    for month_idx, month in enumerate(MONTHS):
        print(f"Generating data for {month}...")

        # --- Scenarios Trigger Check ---

        # Scenario A: Material Cost Spike (June 2025)
        # Event: Global Neon Gas Shortage -> Impacts ITEM-PR-EUV price
        item_price_multiplier = {item: 1.0 for item in items_df['id']}

        if month == '2025-06':
            evt_id = f"EVT-{month}-MARKET"
            external_events.append({
                'id': evt_id, 'date': f"{month}-15",
                'title': 'Global Neon Gas Shortage',
                'description': 'Supply chain disruption causing PR price hike.',
                'category': 'Market'
            })
            # Impact Relationship
            rel_impacts.append({'from': evt_id, 'to': 'ITEM-PR-EUV'})
            item_price_multiplier['ITEM-PR-EUV'] = 1.25 # 25% increase

        # Scenario B: HBM Yield Drop (Sept 2025)
        # Event: Clean Room Contamination
        hbm_yield_mult = 1.0
        if month == '2025-09':
            evt_id = f"EVT-{month}-OPS"
            external_events.append({
                'id': evt_id, 'date': f"{month}-10",
                'title': 'M16 Clean Room Contamination Warning',
                'description': 'Detected micro-particles in MR-MUF area.',
                'category': 'Operations'
            })
            rel_impacts.append({'from': evt_id, 'to': 'VF-MR-MUF'})
            hbm_yield_mult = 0.925 # Drops to ~92% (Base is usually high)

        # Scenario C: Volume Ramp-up (Nov 2025 - Jan 2026)
        # Event: AI Server Demand Surge
        if month == '2025-11':
            evt_id = f"EVT-{month}-SALES"
            external_events.append({
                'id': evt_id, 'date': f"{month}-01",
                'title': 'AI Server Demand Surge',
                'description': 'Strategic ramp-up for HBM3E.',
                'category': 'Sales'
            })
            # Impact on HBM Product (conceptual, maybe link to Product?)
            # For schema strictness, let's link to VFArea or Item. Or just keep event.
            pass

        # Apply Volume Ramp
        current_volumes = base_volumes.copy()
        if month >= '2025-11':
            current_volumes['PROD-HBM3E'] = int(current_volumes['PROD-HBM3E'] * 1.4) # 40% increase

        # --- Generate Data ---

        # 1. Calculate Product-Process Intersections first to aggregate VF totals
        # We need to know how much each product consumes of each VF to build VF states

        # Structure: vf_id -> { total_input, total_output, cost_contributors: [], allocations: [] }
        vf_month_data = {vf: {'input': 0, 'output': 0, 'items': {}, 'prod_allocs': []} for vf in vf_df['id']}

        for prod_id, route in prod_routing.items():
            vol = current_volumes[prod_id]
            # Random fluctuation
            vol = int(vol * np.random.uniform(0.98, 1.02))

            for vf_id in route:
                # Determine Yield
                step_yield = np.random.uniform(0.99, 0.999)
                if prod_id == 'PROD-HBM3E' and vf_id == 'VF-MR-MUF' and month == '2025-09':
                    step_yield = 0.92 # Scenario B

                input_qty = vol
                output_qty = int(input_qty * step_yield)

                # Accumulate VF totals
                vf_month_data[vf_id]['input'] += input_qty
                vf_month_data[vf_id]['output'] += output_qty

                # Calculate Material Usage for this Prod-VF instance
                usage_def = vf_item_usage.get(vf_id, {})

                step_mat_cost = 0
                for item_id, qty_per_unit in usage_def.items():
                    # Get base price
                    base_price = items_df[items_df['id'] == item_id]['base_price'].values[0]
                    price = base_price * item_price_multiplier[item_id]

                    total_item_qty = input_qty * qty_per_unit
                    total_item_cost = total_item_qty * price

                    # Add to VF-Item aggregation
                    if item_id not in vf_month_data[vf_id]['items']:
                        vf_month_data[vf_id]['items'][item_id] = {'qty': 0, 'amount': 0}
                    vf_month_data[vf_id]['items'][item_id]['qty'] += total_item_qty
                    vf_month_data[vf_id]['items'][item_id]['amount'] += total_item_cost

                    step_mat_cost += total_item_cost

                # Add Overhead (Simplified: fixed rate per unit)
                overhead_rate = 10 # dummy
                step_overhead = input_qty * overhead_rate

                # We will register the allocation logic here
                # But we need the VF State ID first.
                vf_month_data[vf_id]['prod_allocs'].append({
                    'prod_id': prod_id,
                    'mat_cost': step_mat_cost,
                    'overhead_cost': step_overhead,
                    'output_qty': output_qty // len(route) # Rough attribution for "Product State" volume?
                    # Actually MonthlyProductState is usually finished goods or WIP.
                    # Let's say MonthlyProductState represents the Finished Good status for that month.
                })

        # 2. Create MonthlyVFState Nodes
        for vf_id, data in vf_month_data.items():
            state_id = f"STATE-{vf_id}-{month}"

            total_mat_cost = sum(i['amount'] for i in data['items'].values())
            total_overhead = sum(a['overhead_cost'] for a in data['prod_allocs'])
            total_cost = total_mat_cost + total_overhead

            yield_rate = (data['output'] / data['input']) if data['input'] > 0 else 0

            vf_states.append({
                'id': state_id,
                'vf_id': vf_id, # Helper for relationship
                'month': month,
                'total_cost': round(total_cost, 2),
                'production_volume': data['input'],
                'output_volume': data['output'],
                'yield_rate': round(yield_rate, 4)
            })

            # Relations: Material -> VFState
            for item_id, item_data in data['items'].items():
                rel_contributes.append({
                    'from': item_id,
                    'to': state_id,
                    'amount': round(item_data['amount'], 2),
                    'qty': round(item_data['qty'], 2)
                })

            # Scenario B: Symptom Link
            if vf_id == 'VF-MR-MUF' and month == '2025-09':
                rel_has_symptom.append({'from': state_id, 'to': 'SYMP-VOID'})
                # Ensure Factor link exists (static, but good to double check or re-emit if needed)
                # We do static generation for Symptoms/Factors, but relationships might be needed.
                # Actually, schema says (:Symptom)-[:CAUSED_BY]->(:Factor). This is static master data rel.
                # But (:MonthlyVFState)-[:HAS_SYMPTOM]->(:Symptom) is dynamic.

            # Relations: NEXT_MONTH
            if vf_id in prev_vf_states:
                rel_next_vf.append({'from': prev_vf_states[vf_id], 'to': state_id})
            prev_vf_states[vf_id] = state_id


        # 3. Create MonthlyProductState Nodes
        # Aggregate costs from VFs to Products

        prod_month_data = {p: {'cost': 0, 'volume': 0} for p in prod_df['id']}

        # Allocations from VF States
        for vf_id, data in vf_month_data.items():
            vf_state_id = f"STATE-{vf_id}-{month}"

            total_vf_cost = sum(a['mat_cost'] + a['overhead_cost'] for a in data['prod_allocs'])

            for alloc in data['prod_allocs']:
                p_id = alloc['prod_id']
                cost_share = alloc['mat_cost'] + alloc['overhead_cost']

                # Allocation Ratio
                ratio = cost_share / total_vf_cost if total_vf_cost > 0 else 0

                # Prod State Accumulation
                prod_month_data[p_id]['cost'] += cost_share

                # Volume: We use the volume of the FINAL step as the Product Volume
                # Check if this VF is the last step for this product
                if vf_id == prod_routing[p_id][-1]:
                    prod_month_data[p_id]['volume'] = alloc['output_qty'] # Actually stored in 'output' of VF logic above?
                    # Re-logic: alloc['output_qty'] in my loop was just output of that step.
                    # Yes, if it is last step, it is finished good volume.
                    # Wait, in the loop above `vf_month_data[vf_id]['output']` is total output of VF.
                    # `alloc` logic didn't explicitly store specific output per product, but let's assume `output_qty` derived from input `vol` is correct.
                    # Yes `input_qty = vol` (where vol is per product).
                    prod_month_data[p_id]['volume'] = int(vol * (0.99 if month != '2025-09' else 0.92)) # Approximation for now to match logic

                # Create Relationship: VFState -> ProdState
                # We need ProdState ID.
                prod_state_id = f"STATE-{p_id}-{month}"
                rel_allocates.append({
                    'from': vf_state_id,
                    'to': prod_state_id,
                    'amount': round(cost_share, 2),
                    'ratio': round(ratio, 4)
                })

        for p_id, data in prod_month_data.items():
            state_id = f"STATE-{p_id}-{month}"
            vol = data['volume']
            total_cost = data['cost']
            unit_cost = total_cost / vol if vol > 0 else 0

            prod_states.append({
                'id': state_id,
                'prod_id': p_id,
                'month': month,
                'total_cost': round(total_cost, 2),
                'output_volume': vol,
                'unit_cost': round(unit_cost, 2)
            })

            # Relations: NEXT_MONTH
            if p_id in prev_prod_states:
                rel_next_prod.append({'from': prev_prod_states[p_id], 'to': state_id})
            prev_prod_states[p_id] = state_id

    # Symptom -> Factor (Static)
    rel_caused_by.append({'from': 'SYMP-VOID', 'to': 'FACT-MAT-BATCH'})

    return {
        'vf_states': pd.DataFrame(vf_states),
        'prod_states': pd.DataFrame(prod_states),
        'external_events': pd.DataFrame(external_events),
        'rel_contributes': pd.DataFrame(rel_contributes),
        'rel_allocates': pd.DataFrame(rel_allocates),
        'rel_next_vf': pd.DataFrame(rel_next_vf),
        'rel_next_prod': pd.DataFrame(rel_next_prod),
        'rel_has_symptom': pd.DataFrame(rel_has_symptom),
        'rel_caused_by': pd.DataFrame(rel_caused_by),
        'rel_impacts': pd.DataFrame(rel_impacts)
    }

# ==========================================
# 3. Main Execution & Export
# ==========================================

def main():
    print("Generating Master Data...")
    master = generate_master_data()

    print("Generating Transactions...")
    trans = generate_transactions(master)

    # Export Master
    print(f"Exporting to {NEO4J_DIR}...")
    master['companies'].to_csv(f'{NEO4J_DIR}/companies.csv', index=False)
    master['factories'].to_csv(f'{NEO4J_DIR}/factories.csv', index=False)
    master['areas'].to_csv(f'{NEO4J_DIR}/areas.csv', index=False)
    master['vf_areas'].to_csv(f'{NEO4J_DIR}/vf_areas.csv', index=False)
    master['families'].to_csv(f'{NEO4J_DIR}/product_families.csv', index=False)
    master['products'].to_csv(f'{NEO4J_DIR}/products_v2.csv', index=False)
    master['accounts'].to_csv(f'{NEO4J_DIR}/accounts.csv', index=False)
    master['sub_accounts'].to_csv(f'{NEO4J_DIR}/sub_accounts.csv', index=False)
    master['items'].to_csv(f'{NEO4J_DIR}/material_items.csv', index=False)
    master['symptoms'].to_csv(f'{NEO4J_DIR}/symptoms_v2.csv', index=False)
    master['factors'].to_csv(f'{NEO4J_DIR}/factors_v2.csv', index=False)

    # Export Transactions
    trans['vf_states'].to_csv(f'{NEO4J_DIR}/monthly_vf_states.csv', index=False)
    trans['prod_states'].to_csv(f'{NEO4J_DIR}/monthly_product_states_v2.csv', index=False)
    trans['external_events'].to_csv(f'{NEO4J_DIR}/external_events.csv', index=False)

    # Export Relationships
    trans['rel_contributes'].to_csv(f'{NEO4J_DIR}/rel_contributes.csv', index=False)
    trans['rel_allocates'].to_csv(f'{NEO4J_DIR}/rel_allocates_v2.csv', index=False)
    trans['rel_next_vf'].to_csv(f'{NEO4J_DIR}/rel_next_vf.csv', index=False)
    trans['rel_next_prod'].to_csv(f'{NEO4J_DIR}/rel_next_prod.csv', index=False)
    trans['rel_has_symptom'].to_csv(f'{NEO4J_DIR}/rel_has_symptom.csv', index=False)
    trans['rel_caused_by'].to_csv(f'{NEO4J_DIR}/rel_caused_by_v2.csv', index=False)
    trans['rel_impacts'].to_csv(f'{NEO4J_DIR}/rel_impacts.csv', index=False)

    # Helper Relationships for Hierarchy
    # Company -> Factory
    pd.DataFrame({'from': 'SK-HYNIX', 'to': ['FAC-M16', 'FAC-M15']}).explode('to').to_csv(f'{NEO4J_DIR}/rel_has_factory.csv', index=False)
    # Factory -> Area
    pd.DataFrame({'from': 'FAC-M16', 'to': ['AREA-FAB-CLEAN']}).to_csv(f'{NEO4J_DIR}/rel_has_area.csv', index=False)
    # Area -> VF
    master['vf_areas'][['area_id', 'id']].rename(columns={'area_id':'from', 'id':'to'}).to_csv(f'{NEO4J_DIR}/rel_hosts_vf.csv', index=False)
    # Family -> Product
    master['products'][['family_id', 'id']].rename(columns={'family_id':'from', 'id':'to'}).to_csv(f'{NEO4J_DIR}/rel_includes_product.csv', index=False)
    # Account -> SubAccount
    master['sub_accounts'][['account_id', 'id']].rename(columns={'account_id':'from', 'id':'to'}).to_csv(f'{NEO4J_DIR}/rel_has_sub.csv', index=False)
    # SubAccount -> Item
    master['items'][['sub_account_id', 'id']].rename(columns={'sub_account_id':'from', 'id':'to'}).to_csv(f'{NEO4J_DIR}/rel_includes_item.csv', index=False)

    # VF State -> VF (Reverse link for lookup if needed, or just rely on id parsing. Let's add explicit link for cleaner graph)
    # Actually schema: `(:VFArea)-[:HAS_STATE]->(:MonthlyVFState)` ? The prompt implies TS linked list.
    # Usually we want `(:VFArea)-[:HAS_STATE]->(:MonthlyVFState)`.
    # Let's generate it.
    vf_state_rel = trans['vf_states'][['vf_id', 'id']].rename(columns={'vf_id':'from', 'id':'to'})
    vf_state_rel.to_csv(f'{NEO4J_DIR}/rel_vf_has_state.csv', index=False)

    # Product -> Product State
    prod_state_rel = trans['prod_states'][['prod_id', 'id']].rename(columns={'prod_id':'from', 'id':'to'})
    prod_state_rel.to_csv(f'{NEO4J_DIR}/rel_prod_has_state.csv', index=False)


    print("Done.")

if __name__ == "__main__":
    main()
