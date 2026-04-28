# migrations/

Schema versioning for `pipeline.db`. The runner lives in `db/db.py`
(`_apply_migrations`) and is invoked by `db/init_db.py` and once per process
when `db.con()` is first called.

## Rules

1. **Filename format:** `NNN-short-name.sql` where `NNN` is a zero-padded
   integer. Files are applied in lexical order. The integer is the schema
   version recorded in the `schema_version` table.

2. **Append-only.** Once a migration has shipped (tagged release or pushed to
   `main`), do not edit it. To fix a mistake, write a new migration.

3. **Idempotent where possible.** Use `CREATE TABLE IF NOT EXISTS`,
   `CREATE INDEX IF NOT EXISTS`, etc. The migration runner skips files whose
   version is already in `schema_version`, but idempotency makes the system
   forgiving when council members upgrade from older builds.

4. **Pure SQL.** No Python data backfills here; do those in `db/db.py` if
   needed and have the migration just adjust the schema.

5. **One concern per migration.** Don't bundle "add column X" with "rename
   table Y" — review and rollback are easier with small, focused diffs.

## Bootstrapping v0.1.0 databases

`001-initial.sql` is written so that running it against a v0.1.0 `pipeline.db`
(which already has all the original tables) is a no-op for those tables — the
`IF NOT EXISTS` clauses skip them. The runner then records `version=1` in
`schema_version` and the DB is upgraded in place with no data loss.

## How the runner works

```
1. Open pipeline.db.
2. Try SELECT MAX(version) FROM schema_version. If the table doesn't exist,
   treat current version as 0.
3. List migrations/[0-9][0-9][0-9]-*.sql in lexical order.
4. For each migration whose version > current: executescript() it, then
   INSERT INTO schema_version (version, migration_name) VALUES (?, ?).
5. Commit per migration. If a migration raises, the runner rolls back and
   stops; subsequent migrations are not applied.
```

Run manually:

```bash
python3 db/init_db.py        # apply any pending migrations
```
