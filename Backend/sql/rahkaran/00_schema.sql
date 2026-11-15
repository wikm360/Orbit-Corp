-- Semantic layer for the Rahkaran database ("ai" schema). Idempotent: safe to re-run after every restore.
IF SCHEMA_ID('ai') IS NULL EXEC('CREATE SCHEMA ai AUTHORIZATION dbo');
GO
-- Hidden build schema: holds the heavy source query of ai.ledger_lines. The reader has NO rights on it and it is not in the catalogs.
IF SCHEMA_ID('ai_src') IS NULL EXEC('CREATE SCHEMA ai_src AUTHORIZATION dbo');
GO
