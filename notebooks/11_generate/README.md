# Step 11: LLM Response Generation

## 🇩🇰 Danish Response Generation with GPT-4-turbo

This step generates Danish answers to construction queries using GPT-4-turbo, with structured citations and confidence scoring.

## 🎯 Key Features

- **Danish Language**: All responses generated in Danish
- **Structured Citations**: Automatic source attribution with page numbers and sections
- **Confidence Scoring**: LLM indicates confidence level for each citation
- **Quality Filtering**: Only considers results with similarity score ≥ 0.5
- **LLM Decision**: Let the LLM choose which results are relevant
- **Dual Output**: JSON and HTML formats for easy consumption

## 🔧 Configuration

### OpenAI Settings
- **Model**: `gpt-4-turbo`
- **Temperature**: 0.1 (low for factual accuracy)
- **Max Tokens**: 2000

### Context Management
- **Max Results**: 12 results sent to LLM
- **Min Threshold**: 0.5 similarity score
- **Max Citations**: 5 citations per response

### Test Queries
Uses the same Danish construction queries from step 7:
- "regnvand"
- "omkostninger for opmåling og beregning"
- "projekt information"

## 📊 Output Structure

### JSON Response
```json
{
  "query": "regnvand",
  "answer": "Baseret på byggedokumenterne...",
  "citations": [
    {
      "source": "test-with-little-variety.pdf",
      "page": 4,
      "section": "1.2 Demonstrationsejendommen",
      "content_snippet": "Principper for regnvandshåndtering...",
      "confidence": 0.95,
      "similarity_score": 0.994
    }
  ],
  "metadata": {
    "search_method": "hybrid_60_40",
    "results_considered": 12,
    "results_cited": 3,
    "generation_time_ms": 2500,
    "tokens_used": 1850
  }
}
```

### HTML Output
Professional HTML format with:
- Color-coded confidence levels
- Source metadata
- Performance metrics
- Easy-to-read layout

## 🚀 Usage

1. **Auto-detection**: Automatically finds latest step 8 results
2. **Run Generation**: `python generate_openai.py`
3. **Review Output**: Check both JSON and HTML files

## 📁 Output Files

```
11_run_YYYYMMDD_HHMMSS/
├── generated_responses/
│   ├── hybrid_60_40_regnvand_response.json
│   ├── hybrid_60_40_regnvand_response.html
│   ├── hybrid_60_40_omkostninger_response.json
│   ├── hybrid_60_40_omkostninger_response.html
│   ├── hybrid_60_40_projekt_response.json
│   └── hybrid_60_40_projekt_response.html
└── generation_summary.json
```

## 🎯 Design Decisions

1. **Score Threshold**: 0.5 (not 0.3) for meaningful relevance
2. **LLM Decision**: Let LLM choose which results to use and cite
3. **Irrelevant Queries**: Graceful "no information found" response
4. **Citations**: Include ALL sources used, not just top results
5. **Confidence**: Include confidence scores for transparency
6. **Danish Language**: All prompts and responses in Danish

## 🔍 Error Handling

- **API Failures**: Retry with exponential backoff
- **Poor Results**: Fallback to "no information found"
- **Low Confidence**: Mark uncertain information clearly
- **Technical Errors**: Graceful degradation with error messages

## 📈 Performance Metrics

- **Response Time**: Target < 30 seconds
- **Token Usage**: Track for cost optimization
- **Confidence Scores**: Monitor quality
- **Citation Accuracy**: Validate source references 