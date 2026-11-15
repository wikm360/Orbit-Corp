-- Materialize ai.ledger_lines. The source query (ai_src.ledger_lines, ~700K rows x 8 joins) is too heavy to be evaluated per question: aggregating
-- views on top of it (counterparty_balances, vendor_balances, ...) took 30-100 s and hit the query timeout. The database is READ_ONLY and changes only
-- when a new company backup is restored (rahkaran-refresh re-runs this file every time), so a physical copy is always exactly as fresh as the view.
-- Public contract is unchanged: ai.ledger_lines is still a VIEW with the same columns (descriptions, catalogs and hints keep working); it just
-- reads the table ai.ledger_lines_mat (PAGE compressed, ~0.3-0.4 GB instead of 0.9 GB uncompressed).
IF OBJECT_ID('ai.ledger_lines_mat', 'U') IS NOT NULL DROP TABLE ai.ledger_lines_mat;
GO
SELECT * INTO ai.ledger_lines_mat FROM ai_src.ledger_lines;
GO
CREATE UNIQUE CLUSTERED INDEX cx_ledger_lines_mat ON ai.ledger_lines_mat (fiscal_year, voucher_date, line_id) WITH (DATA_COMPRESSION = PAGE);
GO
CREATE NONCLUSTERED INDEX ix_llm_counterparty ON ai.ledger_lines_mat (counterparty_dl_code) WITH (DATA_COMPRESSION = PAGE);
CREATE NONCLUSTERED INDEX ix_llm_account ON ai.ledger_lines_mat (gl_code, sl_code) WITH (DATA_COMPRESSION = PAGE);
CREATE NONCLUSTERED INDEX ix_llm_contract ON ai.ledger_lines_mat (contract_dl_code) WITH (DATA_COMPRESSION = PAGE);
CREATE NONCLUSTERED INDEX ix_llm_equipment ON ai.ledger_lines_mat (equipment_dl_code) WITH (DATA_COMPRESSION = PAGE);
CREATE NONCLUSTERED INDEX ix_llm_voucher ON ai.ledger_lines_mat (voucher_id) WITH (DATA_COMPRESSION = PAGE);
GO
-- Fail the whole refresh (the live database stays untouched) if the copy differs from the source.
DECLARE @src_rows bigint, @src_dr decimal(38,4), @src_cr decimal(38,4), @mat_rows bigint, @mat_dr decimal(38,4), @mat_cr decimal(38,4);
SELECT @src_rows = COUNT_BIG(*), @src_dr = SUM(CAST(debit AS decimal(38,4))), @src_cr = SUM(CAST(credit AS decimal(38,4))) FROM ai_src.ledger_lines;
SELECT @mat_rows = COUNT_BIG(*), @mat_dr = SUM(CAST(debit AS decimal(38,4))), @mat_cr = SUM(CAST(credit AS decimal(38,4))) FROM ai.ledger_lines_mat;
IF @mat_rows = 0 OR @src_rows <> @mat_rows OR ABS(ISNULL(@src_dr, 0) - ISNULL(@mat_dr, 0)) > 0.01 OR ABS(ISNULL(@src_cr, 0) - ISNULL(@mat_cr, 0)) > 0.01
    THROW 50001, N'ai.ledger_lines_mat does not match ai_src.ledger_lines (row count / debit / credit)', 1;
GO
CREATE OR ALTER VIEW ai.ledger_lines AS
SELECT * FROM ai.ledger_lines_mat;
GO
