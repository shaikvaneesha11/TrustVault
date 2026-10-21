import os

from dotenv import load_dotenv

load_dotenv()

test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url:
    raise RuntimeError("Set TEST_DATABASE_URL in .env (a separate test database)")
if test_url == os.environ.get("DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")

# Point the whole app at the test database before it is imported.
os.environ["DATABASE_URL"] = test_url
os.environ["COOKIE_SECURE"] = "0"

from app.db import engine  # noqa: E402
from app.db_rules import install_rules  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(engine)
install_rules(engine)