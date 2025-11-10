# Configuration Strategy for LangChain RAG Integration
# Phase 4: Runtime Configuration and Provider Management

**Version:** 1.0  
**Date:** November 8, 2025  
**Status:** Design Document  
**Architect:** Software Architecture Agent

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Architecture](#configuration-architecture)
3. [LLM Provider Configuration](#llm-provider-configuration)
4. [Model Selection Strategy](#model-selection-strategy)
5. [Environment-Based Configuration](#environment-based-configuration)
6. [Feature Flags](#feature-flags)
7. [Cost Management Configuration](#cost-management-configuration)
8. [Performance Tuning](#performance-tuning)
9. [Security Configuration](#security-configuration)

---

## Overview

This document defines the configuration strategy for the LangChain RAG integration, enabling runtime provider selection, model configuration, and system behavior tuning without code changes.

### Configuration Principles

1. **Environment-Driven**: Configuration through environment variables
2. **Provider-Agnostic**: Easy switching between LLM providers
3. **Cost-Aware**: Built-in cost monitoring and limits
4. **Security-First**: Secure API key management
5. **Feature-Flexible**: Feature flags for gradual rollouts
6. **Performance-Tuned**: Configurable optimization parameters

---

## Configuration Architecture

### Configuration Layers

```
┌─────────────────────────────────────────────────────────────┐
│                  Configuration Hierarchy                     │
│                                                              │
│  1. Default Configuration (Code)                            │
│     ├─> Sensible defaults                                   │
│     └─> Fallback values                                     │
│                                                              │
│  2. Environment Variables (.env)                            │
│     ├─> Development/Production settings                     │
│     └─> Override defaults                                   │
│                                                              │
│  3. Configuration Files (config.yaml) [Optional]            │
│     ├─> Complex configurations                              │
│     └─> Template libraries                                  │
│                                                              │
│  4. Runtime Configuration (API/Admin Panel) [Future]        │
│     ├─> Dynamic adjustments                                 │
│     └─> A/B testing parameters                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Configuration Schema

```python
# app/infrastructure/config.py (EXTENDED)

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, SecretStr, validator

class LLMProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    
    provider_name: Literal["openai", "anthropic", "local"] = Field(...)
    api_key: Optional[SecretStr] = Field(default=None)
    api_base: Optional[str] = Field(default=None)
    model_name: str = Field(...)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0, le=8000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    timeout: int = Field(default=60, gt=0)
    max_retries: int = Field(default=3, ge=0)
    
    # Cost limits (per request)
    max_cost_per_request: Optional[float] = Field(default=None)
    
    # Provider-specific settings
    organization_id: Optional[str] = Field(default=None)  # OpenAI
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)


class RAGConfig(BaseModel):
    """Comprehensive RAG configuration."""
    
    # === Provider Selection ===
    default_provider: Literal["openai", "anthropic", "local"] = Field(default="openai")
    
    # Provider configurations
    openai_config: Optional[LLMProviderConfig] = Field(default=None)
    anthropic_config: Optional[LLMProviderConfig] = Field(default=None)
    local_config: Optional[LLMProviderConfig] = Field(default=None)
    
    # === Chain Configuration ===
    chain_type: Literal["stuff", "map_reduce", "refine", "map_rerank"] = Field(default="stuff")
    enable_streaming: bool = Field(default=True)
    enable_conversation_memory: bool = Field(default=True)
    memory_type: Literal["buffer", "summary", "vector"] = Field(default="buffer")
    
    # === Context Management ===
    max_context_tokens: int = Field(default=3500, gt=0)
    max_history_messages: int = Field(default=10, ge=0)
    context_diversity_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # === Retrieval Configuration ===
    retrieval_top_k: int = Field(default=5, gt=0, le=50)
    retrieval_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_multi_query: bool = Field(default=False)
    multi_query_variations: int = Field(default=3, ge=2, le=5)
    enable_reranking: bool = Field(default=False)
    reranking_model: Optional[str] = Field(default=None)
    
    # === Prompt Engineering ===
    default_template: str = Field(default="general_qa_v1")
    enable_few_shot: bool = Field(default=False)
    few_shot_examples_count: int = Field(default=3, ge=0, le=10)
    
    # === Quality & Safety ===
    enable_hallucination_detection: bool = Field(default=True)
    hallucination_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_citation_verification: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    enable_content_filtering: bool = Field(default=True)
    
    # === Performance ===
    enable_response_caching: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, gt=0)
    cache_backend: Literal["memory", "redis"] = Field(default="memory")
    enable_parallel_retrieval: bool = Field(default=False)
    parallel_workers: int = Field(default=3, ge=1, le=10)
    
    # === Cost Management ===
    enable_cost_tracking: bool = Field(default=True)
    daily_cost_limit: Optional[float] = Field(default=None)
    monthly_cost_limit: Optional[float] = Field(default=None)
    cost_alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    enable_auto_model_downgrade: bool = Field(default=False)
    
    # === Monitoring & Logging ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    enable_performance_metrics: bool = Field(default=True)
    enable_quality_metrics: bool = Field(default=True)
    metrics_export_interval: int = Field(default=60, gt=0)
    
    # === Feature Flags ===
    features: Dict[str, bool] = Field(default_factory=dict)
    
    @validator("openai_config", "anthropic_config", "local_config", pre=True, always=True)
    def ensure_provider_config(cls, v, values, field):
        """Ensure provider config exists for default provider."""
        if field.name == f"{values.get('default_provider')}_config" and v is None:
            raise ValueError(f"Configuration required for default provider: {values.get('default_provider')}")
        return v


class AppSettings(BaseSettings):
    """Extended application settings with RAG configuration."""
    
    # ... existing configurations ...
    
    # RAG Configuration
    rag: RAGConfig = Field(default_factory=RAGConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
```

---

## LLM Provider Configuration

### OpenAI Configuration

```bash
# .env configuration for OpenAI

# Provider Selection
RAG__DEFAULT_PROVIDER=openai

# OpenAI Specific Settings
RAG__OPENAI_CONFIG__PROVIDER_NAME=openai
RAG__OPENAI_CONFIG__API_KEY=sk-...
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-3.5-turbo
RAG__OPENAI_CONFIG__TEMPERATURE=0.7
RAG__OPENAI_CONFIG__MAX_TOKENS=2000
RAG__OPENAI_CONFIG__TOP_P=1.0
RAG__OPENAI_CONFIG__TIMEOUT=60
RAG__OPENAI_CONFIG__MAX_RETRIES=3
RAG__OPENAI_CONFIG__ORGANIZATION_ID=org-...
```

**Available OpenAI Models:**

| Model | Context Window | Cost (per 1K tokens) | Use Case |
|-------|----------------|---------------------|----------|
| gpt-4 | 8K | $0.03/$0.06 (in/out) | Complex queries, high quality |
| gpt-4-32k | 32K | $0.06/$0.12 (in/out) | Large context, comprehensive analysis |
| gpt-3.5-turbo | 4K | $0.0015/$0.002 (in/out) | General queries, cost-effective |
| gpt-3.5-turbo-16k | 16K | $0.003/$0.004 (in/out) | Medium context, balanced cost |

### Anthropic Configuration

```bash
# .env configuration for Anthropic Claude

# Provider Selection
RAG__DEFAULT_PROVIDER=anthropic

# Anthropic Specific Settings
RAG__ANTHROPIC_CONFIG__PROVIDER_NAME=anthropic
RAG__ANTHROPIC_CONFIG__API_KEY=sk-ant-...
RAG__ANTHROPIC_CONFIG__MODEL_NAME=claude-3-opus-20240229
RAG__ANTHROPIC_CONFIG__TEMPERATURE=0.7
RAG__ANTHROPIC_CONFIG__MAX_TOKENS=2000
RAG__ANTHROPIC_CONFIG__TIMEOUT=60
RAG__ANTHROPIC_CONFIG__MAX_RETRIES=3
```

**Available Anthropic Models:**

| Model | Context Window | Cost (per 1K tokens) | Use Case |
|-------|----------------|---------------------|----------|
| claude-3-opus | 200K | $0.015/$0.075 (in/out) | Highest capability, large context |
| claude-3-sonnet | 200K | $0.003/$0.015 (in/out) | Balanced performance/cost |
| claude-3-haiku | 200K | $0.00025/$0.00125 (in/out) | Fast, cost-effective |

### Local Model Configuration (Ollama)

```bash
# .env configuration for Local LLM via Ollama

# Provider Selection
RAG__DEFAULT_PROVIDER=local

# Local Model Settings
RAG__LOCAL_CONFIG__PROVIDER_NAME=local
RAG__LOCAL_CONFIG__API_BASE=http://localhost:11434
RAG__LOCAL_CONFIG__MODEL_NAME=llama2
RAG__LOCAL_CONFIG__TEMPERATURE=0.7
RAG__LOCAL_CONFIG__MAX_TOKENS=2000
RAG__LOCAL_CONFIG__TIMEOUT=120
```

**Supported Local Models (via Ollama):**

- `llama2` (7B, 13B, 70B)
- `mistral` (7B)
- `mixtral` (8x7B)
- `codellama` (7B, 13B, 34B)
- `phi-2` (2.7B)

---

## Model Selection Strategy

### Intelligent Model Selection

```python
class ModelSelector:
    """Select appropriate model based on query characteristics and constraints."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        # Model capability matrix
        self.model_capabilities = {
            "gpt-4": {
                "quality": 10,
                "speed": 5,
                "cost": 3,
                "context_window": 8192,
                "strengths": ["complex_reasoning", "accuracy", "consistency"]
            },
            "gpt-3.5-turbo": {
                "quality": 7,
                "speed": 9,
                "cost": 9,
                "context_window": 4096,
                "strengths": ["speed", "cost_efficiency"]
            },
            "claude-3-opus": {
                "quality": 10,
                "speed": 6,
                "cost": 2,
                "context_window": 200000,
                "strengths": ["large_context", "accuracy", "safety"]
            },
            "claude-3-haiku": {
                "quality": 7,
                "speed": 10,
                "cost": 10,
                "context_window": 200000,
                "strengths": ["speed", "cost_efficiency", "large_context"]
            },
            "llama2": {
                "quality": 6,
                "speed": 7,
                "cost": 10,  # Free (local)
                "context_window": 4096,
                "strengths": ["privacy", "no_api_costs", "offline_capable"]
            }
        }
    
    def select_model(
        self,
        query: str,
        context_size: int,
        priority: Literal["quality", "speed", "cost", "balanced"] = "balanced",
        conversation_history_size: int = 0
    ) -> str:
        """
        Select the most appropriate model.
        
        Args:
            query: User query
            context_size: Size of retrieved context (tokens)
            priority: Optimization priority
            conversation_history_size: Size of conversation history (tokens)
            
        Returns:
            Model name
        """
        # Calculate total token requirement
        total_tokens = (
            self._count_tokens(query) +
            context_size +
            conversation_history_size +
            500  # System prompt
        )
        
        # Analyze query complexity
        complexity = self._analyze_query_complexity(query)
        
        # Filter models by context window
        viable_models = {
            name: caps for name, caps in self.model_capabilities.items()
            if caps["context_window"] >= total_tokens
        }
        
        if not viable_models:
            raise ValueError(f"No model can handle {total_tokens} tokens")
        
        # Select based on priority
        if priority == "quality":
            return max(viable_models, key=lambda m: viable_models[m]["quality"])
        elif priority == "speed":
            return max(viable_models, key=lambda m: viable_models[m]["speed"])
        elif priority == "cost":
            return max(viable_models, key=lambda m: viable_models[m]["cost"])
        else:  # balanced
            if complexity == "complex":
                # Prefer quality for complex queries
                return self._select_quality_model(viable_models)
            else:
                # Prefer cost efficiency for simple queries
                return self._select_cost_efficient_model(viable_models)
    
    def _analyze_query_complexity(self, query: str) -> Literal["simple", "complex"]:
        """Determine query complexity."""
        indicators = {
            "complex": ["why", "how", "analyze", "compare", "explain in detail"],
            "simple": ["what", "when", "who", "list"]
        }
        
        query_lower = query.lower()
        complex_count = sum(1 for kw in indicators["complex"] if kw in query_lower)
        simple_count = sum(1 for kw in indicators["simple"] if kw in query_lower)
        
        # Also consider length
        if len(query.split()) > 20:
            complex_count += 1
        
        return "complex" if complex_count > simple_count else "simple"
    
    def _select_quality_model(self, models: Dict) -> str:
        """Select highest quality model within constraints."""
        return max(models, key=lambda m: models[m]["quality"])
    
    def _select_cost_efficient_model(self, models: Dict) -> str:
        """Select most cost-efficient model."""
        return max(models, key=lambda m: models[m]["cost"])
```

### Configuration Examples

**High-Quality, Cost-Unconstrained:**
```bash
RAG__DEFAULT_PROVIDER=openai
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-4
RAG__RETRIEVAL_TOP_K=10
RAG__ENABLE_RERANKING=true
RAG__ENABLE_HALLUCINATION_DETECTION=true
```

**Cost-Optimized:**
```bash
RAG__DEFAULT_PROVIDER=openai
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-3.5-turbo
RAG__RETRIEVAL_TOP_K=5
RAG__ENABLE_RESPONSE_CACHING=true
RAG__CACHE_TTL_SECONDS=7200
RAG__DAILY_COST_LIMIT=10.00
```

**Privacy-Focused (Local):**
```bash
RAG__DEFAULT_PROVIDER=local
RAG__LOCAL_CONFIG__MODEL_NAME=llama2
RAG__ENABLE_RESPONSE_CACHING=false
```

**Large Context:**
```bash
RAG__DEFAULT_PROVIDER=anthropic
RAG__ANTHROPIC_CONFIG__MODEL_NAME=claude-3-opus-20240229
RAG__MAX_CONTEXT_TOKENS=10000
RAG__RETRIEVAL_TOP_K=15
```

---

## Environment-Based Configuration

### Development Environment

```bash
# .env.development

# Development settings
ENVIRONMENT=development
DEBUG=true

# RAG Configuration - Development
RAG__DEFAULT_PROVIDER=openai
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-3.5-turbo  # Cheaper for dev
RAG__ENABLE_RESPONSE_CACHING=false  # Disable for testing
RAG__LOG_LEVEL=DEBUG
RAG__ENABLE_PERFORMANCE_METRICS=true
RAG__DAILY_COST_LIMIT=5.00  # Low limit for dev

# Relaxed constraints for testing
RAG__CONFIDENCE_THRESHOLD=0.5
RAG__RETRIEVAL_SCORE_THRESHOLD=0.6
```

### Testing Environment

```bash
# .env.testing

# Testing settings
ENVIRONMENT=testing

# RAG Configuration - Testing
RAG__DEFAULT_PROVIDER=local  # Use local for faster tests
RAG__LOCAL_CONFIG__MODEL_NAME=llama2
RAG__ENABLE_RESPONSE_CACHING=true
RAG__CACHE_BACKEND=memory
RAG__LOG_LEVEL=WARNING

# Strict validation for tests
RAG__ENABLE_HALLUCINATION_DETECTION=true
RAG__ENABLE_CITATION_VERIFICATION=true
```

### Production Environment

```bash
# .env.production

# Production settings
ENVIRONMENT=production
DEBUG=false

# RAG Configuration - Production
RAG__DEFAULT_PROVIDER=openai
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-4  # Best quality
RAG__ENABLE_RESPONSE_CACHING=true
RAG__CACHE_BACKEND=redis
RAG__CACHE_TTL_SECONDS=3600
RAG__LOG_LEVEL=INFO

# Production safety measures
RAG__ENABLE_HALLUCINATION_DETECTION=true
RAG__ENABLE_CITATION_VERIFICATION=true
RAG__ENABLE_CONTENT_FILTERING=true
RAG__CONFIDENCE_THRESHOLD=0.7

# Cost controls
RAG__DAILY_COST_LIMIT=100.00
RAG__MONTHLY_COST_LIMIT=3000.00
RAG__ENABLE_AUTO_MODEL_DOWNGRADE=true

# Performance optimization
RAG__ENABLE_PARALLEL_RETRIEVAL=true
RAG__PARALLEL_WORKERS=5
```

---

## Feature Flags

### Feature Flag Configuration

```python
class RAGFeatureFlags:
    """Feature flags for gradual rollout and A/B testing."""
    
    # Flag definitions
    FLAGS = {
        # Core features
        "rag_v2": {
            "description": "New RAG pipeline with improved retrieval",
            "default": False,
            "rollout_percentage": 0
        },
        "streaming_responses": {
            "description": "Enable streaming for real-time responses",
            "default": True,
            "rollout_percentage": 100
        },
        
        # Experimental features
        "multi_query_retrieval": {
            "description": "Generate multiple query variations",
            "default": False,
            "rollout_percentage": 10
        },
        "neural_reranking": {
            "description": "Use neural model for result reranking",
            "default": False,
            "rollout_percentage": 0
        },
        "hallucination_detection": {
            "description": "Active hallucination detection",
            "default": True,
            "rollout_percentage": 100
        },
        
        # Performance features
        "aggressive_caching": {
            "description": "Extended cache TTL and broader matching",
            "default": False,
            "rollout_percentage": 50
        },
        "parallel_retrieval": {
            "description": "Parallel execution of retrieval strategies",
            "default": False,
            "rollout_percentage": 0
        },
        
        # Quality features
        "gpt4_for_complex": {
            "description": "Use GPT-4 for complex queries",
            "default": False,
            "rollout_percentage": 25
        },
        "enhanced_citations": {
            "description": "More detailed source citations",
            "default": True,
            "rollout_percentage": 100
        }
    }
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.user_flags = config.features
    
    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if feature is enabled for user.
        
        Args:
            flag_name: Feature flag name
            user_id: User identifier for consistent hashing
            
        Returns:
            True if enabled for this user
        """
        # Check user-specific override
        if flag_name in self.user_flags:
            return self.user_flags[flag_name]
        
        # Get flag definition
        flag = self.FLAGS.get(flag_name)
        if not flag:
            return False
        
        # Check rollout percentage
        if user_id:
            return self._check_rollout(flag_name, user_id, flag["rollout_percentage"])
        else:
            return flag["default"]
    
    def _check_rollout(
        self,
        flag_name: str,
        user_id: str,
        percentage: int
    ) -> bool:
        """Consistent hash-based rollout."""
        import hashlib
        hash_val = int(hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest(), 16)
        return (hash_val % 100) < percentage
```

### Feature Flag Usage

```python
# In RAG service
class RAGService:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.feature_flags = RAGFeatureFlags(config)
    
    async def ask_question(self, query: str, user_id: str):
        # Check feature flags
        use_multi_query = self.feature_flags.is_enabled("multi_query_retrieval", user_id)
        use_reranking = self.feature_flags.is_enabled("neural_reranking", user_id)
        use_gpt4 = self.feature_flags.is_enabled("gpt4_for_complex", user_id)
        
        # Apply features conditionally
        if use_multi_query:
            queries = self._generate_query_variations(query)
        else:
            queries = [query]
        
        # ... rest of logic
```

---

## Cost Management Configuration

### Cost Tracking

```python
class CostTracker:
    """Track and enforce cost limits."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.daily_usage = 0.0
        self.monthly_usage = 0.0
        self.usage_log = []
    
    async def check_and_record(
        self,
        estimated_cost: float,
        query_type: str
    ) -> bool:
        """
        Check if request is within limits and record usage.
        
        Returns:
            True if within limits, False otherwise
        """
        # Check daily limit
        if self.config.daily_cost_limit:
            if self.daily_usage + estimated_cost > self.config.daily_cost_limit:
                return False
        
        # Check monthly limit
        if self.config.monthly_cost_limit:
            if self.monthly_usage + estimated_cost > self.config.monthly_cost_limit:
                return False
        
        # Record usage
        self.daily_usage += estimated_cost
        self.monthly_usage += estimated_cost
        
        self.usage_log.append({
            "timestamp": datetime.now(),
            "cost": estimated_cost,
            "query_type": query_type,
            "model": self.config.default_provider
        })
        
        # Check alert threshold
        if self.config.daily_cost_limit:
            if self.daily_usage >= (self.config.daily_cost_limit * self.config.cost_alert_threshold):
                await self._send_cost_alert("daily")
        
        return True
```

### Auto Model Downgrade

```python
class AutoModelDowngrade:
    """Automatically downgrade to cheaper models when approaching limits."""
    
    def __init__(self, config: RAGConfig, cost_tracker: CostTracker):
        self.config = config
        self.cost_tracker = cost_tracker
        
        # Model tier list (quality descending, cost descending)
        self.model_tiers = [
            ("openai", "gpt-4"),
            ("openai", "gpt-3.5-turbo-16k"),
            ("openai", "gpt-3.5-turbo"),
            ("anthropic", "claude-3-haiku"),
            ("local", "llama2")
        ]
    
    def get_appropriate_model(self) -> Tuple[str, str]:
        """
        Get model based on remaining budget.
        
        Returns:
            (provider, model) tuple
        """
        if not self.config.enable_auto_model_downgrade:
            return (self.config.default_provider, self.get_default_model())
        
        # Calculate budget pressure
        pressure = self._calculate_budget_pressure()
        
        if pressure < 0.5:
            # Low pressure - use preferred model
            return (self.config.default_provider, self.get_default_model())
        elif pressure < 0.8:
            # Medium pressure - downgrade one tier
            return self.model_tiers[1]
        else:
            # High pressure - use cheapest model
            return self.model_tiers[-1]
    
    def _calculate_budget_pressure(self) -> float:
        """Calculate how close we are to budget limits (0.0 to 1.0)."""
        pressures = []
        
        if self.config.daily_cost_limit:
            daily_pressure = self.cost_tracker.daily_usage / self.config.daily_cost_limit
            pressures.append(daily_pressure)
        
        if self.config.monthly_cost_limit:
            monthly_pressure = self.cost_tracker.monthly_usage / self.config.monthly_cost_limit
            pressures.append(monthly_pressure)
        
        return max(pressures) if pressures else 0.0
```

---

## Performance Tuning

### Performance Configuration

```bash
# Performance tuning parameters

# Cache configuration
RAG__ENABLE_RESPONSE_CACHING=true
RAG__CACHE_BACKEND=redis
RAG__CACHE_TTL_SECONDS=3600
RAG__CACHE_MAX_SIZE_MB=500

# Parallel processing
RAG__ENABLE_PARALLEL_RETRIEVAL=true
RAG__PARALLEL_WORKERS=5
RAG__PARALLEL_TIMEOUT_SECONDS=10

# Token optimization
RAG__MAX_CONTEXT_TOKENS=3500
RAG__ENABLE_CONTEXT_COMPRESSION=true
RAG__COMPRESSION_RATIO=0.7

# Retrieval optimization
RAG__RETRIEVAL_TOP_K=5
RAG__ENABLE_EARLY_STOPPING=true
RAG__MIN_RELEVANCE_IMPROVEMENT=0.05
```

### Timeout Configuration

```python
class TimeoutConfig(BaseModel):
    """Timeout settings for various operations."""
    
    # Retrieval timeouts
    embedding_generation_timeout: int = Field(default=10)
    vector_search_timeout: int = Field(default=5)
    
    # LLM timeouts
    llm_generation_timeout: int = Field(default=60)
    streaming_chunk_timeout: int = Field(default=5)
    
    # Cache timeouts
    cache_read_timeout: int = Field(default=1)
    cache_write_timeout: int = Field(default=2)
    
    # Total request timeout
    total_request_timeout: int = Field(default=90)
```

---

## Security Configuration

### API Key Management

```python
class SecureConfigLoader:
    """Secure configuration loading with encryption support."""
    
    @staticmethod
    def load_api_keys() -> Dict[str, str]:
        """
        Load API keys securely.
        
        Priority order:
        1. Environment variables
        2. Encrypted secrets file
        3. Cloud secrets manager (AWS Secrets Manager, Azure Key Vault)
        """
        keys = {}
        
        # Try environment variables first
        keys["openai"] = os.getenv("RAG__OPENAI_CONFIG__API_KEY")
        keys["anthropic"] = os.getenv("RAG__ANTHROPIC_CONFIG__API_KEY")
        
        # Fall back to secrets manager if configured
        if os.getenv("USE_SECRETS_MANAGER"):
            keys.update(SecureConfigLoader._load_from_secrets_manager())
        
        return keys
    
    @staticmethod
    def _load_from_secrets_manager() -> Dict[str, str]:
        """Load from cloud secrets manager."""
        # Implementation for AWS Secrets Manager, Azure Key Vault, etc.
        pass
```

### Configuration Validation

```python
class ConfigValidator:
    """Validate configuration security and correctness."""
    
    @staticmethod
    def validate(config: RAGConfig) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Security checks
        if config.default_provider == "openai":
            if not config.openai_config or not config.openai_config.api_key:
                issues.append("ERROR: OpenAI API key is required")
        
        # Cost safety checks
        if not config.enable_cost_tracking:
            issues.append("WARNING: Cost tracking is disabled")
        
        if not config.daily_cost_limit and not config.monthly_cost_limit:
            issues.append("WARNING: No cost limits set")
        
        # Performance checks
        if config.max_context_tokens > 10000:
            issues.append("WARNING: Very large context window may impact performance")
        
        if config.retrieval_top_k > 20:
            issues.append("WARNING: High top_k may increase costs and latency")
        
        # Feature compatibility checks
        if config.enable_streaming and config.chain_type == "map_reduce":
            issues.append("WARNING: Streaming not fully supported with map_reduce chain")
        
        return issues
```

---

## Configuration Examples

### Minimal Configuration

```bash
# Minimal .env for quick start
RAG__DEFAULT_PROVIDER=openai
RAG__OPENAI_CONFIG__API_KEY=sk-...
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-3.5-turbo
```

### Production-Ready Configuration

```bash
# Production .env with all bells and whistles

# Core Configuration
ENVIRONMENT=production
RAG__DEFAULT_PROVIDER=openai

# OpenAI Configuration
RAG__OPENAI_CONFIG__API_KEY=sk-...
RAG__OPENAI_CONFIG__MODEL_NAME=gpt-4
RAG__OPENAI_CONFIG__TEMPERATURE=0.7
RAG__OPENAI_CONFIG__MAX_TOKENS=2000
RAG__OPENAI_CONFIG__TIMEOUT=60
RAG__OPENAI_CONFIG__MAX_RETRIES=3

# Chain Configuration
RAG__CHAIN_TYPE=stuff
RAG__ENABLE_STREAMING=true
RAG__ENABLE_CONVERSATION_MEMORY=true
RAG__MEMORY_TYPE=summary

# Context Management
RAG__MAX_CONTEXT_TOKENS=3500
RAG__MAX_HISTORY_MESSAGES=10
RAG__CONTEXT_DIVERSITY_WEIGHT=0.3

# Retrieval Configuration
RAG__RETRIEVAL_TOP_K=5
RAG__RETRIEVAL_SCORE_THRESHOLD=0.7
RAG__ENABLE_RERANKING=true

# Quality & Safety
RAG__ENABLE_HALLUCINATION_DETECTION=true
RAG__HALLUCINATION_THRESHOLD=0.7
RAG__ENABLE_CITATION_VERIFICATION=true
RAG__CONFIDENCE_THRESHOLD=0.7
RAG__ENABLE_CONTENT_FILTERING=true

# Performance
RAG__ENABLE_RESPONSE_CACHING=true
RAG__CACHE_TTL_SECONDS=3600
RAG__CACHE_BACKEND=redis
RAG__ENABLE_PARALLEL_RETRIEVAL=true
RAG__PARALLEL_WORKERS=5

# Cost Management
RAG__ENABLE_COST_TRACKING=true
RAG__DAILY_COST_LIMIT=100.00
RAG__MONTHLY_COST_LIMIT=3000.00
RAG__COST_ALERT_THRESHOLD=0.8
RAG__ENABLE_AUTO_MODEL_DOWNGRADE=true

# Monitoring
RAG__LOG_LEVEL=INFO
RAG__ENABLE_PERFORMANCE_METRICS=true
RAG__ENABLE_QUALITY_METRICS=true
RAG__METRICS_EXPORT_INTERVAL=60
```

---

**Document Status**: Complete  
**Next Document**: Performance Optimization Plan  
**Owner**: Software Architecture Agent
