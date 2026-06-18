# Creates tables directly for sqlite (bypassing alembic ALTER limitations)
from app.config import settings
from app.database import Base
import sqlalchemy as sa

# import models so they are registered on Base.metadata
import app.models.user
import app.models.patient
import app.models.medical_record
import app.models.lab_result
import app.models.audit_log

db_url = settings.DATABASE_URL
print('Creating tables in', db_url)

if db_url.startswith('sqlite'):
	# Use a synchronous sqlite engine for metadata.create_all
	sync_url = db_url.replace('sqlite+aiosqlite', 'sqlite')
	engine = sa.create_engine(sync_url)
	Base.metadata.create_all(bind=engine)
else:
	# Fallback: try to use sync_engine if available
	from app.database import engine as async_engine
	Base.metadata.create_all(bind=async_engine.sync_engine)

print('Done')
