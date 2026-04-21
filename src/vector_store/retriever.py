"""
Semantic Retriever - Semantic Search System.
Integrates ChromaDB + Embeddings to retrieve relevant historical context.
Supports automatic language detection (PT, FR, EN).
"""

from typing import List, Dict, Optional
from langdetect import detect, LangDetectException
from .chroma_manager import ChromaManager
from .embeddings import EmbeddingGenerator
import json
import numpy as np


class SemanticRetriever:
    """Retrieves similar documents using vector semantic search."""
    
    def __init__(
        self,
        persist_directory: str = "./data/vector_store",
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """
        Initialize the semantic search system.
        
        Args:
            persist_directory: ChromaDB persistence directory.
            embedding_model: Model used for embedding generation.
                            Default: paraphrase-multilingual-MiniLM-L12-v2
                            Supports PT, FR, EN and 50+ languages.
        """
        self.chroma_manager = ChromaManager(persist_directory)
        self.embedding_generator = EmbeddingGenerator(embedding_model)
    
    def _detect_language(self, text: str) -> str:
        """
        Detect text language automatically.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Language code (pt, fr, en, etc.) or 'unknown'.
        """
        try:
            detected = detect(text)
            # Normalize language codes
            if detected.startswith('pt'):
                return 'pt'
            elif detected.startswith('fr'):
                return 'fr'
            elif detected.startswith('en'):
                return 'en'
            return detected
        except (LangDetectException, Exception):
            return 'unknown'
        
    def add_analysis(
        self,
        document_text: str,
        risks_identified: List[Dict],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a full analysis to the vector store.
        
        Args:
            document_text: Full text of analyzed document.
            risks_identified: List of identified risks (analysis output).
            metadata: Additional metadata (project name, date, etc.).
            
        Returns:
            Stored document ID.
        """
        # Generate document embedding
        embedding = self.embedding_generator.encode_text(document_text)
        
        # Detect language automatically
        detected_language = self._detect_language(document_text)
        
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata['language'] = detected_language  # Store detected language
        full_metadata['num_risks'] = len(risks_identified)
        full_metadata['risks_summary'] = json.dumps(risks_identified, ensure_ascii=False)
        
        # Extract risk categories
        categories = [risk.get('Category', risk.get('Categoria', 'Not specified')) for risk in risks_identified]
        full_metadata['risk_categories'] = json.dumps(list(set(categories)))
        
        # Store in ChromaDB
        doc_id = self.chroma_manager.add_document(
            document_text=document_text,
            embedding=embedding,
            metadata=full_metadata
        )
        
        return doc_id
    
    def add_historical_fmea(
        self,
        product_name: str,
        failure_modes_df,
        file_name: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add historical FMEA data from parsed Excel/JSON to vector store.
        Each failure mode becomes a searchable document.
        
        Args:
            product_name: Product/system name
            failure_modes_df: Pandas DataFrame with parsed FMEA data
            file_name: Original file name
            metadata: Additional metadata (upload date, analyst, etc.)
            
        Returns:
            Dictionary with storage statistics
        """
        from datetime import datetime
        
        stored_count = 0
        failed_count = 0
        doc_ids = []
        
        # Base metadata
        base_metadata = metadata or {}
        base_metadata['product_name'] = product_name
        base_metadata['source_file'] = file_name
        base_metadata['upload_date'] = datetime.now().isoformat()
        base_metadata['document_type'] = 'historical_fmea'
        
        # Process each failure mode
        for idx, row in failure_modes_df.iterrows():
            try:
                # Build searchable text document from failure mode
                doc_parts = []
                
                # Core FMEA fields
                if 'failure_mode' in row and row['failure_mode']:
                    doc_parts.append(f"Failure Mode: {row['failure_mode']}")
                
                if 'failure_cause' in row and row['failure_cause']:
                    doc_parts.append(f"Potential Cause: {row['failure_cause']}")
                
                if 'failure_effect' in row and row['failure_effect']:
                    doc_parts.append(f"Potential Effect: {row['failure_effect']}")
                
                if 'current_controls' in row and row['current_controls']:
                    doc_parts.append(f"Current Controls: {row['current_controls']}")
                
                if 'recommended_action' in row and row['recommended_action']:
                    doc_parts.append(f"Recommended Action: {row['recommended_action']}")
                
                # Skip if no meaningful content
                if not doc_parts:
                    failed_count += 1
                    continue
                
                # Combine into searchable document
                document_text = "\n".join(doc_parts)
                
                # Generate embedding
                embedding = self.embedding_generator.encode_text(document_text)
                
                # Detect language
                detected_language = self._detect_language(document_text)
                
                # Prepare failure mode metadata
                fm_metadata = base_metadata.copy()
                fm_metadata['language'] = detected_language
                fm_metadata['failure_mode'] = str(row.get('failure_mode', ''))[:500]
                
                # Risk ratings
                if 'severity' in row:
                    fm_metadata['severity'] = int(row['severity']) if row['severity'] is not None else None
                if 'occurrence' in row:
                    fm_metadata['occurrence'] = int(row['occurrence']) if row['occurrence'] is not None else None
                if 'detection' in row:
                    fm_metadata['detection'] = int(row['detection']) if row['detection'] is not None else None
                if 'rpn' in row:
                    fm_metadata['rpn'] = int(row['rpn']) if row['rpn'] is not None else None
                
                # Additional fields
                if 'responsibility' in row:
                    fm_metadata['responsibility'] = str(row.get('responsibility', ''))[:200]
                if 'status' in row:
                    fm_metadata['status'] = str(row.get('status', ''))[:100]
                
                # Store in ChromaDB
                doc_id = self.chroma_manager.add_document(
                    document_text=document_text,
                    embedding=embedding,
                    metadata=fm_metadata
                )
                
                doc_ids.append(doc_id)
                stored_count += 1
                
            except Exception as e:
                print(f"Error storing failure mode at row {idx}: {e}")
                failed_count += 1
                continue
        
        return {
            'stored_count': stored_count,
            'failed_count': failed_count,
            'doc_ids': doc_ids,
            'product_name': product_name
        }
    
    def find_similar_cases(
        self,
        query_text: str,
        n_results: int = 3,
        similarity_threshold: float = 0.75,
        filter_language: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar historical cases.
        
        Args:
            query_text: Query text used for similarity search.
            n_results: Maximum number of results.
            similarity_threshold: Minimum similarity threshold (0-1).
            filter_language: Filter by language (pt, fr, en) or None for all.
            
        Returns:
            List of similar cases found.
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.encode_text(query_text)
        
        # Search in ChromaDB
        results = self.chroma_manager.query_similar(
            query_embedding=query_embedding,
            n_results=n_results
        )
        
        # Process results
        similar_cases = []
        
        if results and results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                # Compute similarity (ChromaDB returns distance, not similarity)
                # Convert distance to similarity: sim = 1 / (1 + distance)
                distance = results['distances'][0][i]
                similarity = 1 / (1 + distance)
                
                # Filter by threshold
                if similarity >= similarity_threshold:
                    metadata = results['metadatas'][0][i]
                    
                    # Filter by language if specified
                    if filter_language:
                        doc_language = metadata.get('language', 'unknown')
                        if doc_language != filter_language:
                            continue  # Skip this document
                    
                    case = {
                        'document_text': results['documents'][0][i],
                        'metadata': metadata,
                        'similarity': similarity,
                        'doc_id': results['ids'][0][i]
                    }
                    
                    # Parse historical risks
                    if 'risks_summary' in case['metadata']:
                        try:
                            case['historical_risks'] = json.loads(case['metadata']['risks_summary'])
                        except:
                            case['historical_risks'] = []
                    
                    similar_cases.append(case)
        
        # PRIORITIZE analyses with complete feedback
        # Complete feedback > Partial feedback > No feedback
        similar_cases.sort(key=lambda x: (
            x['metadata'].get('feedback_complete', False),  # Complete feedback first
            x['metadata'].get('has_feedback', False),       # Then any feedback
            x['similarity']                                 # Finally, similarity
        ), reverse=True)
        
        return similar_cases
    
    def build_context_prompt(
        self,
        current_document: str,
        n_similar: int = 2
    ) -> str:
        """
        Build enriched prompt with historical context - IMPROVED VERSION.
        
        Args:
            current_document: Current document being analyzed.
            n_similar: Number of similar cases to include.
            
        Returns:
            Formatted string with historical context.
        """
        similar_cases = self.find_similar_cases(current_document, n_results=n_similar + 2, similarity_threshold=0.75)
        
        # Filter out cases that are the same document (similarity >= 99%)
        similar_cases = [case for case in similar_cases if case['similarity'] < 0.99]
        
        # Limit to requested number after filtering
        similar_cases = similar_cases[:n_similar]
        
        if not similar_cases:
            return ""
        
        # Clearer header
        context_parts = [
            "LESSONS LEARNED (similar previous analyses):\n",
            f"Found {len(similar_cases)} case(s) in history for reference.\n",
            "IMPORTANT: Use these lessons as INSPIRATION, not as absolute rules. Also identify UNIQUE risks in this document.\n"
        ]
        
        for i, case in enumerate(similar_cases, 1):
            similarity_pct = case['similarity'] * 100
            
            # Extract metadata
            metadata = case.get('metadata', {})
            doc_date = metadata.get('analysis_date', 'Unknown date')
            # Format date if it's in ISO format
            if 'T' in doc_date:
                doc_date = doc_date.split('T')[0]  # Keep only date (YYYY-MM-DD)
                # Convert to DD/MM/YYYY
                try:
                    parts = doc_date.split('-')
                    doc_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                except:
                    pass
            
            files_analyzed = metadata.get('files_analyzed', 'Unidentified file')
            doc_id_short = case['doc_id'][:8]
            doc_preview = case.get('document_text', '')[:300]  # Preview of first 300 characters
            
            # Check simplified feedback
            has_feedback = metadata.get('has_feedback', False)
            feedback_complete = metadata.get('feedback_complete', False)
            
            # Improved descriptive header
            feedback_info = ""
            if feedback_complete:
                feedback_info = f"\n  ✅ USER VALIDATED (Complete feedback available)"
            elif has_feedback:
                feedback_info = f"\n  ⚠️ PARTIAL FEEDBACK (Some risks validated)"
            
            context_parts.append(
                f"\n{'=' * 60}\n"
                f"HISTORICAL CASE #{i}\n"
                f"  - File(s): {files_analyzed}\n"
                f"  - Analyzed on: {doc_date}\n"
                f"  - Similarity: {similarity_pct:.1f}%\n"
                f"  - ID: {doc_id_short}{feedback_info}\n"
                f"{'=' * 60}"
            )
            
            # Historical document preview
            if doc_preview:
                context_parts.append(f"\nDocument preview:")
                context_parts.append(f'"{doc_preview}..."')
            
            # Historical risks with simplified feedback
            if 'historical_risks' in case and case['historical_risks']:
                context_parts.append(f"\nRisks identified in that analysis:")
                
                # If feedback exists, load it
                risk_feedback_map = {}
                if has_feedback and 'risk_feedback' in metadata:
                    try:
                        risk_feedback_map = json.loads(metadata['risk_feedback'])
                    except:
                        pass
                
                for idx, risk in enumerate(case['historical_risks'][:3], 1):
                    category = risk.get('Category', risk.get('Categoria', 'N/A'))
                    desc = risk.get('Risk Description', risk.get('Descrição do Risco', 'N/A'))[:100]
                    action = risk.get('Suggested Action', risk.get('Ação Sugerida', 'N/A'))[:120]
                    prob = risk.get('Probability', risk.get('Probabilidade', 'N/A'))
                    impact = risk.get('Impact', risk.get('Impacto', 'N/A'))
                    
                    context_parts.append(f"\n  {idx}. [{category}] {desc}...")
                    context_parts.append(f"     Probability: {prob} | Impact: {impact}")
                    context_parts.append(f"     Applied action: {action}")
                    
                    # Add simplified feedback if available
                    feedback_item = risk_feedback_map.get(str(idx - 1), {})
                    if isinstance(feedback_item, dict):
                        feedback_value = feedback_item.get('worked')
                        if feedback_value == 'Yes':
                            context_parts.append(f"     ✅ USER FEEDBACK: This action WORKED! Use similar approach for this type of risk.")
                        elif feedback_value == 'No':
                            context_parts.append(f"     ❌ USER FEEDBACK: This action DID NOT WORK! Try a different strategy.")
                            # If user suggested an alternative action
                            alternative = feedback_item.get('alternative_action', '').strip()
                            if alternative:
                                context_parts.append(f"     💡 USER SUGGESTS: {alternative}")
                    elif feedback_item == 'Yes':
                        # Backward compatibility with old format (string)
                        context_parts.append(f"     ✅ USER FEEDBACK: This action WORKED! Use similar approach for this type of risk.")
                    elif feedback_item == 'No':
                        context_parts.append(f"     ❌ USER FEEDBACK: This action DID NOT WORK! Try a different strategy.")
                    elif has_feedback:
                        context_parts.append(f"     ⭕ No feedback provided for this risk")
        
        context_parts.append(
            "\n\nUse these lessons as REFERENCE to enrich your suggestions, "
            "but also identify NEW and SPECIFIC risks for the current document.\n"
        )
        
        return "\n".join(context_parts)
    
    def get_statistics(self) -> Dict:
        """Return statistics of stored history."""
        total_docs = self.chroma_manager.count_documents()
        
        return {
            'total_documents': total_docs,
            'embedding_model': self.embedding_generator.model_name,
            'embedding_dimension': self.embedding_generator.get_model_info()['embedding_dimension']
        }
    
    def find_similar_risks(
        self,
        risk_description: str,
        similarity_threshold: float = 0.70,
        max_results: int = 10,
        exclude_doc_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar risks in analysis history using semantic search.
        
        Args:
            risk_description: Risk description to compare.
            similarity_threshold: Minimum similarity threshold (0-1).
            max_results: Maximum number of analyses to inspect.
            
        Returns:
            List of dicts with:
            {
                'analysis_number': int,  # Analysis number in history
                'analysis_date': str,    # Analysis date
                'doc_id': str,           # Document ID
                'similar_risks': [       # List of similar risks in this analysis
                    {
                        'risk_description': str,
                        'category': str,
                        'probability': str,
                        'impact': str,
                        'strategy': str,
                        'action': str,
                        'similarity': float,  # Similarity score
                        'feedback': dict or None  # User feedback if available
                    }
                ]
            }
        """
        # Generate embedding for current risk
        risk_embedding = self.embedding_generator.encode_text(risk_description)
        
        # Search similar analyses
        results = self.chroma_manager.query_similar(
            query_embedding=risk_embedding,
            n_results=max_results
        )
        
        similar_analyses = []
        
        if results and results['documents'] and len(results['documents'][0]) > 0:
            # Get all documents for correct numbering
            all_docs = self.chroma_manager.get_all_documents()
            all_ids = all_docs['ids'] if all_docs else []
            
            for i in range(len(results['documents'][0])):
                doc_id = results['ids'][0][i]
                
                # Ignore current analysis (no sense comparing to itself)
                if exclude_doc_id and doc_id == exclude_doc_id:
                    continue
                
                metadata = results['metadatas'][0][i]
                
                # Find analysis number in history
                try:
                    analysis_number = all_ids.index(doc_id) + 1
                except ValueError:
                    analysis_number = i + 1
                
                # Process stored risks in this analysis
                if 'risks_summary' in metadata:
                    try:
                        risks_in_analysis = json.loads(metadata['risks_summary'])
                        
                        # Load feedback if available
                        risk_feedback_map = {}
                        if 'risk_feedback' in metadata:
                            try:
                                risk_feedback_map = json.loads(metadata['risk_feedback'])
                            except:
                                pass
                        
                        # Compare current risk with each risk in this analysis
                        similar_risks_in_this_analysis = []
                        
                        # OPTIMIZATION: Limit to first 5 risks per historical analysis
                        # This avoids processing unnecessary hundreds of risks
                        for risk_idx, historical_risk in enumerate(risks_in_analysis[:5]):
                            # Get historical risk description
                            historical_desc = historical_risk.get('Risk Description', '') or \
                                            historical_risk.get('Descrição do Risco', '')
                            
                            if not historical_desc:
                                continue
                            
                            # Compute similarity between current and historical risk
                            historical_embedding = self.embedding_generator.encode_text(historical_desc)
                            
                            # Cosine similarity
                            import numpy as np
                            similarity = float(np.dot(risk_embedding, historical_embedding) / 
                                             (np.linalg.norm(risk_embedding) * np.linalg.norm(historical_embedding)))
                            
                            # If above threshold, add to results
                            if similarity >= similarity_threshold:
                                # Extract feedback if available
                                feedback = None
                                if str(risk_idx) in risk_feedback_map:
                                    feedback = risk_feedback_map[str(risk_idx)]
                                
                                similar_risks_in_this_analysis.append({
                                    'risk_description': historical_desc,
                                    'category': historical_risk.get('Category', historical_risk.get('Categoria', 'N/A')),
                                    'probability': historical_risk.get('Probability', historical_risk.get('Probabilidade', 'N/A')),
                                    'impact': historical_risk.get('Impact', historical_risk.get('Impacto', 'N/A')),
                                    'strategy': historical_risk.get('Strategy', historical_risk.get('Estratégia', 'N/A')),
                                    'action': historical_risk.get('Suggested Action', historical_risk.get('Ação Sugerida', 'N/A')),
                                    'similarity': similarity,
                                    'feedback': feedback
                                })
                            
                            # OPTIMIZATION: Early stopping when 3 similar risks are found
                            if len(similar_risks_in_this_analysis) >= 3:
                                break
                        
                        # If similar risks were found, add this analysis to results
                        if similar_risks_in_this_analysis:
                            # Sort by similarity
                            similar_risks_in_this_analysis.sort(key=lambda x: x['similarity'], reverse=True)
                            
                            analysis_date = metadata.get('analysis_date', metadata.get('timestamp', 'Unknown'))
                            if 'T' in analysis_date:
                                analysis_date = analysis_date.split('T')[0]
                            
                            similar_analyses.append({
                                'analysis_number': analysis_number,
                                'analysis_date': analysis_date,
                                'doc_id': doc_id,
                                'file_name': metadata.get('files_analyzed', 'Unknown'),
                                'similar_risks': similar_risks_in_this_analysis
                            })
                    
                    except Exception as e:
                        print(f"Error processing risks for doc {doc_id}: {e}")
                        continue
        
        # Sort by analysis number (most recent first)
        similar_analyses.sort(key=lambda x: x['analysis_number'], reverse=True)
        
        return similar_analyses
    
    def delete_document(self, doc_id: str):
        """Delete one specific document from history."""
        return self.chroma_manager.delete_document(doc_id)
    
    def clear_history(self):
        """Clear the entire history (use with caution!)."""
        return self.chroma_manager.reset_collection()
    
    def get_available_products(self) -> List[Dict]:
        """
        Get list of unique products available in the vector database.
        
        Returns:
            List of products with metadata (name, num_fmeas, last_update, etc.)
        """
        try:
            collection = self.chroma_manager.get_or_create_collection()
            
            # Get all metadata
            all_data = collection.get(
                include=['metadatas']
            )
            
            if not all_data or not all_data['metadatas']:
                return []
            
            # Extract unique products
            products_dict = {}
            
            for metadata in all_data['metadatas']:
                product_name = metadata.get('product_name')
                
                if not product_name:
                    continue
                
                if product_name not in products_dict:
                    products_dict[product_name] = {
                        'product_name': product_name,
                        'fmea_count': 0,
                        'source_files': set(),
                        'last_update': metadata.get('upload_date', ''),
                        'languages': set(),
                        'avg_severity': [],
                        'avg_rpn': []
                    }
                
                # Accumulate statistics
                products_dict[product_name]['fmea_count'] += 1
                
                if 'source_file' in metadata:
                    products_dict[product_name]['source_files'].add(metadata['source_file'])
                
                if 'language' in metadata:
                    products_dict[product_name]['languages'].add(metadata['language'])
                
                if 'severity' in metadata and metadata['severity']:
                    try:
                        products_dict[product_name]['avg_severity'].append(int(metadata['severity']))
                    except:
                        pass
                
                if 'rpn' in metadata and metadata['rpn']:
                    try:
                        products_dict[product_name]['avg_rpn'].append(int(metadata['rpn']))
                    except:
                        pass
                
                # Track most recent update
                upload_date = metadata.get('upload_date', '')
                if upload_date > products_dict[product_name]['last_update']:
                    products_dict[product_name]['last_update'] = upload_date
            
            # Convert to list and calculate averages
            products_list = []
            for product_name, data in products_dict.items():
                product_info = {
                    'product_name': product_name,
                    'display_name': f"{product_name} ({data['fmea_count']} FMEAs)",
                    'fmea_count': data['fmea_count'],
                    'source_files': ', '.join(sorted(data['source_files']))[:200],
                    'last_update': data['last_update'][:10] if data['last_update'] else 'Unknown',
                    'languages': ', '.join(sorted(data['languages'])),
                    'status': 'Active'
                }
                
                # Calculate averages
                if data['avg_severity']:
                    product_info['avg_severity'] = round(sum(data['avg_severity']) / len(data['avg_severity']), 1)
                else:
                    product_info['avg_severity'] = None
                
                if data['avg_rpn']:
                    product_info['avg_rpn'] = round(sum(data['avg_rpn']) / len(data['avg_rpn']), 1)
                else:
                    product_info['avg_rpn'] = None
                
                products_list.append(product_info)
            
            # Sort by most recent update
            products_list.sort(key=lambda x: x['last_update'], reverse=True)
            
            return products_list
            
        except Exception as e:
            print(f"Error getting products from Vector DB: {e}")
            return []
