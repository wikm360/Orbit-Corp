-- Fixed-asset views (FAM3). Amounts in Rials. One calculation area exists (CalculationAreaRef = 1).

-- ai.asset_groups: asset class > asset group hierarchy with asset counts.
CREATE OR ALTER VIEW ai.asset_groups AS
SELECT g.AssetGroupID AS asset_group_id, g.Code AS asset_group_code, g.Title AS asset_group,
       c.AssetClassID AS asset_class_id, c.Code AS asset_class_code, c.Title AS asset_class,
       g.IsActive AS is_active,
       (SELECT COUNT(*) FROM FAM3.Asset a WHERE a.AssetGroupRef = g.AssetGroupID) AS asset_count
FROM FAM3.AssetGroup g
JOIN FAM3.AssetClass c ON c.AssetClassID = g.AssetClassRef;
GO

-- ai.asset_locations: places where assets are deployed (SettlementPlace: factories, projects, offices) with asset counts.
CREATE OR ALTER VIEW ai.asset_locations AS
SELECT sp.SettlementPlaceID AS location_id, sp.Code AS location_code, sp.Title AS location_name, sp.IsActive AS is_active,
       (SELECT COUNT(*) FROM FAM3.Asset a WHERE a.SettlementPlaceRef = sp.SettlementPlaceID) AS asset_count
FROM FAM3.SettlementPlace sp;
GO

-- ai.assets: one row per fixed asset with its CURRENT state and values. status: پلاک شده (active) / حذف شده (disposed) / فروش رفته (sold) / ...
-- cost, accumulated_depreciation, book_value come from FAM3.vwAssetCost (current). plaque_number is the asset tag number.
CREATE OR ALTER VIEW ai.assets AS
SELECT a.AssetID AS asset_id,
       a.PlaqueNumber AS plaque_number,
       a.OldPlaqueNumber AS old_plaque_number,
       a.Title AS asset_title,
       ag.asset_class, ag.asset_group, ag.asset_group_id,
       ia.State AS status_code,
       stl.Value AS status,
       CASE WHEN ia.State = 1 THEN 1 ELSE 0 END AS is_active_asset,
       CAST(a.UtilizationDate AS date) AS utilization_date,
       uc.jalali_date AS utilization_date_jalali,
       DATEDIFF(MONTH, a.UtilizationDate, GETDATE()) / 12.0 AS approx_age_years,
       sp.Title AS location_name,
       sp.Code AS location_code,
       RTRIM(cc.Name) AS cost_center_name,
       ccd.Code AS cost_center_dl_code,
       RTRIM(pr.Name) AS project_name,
       cp.Cost AS cost,
       cp.AccumulatedDeprecitionValue AS accumulated_depreciation,
       cp.BookValue AS book_value,
       cp.SalvageValue AS salvage_value,
       dsl.Value AS depreciation_state,
       dm.Title AS depreciation_method,
       main.UsefulLife AS useful_life_years,
       main.DepreciationRate AS depreciation_rate_percent,
       CAST(main.DepreciationCalculationStartDate AS date) AS depreciation_start_date,
       supp.Code AS supplier_dl_code,
       RTRIM(supp.Title) AS supplier_name,
       dp.FullName AS deliverer_name,
       cpa.FullName AS collector_name,
       phy.Value AS physical_location
FROM FAM3.Asset a
JOIN ai.asset_groups ag ON ag.asset_group_id = a.AssetGroupRef
LEFT JOIN FAM3.AssetInCalculationArea ia ON ia.AssetRef = a.AssetID AND ia.CalculationAreaRef = 1
LEFT JOIN SYS3.Lookup stl ON stl.Type = 'AssetState' AND stl.Code = ia.State
LEFT JOIN FAM3.vwAssetCost cp ON cp.AssetID = a.AssetID AND cp.CalculationAreaRef = 1
LEFT JOIN SYS3.Lookup dsl ON dsl.Type = 'DepreciationCalculationState' AND dsl.Code = cp.DepreciationState
LEFT JOIN FAM3.SettlementPlace sp ON sp.SettlementPlaceID = a.SettlementPlaceRef
LEFT JOIN GNR3.CostCenter cc ON cc.CostCenterID = a.CostCenterRef
LEFT JOIN FIN3.DL ccd ON ccd.DLTypeRef = 4 AND ccd.ReferenceID = cc.CostCenterID
LEFT JOIN GNR3.Project pr ON pr.ProjectID = a.ProjectRef
LEFT JOIN FIN3.DL supp ON supp.DLID = a.CounterPartRef
LEFT JOIN GNR3.Party dp ON dp.PartyID = a.DelivererRef
LEFT JOIN FAM3.Collector col ON col.CollectorID = a.CollectorRef
LEFT JOIN GNR3.Party cpa ON cpa.PartyID = col.PartyRef
LEFT JOIN SYS3.Lookup phy ON phy.Type = 'PhysicalLocationType' AND phy.Code = a.PhysicalLocation
LEFT JOIN ai.calendar uc ON uc.gregorian_date = CAST(a.UtilizationDate AS date)
OUTER APPLY (SELECT TOP 1 c.UsefulLife, c.DepreciationRate, c.DepreciationCalculationStartDate, c.DepreciationMethodRef
             FROM FAM3.CostPart c WHERE c.AssetRef = a.AssetID AND c.IsActive = 1 AND c.CalculationAreaRef = 1
             ORDER BY c.CostType, c.CostPartID) main
LEFT JOIN FAM3.DepreciationMethod dm ON dm.DepreciationMethodID = main.DepreciationMethodRef;
GO

-- ai.asset_value_by_group: current cost / accumulated depreciation / book value per asset class, group and status.
CREATE OR ALTER VIEW ai.asset_value_by_group AS
SELECT asset_class, asset_group, status, COUNT(*) AS asset_count,
       SUM(ISNULL(cost, 0)) AS cost, SUM(ISNULL(accumulated_depreciation, 0)) AS accumulated_depreciation, SUM(ISNULL(book_value, 0)) AS book_value
FROM ai.assets
GROUP BY asset_class, asset_group, status;
GO

-- ai.asset_value_by_location_cost_center: current values per location and cost center (active assets only).
CREATE OR ALTER VIEW ai.asset_value_by_location AS
SELECT location_name, cost_center_name, project_name, COUNT(*) AS asset_count,
       SUM(ISNULL(cost, 0)) AS cost, SUM(ISNULL(accumulated_depreciation, 0)) AS accumulated_depreciation, SUM(ISNULL(book_value, 0)) AS book_value
FROM ai.assets
WHERE is_active_asset = 1
GROUP BY location_name, cost_center_name, project_name;
GO

-- ai.asset_transactions: the history of every asset event (acquisition, depreciation run, transfer, sale, elimination ...).
-- transaction_type: تحصیل، محاسبه استهلاک، فروش، حذف، انتقال داخلی، استقرار، مخارج پس از تحصیل، خروج از سازمان ...
-- Depreciation-run rows (type 2) are ~92% of the table: filter on transaction_type_code <> 2 for business events.
CREATE OR ALTER VIEW ai.asset_transactions AS
SELECT t.AssetTransactionID AS transaction_id,
       t.AssetRef AS asset_id,
       a.PlaqueNumber AS plaque_number,
       a.Title AS asset_title,
       t.TransactionType AS transaction_type_code,
       tt.Value AS transaction_type,
       t.AssetState AS asset_state_code,
       ast.Value AS asset_state_after,
       t.DocumentState AS document_state_code,
       ds.Value AS document_state,
       t.DocumentNumber AS document_number,
       CAST(t.DocumentDate AS date) AS document_date,
       c.jalali_date,
       c.jalali_ym,
       t.FiscalYearRef AS fiscal_year_id,
       c.fiscal_year,
       sp.Title AS location_name,
       RTRIM(cc.Name) AS cost_center_name,
       RTRIM(pr.Name) AS project_name,
       ag.Title AS asset_group
FROM FAM3.AssetTransaction t
JOIN FAM3.Asset a ON a.AssetID = t.AssetRef
JOIN ai.calendar c ON c.gregorian_date = CAST(t.DocumentDate AS date)
LEFT JOIN SYS3.Lookup tt ON tt.Type = 'AssetTransactionType' AND tt.Code = t.TransactionType
LEFT JOIN SYS3.Lookup ast ON ast.Type = 'AssetState' AND ast.Code = t.AssetState
LEFT JOIN SYS3.Lookup ds ON ds.Type = 'DocumentState' AND ds.Code = t.DocumentState
LEFT JOIN FAM3.SettlementPlace sp ON sp.SettlementPlaceID = t.SettlementPlaceRef
LEFT JOIN GNR3.CostCenter cc ON cc.CostCenterID = t.CostCenterRef
LEFT JOIN GNR3.Project pr ON pr.ProjectID = t.ProjectRef
LEFT JOIN FAM3.AssetGroup ag ON ag.AssetGroupID = t.AssetGroupRef;
GO

-- ai.asset_depreciation: depreciation per asset and depreciation run (monthly): the amount charged, the accumulated depreciation and the cost after the run.
CREATE OR ALTER VIEW ai.asset_depreciation AS
SELECT d.DepreciationID AS depreciation_id, d.AssetRef AS asset_id, a.PlaqueNumber AS plaque_number, a.Title AS asset_title,
       ag.asset_class, ag.asset_group,
       CAST(d.Date AS date) AS depreciation_date, c.jalali_date, c.jalali_ym, c.jalali_month_name, d.FiscalYearRef AS fiscal_year_id, c.fiscal_year,
       x.depreciation_amount, x.accumulated_depreciation, x.cost, x.duration_days,
       RTRIM(cc.Name) AS cost_center_name, sp.Title AS location_name
FROM FAM3.Depreciation d
JOIN FAM3.Asset a ON a.AssetID = d.AssetRef
JOIN ai.asset_groups ag ON ag.asset_group_id = a.AssetGroupRef
JOIN ai.calendar c ON c.gregorian_date = CAST(d.Date AS date)
CROSS APPLY (SELECT SUM(p.DepreciationValue) AS depreciation_amount, SUM(p.AccumulatedDepreciationValue) AS accumulated_depreciation,
                    SUM(p.Cost) AS cost, MAX(p.Duration) AS duration_days
             FROM FAM3.CostPartTransaction p WHERE p.AssetTransactionRef = d.AssetTransactionRef) x
LEFT JOIN FAM3.AssetTransaction t ON t.AssetTransactionID = d.AssetTransactionRef
LEFT JOIN GNR3.CostCenter cc ON cc.CostCenterID = t.CostCenterRef
LEFT JOIN FAM3.SettlementPlace sp ON sp.SettlementPlaceID = t.SettlementPlaceRef;
GO

-- ai.depreciation_summary_month: depreciation expense per Jalali month and asset class/group.
CREATE OR ALTER VIEW ai.depreciation_summary_month AS
SELECT fiscal_year, jalali_ym, MAX(jalali_month_name) AS jalali_month_name, asset_class, asset_group,
       COUNT(DISTINCT asset_id) AS asset_count, SUM(depreciation_amount) AS depreciation_amount
FROM ai.asset_depreciation
GROUP BY fiscal_year, jalali_ym, asset_class, asset_group;
GO

-- ai.asset_acquisitions: purchase / acquisition receipts per asset line: supplier, amount, tag number, group, location, cost center.
CREATE OR ALTER VIEW ai.asset_acquisitions AS
SELECT r.AcquisitionReceiptID AS receipt_id, r.Number AS receipt_number, CAST(r.Date AS date) AS receipt_date, c.jalali_date, c.fiscal_year,
       acq.Value AS acquisition_type, rs.Value AS receipt_state, RTRIM(supp.Title) AS supplier_name, supp.Code AS supplier_dl_code,
       i.AcquisitionReceiptItemID AS item_id, i.RowNumber AS line_no, i.AssetRef AS asset_id, i.PlaqueNumber AS plaque_number, i.Title AS item_title,
       ag.asset_class, ag.asset_group, i.PurchaseAmount AS purchase_amount, CAST(i.UtilizationDate AS date) AS utilization_date,
       sp.Title AS location_name, RTRIM(cc.Name) AS cost_center_name, RTRIM(pr.Name) AS project_name, r.Description AS description
FROM FAM3.AcquisitionReceipt r
JOIN FAM3.AcquisitionReceiptItem i ON i.AcquisitionReceiptRef = r.AcquisitionReceiptID
JOIN ai.calendar c ON c.gregorian_date = CAST(r.Date AS date)
LEFT JOIN SYS3.Lookup acq ON acq.Type = 'AcquisitionType' AND acq.Code = r.AcquisitionType
LEFT JOIN SYS3.Lookup rs ON rs.Type = 'AcquisitionReceiptState' AND rs.Code = r.State
LEFT JOIN FIN3.DL supp ON supp.DLID = r.CounterPartRef
LEFT JOIN ai.asset_groups ag ON ag.asset_group_id = i.AssetGroupRef
LEFT JOIN FAM3.SettlementPlace sp ON sp.SettlementPlaceID = i.SettlementPlaceRef
LEFT JOIN GNR3.CostCenter cc ON cc.CostCenterID = i.CostCenterRef
LEFT JOIN GNR3.Project pr ON pr.ProjectID = i.ProjectRef;
GO

-- ai.asset_sales: assets sold (FAM3.Sales + SalesItem): buyer, sale amount, date. Combine with ai.assets for the book value.
CREATE OR ALTER VIEW ai.asset_sales AS
SELECT s.SalesID AS sale_id, s.Number AS sale_number, CAST(s.Date AS date) AS sale_date, c.jalali_date, c.fiscal_year,
       RTRIM(buyer.Title) AS buyer_name, buyer.Code AS buyer_dl_code,
       i.AssetRef AS asset_id, a.PlaqueNumber AS plaque_number, a.Title AS asset_title, ag.asset_class, ag.asset_group,
       i.SalesAmount AS sales_amount, i.NetSales AS net_sales, i.Description AS item_description, s.Description AS description
FROM FAM3.Sales s
JOIN FAM3.SalesItem i ON i.SalesRef = s.SalesID
JOIN FAM3.Asset a ON a.AssetID = i.AssetRef
JOIN ai.asset_groups ag ON ag.asset_group_id = a.AssetGroupRef
JOIN ai.calendar c ON c.gregorian_date = CAST(s.Date AS date)
LEFT JOIN FIN3.DL buyer ON buyer.DLID = s.CounterPartRef;
GO

-- ai.asset_disposals: assets eliminated / written off (FAM3.Elimination + EliminationItem).
CREATE OR ALTER VIEW ai.asset_disposals AS
SELECT e.EliminationID AS elimination_id, e.Number AS elimination_number, CAST(e.Date AS date) AS elimination_date, c.jalali_date, c.fiscal_year,
       i.AssetRef AS asset_id, a.PlaqueNumber AS plaque_number, a.Title AS asset_title, ag.asset_class, ag.asset_group,
       i.Description AS item_description, e.Description AS description
FROM FAM3.Elimination e
JOIN FAM3.EliminationItem i ON i.EliminationRef = e.EliminationID
JOIN FAM3.Asset a ON a.AssetID = i.AssetRef
JOIN ai.asset_groups ag ON ag.asset_group_id = a.AssetGroupRef
JOIN ai.calendar c ON c.gregorian_date = CAST(e.Date AS date);
GO

-- ai.asset_transfers: internal transfers of assets between locations / cost centers / custodians (destination attributes of each transferred asset).
CREATE OR ALTER VIEW ai.asset_transfers AS
SELECT t.InternalTransferID AS transfer_id, t.Number AS transfer_number, CAST(t.Date AS date) AS transfer_date, c.jalali_date, c.fiscal_year,
       i.AssetRef AS asset_id, a.PlaqueNumber AS plaque_number, a.Title AS asset_title,
       sp.Title AS destination_location, RTRIM(cc.Name) AS destination_cost_center, RTRIM(pr.Name) AS destination_project,
       dp.FullName AS new_deliverer, i.Description AS item_description, t.Description AS description
FROM FAM3.InternalTransfer t
JOIN FAM3.InternalTransferItem i ON i.InternalTransferRef = t.InternalTransferID
JOIN FAM3.Asset a ON a.AssetID = i.AssetRef
JOIN ai.calendar c ON c.gregorian_date = CAST(t.Date AS date)
LEFT JOIN FAM3.SettlementPlace sp ON sp.SettlementPlaceID = i.SettlementPlaceRef
LEFT JOIN GNR3.CostCenter cc ON cc.CostCenterID = i.CostCenterRef
LEFT JOIN GNR3.Project pr ON pr.ProjectID = i.ProjectRef
LEFT JOIN GNR3.Party dp ON dp.PartyID = i.DelivererRef;
GO

-- ai.asset_attributes: free attributes of assets (manufacturer, serial, model, tonnage ...): FAM3.AssetExtraField / AssetExtraFieldValue.
CREATE OR ALTER VIEW ai.asset_attributes AS
SELECT v.AssetRef AS asset_id, a.PlaqueNumber AS plaque_number, a.Title AS asset_title, f.Title AS attribute_name, v.Value AS attribute_value
FROM FAM3.AssetExtraFieldValue v
JOIN FAM3.AssetExtraField f ON f.AssetExtraFieldID = v.AssetExtraFieldRef
JOIN FAM3.Asset a ON a.AssetID = v.AssetRef;
GO

-- ai.asset_ledger_reconciliation: current fixed-asset sub-ledger vs general ledger (all history, state 4/32) for cost (GL 1210 excluding the control SL 121013)
-- and accumulated depreciation (GL 1211). difference = ledger - asset module. Useful to answer "does the asset register match the books?".
CREATE OR ALTER VIEW ai.asset_ledger_reconciliation AS
SELECT x.item, x.asset_module_amount, x.ledger_amount, x.ledger_amount - x.asset_module_amount AS difference
FROM (
    SELECT N'بهای تمام‌شده دارایی‌های ثابت (فقط دارایی‌های فعال)' AS item,
           (SELECT SUM(ISNULL(cost,0)) FROM ai.assets WHERE is_active_asset = 1) AS asset_module_amount,
           (SELECT SUM(net_debit) FROM ai.ledger_lines WHERE is_valid_for_reports = 1 AND gl_code = '1210' AND sl_code <> '121013') AS ledger_amount
    UNION ALL
    SELECT N'استهلاک انباشته (فقط دارایی‌های فعال)',
           (SELECT SUM(ISNULL(accumulated_depreciation,0)) FROM ai.assets WHERE is_active_asset = 1),
           (SELECT -SUM(net_debit) FROM ai.ledger_lines WHERE is_valid_for_reports = 1 AND gl_code = '1211')
) x;
GO
