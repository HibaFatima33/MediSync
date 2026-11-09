-- Question 2: consumed packs are the consistently named actual measure.
SELECT d.YearMonth,h.HospitalID,h.HospitalName,m.MedicineID,m.GenericName,
       SUM(f.ForecastDemandPacks) AS ForecastPacks,
       SUM(f.ConsumedQuantityPacks) AS ActualConsumedPacks,
       SUM(f.ForecastDemandPacks-f.ConsumedQuantityPacks) AS SignedForecastErrorPacks,
       SUM(f.UnfulfilledDemandPacks) AS UnmetPacks,
       SUM(f.RequestedQuantityPacks) AS RequestedPacks,
       SUM(f.ReceivedQuantityPacks) AS ReceivedPacks,
       ROUND(100.0*SUM(ABS(f.ForecastDemandPacks-f.ConsumedQuantityPacks)) /
             NULLIF(SUM(f.ConsumedQuantityPacks),0),2) AS WAPEPercent
FROM FactHospitalDemand f
JOIN DimHospital h ON h.HospitalKey=f.HospitalKey
JOIN DimMedicine m ON m.MedicineKey=f.MedicineKey
JOIN DimDate d ON d.DateKey=f.DemandDateKey
GROUP BY d.YearMonth,h.HospitalID,h.HospitalName,m.MedicineID,m.GenericName
ORDER BY d.YearMonth,UnmetPacks DESC,h.HospitalID,m.MedicineID;
