-- Question 1: compare money and packs separately. No return refund is invented.
SELECT d.YearMonth, m.MedicineID, m.GenericName, c.SalesChannel, l.City, l.State,
       SUM(f.QuantitySoldPacks) AS SoldPacks,
       SUM(f.ReturnedQuantityPacks) AS ReturnedPacks,
       SUM(f.NetSalesAmountUSD) AS NetSalesUSD,
       SUM(f.GrossMarginUSD) AS GrossProfitUSD,
       ROUND(100.0*SUM(f.GrossMarginUSD)/NULLIF(SUM(f.NetSalesAmountUSD),0),2) AS GrossMarginPct
FROM FactPharmacySales f
JOIN DimMedicine m ON m.MedicineKey=f.MedicineKey
JOIN DimDate d ON d.DateKey=f.SalesDateKey
JOIN DimSalesProfile c ON c.SalesProfileKey=f.SalesProfileKey
JOIN DimPharmacy p ON p.PharmacyKey=f.PharmacyKey
JOIN DimLocation l ON l.LocationKey=p.LocationKey
GROUP BY d.YearMonth,m.MedicineID,m.GenericName,c.SalesChannel,l.City,l.State
ORDER BY d.YearMonth,NetSalesUSD DESC;
