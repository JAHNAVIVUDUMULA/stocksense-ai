import pytest
from app.database.base import Base
from app.database.session import engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database tables are created before running tests."""
    Base.metadata.create_all(bind=engine)
    yield
