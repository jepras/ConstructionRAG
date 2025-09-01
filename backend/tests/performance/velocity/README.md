# Velocity Performance Testing & Analysis

This directory contains tools and results for tracking ConstructionRAG indexing pipeline performance and velocity metrics over time.

## 📊 Analysis Scripts

### 1. `analyze_and_track_performance.py` (Main Tool)
Analyzes indexing run performance and saves results for tracking improvements over time.

**Usage:**
```bash
cd backend
python tests/performance/velocity/analyze_and_track_performance.py <indexing_run_id> "Description of changes"

# Example:
python tests/performance/velocity/analyze_and_track_performance.py ca079abb-b746-45fb-b448-0c4f5f185f8c "Baseline - before optimizations"
```

**Output:**
- JSON file with detailed metrics: `perf_YYYYMMDD_HHMMSS_<run_id>.json`
- Appends to CSV history: `performance_history.csv`

### 2. `analyze_timing_detailed.py`
Provides detailed VLM metrics and parallelization analysis.

**Usage:**
```bash
python tests/performance/velocity/analyze_timing_detailed.py
```

### 3. `analyze_all_timings.py`
Basic timing analysis with console output only.

**Usage:**
```bash
python tests/performance/velocity/analyze_all_timings.py
```

## 📈 Tracked Metrics

### Summary Metrics
- **Wall clock time** - Actual time from start to finish
- **Sequential sum** - Sum of all step times (shows parallelization)
- **Parallelization factor** - How much faster than sequential
- **Documents & pages processed**

### Step Breakdown
- **Partition** - PDF text extraction time
- **Metadata** - Document metadata extraction
- **Enrichment** - VLM processing (images/tables)
- **Chunking** - Text chunking time
- **Embedding** - Vector embedding generation

### VLM Metrics
- **Total images/tables processed**
- **Average seconds per item**
- **Processing rate (items/second)**

### Performance Rates
- **Pages per second**
- **Documents per minute**
- **Average seconds per document**

## 📁 Output Files

### `performance_history.csv`
Tracks key metrics over time for easy comparison:
```csv
timestamp,run_id,description,docs,wall_time_min,sequential_min,parallelization,partition_pct,enrichment_pct,embedding_pct,vlm_items,vlm_sec_per_item,pages_per_sec
```

### `perf_*.json`
Detailed metrics for each analysis run, including:
- Complete timing breakdown
- Top slowest documents
- VLM processing details
- Step-by-step timings

## 🎯 Performance Targets

Based on baseline analysis (17.7 minutes for 14 docs):

| Metric | Current | Target | Improvement Needed |
|--------|---------|--------|-------------------|
| Wall Clock Time | 17.7 min | 5 min | 3.5x faster |
| Parallelization | 1.15x | 5x | Better concurrency |
| VLM per item | 7.7 sec | 2 sec | Batch processing |
| Pages/second | 0.25 | 1.0 | 4x faster |

## 🚀 Optimization Strategies

### 1. Increase Parallelization (Biggest Win)
- Process 10+ documents simultaneously
- Expected improvement: 3-5x

### 2. Optimize VLM Processing
- Batch multiple images per API call
- Use faster models for simple content
- Skip VLM for text-only pages
- Expected improvement: 2-3x

### 3. Improve PDF Extraction
- Optimize partition step for slow PDFs
- Consider alternative PDF libraries
- Expected improvement: 1.5x

## 📊 How to Track Improvements

1. **Before making changes:** Run baseline analysis
2. **After optimization:** Run with new indexing run
3. **Compare results:** Check `performance_history.csv`
4. **Document changes:** Use descriptive messages

Example workflow:
```bash
# Baseline
python tests/performance/velocity/analyze_and_track_performance.py <run1> "Baseline"

# After adding parallelization
python tests/performance/velocity/analyze_and_track_performance.py <run2> "Added 5x parallelization"

# After VLM optimization
python tests/performance/velocity/analyze_and_track_performance.py <run3> "Batch VLM processing enabled"
```

## 🔍 Analyzing Results

To see improvement trends:
1. Open `performance_history.csv` in Excel/Numbers
2. Create charts for wall_time_min over time
3. Compare parallelization factors
4. Track VLM seconds per item improvements

The goal is to see consistent improvement in:
- Decreasing wall clock time
- Increasing parallelization factor
- Decreasing VLM seconds per item
- Increasing pages per second