from sqlalchemy import text

RULES = [
    """
    CREATE OR REPLACE FUNCTION audit_log_block_change() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log is append-only';
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS audit_log_no_change ON audit_log",
    """
    CREATE TRIGGER audit_log_no_change
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_block_change()
    """,
    "DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log",
    """
    CREATE TRIGGER audit_log_no_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_block_change()
    """,
]


def install_rules(engine):
    with engine.begin() as conn:
        for statement in RULES:
            conn.execute(text(statement))


if __name__ == "__main__":
    from app.db import engine
    install_rules(engine)
    print("Audit rules installed")