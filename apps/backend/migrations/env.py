import os
from alembic import context
from sqlalchemy import create_engine
from logistics_backend.persistence.resource_models import metadata
from logistics_backend.persistence import runtime_models

url = os.environ["DATABASE_URL"]
if not url.startswith("postgresql+psycopg://"):
    raise ValueError("DATABASE_URL must use postgresql+psycopg")
if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
