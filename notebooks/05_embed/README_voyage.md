# Voyage Embedding API - Danish Construction Documents

This script tests and evaluates Voyage `voyage-multilingual-2` embedding API for Danish construction documents.

## Setup

### 1. Install Dependencies

```bash
# Activate your virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements_voyage.txt
```

### 2. Environment Variables

Create a `.env` file in the project root with your API key:

```env
VOYAGE_API_KEY=your_voyage_api_key_here
```

### 3. API Key

- **Voyage AI**: Get your API key from [Voyage AI Console](https://console.voyageai.com/)

## Usage

### Running the Voyage Embedding Pipeline

```python
# Run the complete Voyage embedding pipeline
python embed_voyage.py
```

### What the Script Does

1. **Loads Chunks**: Automatically finds and loads the latest chunking run
2. **Quality Testing**: Tests Voyage API on Danish construction texts
3. **Performance Benchmark**: Measures speed and estimated costs
4. **Comprehensive Validation**: Validates embedding quality and detects outliers
5. **Generates Embeddings**: Creates embeddings for all chunks
6. **Saves Results**: Stores embedded chunks and analysis

### Output Files

The script creates several output files in `data/internal/05_embedding_voyage/voyage_run_YYYYMMDD_HHMMSS/`:

- `embedded_chunks_voyage.pkl` - Complete embedded chunks (pickle format)
- `embedded_chunks_voyage.json` - Complete embedded chunks (JSON format)
- `embedding_validation.json` - Quality validation results
- `performance_benchmark.json` - Speed and cost analysis
- `embedding_analysis.json` - Statistical analysis of embeddings

## Test Texts

The script uses these Danish construction texts for testing:

- "Facaderne er pudsede, og de skal renoveres både på vej- og gårdfacaden"
- "Der er 53 vindues- og dørhuller i hver af de to facader"
- "Taget er et 45 graders skifertag med tre kviste"
- "Fundamentet er støbt i beton med armering"
- "Vinduerne er dobbeltglas med energisparprofil"
- "Tagrenovering omfatter nye tagsten og isolering"
- "Facadepudsen skal fjernes og erstattes med nyt"
- "Gulvene er af træ og skal slibes og lakkeres"
- "Elektrisk installation skal opgraderes til moderne standard"
- "Ventilationssystemet skal renoveres og udvides"

## Evaluation Criteria

### Quality Tests

1. **Self-Similarity**: Identical texts should have identical embeddings
2. **Semantic Similarity**: Related construction terms should be similar
3. **Danish Character Handling**: Proper handling of æ, ø, å characters
4. **Domain Clustering**: Construction terms should cluster together

### Performance Metrics

- **Speed**: Texts processed per second
- **Cost**: Estimated cost per 1,000 texts
- **Reliability**: Retry logic and error handling

### Validation Tests

- **Outlier Detection**: Identifies unusual embeddings
- **Statistical Analysis**: Basic embedding statistics
- **Content Analysis**: Distribution by content type and size

## Model Specifications

| Provider | Model | Dimensions | Language Support |
|----------|-------|------------|------------------|
| Voyage | voyage-multilingual-2 | 1024 | Multilingual |

## Features

### Error Handling
- Retry logic with exponential backoff
- Comprehensive error reporting
- Graceful failure handling

### Batch Processing
- Configurable batch sizes
- Progress tracking
- Memory-efficient processing

### Quality Assurance
- Embedding validation
- Outlier detection
- Statistical analysis
- Danish language testing

## Next Steps

After running the script:

1. Review the validation results in `embedding_validation.json`
2. Check performance metrics in `performance_benchmark.json`
3. Use the embedded chunks for ChromaDB storage
4. Analyze the embedding quality for your specific use case

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your `.env` file is in the project root
2. **Import Errors**: Make sure you've installed all requirements
3. **Rate Limiting**: The script includes retry logic, but you may need to adjust batch sizes
4. **Memory Issues**: Reduce batch size if processing large datasets

### Getting Help

- Check the console output for detailed error messages
- Review the generated JSON files for specific test results
- Ensure your virtual environment is activated before running

## Cost Estimation

Voyage AI pricing (approximate):
- ~$0.005 per 1,000 texts
- Cost scales linearly with text count
- No minimum usage requirements

## Performance Notes

- Voyage multilingual-2 is optimized for multilingual content
- Good performance on Danish text
- 1024-dimensional embeddings provide good semantic representation
- Suitable for construction domain vocabulary 