import os
import subprocess

import pytest


@pytest.mark.integration
def test_real_postgres_migration_reaches_head():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set TEST_DATABASE_URL to an isolated PostgreSQL database")
    env = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
    result = subprocess.run(["alembic", "current"], check=True, env=env,
                            capture_output=True, text=True)
    assert "c4d9e721ab34" in result.stdout
