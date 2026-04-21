"""
FMEA 5.0 - Intelligent FMEA Extractor (Redesigned)
Clean JSON extraction from Excel FMEA files.
No decorative text, just structured data ready for AI.
"""

import pandas as pd
import re
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime
from .fmea_schema import (
    FMEARecord, FMEADocument,
    clean_cell_value, validate_fmea_value
)


class FMEAExtractorV2:
    """
    Extract clean, structured JSON from FMEA Excel files.
    
    Philosophy:
    - Numbers as numbers (not strings)
    - No decorative headers
    - Clean cell values (whitespace removed, normalized)
    - Validate ranges (severity/occurrence/detection: 1-10)
    - JSON as primary format
    """
    
    # Multilingual column detection patterns
    COLUMN_PATTERNS = {
        'item': [
            'item', 'component', 'part', 'system', 'subsystem', 'element',
            'componente', 'peça', 'sistema', 'elemento',
            'pièce', 'composant', 'système', 'étape'
        ],
        'function': [
            'function', 'fonction', 'função', 'funcao'
        ],
        'failure_mode': [
            'failure mode', 'failure', 'failure type', 'potential failure', 'defect',
            'modo de falha', 'falha', 'defeito', 'defaillance',
            'mode de défaillance', 'défaillance potentielle'
        ],
        'effect': [
            'effect', 'failure effect', 'potential effect', 'consequence', 'impact',
            'efeito', 'consequência', 'impacto',
            'effet', 'conséquence'
        ],
        'cause': [
            'cause', 'potential cause', 'root cause', 'failure cause', 'origin',
            'causa', 'causa raiz', 'origem',
            'cause racine', 'origine'
        ],
        'severity': [
            'severity', 'sev', 's', 'severidade', 'gravidade', 'sévérité', 'grav'
        ],
        'occurrence': [
            'occurrence', 'occ', 'o', 'frequency', 'freq',
            'ocorrência', 'frequência', 'freq',
            'fréquence'
        ],
        'current_controls_prevention': [
            'current design controls - prevention',
            'current design controls prevention',
            'design controls - prevention',
            'controls - prevention',
            'controls prevention',
            'prevention controls',
            'controles de prevenção',
            'controles prevenção',
            'contrôles de prévention'
        ],
        'current_controls_detection': [
            'current design controls - detection',
            'current design controls detection',
            'design controls - detection',
            'controls - detection',
            'controls detection',
            'detection controls',
            'controles de detecção',
            'controles detecção',
            'contrôles de détection'
        ],
        'detection': [
            'detection', 'det', 'd', 'detectability', 'detect',
            'detecção', 'detectabilidade',
            'détection', 'détectabilité'
        ],
        'rpn': [
            'rpn', 'risk priority number', 'priority', 'risk priority',
            'npr', 'número de prioridade de risco', 'prioridade'
        ],
        'current_controls': [
            'current controls', 'controls', 'design controls',
            'controles atuais', 'controles',
            'contrôles actuels', 'prevention', 'prevenção',
            'prévention'
        ],
        'recommended_action': [
            'recommended action', 'action', 'corrective action',
            'ação recomendada', 'ação corretiva',
            'action recommandée', 'action corrective'
        ],
        'responsibility': [
            'responsibility', 'responsible', 'owner', 'assigned to',
            'responsável', 'responsabilidade',
            'responsabilité'
        ],
        'action_taken': [
            'action taken', 'actions completed', 'completion',
            'ação executada', 'ação realizada',
            'action prise'
        ],
        'status': [
            'status', 'state', 'estado', 'état'
        ],
        'target_date': [
            'target date', 'due date', 'deadline',
            'data prevista', 'prazo',
            'date cible', 'échéance'
        ],
        'completion_date': [
            'completion date', 'completed date', 'closed date',
            'data de conclusão', 'data de fechamento',
            'date d\'achèvement'
        ]
    }
    
    def __init__(self):
        """Initialize FMEA extractor."""
        pass
    
    def detect_fmea_columns(self, df: pd.DataFrame) -> Optional[Dict[str, str]]:
        """
        Detect FMEA columns by matching patterns.
        
        Args:
            df: DataFrame with potential FMEA data
            
        Returns:
            Dict mapping standard_name -> actual_column_name, or None if not FMEA
        """
        column_mapping = {}
        claimed_columns: set = set()
        df_columns_lower = {col: str(col).lower().strip() for col in df.columns}
        
        # Try to match each standard field
        for standard_name, patterns in self.COLUMN_PATTERNS.items():
            for actual_col, col_lower in df_columns_lower.items():
                if actual_col in claimed_columns:
                    continue  # skip columns already assigned to another field
                # Check if any pattern matches
                # For single-letter patterns, require exact match
                # For longer patterns, allow substring match
                for pattern in patterns:
                    if len(pattern) == 1:
                        # Single letter: exact match only (e.g., 's' must be entire column name)
                        if col_lower == pattern:
                            column_mapping[standard_name] = actual_col
                            claimed_columns.add(actual_col)
                            break
                    else:
                        # Multi-character: substring match
                        if pattern in col_lower:
                            column_mapping[standard_name] = actual_col
                            claimed_columns.add(actual_col)
                            break
                if standard_name in column_mapping:
                    break
        
        # Must have at least: item, failure_mode, effect, cause
        required = {'item', 'failure_mode', 'effect', 'cause'}
        detected = set(column_mapping.keys())
        
        if required.issubset(detected):
            return column_mapping
        else:
            return None
    
    def extract_fmea_document(
        self,
        file_path: str,
        filename: str,
        sheet_name: Optional[str] = None
    ) -> Optional[FMEADocument]:
        """
        Extract complete FMEA document from Excel file.
        
        Args:
            file_path: Path to Excel file or file object
            filename: Original filename for traceability
            sheet_name: Specific sheet to read (None = first sheet)
            
        Returns:
            FMEADocument with clean JSON structure, or None if not FMEA
        """
        try:
            # Read Excel - try different header configurations
            xl_file = pd.ExcelFile(file_path)
            
            if sheet_name:
                sheets_to_try = [sheet_name]
            else:
                sheets_to_try = xl_file.sheet_names
            
            for sheet in sheets_to_try:
                # Try different skiprows configurations (0 to 6 - flexible header detection)
                for skip in [0, 1, 2, 3, 4, 5, 6]:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet, skiprows=skip)
                        
                        # Skip if too few rows
                        if len(df) < 1:
                            continue
                        
                        # Try to detect FMEA columns
                        column_map = self.detect_fmea_columns(df)
                        
                        if column_map:
                            # Found valid FMEA structure!
                            sheet_name = sheet
                            break
                    except:
                        continue
                
                if column_map:
                    break
            else:
                # No valid FMEA structure found
                return None
            
            # Extract failures
            failures = []
            for idx, row in df.iterrows():
                failure = self._extract_record(row, column_map, filename, sheet_name, idx + 2)
                if failure:
                    failures.append(failure)
            
            if not failures:
                return None
            
            # Create document
            document = FMEADocument(
                failures=failures,
                source_file=filename,
                extraction_date=datetime.now().isoformat(),
                component=self._infer_component(filename),
                phase=self._infer_phase(filename)
            )
            
            return document
            
        except Exception as e:
            print(f"Error extracting FMEA from {filename}: {e}")
            return None
    
    def _extract_record(
        self,
        row: pd.Series,
        column_map: Dict[str, str],
        source_file: str,
        sheet_name: str,
        row_number: int
    ) -> Optional[FMEARecord]:
        """
        Extract single FMEA record from DataFrame row.
        Clean cells, normalize types, validate ranges.
        """
        # Extract and clean required fields
        component = clean_cell_value(row.get(column_map.get('item')), 'string')
        failure_mode = clean_cell_value(row.get(column_map.get('failure_mode')), 'string')
        effect = clean_cell_value(row.get(column_map.get('effect')), 'string')
        cause = clean_cell_value(row.get(column_map.get('cause')), 'string')
        
        # Skip row if missing required fields
        if not all([component, failure_mode, effect, cause]):
            return None
        
        # FILTER OUT HEADER ROWS that were mistakenly identified as data
        # Check if values look like column names (all uppercase, contain key terms)
        header_indicators = [
            # French
            'systeme', 'etape', 'mode de defaillance', 'defaillance potentielle',
            'effet', 'cause', 'gravite', 'frequence', 'detection',
            # English
            'item', 'component', 'failure mode', 'potential failure',
            'effect', 'cause', 'severity', 'occurrence', 'detection',
            # Portuguese
            'componente', 'modo de falha', 'efeito', 'causa', 
            'severidade', 'ocorrencia', 'deteccao'
        ]
        
        # If component or failure_mode is just a header term, skip
        component_lower = component.lower() if component else ''
        failure_lower = failure_mode.lower() if failure_mode else ''
        
        if any(indicator in component_lower for indicator in ['systeme', 'etape', 'item', 'component', 'componente']):
            if any(indicator in failure_lower for indicator in ['mode', 'failure', 'defaillance', 'falha']):
                return None  # This is a header row, not data
        
        # Extract and clean numeric fields
        severity = clean_cell_value(row.get(column_map.get('severity')), 'int')
        occurrence = clean_cell_value(row.get(column_map.get('occurrence')), 'int')
        detection = clean_cell_value(row.get(column_map.get('detection')), 'int')
        rpn = clean_cell_value(row.get(column_map.get('rpn')), 'int')
        
        # Validate numeric ranges
        if not validate_fmea_value(severity, 'severity'):
            severity = None
        if not validate_fmea_value(occurrence, 'occurrence'):
            occurrence = None
        if not validate_fmea_value(detection, 'detection'):
            detection = None
        if not validate_fmea_value(rpn, 'rpn'):
            rpn = None
        
        # Extract function separately (core field)
        function = clean_cell_value(row.get(column_map.get('function')), 'string')

        # Collect all non-core columns dynamically into extra_fields
        _core_cols = {'item', 'function', 'failure_mode', 'effect', 'cause',
                      'severity', 'occurrence', 'detection', 'rpn'}
        extra_fields: Dict[str, Any] = {}
        for std_key, actual_col in column_map.items():
            if std_key not in _core_cols:
                val = clean_cell_value(row.get(actual_col), 'string')
                if val:
                    extra_fields[std_key] = val

        # Create record
        record = FMEARecord(
            component=component,
            function=function,
            failure_mode=failure_mode,
            effect=effect,
            cause=cause,
            severity=severity,
            occurrence=occurrence,
            detection=detection,
            rpn=rpn,
            extra_fields=extra_fields,
            _source_file=source_file,
            _sheet_name=sheet_name,
            _row_number=row_number
        )
        
        return record
    
    def _infer_component(self, filename: str) -> Optional[str]:
        """Infer component name from filename."""
        # Pattern: FMEA_ComponentName_...
        match = re.search(r'FMEA[_\s]+([A-Za-z_]+)', filename)
        if match:
            component = match.group(1).replace('_', ' ')
            return component
        return None
    
    def _infer_phase(self, filename: str) -> Optional[str]:
        """Infer project phase from filename."""
        # Pattern: ...2025Q1, ...Phase1, ...RD, etc.
        if re.search(r'Q[1-4]', filename, re.IGNORECASE):
            return 'Production'
        elif re.search(r'prototype|proto', filename, re.IGNORECASE):
            return 'Prototype'
        elif re.search(r'design|concept', filename, re.IGNORECASE):
            return 'Design'
        return None


# Convenience functions
def extract_fmea_from_excel(file_path, filename: str) -> Tuple[Optional[str], Optional[FMEADocument]]:
    """
    Extract FMEA from Excel file.
    
    Returns:
        Tuple: (rag_text, fmea_document)
        - rag_text: Clean minimal text for embeddings (or None)
        - fmea_document: Structured FMEADocument (or None)
    """
    extractor = FMEAExtractorV2()
    document = extractor.extract_fmea_document(file_path, filename)
    
    if document:
        rag_text = document.to_rag_text()
        return rag_text, document
    else:
        return None, None


def quick_json_summary(document: FMEADocument) -> str:
    """Generate quick JSON summary for verification."""
    stats = document.get_statistics()
    return f"""FMEA Document Summary:
- Total Failures: {stats['total_failures']}
- Unique Components: {stats['components']}
- Average RPN: {stats['avg_rpn']:.1f if stats['avg_rpn'] else 'N/A'}
- Max RPN: {stats['max_rpn'] if stats['max_rpn'] else 'N/A'}
- High Risk (RPN>=100): {stats['high_risk_count']}"""
