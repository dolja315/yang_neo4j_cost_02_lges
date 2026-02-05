# Semiconductor Cost Variance Dashboard Deployment

This guide explains how to deploy and run the new **Semiconductor Cost Variance Dashboard**.

## 1. Prerequisites

- **Python 3.12+**
- **Neo4j Database** (Version 5.x recommended)
- **Docker & Docker Compose** (Optional, for containerized deployment)

## 2. Environment Setup

Create a `.env` file in the root directory with your Neo4j credentials:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
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
Ensure your Neo4j instance is running, then execute the loader:

```bash
python neo4j/data_loader.py
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

To run the entire stack (Flask API + Streamlit + Neo4j) using Docker Compose:

1.  **Build and Run**:
    ```bash
    docker-compose up --build -d
    ```

2.  **Access Services**:
    -   **Web Dashboard**: http://localhost:8000
    -   **Streamlit App**: http://localhost:8501
    -   **Neo4j Browser**: http://localhost:7474

3.  **Data Persistence**:
    -   Neo4j data is persisted in the `neo4j_data` volume.

## 6. Troubleshooting

-   **"Failed to fetch process status"**: Check if the Neo4j container is running and reachable at the URI specified in `.env`.
-   **Graph Empty**: Ensure `neo4j/data_loader.py` ran successfully and populated the database.
-   **Port Conflicts**: Ensure ports 8000, 8501, 7474, and 7687 are free.
