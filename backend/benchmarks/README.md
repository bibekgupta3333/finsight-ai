# Benchmark Suite

Comprehensive benchmarking framework for evaluating fraud detection approaches.

## Documentation

📚 **Full Guide:** [docs/BENCHMARK-GUIDE.md](../../docs/BENCHMARK-GUIDE.md)

## Quick Start

```bash
# From project root
pnpm benchmark:quick

# Or directly
cd backend
python scripts/run_benchmarks.py --dataset quick_test --baselines xgboost lightgbm rule-based
```

## Available Commands

- `pnpm benchmark` - Run all benchmarks
- `pnpm benchmark:quick` - Quick test (5 samples, <1s)
- `pnpm benchmark:ml` - ML models only
- `pnpm benchmark:suite` - Full benchmark suite
- `pnpm benchmark:all` - All baselines

## Files

- `config.yaml` - Benchmark configuration
- `baselines.py` - Baseline evaluators (ML, Rule-based, Single-agent)
- `runner.py` - Benchmark orchestration
- `__init__.py` - Package initialization

## Results

Results saved to: `backend/data/benchmarks/results/`

For detailed documentation, see [docs/BENCHMARK-GUIDE.md](../../docs/BENCHMARK-GUIDE.md).
