-- 002-roles-add-source-file-and-previous-fit.sql
-- Adds two columns that db.py writes to but v0.1.0 init_db.py never created.
-- The runner treats "duplicate column" errors as success so council members
-- who hand-patched their DB are not blocked.

ALTER TABLE roles ADD COLUMN source_file  TEXT;
ALTER TABLE roles ADD COLUMN previous_fit REAL;
