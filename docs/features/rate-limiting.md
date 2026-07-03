# Rate Limiting

## Features

- Per-user rate limiting
- Sliding window algorithm
- Configurable limits
- Stats endpoint

## Usage

```python
from features.rate_limiting import RateLimiter

limiter = RateLimiter(max_requests=100, window_seconds=60)
allowed = await limiter.check("user123")
stats = await limiter.get_stats("user123")
```
