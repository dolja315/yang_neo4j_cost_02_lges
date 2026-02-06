import os
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USERNAME')
PASSWORD = os.getenv('NEO4J_PASSWORD')

def run_cypher_script(script_path):
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    with open(script_path, 'r') as f:
        cypher_queries = f.read()

    # Split by semicolon to run statements separately (simple parser)
    # Note: This simple split might break if semicolons are in strings, but for our schema it should be fine.
    # Actually, LOAD CSV commands are best run one by one.

    queries = [q.strip() for q in cypher_queries.split(';') if q.strip()]

    with driver.session() as session:
        for query in queries:
            if query.startswith('//'): continue # Skip comments only lines (though split might have caught them)

            print(f"Running: {query[:50]}...")
            try:
                session.run(query)
            except Exception as e:
                print(f"Error running query: {query[:100]}...\n{e}")

    driver.close()
    print("Cypher script execution completed.")

if __name__ == "__main__":
    script_path = 'neo4j/schema_skhynix_v2.cypher'
    if os.path.exists(script_path):
        run_cypher_script(script_path)
    else:
        print(f"Script not found: {script_path}")
