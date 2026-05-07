from config import get_settings
settings = get_settings()

# Upstash requires rediss:// (TLS). If the URL uses redis://, force SSL so
# Celery doesn't silently drop connection on Upstash's TLS-only port.
_redis_url = settings.redis_url
if _redis_url.startswith("redis://") and "upstash.io" in _redis_url:
    _redis_url = "rediss://" + _redis_url[len("redis://"):]

broker_url = _redis_url
result_backend = _redis_url

# Required when broker_url is rediss:// — disables cert verification for
# environments where the Upstash cert chain isn't in the system trust store.
broker_use_ssl = {"ssl_cert_reqs": "none"} if _redis_url.startswith("rediss://") else {}
redis_backend_use_ssl = {"ssl_cert_reqs": "none"} if _redis_url.startswith("rediss://") else {}
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
task_track_started = True
