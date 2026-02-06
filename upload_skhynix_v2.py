import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
IMPORT_DIR = 'data/neo4j_import'

def run_query(session, query, parameters=None):
    try:
        session.run(query, parameters)
    except Exception as e:
        print(f"Error executing query: {e}")
        # print(f"Query: {query[:100]}...")

def batch_load(session, file_path, query, batch_size=1000):
    full_path = os.path.join(IMPORT_DIR, file_path)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        return

    print(f"Loading {file_path}...")
    try:
        # Read CSV
        df = pd.read_csv(full_path)

        # Handle NaN -> None (for Neo4j null)
        df = df.where(pd.notnull(df), None)

        # Convert to list of dicts
        data = df.to_dict('records')

        total = len(data)
        for i in range(0, total, batch_size):
            batch = data[i:i+batch_size]
            run_query(session, query, {'batch': batch})
            print(f"  Processed {min(i+batch_size, total)} / {total}")

    except Exception as e:
        print(f"Error loading {file_path}: {e}")

def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    with driver.session() as session:
        print("1. Wiping Database...")
        run_query(session, "MATCH (n) DETACH DELETE n")

        print("\n2. Creating Constraints...")
        constraints = [
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT factory_id IF NOT EXISTS FOR (f:Factory) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT area_id IF NOT EXISTS FOR (a:Area) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT vfarea_id IF NOT EXISTS FOR (vf:VFArea) REQUIRE vf.id IS UNIQUE",
            "CREATE CONSTRAINT family_id IF NOT EXISTS FOR (fam:ProductFamily) REQUIRE fam.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (acc:CostAccount) REQUIRE acc.id IS UNIQUE",
            "CREATE CONSTRAINT sub_account_id IF NOT EXISTS FOR (sub:CostSubAccount) REQUIRE sub.id IS UNIQUE",
            "CREATE CONSTRAINT item_id IF NOT EXISTS FOR (item:MaterialItem) REQUIRE item.id IS UNIQUE",
            "CREATE CONSTRAINT vfstate_id IF NOT EXISTS FOR (s:MonthlyVFState) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT prodstate_id IF NOT EXISTS FOR (s:MonthlyProductState) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (sym:Symptom) REQUIRE sym.id IS UNIQUE",
            "CREATE CONSTRAINT factor_id IF NOT EXISTS FOR (fact:Factor) REQUIRE fact.id IS UNIQUE",
            "CREATE CONSTRAINT cause_id IF NOT EXISTS FOR (c:Cause) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (evt:ExternalEvent) REQUIRE evt.id IS UNIQUE"
        ]
        for c in constraints:
            run_query(session, c)

        print("\n3. Loading Nodes...")

        # Master Data
        batch_load(session, 'companies.csv',
                   "UNWIND $batch AS row MERGE (c:Company {id: row.id}) SET c.name = row.name")

        batch_load(session, 'factories.csv',
                   "UNWIND $batch AS row MERGE (f:Factory {id: row.id}) SET f.name = row.name, f.type = row.type")

        batch_load(session, 'areas.csv',
                   "UNWIND $batch AS row MERGE (a:Area {id: row.id}) SET a.name = row.name")

        batch_load(session, 'vf_areas.csv',
                   "UNWIND $batch AS row MERGE (vf:VFArea {id: row.id}) SET vf.name = row.name, vf.type = row.type")

        batch_load(session, 'product_families.csv',
                   "UNWIND $batch AS row MERGE (fam:ProductFamily {id: row.id}) SET fam.name = row.name")

        batch_load(session, 'products_v2.csv',
                   "UNWIND $batch AS row MERGE (p:Product {id: row.id}) SET p.name = row.name")

        batch_load(session, 'accounts.csv',
                   "UNWIND $batch AS row MERGE (acc:CostAccount {id: row.id}) SET acc.name = row.name")

        batch_load(session, 'sub_accounts.csv',
                   "UNWIND $batch AS row MERGE (sub:CostSubAccount {id: row.id}) SET sub.name = row.name")

        batch_load(session, 'material_items.csv',
                   "UNWIND $batch AS row MERGE (item:MaterialItem {id: row.id}) SET item.name = row.name, item.unit = row.unit, item.base_price = row.base_price")

        batch_load(session, 'symptoms_v2.csv',
                   "UNWIND $batch AS row MERGE (s:Symptom {id: row.id}) SET s.name = row.name")

        batch_load(session, 'factors_v2.csv',
                   "UNWIND $batch AS row MERGE (f:Factor {id: row.id}) SET f.name = row.name, f.type = row.type")

        batch_load(session, 'causes_v2.csv',
                   "UNWIND $batch AS row MERGE (c:Cause {id: row.id}) SET c.name = row.name, c.category = row.category")

        batch_load(session, 'external_events.csv',
                   "UNWIND $batch AS row MERGE (e:ExternalEvent {id: row.id}) SET e.date = row.date, e.title = row.title, e.description = row.description, e.category = row.category")

        # Transactions
        # Note: Pandas infers types, so row.total_cost etc should be numeric. No explicit toFloat needed if input is float.
        batch_load(session, 'monthly_vf_states.csv', """
                   UNWIND $batch AS row
                   MERGE (s:MonthlyVFState {id: row.id})
                   SET s.month = row.month,
                       s.total_cost = row.total_cost,
                       s.production_volume = row.production_volume,
                       s.output_volume = row.output_volume,
                       s.yield_rate = row.yield_rate
                   """)

        batch_load(session, 'monthly_product_states_v2.csv', """
                   UNWIND $batch AS row
                   MERGE (s:MonthlyProductState {id: row.id})
                   SET s.month = row.month,
                       s.total_cost = row.total_cost,
                       s.output_volume = row.output_volume,
                       s.unit_cost = row.unit_cost
                   """)

        print("\n4. Loading Relationships...")

        # Hierarchy
        batch_load(session, 'rel_has_factory.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Company {id: row.from}), (b:Factory {id: row.to})
                   MERGE (a)-[:HAS_FACTORY]->(b)
                   """)

        batch_load(session, 'rel_has_area.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Factory {id: row.from}), (b:Area {id: row.to})
                   MERGE (a)-[:HAS_AREA]->(b)
                   """)

        batch_load(session, 'rel_hosts_vf.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Area {id: row.from}), (b:VFArea {id: row.to})
                   MERGE (a)-[:HOSTS_VF]->(b)
                   """)

        batch_load(session, 'rel_includes_product.csv', """
                   UNWIND $batch AS row
                   MATCH (a:ProductFamily {id: row.from}), (b:Product {id: row.to})
                   MERGE (a)-[:INCLUDES_PRODUCT]->(b)
                   """)

        batch_load(session, 'rel_has_sub.csv', """
                   UNWIND $batch AS row
                   MATCH (a:CostAccount {id: row.from}), (b:CostSubAccount {id: row.to})
                   MERGE (a)-[:HAS_SUB_ACCOUNT]->(b)
                   """)

        batch_load(session, 'rel_includes_item.csv', """
                   UNWIND $batch AS row
                   MATCH (a:CostSubAccount {id: row.from}), (b:MaterialItem {id: row.to})
                   MERGE (a)-[:INCLUDES_ITEM]->(b)
                   """)

        batch_load(session, 'rel_vf_has_state.csv', """
                   UNWIND $batch AS row
                   MATCH (a:VFArea {id: row.from}), (b:MonthlyVFState {id: row.to})
                   MERGE (a)-[:HAS_STATE]->(b)
                   """)

        batch_load(session, 'rel_prod_has_state.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Product {id: row.from}), (b:MonthlyProductState {id: row.to})
                   MERGE (a)-[:HAS_STATE]->(b)
                   """)

        # Transaction Rels
        batch_load(session, 'rel_contributes.csv', """
                   UNWIND $batch AS row
                   MATCH (a:MaterialItem {id: row.from}), (b:MonthlyVFState {id: row.to})
                   MERGE (a)-[r:CONTRIBUTES_TO]->(b)
                   SET r.amount = row.amount, r.qty = row.qty
                   """)

        batch_load(session, 'rel_allocates_v2.csv', """
                   UNWIND $batch AS row
                   MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyProductState {id: row.to})
                   MERGE (a)-[r:ALLOCATES_TO]->(b)
                   SET r.amount = row.amount, r.ratio = row.ratio
                   """)

        batch_load(session, 'rel_next_vf.csv', """
                   UNWIND $batch AS row
                   MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyVFState {id: row.to})
                   MERGE (a)-[:NEXT_MONTH]->(b)
                   """)

        batch_load(session, 'rel_next_prod.csv', """
                   UNWIND $batch AS row
                   MATCH (a:MonthlyProductState {id: row.from}), (b:MonthlyProductState {id: row.to})
                   MERGE (a)-[:NEXT_MONTH]->(b)
                   """)

        # Scenario Rels
        batch_load(session, 'rel_has_symptom.csv', """
                   UNWIND $batch AS row
                   MATCH (a:MonthlyVFState {id: row.from}), (b:Symptom {id: row.to})
                   MERGE (a)-[:HAS_SYMPTOM]->(b)
                   """)

        batch_load(session, 'rel_caused_by_v2.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Symptom {id: row.from}), (b:Factor {id: row.to})
                   MERGE (a)-[:CAUSED_BY]->(b)
                   """)

        batch_load(session, 'rel_traced_to_root.csv', """
                   UNWIND $batch AS row
                   MATCH (a:Factor {id: row.from}), (b:Cause {id: row.to})
                   MERGE (a)-[:TRACED_TO_ROOT]->(b)
                   """)

        batch_load(session, 'rel_impacts.csv', """
                   UNWIND $batch AS row
                   MATCH (a:ExternalEvent {id: row.from})
                   MATCH (b) WHERE b.id = row.to
                   MERGE (a)-[:IMPACTS]->(b)
                   """)

    driver.close()
    print("\nUpload Complete.")

if __name__ == "__main__":
    main()
