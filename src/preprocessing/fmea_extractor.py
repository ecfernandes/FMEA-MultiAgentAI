"""
FMEA Excel Extractor - Industry 5.0 Framework
Optimized extraction of FMEA data from Excel files for RAG-based AI analysis.

Purpose:
- Extract structured FMEA data preserving semantic relationships
- Format for efficient similarity search in Vector DB
- Maintain traceability to source documents (FMEA 5.0 transparency requirement)
- Support historical FMEA retrieval with confidence scoring
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
import re


class FMEAExtractor:
    """
    Intelligent FMEA Excel extractor for Industry 5.0 framework.
    
    Features:
    - Auto-detects FMEA columns (Failure Mode, Effect, Cause, Severity, etc.)
    - Structures each row as semantic document for RAG
    - Preserves metadata for traceability
    - Optimized for similarity search
    """
    
    # Common FMEA column patterns (multilingual support)
    FMEA_COLUMNS = {
        'item': ['item', 'component', 'part', 'peça', 'componente', 'pièce'],
        'function': ['function', 'função', 'fonction', 'funcao'],
        'failure_mode': ['failure mode', 'modo de falha', 'modo falha', 'mode de défaillance', 
                        'potential failure mode', 'failure'],
        'effect': ['effect', 'efeito', 'effet', 'consequence', 'consequência', 'consequencia',
                   'potential effect'],
        'severity': ['severity', 'severidade', 'sev', 's', 'gravité', 'gravidade'],
        'cause': ['cause', 'causa', 'potential cause', 'root cause'],
        'occurrence': ['occurrence', 'ocorrência', 'occ', 'o', 'frequência', 'frequencia'],
        'detection': ['detection', 'detecção', 'det', 'd', 'détection', 'deteccao'],
        'rpn': ['rpn', 'risk priority number', 'número de prioridade de risco', 'npr'],
        'action': ['action', 'ação', 'acao', 'recommended action', 'corrective action',
                   'prevention', 'prevenção', 'prevencao'],
        'responsibility': ['responsibility', 'responsável', 'responsavel', 'owner', 'responsible'],
        'status': ['status', 'état', 'estado'],
        'date': ['date', 'data', 'target date', 'completion date']
    }
    
    def __init__(self):
        self.column_mapping = {}
        
    def detect_fmea_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Auto-detect FMEA columns by matching patterns.
        
        Returns:
            Dict mapping standard FMEA fields to actual column names
        """
        mapping = {}
        df_columns_lower = {col: col.lower().strip() for col in df.columns}
        
        for field, patterns in self.FMEA_COLUMNS.items():
            for col_original, col_lower in df_columns_lower.items():
                for pattern in patterns:
                    if pattern in col_lower:
                        mapping[field] = col_original
                        break
                if field in mapping:
                    break
        
        self.column_mapping = mapping
        return mapping
    
    def extract_fmea_records(self, excel_file, filename: str) -> List[Dict]:
        """
        Extract FMEA records from Excel file with full structure preservation.
        
        Args:
            excel_file: File object or path to Excel file
            filename: Original filename for metadata
            
        Returns:
            List of FMEA records (dicts) ready for RAG ingestion
        """
        records = []
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                # Skip empty sheets
                if df.empty:
                    continue
                
                # Detect FMEA columns
                self.detect_fmea_columns(df)
                
                # Extract each row as a structured record
                for idx, row in df.iterrows():
                    record = self._build_fmea_record(row, sheet_name, filename, idx)
                    if record:  # Only add non-empty records
                        records.append(record)
        
        except Exception as e:
            raise Exception(f"Error extracting FMEA from {filename}: {str(e)}")
        
        return records
    
    def _build_fmea_record(self, row: pd.Series, sheet_name: str, 
                          filename: str, row_idx: int) -> Optional[Dict]:
        """
        Build a single FMEA record with all relevant fields and metadata.
        
        Structure optimized for:
        - Semantic similarity search (Failure Mode as primary key)
        - Historical context retrieval 
        - Traceability (source file, sheet, row number)
        - Confidence scoring (RPN, ratings available)
        """
        record = {
            # Source metadata (FMEA 5.0 traceability requirement)
            'source_file': filename,
            'sheet': sheet_name,
            'row_number': int(row_idx) + 2,  # Excel row (header=1, data starts at 2)
            
            # Core FMEA fields
            'item': self._safe_get(row, 'item'),
            'function': self._safe_get(row, 'function'),
            'failure_mode': self._safe_get(row, 'failure_mode'),
            'effect': self._safe_get(row, 'effect'),
            'cause': self._safe_get(row, 'cause'),
            
            # Risk ratings
            'severity': self._safe_get_numeric(row, 'severity'),
            'occurrence': self._safe_get_numeric(row, 'occurrence'),
            'detection': self._safe_get_numeric(row, 'detection'),
            'rpn': self._safe_get_numeric(row, 'rpn'),
            
            # Actions and status
            'action': self._safe_get(row, 'action'),
            'responsibility': self._safe_get(row, 'responsibility'),
            'status': self._safe_get(row, 'status'),
            'date': self._safe_get(row, 'date'),
        }
        
        # Only return if we have at least a failure mode
        if record['failure_mode']:
            return record
        return None
    
    def _safe_get(self, row: pd.Series, field: str) -> str:
        """Safely get text field value."""
        if field in self.column_mapping:
            col = self.column_mapping[field]
            value = row.get(col, '')
            if pd.notna(value):
                return str(value).strip()
        return ''
    
    def _safe_get_numeric(self, row: pd.Series, field: str) -> Optional[int]:
        """Safely get numeric field value."""
        if field in self.column_mapping:
            col = self.column_mapping[field]
            value = row.get(col)
            if pd.notna(value):
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    pass
        return None
    
    def format_for_rag(self, records: List[Dict]) -> str:
        """
        Format FMEA records as text optimized for RAG Vector DB ingestion.
        
        Each record becomes a semantic chunk that:
        - Can be retrieved by similarity (failure mode, effect, cause)
        - Maintains full context for AI analysis
        - Includes traceability metadata
        
        Returns:
            Formatted text ready for ChromaDB embedding
        """
        formatted_chunks = []
        
        for record in records:
            # Build semantic chunk with rich context
            chunk_parts = []
            
            # Title/identifier
            if record['item']:
                chunk_parts.append(f"COMPONENT: {record['item']}")
            
            # Core FMEA triad (most important for similarity search)
            if record['failure_mode']:
                chunk_parts.append(f"FAILURE MODE: {record['failure_mode']}")
            if record['effect']:
                chunk_parts.append(f"EFFECT: {record['effect']}")
            if record['cause']:
                chunk_parts.append(f"CAUSE: {record['cause']}")
            
            # Function/context
            if record['function']:
                chunk_parts.append(f"Function: {record['function']}")
            
            # Risk assessment
            risk_parts = []
            if record['severity']:
                risk_parts.append(f"Severity={record['severity']}")
            if record['occurrence']:
                risk_parts.append(f"Occurrence={record['occurrence']}")
            if record['detection']:
                risk_parts.append(f"Detection={record['detection']}")
            if record['rpn']:
                risk_parts.append(f"RPN={record['rpn']}")
            
            if risk_parts:
                chunk_parts.append(f"Risk Assessment: {', '.join(risk_parts)}")
            
            # Actions
            if record['action']:
                chunk_parts.append(f"Recommended Action: {record['action']}")
            
            # Metadata for traceability (FMEA 5.0 requirement)
            metadata = f"[Source: {record['source_file']} | Sheet: {record['sheet']} | Row: {record['row_number']}]"
            chunk_parts.append(metadata)
            
            # Combine into single semantic chunk
            chunk = '\n'.join(chunk_parts)
            formatted_chunks.append(chunk)
            formatted_chunks.append('')  # Blank line between records
        
        return '\n'.join(formatted_chunks)
    
    def get_structured_data(self, records: List[Dict]) -> pd.DataFrame:
        """
        Convert records back to structured DataFrame for analysis/export.
        
        Useful for:
        - Generating new FMEA Excel exports
        - Statistical analysis
        - Validation/quality checks
        """
        return pd.DataFrame(records)


# Convenience functions
def extract_fmea_from_excel(excel_file, filename: str) -> Tuple[str, List[Dict]]:
    """
    Quick extraction: returns both RAG-formatted text and structured records.
    
    Usage:
        rag_text, records = extract_fmea_from_excel(file, "FMEA_Window.xlsx")
        # rag_text -> ingest into ChromaDB
        # records -> keep for analysis/export
    """
    extractor = FMEAExtractor()
    records = extractor.extract_fmea_records(excel_file, filename)
    rag_text = extractor.format_for_rag(records)
    return rag_text, records


def quick_fmea_summary(records: List[Dict]) -> Dict:
    """
    Generate quick statistics about extracted FMEA data.
    """
    if not records:
        return {'total_records': 0}
    
    df = pd.DataFrame(records)
    
    summary = {
        'total_records': len(records),
        'unique_components': df['item'].nunique() if 'item' in df else 0,
        'unique_failure_modes': df['failure_mode'].nunique() if 'failure_mode' in df else 0,
        'avg_rpn': df['rpn'].mean() if 'rpn' in df and df['rpn'].notna().any() else None,
        'high_risk_count': len(df[df['rpn'] > 100]) if 'rpn' in df else 0,
        'sources': df['source_file'].unique().tolist() if 'source_file' in df else [],
    }
    
    return summary
