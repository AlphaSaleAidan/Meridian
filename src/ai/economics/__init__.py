"""
Meridian Economics Module — Industry benchmarks, financial models, and academic citations.

Provides doctorate-level economic analysis frameworks:
  • Industry benchmarks (NRA, NACS, NRF, IBISWorld)
  • Price elasticity estimation
  • Break-even analysis
  • Marginal revenue optimization
  • Working capital efficiency scoring
  • Customer lifetime value models
  • Seasonal decomposition
"""
from .benchmarks import IndustryBenchmarks, CITATIONS
from .models import EconomicModels

__all__ = ["IndustryBenchmarks", "EconomicModels", "CITATIONS"]
