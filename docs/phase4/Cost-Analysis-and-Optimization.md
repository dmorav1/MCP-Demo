# Cost Analysis and Optimization Guide
# Phase 4: RAG System Cost Management

**Version:** 1.0  
**Date:** November 8, 2025  
**Status:** Design Document  
**Architect:** Software Architecture Agent

---

## Table of Contents

1. [Overview](#overview)
2. [Cost Structure](#cost-structure)
3. [Cost Estimation Models](#cost-estimation-models)
4. [Cost Optimization Strategies](#cost-optimization-strategies)
5. [Budget Management](#budget-management)
6. [Cost Monitoring](#cost-monitoring)
7. [Provider Comparison](#provider-comparison)
8. [ROI Analysis](#roi-analysis)

---

## Overview

This document provides comprehensive cost analysis and optimization strategies for the RAG system, enabling informed decisions about LLM provider selection, usage patterns, and cost control mechanisms.

### Cost Principles

1. **Measure Everything**: Track all costs accurately
2. **Optimize Continuously**: Regular cost review and optimization
3. **Balance Quality vs Cost**: Find optimal trade-offs
4. **Cache Aggressively**: Reduce redundant LLM calls
5. **Use Right-Sized Models**: Match model to task complexity
6. **Set Hard Limits**: Prevent cost overruns

---

## Cost Structure

### Cost Components

```
Total RAG System Cost
├── LLM API Costs (70-80% of total)
│   ├── Input tokens
│   ├── Output tokens
│   └── API call overhead
│
├── Infrastructure Costs (15-20% of total)
│   ├── Compute (application servers)
│   ├── Database (PostgreSQL + pgvector)
│   ├── Cache (Redis)
│   └── Network/bandwidth
│
├── Embedding Costs (5-10% of total)
│   ├── Embedding generation API
│   └── Storage for embeddings
│
└── Operational Costs (< 5% of total)
    ├── Monitoring
    ├── Logging
    └── Alerting
```

### LLM Provider Pricing (as of November 2025)

#### OpenAI Pricing

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Context Window |
|-------|----------------------|------------------------|----------------|
| GPT-4 | $30.00 | $60.00 | 8K |
| GPT-4-32K | $60.00 | $120.00 | 32K |
| GPT-3.5-Turbo | $1.50 | $2.00 | 4K |
| GPT-3.5-Turbo-16K | $3.00 | $4.00 | 16K |
| Ada Embeddings (v2) | $0.10 | N/A | N/A |

#### Anthropic Pricing

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Context Window |
|-------|----------------------|------------------------|----------------|
| Claude 3 Opus | $15.00 | $75.00 | 200K |
| Claude 3 Sonnet | $3.00 | $15.00 | 200K |
| Claude 3 Haiku | $0.25 | $1.25 | 200K |

#### Local Model Costs

| Model | Hardware Requirements | Cost | Performance |
|-------|----------------------|------|-------------|
| Llama 2 7B | 16GB GPU | ~$0.50/hr (cloud GPU) | Good for simple tasks |
| Llama 2 13B | 24GB GPU | ~$1.00/hr (cloud GPU) | Better quality |
| Llama 2 70B | 80GB GPU (multi) | ~$3.00/hr (cloud GPU) | Near GPT-3.5 quality |
| Mistral 7B | 16GB GPU | ~$0.50/hr (cloud GPU) | Fast, efficient |

**Note**: Self-hosted models have zero API costs but require infrastructure investment.

---

## Cost Estimation Models

### Simple Cost Calculator

```python
from dataclasses import dataclass
from typing import Literal, Dict

@dataclass
class PricingModel:
    """Pricing for an LLM model."""
    model_name: str
    input_cost_per_1m: float  # USD per 1M tokens
    output_cost_per_1m: float  # USD per 1M tokens
    context_window: int

class CostCalculator:
    """Calculate costs for RAG operations."""
    
    def __init__(self):
        self.pricing = {
            "gpt-4": PricingModel("gpt-4", 30.0, 60.0, 8192),
            "gpt-3.5-turbo": PricingModel("gpt-3.5-turbo", 1.5, 2.0, 4096),
            "claude-3-opus": PricingModel("claude-3-opus", 15.0, 75.0, 200000),
            "claude-3-sonnet": PricingModel("claude-3-sonnet", 3.0, 15.0, 200000),
            "claude-3-haiku": PricingModel("claude-3-haiku", 0.25, 1.25, 200000),
        }
    
    def calculate_request_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a single request."""
        pricing = self.pricing.get(model)
        if not pricing:
            return 0.0
        
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_1m
        
        return input_cost + output_cost
    
    def estimate_daily_cost(
        self,
        model: str,
        avg_queries_per_day: int,
        avg_input_tokens_per_query: int,
        avg_output_tokens_per_query: int,
        cache_hit_rate: float = 0.0
    ) -> Dict[str, float]:
        """
        Estimate daily costs.
        
        Args:
            model: Model name
            avg_queries_per_day: Expected daily queries
            avg_input_tokens_per_query: Average input tokens
            avg_output_tokens_per_query: Average output tokens
            cache_hit_rate: Percentage of queries served from cache (0.0-1.0)
            
        Returns:
            Cost breakdown
        """
        # Calculate for non-cached requests
        uncached_queries = avg_queries_per_day * (1 - cache_hit_rate)
        
        cost_per_request = self.calculate_request_cost(
            model,
            avg_input_tokens_per_query,
            avg_output_tokens_per_query
        )
        
        daily_llm_cost = cost_per_request * uncached_queries
        
        # Add infrastructure costs (estimate)
        infrastructure_multiplier = 0.25  # 25% of LLM cost
        infrastructure_cost = daily_llm_cost * infrastructure_multiplier
        
        return {
            "llm_cost": daily_llm_cost,
            "infrastructure_cost": infrastructure_cost,
            "total_cost": daily_llm_cost + infrastructure_cost,
            "cost_per_query": (daily_llm_cost + infrastructure_cost) / avg_queries_per_day,
            "queries_per_dollar": avg_queries_per_day / (daily_llm_cost + infrastructure_cost) if daily_llm_cost > 0 else 0
        }
    
    def compare_models(
        self,
        queries_per_day: int,
        input_tokens: int,
        output_tokens: int,
        cache_hit_rate: float = 0.4
    ) -> Dict[str, Dict]:
        """Compare costs across different models."""
        comparison = {}
        
        for model_name in self.pricing.keys():
            comparison[model_name] = self.estimate_daily_cost(
                model_name,
                queries_per_day,
                input_tokens,
                output_tokens,
                cache_hit_rate
            )
        
        return comparison


# Example usage
calculator = CostCalculator()

# Scenario: Medium-sized deployment
# - 1000 queries per day
# - Average 1000 input tokens (context + query)
# - Average 200 output tokens (answer)
# - 40% cache hit rate

comparison = calculator.compare_models(
    queries_per_day=1000,
    input_tokens=1000,
    output_tokens=200,
    cache_hit_rate=0.4
)

# Results:
# gpt-4: ~$33.60/day
# gpt-3.5-turbo: ~$1.68/day (20x cheaper!)
# claude-3-opus: ~$21.60/day
# claude-3-haiku: ~$0.34/day (100x cheaper than GPT-4!)
```

### Cost Scenarios

#### Scenario 1: Small Deployment (Startup/POC)

**Profile**:
- 100 queries/day
- Simple questions (avg 500 input tokens, 150 output tokens)
- 30% cache hit rate

**Cost Estimate**:
```python
{
    "gpt-4": "$2.52/day ($75.60/month)",
    "gpt-3.5-turbo": "$0.13/day ($3.90/month)",
    "claude-3-haiku": "$0.03/day ($0.90/month)",
}
```

**Recommendation**: Start with `claude-3-haiku` or `gpt-3.5-turbo` for cost efficiency.

#### Scenario 2: Medium Deployment (Small Business)

**Profile**:
- 1,000 queries/day
- Mixed complexity (avg 1200 input tokens, 250 output tokens)
- 40% cache hit rate

**Cost Estimate**:
```python
{
    "gpt-4": "$42.00/day ($1,260/month)",
    "gpt-3.5-turbo": "$2.10/day ($63/month)",
    "claude-3-sonnet": "$6.30/day ($189/month)",
    "claude-3-haiku": "$0.42/day ($12.60/month)",
}
```

**Recommendation**: Use tiered approach:
- Simple queries → `claude-3-haiku` (~60% of traffic)
- Complex queries → `gpt-4` or `claude-3-sonnet` (~40% of traffic)
- **Blended cost**: ~$17/day (~$510/month)

#### Scenario 3: Large Deployment (Enterprise)

**Profile**:
- 10,000 queries/day
- Mixed complexity (avg 1500 input tokens, 300 output tokens)
- 50% cache hit rate
- High quality requirements

**Cost Estimate**:
```python
{
    "gpt-4": "$525/day ($15,750/month)",
    "gpt-3.5-turbo": "$26.25/day ($787.50/month)",
    "claude-3-opus": "$337.50/day ($10,125/month)",
    "claude-3-sonnet": "$67.50/day ($2,025/month)",
}
```

**Recommendation**: Multi-model strategy with intelligent routing:
- Simple/routine queries (30%) → `gpt-3.5-turbo`
- Standard queries (50%) → `claude-3-sonnet`
- Complex/critical queries (20%) → `gpt-4`
- **Blended cost**: ~$135/day (~$4,050/month)

---

## Cost Optimization Strategies

### 1. Aggressive Caching

**Impact**: 40-60% cost reduction

```python
class CacheOptimizer:
    """Optimize caching for maximum cost savings."""
    
    def __init__(self):
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "cost_saved": 0.0
        }
    
    async def get_cached_or_generate(
        self,
        cache_key: str,
        generator_func: Callable,
        estimated_cost: float
    ) -> Tuple[Any, bool]:
        """Get from cache or generate, tracking savings."""
        cached = await self.cache.get(cache_key)
        
        if cached:
            self.cache_stats["hits"] += 1
            self.cache_stats["cost_saved"] += estimated_cost
            return cached, True
        
        self.cache_stats["misses"] += 1
        result = await generator_func()
        await self.cache.set(cache_key, result, ttl=3600)
        
        return result, False
    
    def get_cache_roi(self) -> Dict[str, Any]:
        """Calculate ROI of caching."""
        hit_rate = self.cache_stats["hits"] / (
            self.cache_stats["hits"] + self.cache_stats["misses"]
        )
        
        # Assume Redis costs ~$50/month for 1GB
        redis_monthly_cost = 50.0
        monthly_savings = self.cache_stats["cost_saved"] * 30  # Extrapolate
        
        return {
            "hit_rate": hit_rate,
            "monthly_savings": monthly_savings,
            "cache_cost": redis_monthly_cost,
            "net_savings": monthly_savings - redis_monthly_cost,
            "roi": (monthly_savings / redis_monthly_cost - 1) * 100 if redis_monthly_cost > 0 else 0
        }


# Example: With 40% cache hit rate on 1000 queries/day using GPT-4
# - Cost without cache: $42/day
# - Cost with cache: $25.20/day (40% saved)
# - Monthly savings: ~$504
# - Redis cost: $50/month
# - Net savings: $454/month (10x ROI!)
```

### 2. Intelligent Model Selection

**Impact**: 30-50% cost reduction

```python
class ModelSelector:
    """Select cheapest model that meets quality requirements."""
    
    def __init__(self, cost_calculator: CostCalculator):
        self.calculator = cost_calculator
        self.quality_scores = {
            "gpt-4": 10,
            "claude-3-opus": 10,
            "claude-3-sonnet": 8,
            "gpt-3.5-turbo": 7,
            "claude-3-haiku": 7,
        }
    
    def select_cost_optimal_model(
        self,
        query_complexity: Literal["simple", "medium", "complex"],
        input_tokens: int,
        output_tokens: int,
        min_quality_score: int = 7
    ) -> str:
        """
        Select most cost-effective model meeting quality requirements.
        
        Strategy:
        - Simple queries: Use cheapest model
        - Medium queries: Balance cost and quality
        - Complex queries: Prioritize quality
        """
        viable_models = {
            model: score
            for model, score in self.quality_scores.items()
            if score >= min_quality_score
        }
        
        # Calculate cost for each viable model
        model_costs = {}
        for model in viable_models:
            cost = self.calculator.calculate_request_cost(
                model,
                input_tokens,
                output_tokens
            )
            model_costs[model] = cost
        
        if query_complexity == "simple":
            # Choose cheapest
            return min(model_costs, key=model_costs.get)
        elif query_complexity == "complex":
            # Choose highest quality among viable
            return max(viable_models, key=viable_models.get)
        else:  # medium
            # Balance: cost * quality_score
            scores = {
                model: model_costs[model] * (11 - viable_models[model])
                for model in viable_models
            }
            return min(scores, key=scores.get)


# Example usage:
selector = ModelSelector(calculator)

# Simple query
model = selector.select_cost_optimal_model("simple", 800, 150)
# Returns: "claude-3-haiku" (cheapest)

# Complex query
model = selector.select_cost_optimal_model("complex", 1500, 400, min_quality_score=9)
# Returns: "gpt-4" or "claude-3-opus" (highest quality)
```

### 3. Token Optimization

**Impact**: 20-30% cost reduction

```python
class TokenOptimizationStrategy:
    """Strategies to reduce token usage."""
    
    def optimize_context(
        self,
        context_chunks: List[str],
        max_tokens: int
    ) -> List[str]:
        """
        Optimize context to fit within token budget.
        
        Techniques:
        1. Remove redundant information
        2. Summarize similar chunks
        3. Extract key sentences
        4. Prioritize most relevant
        """
        optimized = []
        total_tokens = 0
        
        for chunk in context_chunks:
            # Remove redundant whitespace
            cleaned = " ".join(chunk.split())
            
            # Extract key sentences if chunk is long
            if len(cleaned.split()) > 100:
                cleaned = self._extract_key_sentences(cleaned)
            
            chunk_tokens = self.count_tokens(cleaned)
            
            if total_tokens + chunk_tokens <= max_tokens:
                optimized.append(cleaned)
                total_tokens += chunk_tokens
            else:
                break
        
        return optimized
    
    def compress_conversation_history(
        self,
        history: List[Dict[str, str]],
        max_tokens: int
    ) -> str:
        """
        Compress conversation history.
        
        Strategy:
        - Keep last 2-3 turns in full
        - Summarize older turns
        """
        if not history:
            return ""
        
        recent = history[-3:]
        old = history[:-3]
        
        compressed = ""
        
        if old:
            # Summarize old history
            summary = self._summarize_history(old)
            compressed += f"Earlier conversation: {summary}\n\n"
        
        # Add recent history verbatim
        for turn in recent:
            compressed += f"Q: {turn['question']}\nA: {turn['answer']}\n\n"
        
        # Ensure within token limit
        if self.count_tokens(compressed) > max_tokens:
            compressed = self.truncate_to_token_limit(compressed, max_tokens)
        
        return compressed
```

### 4. Batch Processing

**Impact**: 10-15% cost reduction

```python
class BatchOptimizer:
    """Batch multiple requests for efficiency."""
    
    async def batch_process_queries(
        self,
        queries: List[str],
        batch_size: int = 5
    ) -> List[str]:
        """
        Process queries in batches.
        
        Benefits:
        - Reduced API overhead
        - Better throughput
        - Can use batch discounts (if available)
        """
        results = []
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*[
                self.process_query(q) for q in batch
            ])
            
            results.extend(batch_results)
        
        return results
```

### 5. Response Truncation

**Impact**: 5-10% cost reduction

```python
def truncate_response(
    response: str,
    max_tokens: int = 500
) -> str:
    """
    Truncate overly long responses.
    
    Users rarely read very long responses, so limit output tokens.
    """
    if count_tokens(response) <= max_tokens:
        return response
    
    # Truncate at sentence boundary
    sentences = response.split('. ')
    truncated = ""
    
    for sentence in sentences:
        if count_tokens(truncated + sentence) < max_tokens:
            truncated += sentence + ". "
        else:
            break
    
    return truncated.strip()
```

### 6. Local Models for Simple Queries

**Impact**: 50-70% cost reduction for applicable queries

```python
class HybridModelStrategy:
    """Use local models for simple queries, cloud for complex."""
    
    def __init__(self):
        self.local_model_available = self._check_local_model()
    
    async def process_query(
        self,
        query: str,
        complexity: str
    ) -> Tuple[str, str]:  # (response, model_used)
        """Route query to appropriate model."""
        
        if complexity == "simple" and self.local_model_available:
            # Use free local model
            response = await self.local_model.generate(query)
            return response, "llama2-local"
        else:
            # Use cloud API
            response = await self.cloud_model.generate(query)
            return response, "gpt-4"


# Cost comparison:
# - 1000 simple queries/day with GPT-4: ~$20/day
# - 1000 simple queries/day with local Llama2: ~$12/day (GPU costs)
# - Savings: ~$8/day (~$240/month)
```

---

## Budget Management

### Budget Configuration

```python
class BudgetManager:
    """Manage and enforce budget limits."""
    
    def __init__(
        self,
        daily_limit: Optional[float] = None,
        monthly_limit: Optional[float] = None,
        alert_threshold: float = 0.8
    ):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.alert_threshold = alert_threshold
        
        self.daily_usage = 0.0
        self.monthly_usage = 0.0
        
        self.usage_log = []
    
    async def check_budget(
        self,
        estimated_cost: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within budget.
        
        Returns:
            (is_allowed, reason_if_denied)
        """
        # Check daily limit
        if self.daily_limit:
            if self.daily_usage + estimated_cost > self.daily_limit:
                return False, "Daily budget exceeded"
            
            # Check alert threshold
            if (self.daily_usage + estimated_cost) >= (self.daily_limit * self.alert_threshold):
                await self._send_alert("daily", self.daily_usage + estimated_cost)
        
        # Check monthly limit
        if self.monthly_limit:
            if self.monthly_usage + estimated_cost > self.monthly_limit:
                return False, "Monthly budget exceeded"
            
            if (self.monthly_usage + estimated_cost) >= (self.monthly_limit * self.alert_threshold):
                await self._send_alert("monthly", self.monthly_usage + estimated_cost)
        
        return True, None
    
    def record_usage(
        self,
        cost: float,
        model: str,
        query_type: str
    ):
        """Record usage for tracking."""
        self.daily_usage += cost
        self.monthly_usage += cost
        
        self.usage_log.append({
            "timestamp": datetime.now(),
            "cost": cost,
            "model": model,
            "query_type": query_type,
            "daily_total": self.daily_usage,
            "monthly_total": self.monthly_usage
        })
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        status = {
            "daily": {
                "usage": self.daily_usage,
                "limit": self.daily_limit,
                "remaining": self.daily_limit - self.daily_usage if self.daily_limit else None,
                "percentage_used": (self.daily_usage / self.daily_limit * 100) if self.daily_limit else 0
            },
            "monthly": {
                "usage": self.monthly_usage,
                "limit": self.monthly_limit,
                "remaining": self.monthly_limit - self.monthly_usage if self.monthly_limit else None,
                "percentage_used": (self.monthly_usage / self.monthly_limit * 100) if self.monthly_limit else 0
            }
        }
        
        return status
    
    async def _send_alert(self, period: str, current_usage: float):
        """Send budget alert."""
        limit = self.daily_limit if period == "daily" else self.monthly_limit
        percentage = (current_usage / limit * 100) if limit else 0
        
        message = f"Budget alert: {period} usage at {percentage:.1f}% (${current_usage:.2f} of ${limit:.2f})"
        
        # Send to monitoring system, Slack, email, etc.
        logger.warning(message)
        # await self.notification_service.send(message)
```

### Auto-Downgrade Strategy

```python
class AutoDowngradeStrategy:
    """Automatically downgrade to cheaper models when approaching budget limit."""
    
    def __init__(
        self,
        budget_manager: BudgetManager,
        model_selector: ModelSelector
    ):
        self.budget_manager = budget_manager
        self.model_selector = model_selector
    
    def get_model_for_budget(
        self,
        desired_model: str,
        input_tokens: int,
        output_tokens: int
    ) -> str:
        """
        Get appropriate model based on remaining budget.
        
        Strategy:
        - If budget comfortable (< 50% used): Use desired model
        - If budget moderate (50-80% used): Downgrade one tier
        - If budget critical (> 80% used): Use cheapest model
        """
        budget_status = self.budget_manager.get_budget_status()
        
        # Use most restrictive budget (daily or monthly)
        daily_pct = budget_status["daily"]["percentage_used"]
        monthly_pct = budget_status["monthly"]["percentage_used"]
        budget_pressure = max(daily_pct, monthly_pct)
        
        if budget_pressure < 50:
            return desired_model
        elif budget_pressure < 80:
            return self._downgrade_model(desired_model, tiers=1)
        else:
            return "claude-3-haiku"  # Cheapest viable model
    
    def _downgrade_model(self, model: str, tiers: int = 1) -> str:
        """Downgrade model by N tiers."""
        model_tiers = [
            "gpt-4",
            "claude-3-opus",
            "claude-3-sonnet",
            "gpt-3.5-turbo",
            "claude-3-haiku"
        ]
        
        if model not in model_tiers:
            return model
        
        current_idx = model_tiers.index(model)
        new_idx = min(current_idx + tiers, len(model_tiers) - 1)
        
        return model_tiers[new_idx]
```

---

## Cost Monitoring

### Monitoring Dashboard Metrics

```python
class CostMonitor:
    """Monitor and track costs with detailed metrics."""
    
    def __init__(self):
        self.metrics = {
            "total_cost": 0.0,
            "cost_by_model": {},
            "cost_by_query_type": {},
            "cost_by_user": {},
            "tokens_by_model": {},
            "cache_savings": 0.0
        }
    
    def record_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        query_type: str,
        user_id: str,
        cache_hit: bool
    ):
        """Record detailed metrics for request."""
        # Total cost
        self.metrics["total_cost"] += cost
        
        # Cost by model
        if model not in self.metrics["cost_by_model"]:
            self.metrics["cost_by_model"][model] = 0.0
        self.metrics["cost_by_model"][model] += cost
        
        # Cost by query type
        if query_type not in self.metrics["cost_by_query_type"]:
            self.metrics["cost_by_query_type"][query_type] = 0.0
        self.metrics["cost_by_query_type"][query_type] += cost
        
        # Cost by user
        if user_id not in self.metrics["cost_by_user"]:
            self.metrics["cost_by_user"][user_id] = 0.0
        self.metrics["cost_by_user"][user_id] += cost
        
        # Tokens by model
        if model not in self.metrics["tokens_by_model"]:
            self.metrics["tokens_by_model"][model] = {"input": 0, "output": 0}
        self.metrics["tokens_by_model"][model]["input"] += input_tokens
        self.metrics["tokens_by_model"][model]["output"] += output_tokens
        
        # Cache savings
        if cache_hit:
            self.metrics["cache_savings"] += cost
    
    def generate_report(self, period: str = "day") -> Dict[str, Any]:
        """Generate cost report."""
        return {
            "period": period,
            "total_cost": self.metrics["total_cost"],
            "cost_breakdown": {
                "by_model": self.metrics["cost_by_model"],
                "by_query_type": self.metrics["cost_by_query_type"],
                "top_users": self._get_top_users(5)
            },
            "token_usage": self.metrics["tokens_by_model"],
            "cache_savings": self.metrics["cache_savings"],
            "cache_roi": self._calculate_cache_roi(),
            "cost_per_query": self._calculate_cost_per_query(),
            "projections": self._project_costs(period)
        }
    
    def _get_top_users(self, n: int) -> List[Tuple[str, float]]:
        """Get top N users by cost."""
        return sorted(
            self.metrics["cost_by_user"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
    
    def _project_costs(self, period: str) -> Dict[str, float]:
        """Project costs for different time periods."""
        daily_cost = self.metrics["total_cost"]  # Assuming metrics are for one day
        
        return {
            "projected_weekly": daily_cost * 7,
            "projected_monthly": daily_cost * 30,
            "projected_yearly": daily_cost * 365
        }
```

### Alerting Rules

```python
class CostAlerting:
    """Alert on cost anomalies and thresholds."""
    
    def __init__(self, cost_monitor: CostMonitor):
        self.monitor = cost_monitor
        self.baselines = {}
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        # High cost user alert
        top_users = self.monitor._get_top_users(3)
        for user_id, cost in top_users:
            if cost > 50.0:  # $50/day for single user
                alerts.append({
                    "type": "high_user_cost",
                    "severity": "warning",
                    "user_id": user_id,
                    "cost": cost,
                    "message": f"User {user_id} has high daily cost: ${cost:.2f}"
                })
        
        # Cost spike detection
        current_cost = self.monitor.metrics["total_cost"]
        if "daily_cost" in self.baselines:
            baseline = self.baselines["daily_cost"]
            if current_cost > baseline * 1.5:  # 50% increase
                alerts.append({
                    "type": "cost_spike",
                    "severity": "critical",
                    "current_cost": current_cost,
                    "baseline_cost": baseline,
                    "message": f"Cost spike detected: ${current_cost:.2f} vs baseline ${baseline:.2f}"
                })
        
        # Model usage anomaly
        for model, cost in self.monitor.metrics["cost_by_model"].items():
            baseline_key = f"model_{model}_cost"
            if baseline_key in self.baselines:
                baseline = self.baselines[baseline_key]
                if cost > baseline * 2:  # 100% increase
                    alerts.append({
                        "type": "model_usage_anomaly",
                        "severity": "warning",
                        "model": model,
                        "cost": cost,
                        "baseline": baseline,
                        "message": f"Unusual {model} usage: ${cost:.2f} vs baseline ${baseline:.2f}"
                    })
        
        return alerts
    
    def update_baselines(self):
        """Update baseline metrics for anomaly detection."""
        self.baselines["daily_cost"] = self.monitor.metrics["total_cost"]
        
        for model, cost in self.monitor.metrics["cost_by_model"].items():
            self.baselines[f"model_{model}_cost"] = cost
```

---

## Provider Comparison

### Cost-Benefit Analysis by Provider

| Provider | Model | Quality | Speed | Cost/1K queries* | Best For |
|----------|-------|---------|-------|------------------|----------|
| OpenAI | GPT-4 | 10/10 | 7/10 | $33.60 | Critical tasks, highest quality |
| OpenAI | GPT-3.5-Turbo | 7/10 | 9/10 | $1.68 | General queries, cost-effective |
| Anthropic | Claude 3 Opus | 10/10 | 8/10 | $21.60 | Large context, complex analysis |
| Anthropic | Claude 3 Sonnet | 8/10 | 9/10 | $6.30 | Balanced quality/cost |
| Anthropic | Claude 3 Haiku | 7/10 | 10/10 | $0.34 | High volume, simple tasks |
| Local | Llama 2 70B | 7/10 | 6/10 | $0 API** | Privacy, no API costs |

\* Based on avg 1000 input tokens, 200 output tokens, 40% cache hit rate  
\*\* Infrastructure costs apply

### Recommendation Matrix

```python
def recommend_provider(
    requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Recommend provider based on requirements.
    
    Args:
        requirements: {
            "volume": "low"|"medium"|"high",
            "quality_needed": "standard"|"high"|"best",
            "budget": "tight"|"moderate"|"flexible",
            "privacy_required": bool,
            "context_size": "small"|"large"
        }
    """
    
    # Privacy requirement
    if requirements.get("privacy_required"):
        return {
            "primary": "local-llama2",
            "reasoning": "Privacy requirements necessitate local deployment"
        }
    
    # Large context requirement
    if requirements.get("context_size") == "large":
        return {
            "primary": "claude-3-sonnet",
            "fallback": "claude-3-haiku",
            "reasoning": "200K context window needed"
        }
    
    # Budget and quality matrix
    budget = requirements.get("budget", "moderate")
    quality = requirements.get("quality_needed", "standard")
    volume = requirements.get("volume", "medium")
    
    if budget == "tight":
        if quality == "best":
            return {"error": "Cannot meet quality requirements with tight budget"}
        return {
            "primary": "claude-3-haiku",
            "reasoning": "Most cost-effective option"
        }
    
    if budget == "flexible":
        if quality == "best":
            return {
                "primary": "gpt-4",
                "fallback": "claude-3-opus",
                "reasoning": "Highest quality models"
            }
    
    # Default: Moderate budget, standard quality
    if volume == "high":
        return {
            "primary": "gpt-3.5-turbo",
            "upgrade_for_complex": "claude-3-sonnet",
            "reasoning": "Balance of cost and quality for high volume"
        }
    
    return {
        "primary": "claude-3-sonnet",
        "fallback": "gpt-3.5-turbo",
        "reasoning": "Best balance for moderate use"
    }
```

---

## ROI Analysis

### Cost-Benefit Framework

```python
class ROICalculator:
    """Calculate ROI for RAG system implementation."""
    
    def calculate_roi(
        self,
        implementation_costs: Dict[str, float],
        operational_costs_monthly: float,
        benefits_monthly: float,
        time_horizon_months: int = 12
    ) -> Dict[str, Any]:
        """
        Calculate ROI for RAG system.
        
        Args:
            implementation_costs: One-time costs (development, setup)
            operational_costs_monthly: Monthly operating costs
            benefits_monthly: Monthly value/savings generated
            time_horizon_months: Analysis period
            
        Returns:
            ROI metrics
        """
        # Total costs
        total_implementation = sum(implementation_costs.values())
        total_operational = operational_costs_monthly * time_horizon_months
        total_costs = total_implementation + total_operational
        
        # Total benefits
        total_benefits = benefits_monthly * time_horizon_months
        
        # Net benefit
        net_benefit = total_benefits - total_costs
        
        # ROI percentage
        roi_percentage = (net_benefit / total_costs * 100) if total_costs > 0 else 0
        
        # Payback period (months)
        if benefits_monthly > operational_costs_monthly:
            monthly_net = benefits_monthly - operational_costs_monthly
            payback_months = total_implementation / monthly_net if monthly_net > 0 else float('inf')
        else:
            payback_months = float('inf')
        
        return {
            "total_costs": total_costs,
            "total_benefits": total_benefits,
            "net_benefit": net_benefit,
            "roi_percentage": roi_percentage,
            "payback_period_months": payback_months,
            "break_even_month": payback_months,
            "monthly_roi": (benefits_monthly / (total_implementation / time_horizon_months + operational_costs_monthly)) - 1
        }


# Example ROI Calculation

# Implementation costs
implementation = {
    "development": 50000,  # Development time
    "setup": 5000,  # Infrastructure setup
    "training": 2000   # Team training
}

# Monthly operational costs
operational_monthly = 500  # LLM API + infrastructure

# Monthly benefits
# - Customer support time saved: $10,000
# - Improved customer satisfaction: $5,000
# - Reduced response time: $3,000
benefits_monthly = 18000

roi_calc = ROICalculator()
roi = roi_calc.calculate_roi(
    implementation_costs=implementation,
    operational_costs_monthly=operational_monthly,
    benefits_monthly=benefits_monthly,
    time_horizon_months=12
)

# Results:
# Total costs: $63,000
# Total benefits: $216,000
# Net benefit: $153,000
# ROI: 243%
# Payback period: 3.3 months
```

---

## Summary

### Cost Optimization Checklist

- [ ] Implement aggressive caching (40-60% savings)
- [ ] Use intelligent model selection (30-50% savings)
- [ ] Optimize token usage (20-30% savings)
- [ ] Set up budget limits and alerts
- [ ] Configure auto-downgrade strategy
- [ ] Implement cost monitoring dashboard
- [ ] Use tiered model approach for mixed workloads
- [ ] Consider local models for simple queries
- [ ] Batch process where possible
- [ ] Truncate overly long responses
- [ ] Regularly review and optimize

### Expected Cost Reductions

| Optimization Strategy | Impact | Effort | Priority |
|----------------------|--------|--------|----------|
| Caching | 40-60% | Low | HIGH |
| Model selection | 30-50% | Medium | HIGH |
| Token optimization | 20-30% | Medium | MEDIUM |
| Batch processing | 10-15% | Low | MEDIUM |
| Response truncation | 5-10% | Low | LOW |
| Local models | 50-70%* | High | MEDIUM |

\* For applicable queries only

### Cost Targets by Scale

| Scale | Daily Queries | Target Cost/Day | Target Cost/Month |
|-------|---------------|----------------|-------------------|
| Small (POC) | 100 | < $1 | < $30 |
| Medium (SMB) | 1,000 | < $10 | < $300 |
| Large (Enterprise) | 10,000 | < $100 | < $3,000 |
| Very Large | 100,000 | < $800 | < $24,000 |

---

**Document Status**: Complete  
**Phase 4 Design Documents**: Complete  
**Owner**: Software Architecture Agent
