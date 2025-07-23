# 07_query - Danish Construction Query Processing

## Overview

The **07_query** step implements Danish-focused query processing for the Construction RAG pipeline. It generates and tests multiple query variations to optimize search performance for Danish construction documents.

## Features

### 🇩🇰 Danish Query Variations
- **Semantic Expansion**: Generate alternative Danish technical terminology
- **HyDE Documents**: Create hypothetical Danish document excerpts
- **Formal Variations**: Professional, official construction language
- **Informal Variations**: Casual contractor/builder language

### 🏷️ Content Categorization
- **quantities** (mængder, numre, målinger, dimensioner)
- **requirements** (specifikationer, standarder, krav, regler)
- **procedures** (processer, trin, metoder, instruktioner)
- **materials** (materialer, komponenter, produkter, udstyr)
- **timeline** (deadlines, tidsplaner, varighed, faser)

### 📊 Performance Testing
- Tests each variation **with and without** content categorization
- Uses validated Danish queries from `06_store` step
- Provides at-a-glance text visualization with content snippets
- Measures categorization impact on search performance

## Configuration

Edit `config/query_processing_config.json` to customize:

```json
{
  "test_queries": [
    "regnvand",
    "omkostninger for opmåling og beregning", 
    "projekt information"
  ],
  "performance_testing": {
    "search_results_count": 20,
    "top_results_display": 3,
    "bottom_results_display": 3,
    "content_snippet_length": 80
  }
}
```

## Usage

### Prerequisites
1. **Environment Variables**: Set `OPENAI_API_KEY` and `VOYAGE_API_KEY`
2. **ChromaDB**: Must have completed step 06_store with populated collection
3. **Dependencies**: OpenAI, Voyage AI, ChromaDB, Pydantic

### Run Analysis
```bash
cd notebooks/07_query
python query_processing.py
```

## Output

### At-a-Glance Visualization
```
=== DANISH QUERY PERFORMANCE ANALYSIS ===

Original Query: "regnvand"

📊 Variation: Semantic Expansion
   Query: "stormwater afledning systemer"
   
   WITH categorization (materials filter):
   Top 3 Results:    Similarity: -0.245, -0.289, -0.312
   ┌─ Rank 1 (-0.245): "Regnvand skal håndteres i henhold til gældende..."
   ├─ Rank 2 (-0.289): "Dræning af overfladevand kræver godkendelse..."  
   └─ Rank 3 (-0.312): "Installation af regnvandsopsamling skal..."
   
   Bottom 3 Results: Similarity: -0.678, -0.701, -0.743
   ┌─ Rank 18 (-0.678): "Betonarbejde udføres efter DS/EN 206..."
   ├─ Rank 19 (-0.701): "Tidsfrister for projektgennemgang..."
   └─ Rank 20 (-0.743): "Administrativ håndtering af dokumenter..."
   
   Range: 0.498 | Avg Top 3: -0.282

🏆 WINNER: Semantic Expansion WITH categorization
   Best similarity: -0.245 (vs -0.267 without categorization)
   📈 Categorization improvement: +0.022 similarity
```

### Generated Files
- `query_performance_reports.json` - Individual query analysis
- `overall_performance_report.json` - Summary across all test queries

## Key Insights

### What This Step Tells You
1. **Which query variation technique works best** for Danish construction content
2. **Whether content categorization helps or hinders** search performance  
3. **How well Danish semantic search is working** overall
4. **Which queries need improvement** based on similarity scores

### Expected Results
- **Semantic expansion** often performs best for technical Danish queries
- **Content categorization** may improve performance by 0.01-0.03 similarity
- **Danish technical terminology** should be recognized effectively
- **Similarity scores > -0.3** indicate excellent performance

## Integration with Pipeline

### Input Dependencies
- **ChromaDB Collection**: From step 06_store with construction documents
- **Validated Test Queries**: Proven Danish queries that work

### Output for Next Steps
- **ProcessedQuery objects**: Ready for step 08_retrieve
- **Performance insights**: Inform retrieval strategy selection
- **Category routing**: Metadata filtering recommendations

### Handoff to 08_retrieve
The query processing results inform the retrieval step about:
- Which query variation techniques to prioritize
- Whether to apply content categorization filters
- Expected similarity score ranges for result quality assessment

## Troubleshooting

### Common Issues
1. **No ChromaDB collection**: Run step 06_store first
2. **API key errors**: Set `OPENAI_API_KEY` and `VOYAGE_API_KEY`
3. **Poor similarity scores**: May need more Danish construction documents
4. **Categorization errors**: Check category detection prompts in config

### Performance Optimization
- **Adjust temperature**: Lower for more consistent results, higher for variety
- **Modify test queries**: Add domain-specific Danish construction terms
- **Tune similarity thresholds**: Based on your document collection quality

## Next Steps

After completing this analysis:
1. **Review performance results** to understand which techniques work best
2. **Implement step 08_retrieve** using the query processing insights
3. **Consider expanding test queries** if performance is suboptimal
4. **Adjust categorization logic** if it's not providing value

The goal is to understand how to optimize Danish construction queries before implementing the full retrieval pipeline in step 08. 