"""
Load WORKS_AT relationships from rel_works_at.csv.
"""
import csv
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def main():
    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    if not uri or not user or not pwd:
        raise RuntimeError("NEO4J env not set")

    csv_path = os.path.join("data", "neo4j_import", "rel_works_at.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with driver.session() as session, open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                params = {
                    "from_id": row["from"],
                    "to_id": row["to"],
                    "standard_time_min": _to_float(row.get("standard_time_min")),
                    "actual_time_min": _to_float(row.get("actual_time_min")),
                    "efficiency_rate": _to_float(row.get("efficiency_rate")),
                    "worker_count": _to_int(row.get("worker_count")),
                }
                session.run(
                    """
                    MATCH (po:ProductionOrder {id: $from_id})
                    MATCH (wc:WorkCenter {id: $to_id})
                    MERGE (po)-[r:WORKS_AT]->(wc)
                    SET r.standard_time_min = $standard_time_min,
                        r.actual_time_min = $actual_time_min,
                        r.efficiency_rate = $efficiency_rate,
                        r.worker_count = $worker_count
                    """,
                    params,
                )
        count = driver.session().run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as c").single()[
            "c"
        ]
        print(f"WORKS_AT rels: {count}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
