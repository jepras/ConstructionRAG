# Performance Analysis

## Usage
```bash
python tests/performance/check/analyze_indexing_performance.py <indexing_run_id> "Description"
```

## Example
```bash
python tests/performance/check/analyze_indexing_performance.py abc123def "Added new VLM model"
```

Outputs:
- JSON: `perf_<timestamp>_<run_id>.json`
- CSV: `performance_history.csv`