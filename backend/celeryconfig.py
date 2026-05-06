from config import get_settings
settings = get_settings()
broker_url = settings.redis_url
result_backend = settings.redis_url
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
task_track_started = True
