"""
Semiconductor Cost Variance Dashboard
Single-File Flask Application with React Frontend (via CDN) and Neo4j Backend.
"""

import os
import json
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Database Connection ---
def get_db_connection():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')

    # Adjust URI scheme for python driver if needed
    if uri.startswith('neo4j+s://'):
        uri = uri.replace('neo4j+s://', 'bolt://') # simplified for this env

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return None

# --- HTML Template (React Frontend) ---
FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cost Variance Detective</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- React & ReactDOM -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>

    <!-- Babel -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>

    <!-- Recharts -->
    <script src="https://unpkg.com/recharts/umd/Recharts.js"></script>

    <!-- React Force Graph -->
    <script src="https://unpkg.com/react-force-graph-2d"></script>

    <!-- Mermaid -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>

    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>

    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
        .graph-container { height: 600px; border: 1px solid #e2e8f0; border-radius: 0.5rem; background: white; }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect, useRef, useMemo } = React;
        const { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell } = Recharts;
        const ForceGraph2D = ReactForceGraph2D;

        // --- API Helper ---
        const api = {
            getProcessStatus: () => fetch('/api/process-status').then(res => res.json()),
            getOrderCosts: (id) => fetch(`/api/order-costs/${id}`).then(res => res.json()),
            getGraphData: (id) => fetch(`/api/graph-data${id ? '?node_id='+id : ''}`).then(res => res.json())
        };

        // --- Components ---

        const Header = () => (
            <header className="bg-slate-900 text-white p-4 shadow-lg flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <i data-lucide="microchip" className="w-8 h-8 text-blue-400"></i>
                    <h1 className="text-xl font-bold tracking-tight">Cost Variance Detective <span className="text-xs font-normal text-slate-400 ml-2">(Neo4j Connected)</span></h1>
                </div>
            </header>
        );

        const ProcessStep = ({ data, onClick, isSelected }) => {
            // Determine risk color based on variance count/amount
            const riskLevel = data.variance_count > 5 ? 'bg-red-100 border-red-500 text-red-700' :
                              data.variance_count > 0 ? 'bg-yellow-50 border-yellow-500 text-yellow-700' :
                              'bg-green-50 border-green-500 text-green-700';

            const selectedClass = isSelected ? 'ring-2 ring-blue-500 shadow-xl scale-105' : 'hover:shadow-md';

            return (
                <div
                    onClick={() => onClick(data)}
                    className={`cursor-pointer transition-all duration-200 border-l-4 p-4 rounded-r-lg ${riskLevel} ${selectedClass} w-64`}
                >
                    <h3 className="font-bold text-lg mb-1">{data.name}</h3>
                    <p className="text-xs font-mono opacity-80 mb-2">{data.type}</p>
                    <div className="flex justify-between items-end">
                        <span className="text-sm font-semibold">{data.variance_count} Issues</span>
                        <span className="text-xs opacity-70">Risk: {(data.total_risk/10000).toFixed(1)}k</span>
                    </div>
                </div>
            );
        };

        const WaterfallChart = ({ orderId }) => {
            const [data, setData] = useState(null);

            useEffect(() => {
                if(orderId) {
                    api.getOrderCosts(orderId).then(setData);
                }
            }, [orderId]);

            if (!data) return <div className="p-4 text-center text-gray-500">Select an order to view costs</div>;
            if (data.error) return <div className="p-4 text-center text-red-500">{data.error}</div>;

            // Transform data for waterfall
            // Planned (Base) -> Material Diff -> Labor Diff -> Overhead Diff -> Actual (Result)
            const chartData = [
                { name: 'Planned', amount: data.planned_cost, fill: '#94a3b8' }, // Slate-400
                { name: 'Material Var', amount: data.variances.MATERIAL || 0, fill: (data.variances.MATERIAL || 0) > 0 ? '#ef4444' : '#22c55e' },
                { name: 'Labor Var', amount: data.variances.LABOR || 0, fill: (data.variances.LABOR || 0) > 0 ? '#ef4444' : '#22c55e' },
                { name: 'Overhead Var', amount: data.variances.OVERHEAD || 0, fill: (data.variances.OVERHEAD || 0) > 0 ? '#ef4444' : '#22c55e' },
                { name: 'Actual', amount: data.actual_cost, fill: '#3b82f6' } // Blue-500
            ];

            return (
                <div className="h-80 w-full">
                    <h3 className="text-lg font-semibold mb-2 px-4">Cost Waterfall: {orderId}</h3>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip formatter={(value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'KRW' }).format(value)} />
                            <Bar dataKey="amount">
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            );
        };

        const ProcessMonitoring = ({ onNavigateToGraph }) => {
            const [processData, setProcessData] = useState([]);
            const [selectedStep, setSelectedStep] = useState(null);
            const [orders, setOrders] = useState([]);
            const [selectedOrder, setSelectedOrder] = useState(null);

            useEffect(() => {
                api.getProcessStatus().then(data => {
                    // Sort by process flow logic (hardcoded sequence for demo)
                    const flow = ['DIE_ATTACH', 'WIRE_BOND', 'MOLDING', 'MARKING'];
                    const sorted = data.sort((a,b) => flow.indexOf(a.type) - flow.indexOf(b.type));
                    setProcessData(sorted);
                });
            }, []);

            // When a step is selected, we should fetch orders for it (mocked/implied for now as part of 'processData' or separate call)
            // For this demo, we'll fetch orders associated with the WC
            useEffect(() => {
                if (selectedStep) {
                    // In a real app, we'd have an API to get orders by WC.
                    // reusing getProcessStatus isn't enough.
                    // Let's assume we can browse orders via graph later,
                    // or we fetch "Top Risky Orders" for this WC here.
                    // I'll add a specific fetch here using a direct cypher query via a generic endpoint or new one.
                    // For simplicity, let's just show a placeholder list or fetch 'risky orders'
                    fetch(`/api/workcenter/${selectedStep.id}/orders`).then(res => res.json()).then(setOrders);
                }
            }, [selectedStep]);

            return (
                <div className="p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-bold text-slate-800">Process Heatmap</h2>
                        <div className="text-sm text-slate-500 flex items-center gap-2">
                            <span className="w-3 h-3 bg-red-500 rounded-full"></span> High Risk
                            <span className="w-3 h-3 bg-yellow-500 rounded-full"></span> Warning
                            <span className="w-3 h-3 bg-green-500 rounded-full"></span> Stable
                        </div>
                    </div>

                    {/* Process Flow */}
                    <div className="flex gap-4 overflow-x-auto pb-4 mb-6">
                        {processData.map((step, idx) => (
                            <div key={step.id} className="flex items-center">
                                <ProcessStep
                                    data={step}
                                    isSelected={selectedStep?.id === step.id}
                                    onClick={setSelectedStep}
                                />
                                {idx < processData.length - 1 && (
                                    <div className="mx-2 text-slate-300">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Drill Down Area */}
                    {selectedStep && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {/* Order List */}
                            <div className="bg-white p-4 rounded-lg shadow border border-slate-200 h-96 overflow-y-auto">
                                <h3 className="font-semibold mb-3 text-slate-700 flex items-center gap-2">
                                    <span className="p-1 bg-slate-100 rounded">🏭 {selectedStep.name}</span>
                                    <span>Active Orders</span>
                                </h3>
                                {orders.length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-10">Loading active orders...</p>
                                ) : (
                                    <ul className="space-y-2">
                                        {orders.map(order => (
                                            <li
                                                key={order.id}
                                                onClick={() => setSelectedOrder(order.id)}
                                                className={`p-3 rounded border cursor-pointer flex justify-between items-center transition-colors ${selectedOrder === order.id ? 'bg-blue-50 border-blue-400' : 'bg-slate-50 border-slate-100 hover:bg-slate-100'}`}
                                            >
                                                <div>
                                                    <div className="font-medium text-sm">{order.id}</div>
                                                    <div className="text-xs text-slate-500">{order.product}</div>
                                                </div>
                                                {order.variance && (
                                                    <span className="text-xs font-bold text-red-600">
                                                        {order.variance.toLocaleString()} Won
                                                    </span>
                                                )}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>

                            {/* Waterfall Chart */}
                            <div className="bg-white p-4 rounded-lg shadow border border-slate-200 col-span-2">
                                {selectedOrder ? (
                                    <div className="h-full flex flex-col">
                                        <div className="flex justify-end mb-2">
                                            <button
                                                onClick={() => onNavigateToGraph(selectedOrder)}
                                                className="text-xs bg-slate-800 text-white px-3 py-1 rounded hover:bg-slate-700 flex items-center gap-1"
                                            >
                                                🔍 Analyze Root Cause
                                            </button>
                                        </div>
                                        <WaterfallChart orderId={selectedOrder} />
                                    </div>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-slate-400 bg-slate-50 rounded border-2 border-dashed border-slate-200">
                                        <p>Select an order to analyze cost variances</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            );
        };

        const GraphExplorer = ({ initialNodeId }) => {
            const graphRef = useRef();
            const [graphData, setGraphData] = useState({ nodes: [], links: [] });
            const [searchId, setSearchId] = useState(initialNodeId || '');
            const [loading, setLoading] = useState(false);

            const fetchGraph = (id) => {
                setLoading(true);
                api.getGraphData(id).then(data => {
                    // Merge new data with existing to avoid full reset, or just replace for simplicity
                    // For ForceGraph, replacing is usually cleaner unless we want incremental expansion
                    setGraphData(data);
                    setLoading(false);
                });
            };

            const handleNodeClick = (node) => {
                // Expand node (fetch more connected nodes)
                // For this demo, we'll just re-center and maybe fetch neighbors if we implemented incremental
                // api.getGraphData(node.id).then(newData => ...merge...)
                // Let's just focus/zoom on it
                graphRef.current.centerAt(node.x, node.y, 1000);
                graphRef.current.zoom(3, 2000);

                // Optionally fetch neighbors here if the backend supported specific expansion
            };

            useEffect(() => {
                if (initialNodeId) {
                    fetchGraph(initialNodeId);
                } else {
                    // Load default "risky" view
                    fetchGraph(null);
                }
            }, [initialNodeId]);

            const handleSearch = (e) => {
                e.preventDefault();
                fetchGraph(searchId);
            };

            return (
                <div className="p-6 h-full flex flex-col">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-bold text-slate-800">Root Cause Explorer</h2>
                        <form onSubmit={handleSearch} className="flex gap-2">
                            <input
                                type="text"
                                value={searchId}
                                onChange={(e) => setSearchId(e.target.value)}
                                placeholder="Search Variance / Order ID..."
                                className="px-3 py-2 border rounded-lg text-sm w-64 focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
                                Search
                            </button>
                        </form>
                    </div>

                    <div className="flex-1 graph-container relative overflow-hidden">
                        {loading && (
                            <div className="absolute inset-0 bg-white/80 z-10 flex items-center justify-center">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                            </div>
                        )}
                        <ForceGraph2D
                            ref={graphRef}
                            graphData={graphData}
                            nodeLabel="label"
                            nodeColor={node => node.color || '#94a3b8'}
                            nodeVal={node => node.size || 5}
                            linkColor={() => '#cbd5e1'}
                            onNodeClick={handleNodeClick}
                            backgroundColor="#ffffff"
                        />
                        <div className="absolute bottom-4 right-4 bg-white/90 p-3 rounded shadow text-xs border border-slate-200">
                            <div className="font-semibold mb-2">Legend</div>
                            <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#ef4444]"></span> Variance (High)</div>
                            <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#3b82f6]"></span> Order</div>
                            <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#f59e0b]"></span> Work Center</div>
                            <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#10b981]"></span> Material</div>
                            <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#8b5cf6]"></span> Cause</div>
                        </div>
                    </div>
                </div>
            );
        };

        const App = () => {
            const [activeTab, setActiveTab] = useState('monitor');
            const [graphTarget, setGraphTarget] = useState(null);

            const handleNavigateToGraph = (nodeId) => {
                setGraphTarget(nodeId);
                setActiveTab('graph');
            };

            return (
                <div className="min-h-screen flex flex-col">
                    <Header />

                    <div className="flex-1 flex flex-col max-w-7xl mx-auto w-full">
                        {/* Tabs */}
                        <div className="flex border-b border-slate-200 bg-white px-6 pt-4 sticky top-0 z-20">
                            <button
                                onClick={() => setActiveTab('monitor')}
                                className={`pb-3 px-4 text-sm font-medium transition-colors border-b-2 ${activeTab === 'monitor' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                            >
                                <span className="flex items-center gap-2">📊 Process Monitoring</span>
                            </button>
                            <button
                                onClick={() => setActiveTab('graph')}
                                className={`pb-3 px-4 text-sm font-medium transition-colors border-b-2 ${activeTab === 'graph' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                            >
                                <span className="flex items-center gap-2">🕸️ Graph Explorer</span>
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 bg-slate-50">
                            {activeTab === 'monitor' && <ProcessMonitoring onNavigateToGraph={handleNavigateToGraph} />}
                            {activeTab === 'graph' && <GraphExplorer initialNodeId={graphTarget} />}
                        </div>
                    </div>
                </div>
            );
        };

        // Lucide icons initialization
        lucide.createIcons();

        // Render
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

# --- Routes ---

@app.route('/')
def index():
    return render_template_string(FRONTEND_HTML)

@app.route('/api/process-status')
def process_status():
    driver = get_db_connection()
    if not driver:
        return jsonify([])
    
    with driver.session() as session:
        # Aggregate variance by WorkCenter
        # Using production order as the link
        query = """
        MATCH (wc:WorkCenter)
        OPTIONAL MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc)
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        RETURN wc.id as id,
               wc.name as name,
               wc.process_type as type,
               count(v) as variance_count,
               sum(coalesce(abs(v.variance_amount), 0)) as total_risk
        ORDER BY type
        """
        result = session.run(query).data()
        return jsonify(result)

@app.route('/api/workcenter/<wc_id>/orders')
def workcenter_orders(wc_id):
    driver = get_db_connection()
    if not driver:
        return jsonify([])
        
    with driver.session() as session:
        # Get top 10 orders with highest variance for this WC
        query = """
        MATCH (po:ProductionOrder)-[:WORKS_AT]->(wc:WorkCenter {id: $wc_id})
        OPTIONAL MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
        WITH po, sum(coalesce(abs(v.variance_amount), 0)) as total_var
        ORDER BY total_var DESC
        LIMIT 10
        RETURN po.id as id, po.product_cd as product, total_var as variance
        """
        result = session.run(query, wc_id=wc_id).data()
        return jsonify(result)

@app.route('/api/order-costs/<order_id>')
def order_costs(order_id):
    driver = get_db_connection()
    if not driver:
        return jsonify({'error': 'DB Connection Failed'})
    
    with driver.session() as session:
        # 1. Get Product Standard Cost (Planned Base)
        # 2. Get Actual Variances

        # Calculate Planned Cost: Qty * Standard Cost of Product
        planned_query = """
        MATCH (po:ProductionOrder {id: $order_id})-[:PRODUCES]->(p:Product)
        RETURN po.planned_qty * p.standard_cost as planned_total
        """
        planned_res = session.run(planned_query, order_id=order_id).single()
        planned_cost = planned_res['planned_total'] if planned_res else 0
        
        # Get Variances by Type
        var_query = """
        MATCH (po:ProductionOrder {id: $order_id})-[:HAS_VARIANCE]->(v:Variance)
        RETURN v.cost_element as type, sum(v.variance_amount) as amount
        """
        vars_res = session.run(var_query, order_id=order_id).data()
        
        variances = {row['type']: row['amount'] for row in vars_res}
        
        # Calculate Actual
        actual_cost = planned_cost + sum(variances.values())
        
        return jsonify({
            'order_id': order_id,
            'planned_cost': planned_cost,
            'variances': variances,
            'actual_cost': actual_cost
        })

@app.route('/api/graph-data')
def graph_data():
    node_id = request.args.get('node_id')
    driver = get_db_connection()
    if not driver:
        return jsonify({'nodes': [], 'links': []})
    
    with driver.session() as session:
        nodes = []
        links = []
        
        if node_id:
            # Expand specific node (1 hop)
            query = """
            MATCH (n) WHERE elementId(n) = $node_id OR n.id = $node_id
            MATCH (n)-[r]-(m)
            RETURN n, r, m LIMIT 50
            """
            result = session.run(query, node_id=node_id)
        else:
            # Default view: Top 5 High Variance Orders + their connections
            query = """
            MATCH (v:Variance)
            WHERE v.severity = 'HIGH'
            WITH v LIMIT 5
            MATCH (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)
            OPTIONAL MATCH (po)-[r]-(related)
            RETURN po as n, r, related as m
            LIMIT 50
            """
            result = session.run(query)
            
        # Parse result
        seen_nodes = set()

        def add_node(neo_node):
            if not neo_node: return
            # Using elementId as generic ID, fallback to 'id' property
            nid = neo_node.get('id') or neo_node.element_id
            if nid in seen_nodes: return
            
            labels = list(neo_node.labels)
            label = labels[0] if labels else 'Node'
            
            # Color logic
            colors = {
                'ProductionOrder': '#3b82f6',
                'Variance': '#ef4444',
                'WorkCenter': '#f59e0b',
                'Material': '#10b981',
                'Cause': '#8b5cf6',
                'Product': '#6366f1'
            }
            color = colors.get(label, '#94a3b8')
            
            # Name/Label logic
            name = neo_node.get('name') or neo_node.get('description') or neo_node.get('id') or label
            if label == 'Variance':
                name = f"{neo_node.get('variance_name')} ({neo_node.get('variance_amount')})"
            
            nodes.append({
                'id': nid,
                'label': name,
                'color': color,
                'group': label,
                'size': 10 if label == 'ProductionOrder' else 5
            })
            seen_nodes.add(nid)
            return nid

        for record in result:
            n = record['n']
            m = record['m']
            r = record['r']
            
            source = add_node(n)
            target = add_node(m)
            
            if source and target and r:
                links.append({
                    'source': source,
                    'target': target,
                    'label': type(r).__name__
                })

        return jsonify({'nodes': nodes, 'links': links})

if __name__ == '__main__':
    print("Starting Semiconductor Cost Variance Dashboard...")
    app.run(host='0.0.0.0', port=8000, debug=True)
