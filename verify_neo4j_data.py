import os
import ssl
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd

def get_neo4j_connection():
    load_dotenv()
    uri = os.getenv('NEO4J_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')

    if not uri:
        print("[Skipping] NEO4J_URI not set.")
        return None

    uri = uri.replace('neo4j+s://', 'bolt://')
    uri = uri.replace('neo4j+ssc://', 'bolt://')

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password), ssl_context=ssl_context)
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"[Error] Could not connect to Neo4j: {e}")
        return None

def verify():
    driver = get_neo4j_connection()
    if not driver:
        return

    print("="*60)
    print("Verifying Neo4j Data for Semiconductor Dashboard")
    print("="*60)

    with driver.session() as session:
        # 1. Check Total Orders and Variances
        print("\n[1] Checking Summary Data...")
        result = session.run("""
            MATCH (po:ProductionOrder)
            WITH count(po) as total_orders
            MATCH (v:Variance)
            RETURN total_orders, count(v) as total_variances
        """)
        record = result.single()
        print(f"  - Total Orders: {record['total_orders']}")
        print(f"  - Total Variances: {record['total_variances']}")

        # 2. Check Cause Analysis
        print("\n[2] Checking Cause Analysis (CAUSED_BY relationship)...")
        result = session.run("""
            MATCH (v:Variance)-[:CAUSED_BY]->(c:Cause)
            RETURN count(v) as count
        """)
        print(f"  - Variances with Cause: {result.single()['count']}")

        # 3. Check Work Center Analysis
        print("\n[3] Checking Work Center Analysis (WORKS_AT relationship)...")
        result = session.run("""
            MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter)
            RETURN count(po) as count
        """)
        print(f"  - Orders with Work Center info: {result.single()['count']}")

    driver.close()
    print("\n[OK] Verification Complete.")

if __name__ == "__main__":
    verify()
