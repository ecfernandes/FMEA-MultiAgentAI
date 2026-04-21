"""
Ontology Builder for FMEA Component Hierarchy
Extracts and visualizes component relationships from FMEA data
"""

import json
import networkx as nx
import plotly.graph_objects as go
from typing import Dict, List, Tuple, Any
import pandas as pd


class FMEAOntologyBuilder:
    """
    Build component ontology from FMEA BOM structures.
    Creates hierarchical graphs showing System → Assembly → Component relationships.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.hierarchy_data = []
        self.product_info = {}
        
    def load_from_json(self, json_data: Dict) -> None:
        """
        Load FMEA data from JSON structure.
        
        Args:
            json_data: Dictionary containing products and bom_structures
        """
        # Store product metadata
        if 'products' in json_data:
            for product in json_data['products']:
                self.product_info[product['product_id']] = product
        # Extract BOM structures
        if 'bom_structures' in json_data:
            for bom in json_data['bom_structures']:
                self._parse_bom_structure(bom)
    
    def _parse_bom_structure(self, bom: Dict) -> None:
        """
        Parse a single BOM structure and add to graph.
        
        Args:
            bom: BOM structure dictionary with hierarchy information
        """
        product_id = bom.get('product_id')
        hierarchy = bom.get('structure_hierarchy', [])
        
        # Add root product node if exists
        if product_id in self.product_info:
            product = self.product_info[product_id]
            self.graph.add_node(
                product_id,
                name=product['product_name'],
                type='Product',
                level=0,
                details=product.get('description', ''),
                code=product.get('product_code', ''),
                revision=product.get('revision', '')
            )
        
        # Build hierarchy
        for item in hierarchy:
            item_id = item['item_id']
            parent_id = item.get('parent_id')
            
            # Add node with all metadata
            self.graph.add_node(
                item_id,
                name=item['item_name'],
                type=item['item_type'],
                level=item['level'],
                quantity=item.get('quantity', 1),
                supplier=item.get('supplier', ''),
                part_number=item.get('part_number', ''),
                material=item.get('material', ''),
                weight=item.get('weight_g', 0)
            )
            
            # Add edge from parent
            if parent_id:
                self.graph.add_edge(parent_id, item_id)
            elif product_id:
                # Connect to root product if no parent
                self.graph.add_edge(product_id, item_id)
    
    def get_hierarchy_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the ontology.
        
        Returns:
            Dictionary with counts and statistics
        """
        node_types = {}
        level_counts = {}
        
        for node, data in self.graph.nodes(data=True):
            # Count by type
            node_type = data.get('type', 'Unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
            
            # Count by level
            level = data.get('level', 0)
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': node_types,
            'level_distribution': level_counts,
            'max_depth': max(level_counts.keys()) if level_counts else 0
        }
    
    def create_plotly_tree(self, product_id: str = None) -> go.Figure:
        """
        Create interactive Plotly tree visualization.
        
        Args:
            product_id: Specific product to visualize (None = all)
        
        Returns:
            Plotly Figure object
        """
        if not self.graph.nodes():
            # Empty graph
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for visualization",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # Filter graph if specific product requested (CORRIGIDO - preserva atributos)
        if product_id and product_id in self.graph:
            # Get all descendants using DFS but preserve node attributes
            nodes_to_keep = list(nx.dfs_preorder_nodes(self.graph, product_id))
            subgraph = self.graph.subgraph(nodes_to_keep).copy()
        else:
            subgraph = self.graph.copy()
        
        # Calculate layout using hierarchy
        pos = self._calculate_hierarchical_layout(subgraph)
        
        # Create edges
        edge_trace = self._create_edge_trace(subgraph, pos)
        
        # Create nodes
        node_trace = self._create_node_trace(subgraph, pos)
        
        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(
                    text="FMEA Component Ontology - Hierarchical Structure",
                    font=dict(size=20, color='#fafafa')
                ),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=20, r=20, t=60),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='#0e1117',
                paper_bgcolor='#0e1117',
                font=dict(color='#fafafa'),
                height=600
            )
        )
        
        return fig
    
    def _calculate_hierarchical_layout(self, graph: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
        """
        Calculate hierarchical layout positions.
        
        Args:
            graph: NetworkX directed graph
        
        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        # Group nodes by level
        levels = {}
        for node, data in graph.nodes(data=True):
            level = data.get('level', 0)
            if level not in levels:
                levels[level] = []
            levels[level].append(node)
        
        # Calculate positions
        pos = {}
        max_level = max(levels.keys()) if levels else 0
        
        for level, nodes in levels.items():
            # Calculate Y position (top to bottom, inverted for proper tree view)
            y = 1.0 - (level / max(max_level, 1))
            num_nodes = len(nodes)
            
            # Calculate X positions (spread evenly)
            for i, node in enumerate(nodes):
                if num_nodes == 1:
                    x = 0.5  # Center single node
                else:
                    # Spread nodes evenly across X axis
                    x = 0.1 + (i / (num_nodes - 1)) * 0.8
                pos[node] = (x, y)
        
        return pos
    
    def _create_edge_trace(self, graph: nx.DiGraph, pos: Dict) -> go.Scatter:
        """
        Create Plotly trace for edges (connections between nodes).
        
        Args:
            graph: NetworkX graph
            pos: Dictionary of node positions
            
        Returns:
            Plotly Scatter trace for edges
        """
        edge_x = []
        edge_y = []
        
        for edge in graph.edges():
            if edge[0] in pos and edge[1] in pos:
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
        
        return go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888888'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        )
    
    def _create_node_trace(self, graph: nx.DiGraph, pos: Dict) -> go.Scatter:
        """
        Create Plotly trace for nodes with colors, sizes, and hover information.
        
        Args:
            graph: NetworkX graph
            pos: Dictionary of node positions
            
        Returns:
            Plotly Scatter trace for nodes
        """
        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_color = []
        node_size = []
        
        # Color mapping by type
        type_colors = {
            'Product': '#ff4b4b',      # Red
            'Assembly': '#1f77b4',     # Blue
            'Component': '#2ca02c',    # Green
            'Unknown': '#888888'       # Gray
        }
        
        for node, data in graph.nodes(data=True):
            if node not in pos:
                continue
                
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Node label (shortened for display)
            name = data.get('name', node)
            short_name = name if len(name) <= 20 else name[:17] + '...'
            node_text.append(short_name)
            
            # Hover information
            hover_info = f"<b>{name}</b><br>"
            hover_info += f"<b>Type:</b> {data.get('type', 'Unknown')}<br>"
            hover_info += f"<b>Level:</b> {data.get('level', 0)}<br>"
            
            if data.get('part_number'):
                hover_info += f"<b>P/N:</b> {data.get('part_number')}<br>"
            if data.get('supplier'):
                hover_info += f"<b>Supplier:</b> {data.get('supplier')}<br>"
            if data.get('quantity', 1) > 1:
                hover_info += f"<b>Qty:</b> {data.get('quantity')}<br>"
            if data.get('material'):
                hover_info += f"<b>Material:</b> {data.get('material')}<br>"
            if data.get('weight'):
                hover_info += f"<b>Weight:</b> {data.get('weight')}g<br>"
            
            node_hover.append(hover_info)
            
            # Node color by type
            node_type = data.get('type', 'Unknown')
            node_color.append(type_colors.get(node_type, '#888888'))
            
            # Node size by level (root larger, leaves smaller)
            if node_type == 'Product':
                size = 40
            elif node_type == 'Assembly':
                size = 30
            else:
                size = 20
            node_size.append(size)
        
        return go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="bottom center",
            textfont=dict(size=9, color='#fafafa', family='Arial'),
            hovertext=node_hover,
            hoverinfo='text',
            marker=dict(
                size=node_size,
                color=node_color,
                line=dict(width=2, color='#fafafa'),
                opacity=0.9
            ),
            showlegend=False
        )
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """
        Export ontology to pandas DataFrame.
        
        Returns:
            DataFrame with all nodes and their properties
        """
        if not self.graph.nodes():
            return pd.DataFrame()
            
        data = []
        for node, attrs in self.graph.nodes(data=True):
            row = {'node_id': node}
            row.update(attrs)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Reorder columns for better readability
        preferred_order = ['node_id', 'name', 'type', 'level', 'part_number', 
                          'supplier', 'quantity', 'material', 'weight']
        existing_cols = [col for col in preferred_order if col in df.columns]
        other_cols = [col for col in df.columns if col not in existing_cols]
        
        return df[existing_cols + other_cols]
    
    def find_component_path(self, component_id: str) -> List[str]:
        """
        Find path from root to component.
        
        Args:
            component_id: ID of target component
        
        Returns:
            List of node IDs from root to target
        """
        # Find root nodes (nodes with no predecessors)
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        
        for root in roots:
            if nx.has_path(self.graph, root, component_id):
                return nx.shortest_path(self.graph, root, component_id)
        
        return []
