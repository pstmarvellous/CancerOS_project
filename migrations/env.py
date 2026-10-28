from alembic import context
from sqlalchemy import create_engine

from canceros.settings import Settings

config = Settings()
if not config.database_url:
    raise RuntimeError("Private database configuration required")
engine = create_engine(config.database_url.get_secret_value(), hide_parameters=True)
with engine.connect() as connection:
    # Serialize migration launchers before Alembic checks/creates its version table.
    connection.exec_driver_sql("SELECT pg_advisory_lock(193304)")
    connection.commit()
    try:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.exec_driver_sql("SELECT pg_advisory_unlock(193304)")
        connection.commit()
