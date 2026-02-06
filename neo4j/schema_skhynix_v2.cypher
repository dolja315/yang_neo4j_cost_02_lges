// WIPE DATABASE
MATCH (n) DETACH DELETE n;

// ==========================================
// 1. CONSTRAINTS
// ==========================================

CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT factory_id IF NOT EXISTS FOR (f:Factory) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT area_id IF NOT EXISTS FOR (a:Area) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT vfarea_id IF NOT EXISTS FOR (vf:VFArea) REQUIRE vf.id IS UNIQUE;

CREATE CONSTRAINT family_id IF NOT EXISTS FOR (fam:ProductFamily) REQUIRE fam.id IS UNIQUE;
CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT account_id IF NOT EXISTS FOR (acc:CostAccount) REQUIRE acc.id IS UNIQUE;
CREATE CONSTRAINT sub_account_id IF NOT EXISTS FOR (sub:CostSubAccount) REQUIRE sub.id IS UNIQUE;
CREATE CONSTRAINT item_id IF NOT EXISTS FOR (item:MaterialItem) REQUIRE item.id IS UNIQUE;

CREATE CONSTRAINT vfstate_id IF NOT EXISTS FOR (s:MonthlyVFState) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT prodstate_id IF NOT EXISTS FOR (s:MonthlyProductState) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (sym:Symptom) REQUIRE sym.id IS UNIQUE;
CREATE CONSTRAINT factor_id IF NOT EXISTS FOR (fact:Factor) REQUIRE fact.id IS UNIQUE;
CREATE CONSTRAINT cause_id IF NOT EXISTS FOR (c:Cause) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (evt:ExternalEvent) REQUIRE evt.id IS UNIQUE;

// ==========================================
// 2. LOAD MASTER DATA
// ==========================================

LOAD CSV WITH HEADERS FROM 'file:///companies.csv' AS row
MERGE (c:Company {id: row.id})
SET c.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///factories.csv' AS row
MERGE (f:Factory {id: row.id})
SET f.name = row.name, f.type = row.type;

LOAD CSV WITH HEADERS FROM 'file:///areas.csv' AS row
MERGE (a:Area {id: row.id})
SET a.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///vf_areas.csv' AS row
MERGE (vf:VFArea {id: row.id})
SET vf.name = row.name, vf.type = row.type;

LOAD CSV WITH HEADERS FROM 'file:///product_families.csv' AS row
MERGE (fam:ProductFamily {id: row.id})
SET fam.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///products_v2.csv' AS row
MERGE (p:Product {id: row.id})
SET p.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///accounts.csv' AS row
MERGE (acc:CostAccount {id: row.id})
SET acc.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///sub_accounts.csv' AS row
MERGE (sub:CostSubAccount {id: row.id})
SET sub.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///material_items.csv' AS row
MERGE (item:MaterialItem {id: row.id})
SET item.name = row.name, item.unit = row.unit, item.base_price = toFloat(row.base_price);

LOAD CSV WITH HEADERS FROM 'file:///symptoms_v2.csv' AS row
MERGE (s:Symptom {id: row.id})
SET s.name = row.name;

LOAD CSV WITH HEADERS FROM 'file:///factors_v2.csv' AS row
MERGE (f:Factor {id: row.id})
SET f.name = row.name, f.type = row.type;

LOAD CSV WITH HEADERS FROM 'file:///causes_v2.csv' AS row
MERGE (c:Cause {id: row.id})
SET c.name = row.name, c.category = row.category;

LOAD CSV WITH HEADERS FROM 'file:///external_events.csv' AS row
MERGE (e:ExternalEvent {id: row.id})
SET e.date = row.date, e.title = row.title, e.description = row.description, e.category = row.category;

// ==========================================
// 3. LOAD TRANSACTION DATA
// ==========================================

LOAD CSV WITH HEADERS FROM 'file:///monthly_vf_states.csv' AS row
MERGE (s:MonthlyVFState {id: row.id})
SET s.month = row.month,
    s.total_cost = toFloat(row.total_cost),
    s.production_volume = toInteger(row.production_volume),
    s.output_volume = toInteger(row.output_volume),
    s.yield_rate = toFloat(row.yield_rate);

LOAD CSV WITH HEADERS FROM 'file:///monthly_product_states_v2.csv' AS row
MERGE (s:MonthlyProductState {id: row.id})
SET s.month = row.month,
    s.total_cost = toFloat(row.total_cost),
    s.output_volume = toInteger(row.output_volume),
    s.unit_cost = toFloat(row.unit_cost);

// ==========================================
// 4. LOAD RELATIONSHIPS
// ==========================================

// Hierarchy
LOAD CSV WITH HEADERS FROM 'file:///rel_has_factory.csv' AS row
MATCH (a:Company {id: row.from}), (b:Factory {id: row.to})
MERGE (a)-[:HAS_FACTORY]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_has_area.csv' AS row
MATCH (a:Factory {id: row.from}), (b:Area {id: row.to})
MERGE (a)-[:HAS_AREA]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_hosts_vf.csv' AS row
MATCH (a:Area {id: row.from}), (b:VFArea {id: row.to})
MERGE (a)-[:HOSTS_VF]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_includes_product.csv' AS row
MATCH (a:ProductFamily {id: row.from}), (b:Product {id: row.to})
MERGE (a)-[:INCLUDES_PRODUCT]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_has_sub.csv' AS row
MATCH (a:CostAccount {id: row.from}), (b:CostSubAccount {id: row.to})
MERGE (a)-[:HAS_SUB_ACCOUNT]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_includes_item.csv' AS row
MATCH (a:CostSubAccount {id: row.from}), (b:MaterialItem {id: row.to})
MERGE (a)-[:INCLUDES_ITEM]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_vf_has_state.csv' AS row
MATCH (a:VFArea {id: row.from}), (b:MonthlyVFState {id: row.to})
MERGE (a)-[:HAS_STATE]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_prod_has_state.csv' AS row
MATCH (a:Product {id: row.from}), (b:MonthlyProductState {id: row.to})
MERGE (a)-[:HAS_STATE]->(b);

// Transactions
LOAD CSV WITH HEADERS FROM 'file:///rel_contributes.csv' AS row
MATCH (a:MaterialItem {id: row.from}), (b:MonthlyVFState {id: row.to})
MERGE (a)-[r:CONTRIBUTES_TO]->(b)
SET r.amount = toFloat(row.amount), r.qty = toFloat(row.qty);

LOAD CSV WITH HEADERS FROM 'file:///rel_allocates_v2.csv' AS row
MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyProductState {id: row.to})
MERGE (a)-[r:ALLOCATES_TO]->(b)
SET r.amount = toFloat(row.amount), r.ratio = toFloat(row.ratio);

LOAD CSV WITH HEADERS FROM 'file:///rel_next_vf.csv' AS row
MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyVFState {id: row.to})
MERGE (a)-[:NEXT_MONTH]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_next_prod.csv' AS row
MATCH (a:MonthlyProductState {id: row.from}), (b:MonthlyProductState {id: row.to})
MERGE (a)-[:NEXT_MONTH]->(b);

// Scenarios / Root Cause
LOAD CSV WITH HEADERS FROM 'file:///rel_has_symptom.csv' AS row
MATCH (a:MonthlyVFState {id: row.from}), (b:Symptom {id: row.to})
MERGE (a)-[:HAS_SYMPTOM]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_caused_by_v2.csv' AS row
MATCH (a:Symptom {id: row.from}), (b:Factor {id: row.to})
MERGE (a)-[:CAUSED_BY]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_traced_to_root.csv' AS row
MATCH (a:Factor {id: row.from}), (b:Cause {id: row.to})
MERGE (a)-[:TRACED_TO_ROOT]->(b);

LOAD CSV WITH HEADERS FROM 'file:///rel_impacts.csv' AS row
MATCH (a:ExternalEvent {id: row.from})
MATCH (b) WHERE b.id = row.to  // Dynamic match
MERGE (a)-[:IMPACTS]->(b);
