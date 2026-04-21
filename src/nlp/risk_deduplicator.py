"""
Module to detect and group duplicate/similar risks.
Overlap analysis across multiple files.
"""

from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer, util
import numpy as np


class RiskDeduplicator:
    """
    Detects similar/duplicate risks using semantic embeddings.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the deduplicator.
        
        Args:
            model_name: Sentence Transformer model for embeddings.
        """
        self.model = SentenceTransformer(model_name)
    
    
    def analyze_overlap(self, risks: List[Dict], similarity_threshold: float = 0.75) -> Dict:
        """
        Analyze overlap among identified risks.
        
        Args:
            risks: List of risks (each one with risk description and source).
            similarity_threshold: Similarity threshold (0-1).
        
        Returns:
            Dict with risk statistics and groups.
        """
        if len(risks) < 2:
            return {
                'total_risks': len(risks),
                'unique_risks': len(risks),
                'recurring_risks': 0,
                'groups': []
            }
        
        # Extract descriptions
        descriptions = [r.get('Risk Description', r.get('Descrição do Risco', '')) for r in risks]
        
        # Generate embeddings
        embeddings = self.model.encode(descriptions, convert_to_tensor=True)
        
        # Compute similarity matrix
        similarities = util.cos_sim(embeddings, embeddings).cpu().numpy()
        
        # Group similar risks
        groups = []
        processed = set()
        
        for i in range(len(risks)):
            if i in processed:
                continue
            
            # Find similar risks
            similar_indices = []
            for j in range(len(risks)):
                if i != j and similarities[i][j] >= similarity_threshold:
                    similar_indices.append(j)
            
            if similar_indices:
                # Recurring risk
                group_indices = [i] + similar_indices
                groups.append({
                    'type': 'recurring',
                    'indices': group_indices,
                    'count': len(group_indices),
                    'risks': [risks[idx] for idx in group_indices],
                    'similarity_avg': float(np.mean([similarities[i][j] for j in similar_indices]))
                })
                processed.update(group_indices)
            else:
                # Unique risk
                groups.append({
                    'type': 'unique',
                    'indices': [i],
                    'count': 1,
                    'risks': [risks[i]],
                    'similarity_avg': 1.0
                })
                processed.add(i)
        
        # Compute statistics
        recurring_groups = [g for g in groups if g['type'] == 'recurring']
        unique_groups = [g for g in groups if g['type'] == 'unique']
        
        return {
            'total_risks': len(risks),
            'unique_risks': len(unique_groups),
            'recurring_risks': len(recurring_groups),
            'recurring_instances': sum([g['count'] for g in recurring_groups]),
            'groups': groups
        }
    
    
    def format_overlap_report(self, analysis_result: Dict) -> str:
        """
        Format overlap analysis into readable text.
        
        Args:
            analysis_result: Result from analyze_overlap().
        
        Returns:
            Formatted string for display.
        """
        if analysis_result['recurring_risks'] == 0:
            return "All identified risks are unique (no duplicates detected)."
        
        report_parts = [
            "OVERLAP ANALYSIS ACROSS FILES\n",
            f"Total risks: {analysis_result['total_risks']}",
            f"  - {analysis_result['unique_risks']} unique risks",
            f"  - {analysis_result['recurring_risks']} recurring themes "
            f"({analysis_result['recurring_instances']} occurrences)\n"
        ]
        
        # List recurring risks
        recurring_groups = [g for g in analysis_result['groups'] if g['type'] == 'recurring']
        
        if recurring_groups:
            report_parts.append("\nRECURRING THEMES (appear in multiple contexts):\n")
            
            for i, group in enumerate(recurring_groups, 1):
                risk_sample = group['risks'][0]
                desc = risk_sample.get('Risk Description', risk_sample.get('Descrição do Risco', 'N/A'))[:100]
                category = risk_sample.get('Category', risk_sample.get('Categoria', 'N/A'))
                sources = set([r.get('Source', r.get('Fonte', 'Unknown')) for r in group['risks']])
                
                report_parts.append(f"\n{i}. [{category}] {desc}...")
                report_parts.append(f"   Mentioned in: {', '.join(sources)}")
                report_parts.append(f"   Recurrence suggests a persistent issue - ATTENTION!")
        
        report_parts.append(
            "\n\nInterpretation: Risks that appear in multiple documents "
            "may indicate systemic problems that require immediate attention."
        )
        
        return "\n".join(report_parts)
