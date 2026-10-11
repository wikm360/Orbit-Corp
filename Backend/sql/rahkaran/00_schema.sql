-- Semantic layer for the Rahkaran database ("ai" schema). Idempotent: safe to re-run after every restore.
IF SCHEMA_ID('ai') IS NULL EXEC('CREATE SCHEMA ai AUTHORIZATION dbo');
GO
