"""Quick test script for FMEA extraction"""
from src.preprocessing.fmea_extractor_v2 import FMEAExtractorV2
import os

# List FMEA files
files = [f for f in os.listdir('data') if f.startswith('FMEA_Window')]
print(f"✓ Arquivos FMEA encontrados: {len(files)}")

if files:
    # Test extraction on first file
    test_file = os.path.join('data', files[0])
    print(f"\n✓ Testando extração: {files[0]}")
    
    extractor = FMEAExtractorV2()
    doc = extractor.extract_fmea_document(test_file, files[0])
    
    if doc:
        print(f"✓ Extração bem-sucedida!")
        print(f"  - Total de registros: {len(doc.records)}")
        print(f"  - Componente: {doc.component}")
        print(f"  - Fase: {doc.phase}")
        
        # Show first record
        if doc.records:
            print(f"\n✓ Primeiro registro:")
            first = doc.records[0]
            print(f"  - Item: {first.item}")
            print(f"  - Failure Mode: {first.failure_mode}")
            print(f"  - Severity: {first.severity} (tipo: {type(first.severity).__name__})")
            print(f"  - RPN: {first.rpn} (tipo: {type(first.rpn).__name__})")
        
        # Test JSON export
        json_str = doc.to_json()
        print(f"\n✓ JSON gerado: {len(json_str)} caracteres")
        
        # Test RAG text
        rag_text = doc.to_rag_text()
        print(f"✓ RAG text gerado: {len(rag_text)} caracteres")
        print(f"\n✓ Preview RAG text (primeiros 200 chars):")
        print(rag_text[:200])
        
    else:
        print("✗ Falha na extração - arquivo não é FMEA válido")
else:
    print("✗ Nenhum arquivo FMEA encontrado para teste")
