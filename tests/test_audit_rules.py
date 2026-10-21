import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.audit import verify_chain, write_audit
from app.db import SessionLocal, engine


def run(sql):
    with engine.begin() as conn:
        conn.execute(text(sql))


def test_audit_rows_cannot_be_changed_or_removed():
    with SessionLocal() as db:
        write_audit(db, None, "test", "allowed", None, "rule check")
    with pytest.raises(DBAPIError):
        run("update audit_log set detail = 'x' "
            "where id = (select max(id) from audit_log)")
    with pytest.raises(DBAPIError):
        run("delete from audit_log")
    with pytest.raises(DBAPIError):
        run("truncate audit_log")
    with SessionLocal() as db:
        assert verify_chain(db)[0] is True