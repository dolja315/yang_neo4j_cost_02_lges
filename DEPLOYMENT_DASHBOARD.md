# Semiconductor Cost Variance Dashboard Deployment

This guide explains how to deploy and run the new **Semiconductor Cost Variance Dashboard**.

## 1. Prerequisites

- **Python 3.12+**
- **Neo4j Aura Database** (Cloud)
- **Docker & Docker Compose** (Optional, for containerized deployment)

## 2. Environment Setup

Create a `.env` file in the root directory with your Neo4j Aura credentials:

```env
NEO4J_URI=neo4j+ssc://<your-aura-db-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
```

## 3. Data Generation & Loading

Before running the dashboard, you must generate the semiconductor dataset and load it into Neo4j.

### Step 1: Generate Data
Run the generation script to create CSV files in `data/neo4j_import/`:

```bash
pip install -r requirements.txt
python generate_data_semiconductor.py
```

This will create:
- Standard nodes: `products.csv`, `materials.csv`, `work_centers.csv`, `production_orders.csv`, `variances.csv`, `causes.csv`
- Relationship files: `rel_*.csv`
- **New Relationship files**: `rel_variance_material.csv`, `rel_variance_workcenter.csv`, `rel_variance_defect.csv`, `rel_variance_failure.csv`

### Step 2: Load Data to Neo4j
Ensure your `.env` file is set up correctly, then execute the loader:

```bash
python upload_to_neo4j.py
```
*Note: This script will clear the existing database (`clear_first=True` by default).*

## 4. Running the Application (Local)

Start the Flask API server which serves the dashboard:

```bash
gunicorn --bind 0.0.0.0:8000 --chdir visualization --timeout 600 graph_api_server:app
```

Access the dashboard at: **http://localhost:8000/**

### Dashboard Features:
- **Tab 1**: Original Dashboard (Legacy View)
- **Tab 2**: **Process Monitoring** (Heatmap & Drill-down)
- **Tab 3**: **Graph Explorer** (Root Cause Analysis with "Spider Legs" visualization)

## 5. Docker Deployment

To run the application using Docker Compose:

1.  **Build and Run**:
    ```bash
    docker-compose up --build -d
    ```

2.  **Access Services**:
    -   **Web Dashboard**: http://localhost:8000

## 6. Troubleshooting

-   **"Failed to fetch process status"**: Check if the Neo4j Aura instance is reachable and the `.env` credentials are correct.
-   **Graph Empty**: Ensure `upload_to_neo4j.py` ran successfully and populated the database.
-   **Port Conflicts**: Ensure port 8000 is free.
