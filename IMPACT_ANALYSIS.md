# Impact Analysis: Dashboard & Data Enhancements

## Overview
This document outlines the changes made to the Semiconductor Cost Variance Dashboard to address user requirements regarding process monitoring, analysis layout, and data completeness.

## 1. Data Generation Updates
**File:** `generate_data_semiconductor.py`

*   **Variance Distribution:** Previously, variances were concentrated or not explicitly linked to all relevant WorkCenters.
    *   **Change:** Updated `generate_variance_analysis` to infer the correct WorkCenter for Material variances based on material type (e.g., Wire -> Wire Bond, EMC -> Molding, Wafer -> Die Attach).
    *   **Impact:** Variances are now distributed across multiple process steps (Die Attach, Wire Bond, Molding), reflecting a more realistic manufacturing scenario. This directly addresses the issue where "only Die Attach had variance".
    *   **Note:** `data/neo4j_import/rel_variance_workcenter.csv` now contains relationships for multiple WorkCenters.

## 2. Process Monitoring (Heatmap)
**File:** `new_dashboard.html`

*   **Step Aggregation:**
    *   **Change:** The Heatmap logic was updated to aggregate data by Process Group (Die Attach, Wire Bond, Molding, Marking) instead of displaying individual WorkCenter IDs.
    *   **Impact:** If multiple WorkCenters exist for a single process type (e.g., `WC-DA-01`, `WC-DA-02`), their risk levels are now summed up under a single "Die Attach" step, providing a clearer high-level view.

## 3. Dashboard Layout Refactoring
**File:** `new_dashboard.html`

*   **Analysis Panel Repositioning:**
    *   **Change:** The "Side Drawer" (Analysis view) has been removed. A new "Bottom Analysis Panel" has been introduced within the Process Monitoring tab (`Tab 2`).
    *   **Impact:** The Cost Breakdown (Waterfall) chart and Root Cause Graph are now displayed in a larger, full-width panel below the Heatmap, improving readability and usability as requested.

## 4. Cost Allocation Feature
**File:** `new_dashboard.html`, `graph_api_server.py`

*   **UI Integration:**
    *   **Change:** Added a "View Allocation" button in the Analysis Panel when a Process/WorkCenter is selected.
    *   **Impact:** Users can now visualize the Cost Allocation flow (WorkCenter -> CostPool -> ProductionOrder) directly in the dashboard, confirming the feature's existence and accessibility.

## 5. Comparative Analysis Fix
**File:** `comparison.html`

*   **API Connectivity:**
    *   **Change:** Corrected the hardcoded API base URL from `http://localhost:8000/api` to relative `/api`.
    *   **Impact:** This resolves potential connectivity or CORS issues, ensuring that the dropdowns for Product, Process, and Period are correctly populated.

## Summary of User Value
*   **Visual Clarity:** Better layout and aggregated views.
*   **Data Completeness:** More realistic data spread across processes.
*   **Functional Fixes:** Comparative analysis tool is now operational.
