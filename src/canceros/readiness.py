from sqlalchemy import text

from canceros.jobs import queue_for
from canceros.persistence import engine_for
from canceros.storage import PrivateStorage


def dependencies_ready(config):
    engine = None
    try:
        engine = engine_for(config)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        queue_for(config).ping()
        storage = PrivateStorage(config)
        storage.client.head_bucket(Bucket=storage.bucket)
        return (
            storage.client.get_bucket_versioning(Bucket=storage.bucket).get("Status") == "Enabled"
        )
    except Exception:
        return False
    finally:
        if engine is not None:
            engine.dispose()
