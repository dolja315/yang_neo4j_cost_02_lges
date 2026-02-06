import os
import sys
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USERNAME')
PASSWORD = os.getenv('NEO4J_PASSWORD')
DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
DATA_DIR = 'data/neo4j_import'

def connect():
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        driver.verify_connectivity()
        print(f"Connected to Neo4j: {URI}")
        return driver
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

def clear_database(driver):
    print("Clearing database...")
    with driver.session(database=DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("Database cleared.")

def create_constraints(driver):
    print("Creating constraints...")
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
        "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (evt:ExternalEvent) REQUIRE evt.id IS UNIQUE"
    ]
    with driver.session(database=DATABASE) as session:
        for constraint in constraints:
            session.run(constraint)
    print("Constraints created.")

def load_csv_data(driver, filename, query, batch_size=1000):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Loading {filename}...")
    try:
        df = pd.read_csv(filepath)
        # Convert NaN to None for Neo4j compatibility
        df = df.where(pd.notnull(df), None)

        total_rows = len(df)
        with driver.session(database=DATABASE) as session:
            for start in tqdm(range(0, total_rows, batch_size), desc=filename):
                end = start + batch_size
                batch = df[start:end].to_dict('records')
                session.run(query, rows=batch)
    except Exception as e:
        print(f"Error loading {filename}: {e}")

def run_upload(driver):
    clear_database(driver)
    create_constraints(driver)

    # Master Data
    load_csv_data(driver, 'companies.csv',
        "UNWIND $rows AS row MERGE (c:Company {id: row.id}) SET c.name = row.name")

    load_csv_data(driver, 'factories.csv',
        "UNWIND $rows AS row MERGE (f:Factory {id: row.id}) SET f.name = row.name, f.type = row.type")

    load_csv_data(driver, 'areas.csv',
        "UNWIND $rows AS row MERGE (a:Area {id: row.id}) SET a.name = row.name")

    load_csv_data(driver, 'vf_areas.csv',
        "UNWIND $rows AS row MERGE (vf:VFArea {id: row.id}) SET vf.name = row.name, vf.type = row.type")

    load_csv_data(driver, 'product_families.csv',
        "UNWIND $rows AS row MERGE (fam:ProductFamily {id: row.id}) SET fam.name = row.name")

    load_csv_data(driver, 'products_v2.csv',
        "UNWIND $rows AS row MERGE (p:Product {id: row.id}) SET p.name = row.name")

    load_csv_data(driver, 'accounts.csv',
        "UNWIND $rows AS row MERGE (acc:CostAccount {id: row.id}) SET acc.name = row.name")

    load_csv_data(driver, 'sub_accounts.csv',
        "UNWIND $rows AS row MERGE (sub:CostSubAccount {id: row.id}) SET sub.name = row.name")

    load_csv_data(driver, 'material_items.csv',
        """UNWIND $rows AS row
           MERGE (item:MaterialItem {id: row.id})
           SET item.name = row.name, item.unit = row.unit, item.base_price = toFloat(row.base_price)""")

    load_csv_data(driver, 'symptoms_v2.csv',
        "UNWIND $rows AS row MERGE (s:Symptom {id: row.id}) SET s.name = row.name")

    load_csv_data(driver, 'factors_v2.csv',
        "UNWIND $rows AS row MERGE (f:Factor {id: row.id}) SET f.name = row.name, f.type = row.type")

    load_csv_data(driver, 'external_events.csv',
        """UNWIND $rows AS row
           MERGE (e:ExternalEvent {id: row.id})
           SET e.date = row.date, e.title = row.title, e.description = row.description, e.category = row.category""")

    # Transaction Data
    load_csv_data(driver, 'monthly_vf_states.csv',
        """UNWIND $rows AS row
           MERGE (s:MonthlyVFState {id: row.id})
           SET s.month = row.month,
               s.total_cost = toFloat(row.total_cost),
               s.production_volume = toInteger(row.production_volume),
               s.output_volume = toInteger(row.output_volume),
               s.yield_rate = toFloat(row.yield_rate)""")

    load_csv_data(driver, 'monthly_product_states_v2.csv',
        """UNWIND $rows AS row
           MERGE (s:MonthlyProductState {id: row.id})
           SET s.month = row.month,
               s.total_cost = toFloat(row.total_cost),
               s.output_volume = toInteger(row.output_volume),
               s.unit_cost = toFloat(row.unit_cost)""")

    # Relationships
    load_csv_data(driver, 'rel_has_factory.csv',
        """UNWIND $rows AS row
           MATCH (a:Company {id: row.from}), (b:Factory {id: row.to})
           MERGE (a)-[:HAS_FACTORY]->(b)""")

    load_csv_data(driver, 'rel_has_area.csv',
        """UNWIND $rows AS row
           MATCH (a:Factory {id: row.from}), (b:Area {id: row.to})
           MERGE (a)-[:HAS_AREA]->(b)""")

    load_csv_data(driver, 'rel_hosts_vf.csv',
        """UNWIND $rows AS row
           MATCH (a:Area {id: row.from}), (b:VFArea {id: row.to})
           MERGE (a)-[:HOSTS_VF]->(b)""")

    load_csv_data(driver, 'rel_includes_product.csv',
        """UNWIND $rows AS row
           MATCH (a:ProductFamily {id: row.from}), (b:Product {id: row.to})
           MERGE (a)-[:INCLUDES_PRODUCT]->(b)""")

    load_csv_data(driver, 'rel_has_sub.csv',
        """UNWIND $rows AS row
           MATCH (a:CostAccount {id: row.from}), (b:CostSubAccount {id: row.to})
           MERGE (a)-[:HAS_SUB_ACCOUNT]->(b)""")

    load_csv_data(driver, 'rel_includes_item.csv',
        """UNWIND $rows AS row
           MATCH (a:CostSubAccount {id: row.from}), (b:MaterialItem {id: row.to})
           MERGE (a)-[:INCLUDES_ITEM]->(b)""")

    load_csv_data(driver, 'rel_vf_has_state.csv',
        """UNWIND $rows AS row
           MATCH (a:VFArea {id: row.from}), (b:MonthlyVFState {id: row.to})
           MERGE (a)-[:HAS_STATE]->(b)""")

    load_csv_data(driver, 'rel_prod_has_state.csv',
        """UNWIND $rows AS row
           MATCH (a:Product {id: row.from}), (b:MonthlyProductState {id: row.to})
           MERGE (a)-[:HAS_STATE]->(b)""")

    load_csv_data(driver, 'rel_contributes.csv',
        """UNWIND $rows AS row
           MATCH (a:MaterialItem {id: row.from}), (b:MonthlyVFState {id: row.to})
           MERGE (a)-[r:CONTRIBUTES_TO]->(b)
           SET r.amount = toFloat(row.amount), r.qty = toFloat(row.qty)""")

    load_csv_data(driver, 'rel_allocates_v2.csv',
        """UNWIND $rows AS row
           MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyProductState {id: row.to})
           MERGE (a)-[r:ALLOCATES_TO]->(b)
           SET r.amount = toFloat(row.amount), r.ratio = toFloat(row.ratio)""")

    load_csv_data(driver, 'rel_next_vf.csv',
        """UNWIND $rows AS row
           MATCH (a:MonthlyVFState {id: row.from}), (b:MonthlyVFState {id: row.to})
           MERGE (a)-[:NEXT_MONTH]->(b)""")

    load_csv_data(driver, 'rel_next_prod.csv',
        """UNWIND $rows AS row
           MATCH (a:MonthlyProductState {id: row.from}), (b:MonthlyProductState {id: row.to})
           MERGE (a)-[:NEXT_MONTH]->(b)""")

    load_csv_data(driver, 'rel_has_symptom.csv',
        """UNWIND $rows AS row
           MATCH (a:MonthlyVFState {id: row.from}), (b:Symptom {id: row.to})
           MERGE (a)-[:HAS_SYMPTOM]->(b)""")

    load_csv_data(driver, 'rel_caused_by_v2.csv',
        """UNWIND $rows AS row
           MATCH (a:Symptom {id: row.from}), (b:Factor {id: row.to})
           MERGE (a)-[:CAUSED_BY]->(b)""")

    load_csv_data(driver, 'rel_impacts.csv',
        """UNWIND $rows AS row
           MATCH (a:ExternalEvent {id: row.from})
           MATCH (b) WHERE b.id = row.to
           MERGE (a)-[:IMPACTS]->(b)""")

def verify_counts(driver):
    print("\nVerifying counts...")
    with driver.session(database=DATABASE) as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']
    print(f"Nodes: {node_count}")
    print(f"Relationships: {rel_count}")

if __name__ == "__main__":
    driver = connect()
    run_upload(driver)
    verify_counts(driver)
    driver.close()
    print("Done.")
