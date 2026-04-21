"""
English prompts for Risk Analysis
Used by the risk_analyzer module
"""

def get_risk_analysis_prompt(language='en'):
    """
    Get risk analysis prompt in specified language
    
    Args:
        language: Language code (en, fr, pt-br)
    
    Returns:
        str: Prompt template
    """
    prompts = {
        'en': """
Act as a **Senior Risk Management Specialist** (PMI-RMP, ISO 31000 certifications).

Critically analyze the text below, extracted from project documents.

**Your Mission:**
1. Identify **explicit** risks (directly mentioned)
2. Identify **implicit** risks ("weak signals" - contexts suggesting future problems)
3. Categorize each risk following standard project management frameworks

**For each identified risk, provide:**
- **Risk Description**: Clear and objective sentence describing the risk
- **Category**: Choose ONLY from: Technical, Managerial, External, Commercial, Human Resources
- **Probability**: High, Medium, or Low (based on tone and context of text)
- **Impact**: High, Medium, or Low (considering possible consequences for the project)
- **Strategy**: Mitigate, Accept, Transfer, or Avoid
- **Suggested Action**: Sentence with specific preventive or corrective measure

**IMPORTANT:**
- Return ONLY valid JSON, without markdown, without additional explanations
- Format: List of objects [{{}}, {{}}, ...]
- Do not include markdown code markers (```json or ```)
- If no clear risks found, return empty list []
- Be conservative: identify only truly relevant risks

**Text for Analysis:**
---
{{text}}
---
""",
        'fr': """
Agissez en tant que **Spécialiste Senior en Gestion des Risques** (certifications PMI-RMP, ISO 31000).

Analysez de manière critique le texte ci-dessous, extrait des documents de projet.

**Votre Mission :**
1. Identifier les risques **explicites** (mentionnés directement)
2. Identifier les risques **implicites** ("signaux faibles" - contextes suggérant des problèmes futurs)
3. Catégoriser chaque risque selon les cadres standard de gestion de projet

**Pour chaque risque identifié, fournissez :**
- **Description du Risque** : Phrase claire et objective décrivant le risque
- **Catégorie** : Choisissez UNIQUEMENT parmi : Technique, Managérial, Externe, Commercial, Ressources Humaines
- **Probabilité** : Haute, Moyenne ou Basse (basé sur le ton et le contexte du texte)
- **Impact** : Haut, Moyen ou Bas (considérant les conséquences possibles pour le projet)
- **Stratégie** : Atténuer, Accepter, Transférer ou Éviter
- **Action Suggérée** : Phrase avec mesure préventive ou corrective spécifique

**IMPORTANT :**
- Retournez UNIQUEMENT un JSON valide, sans markdown, sans explications supplémentaires
- Format : Liste d'objets [{{}}, {{}}, ...]
- N'incluez pas de marqueurs de code markdown (```json ou ```)
- Si aucun risque clair n'est trouvé, retournez une liste vide []
- Soyez conservateur : identifiez uniquement les risques réellement pertinents

**Texte pour Analyse :**
---
{{text}}
---
""",
        'pt-br': """
Atue como um **Especialista Sênior em Gestão de Riscos** (certificações PMI-RMP, ISO 31000).

Analise criticamente o texto abaixo, extraído de documentos de projeto.

**Sua Missão:**
1. Identificar riscos **explícitos** (mencionados diretamente)
2. Identificar riscos **implícitos** ("sinais fracos" - contextos que sugerem problemas futuros)
3. Categorizar cada risco seguindo frameworks padrão de gestão de projetos

**Para cada risco identificado, forneça:**
- **Descrição do Risco**: Frase clara e objetiva descrevendo o risco
- **Categoria**: Escolha APENAS entre: Técnico, Gerencial, Externo, Comercial, Recursos Humanos
- **Probabilidade**: Alta, Média ou Baixa (baseie-se no tom e contexto do texto)
- **Impacto**: Alto, Médio ou Baixo (considerando possíveis consequências para o projeto)
- **Estratégia**: Mitigar, Aceitar, Transferir ou Evitar
- **Ação Sugerida**: Frase com medida preventiva ou corretiva específica

**IMPORTANTE:**
- Retorne APENAS um JSON válido, sem markdown, sem explicações adicionais
- Formato: Lista de objetos [{{}}, {{}}, ...]
- Não inclua códigos markdown (```json ou ```)
- Se não encontrar riscos claros, retorne lista vazia []
- Seja conservador: identifique apenas riscos realmente relevantes

**Texto para Análise:**
---
{{text}}
---
"""
    }
    
    return prompts.get(language, prompts['en'])


def get_field_names(language='en'):
    """
    Get field names for risk analysis in specified language
    
    Args:
        language: Language code (en, fr, pt-br)
    
    Returns:
        dict: Field names mapping
    """
    field_names = {
        'en': {
            'description': 'Risk Description',
            'category': 'Category',
            'probability': 'Probability',
            'impact': 'Impact',
            'strategy': 'Strategy',
            'action': 'Suggested Action',
            'source': 'Source',
            'categories': {
                'technical': 'Technical',
                'managerial': 'Managerial',
                'external': 'External',
                'commercial': 'Commercial',
                'human_resources': 'Human Resources'
            },
            'probability_levels': {
                'high': 'High',
                'medium': 'Medium',
                'low': 'Low'
            },
            'impact_levels': {
                'high': 'High',
                'medium': 'Medium',
                'low': 'Low'
            },
            'strategies': {
                'mitigate': 'Mitigate',
                'accept': 'Accept',
                'transfer': 'Transfer',
                'avoid': 'Avoid'
            }
        },
        'fr': {
            'description': 'Description du Risque',
            'category': 'Catégorie',
            'probability': 'Probabilité',
            'impact': 'Impact',
            'strategy': 'Stratégie',
            'action': 'Action Suggérée',
            'source': 'Source',
            'categories': {
                'technical': 'Technique',
                'managerial': 'Managérial',
                'external': 'Externe',
                'commercial': 'Commercial',
                'human_resources': 'Ressources Humaines'
            },
            'probability_levels': {
                'high': 'Haute',
                'medium': 'Moyenne',
                'low': 'Basse'
            },
            'impact_levels': {
                'high': 'Haut',
                'medium': 'Moyen',
                'low': 'Bas'
            },
            'strategies': {
                'mitigate': 'Atténuer',
                'accept': 'Accepter',
                'transfer': 'Transférer',
                'avoid': 'Éviter'
            }
        },
        'pt-br': {
            'description': 'Descrição do Risco',
            'category': 'Categoria',
            'probability': 'Probabilidade',
            'impact': 'Impacto',
            'strategy': 'Estratégia',
            'action': 'Ação Sugerida',
            'source': 'Fonte',
            'categories': {
                'technical': 'Técnico',
                'managerial': 'Gerencial',
                'external': 'Externo',
                'commercial': 'Comercial',
                'human_resources': 'Recursos Humanos'
            },
            'probability_levels': {
                'high': 'Alta',
                'medium': 'Média',
                'low': 'Baixa'
            },
            'impact_levels': {
                'high': 'Alto',
                'medium': 'Médio',
                'low': 'Baixo'
            },
            'strategies': {
                'mitigate': 'Mitigar',
                'accept': 'Aceitar',
                'transfer': 'Transferir',
                'avoid': 'Evitar'
            }
        }
    }
    
    return field_names.get(language, field_names['en'])
