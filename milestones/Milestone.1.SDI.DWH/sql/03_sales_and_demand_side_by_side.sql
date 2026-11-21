-- Question 3: aggregate both facts FIRST. Never add sales to consumption.
WITH sales AS (
 SELECT p.HospitalID,m.MedicineID,d.YearMonth,
        SUM(s.QuantitySoldPacks) AS PharmacySoldPacks,
        SUM(s.NetSalesAmountUSD) AS PharmacyNetSalesUSD
 FROM FactPharmacySales s
 JOIN DimPharmacy p ON p.PharmacyKey=s.PharmacyKey
 JOIN DimMedicine m ON m.MedicineKey=s.MedicineKey
 JOIN DimDate d ON d.DateKey=s.SalesDateKey
 WHERE p.PharmacyType='Hospital Pharmacy' AND p.HospitalID<>''
 GROUP BY p.HospitalID,m.MedicineID,d.YearMonth
), demand AS (
 SELECT h.HospitalID,m.MedicineID,d.YearMonth,
        SUM(f.ForecastDemandPacks) AS ForecastPacks,
        SUM(f.ConsumedQuantityPacks) AS ConsumedPacks,
        SUM(f.UnfulfilledDemandPacks) AS UnmetPacks
 FROM FactHospitalDemand f
 JOIN DimHospital h ON h.HospitalKey=f.HospitalKey
 JOIN DimMedicine m ON m.MedicineKey=f.MedicineKey
 JOIN DimDate d ON d.DateKey=f.DemandDateKey
 GROUP BY h.HospitalID,m.MedicineID,d.YearMonth
)
SELECT COALESCE(s.HospitalID,h.HospitalID) HospitalID,
       COALESCE(s.MedicineID,h.MedicineID) MedicineID,
       COALESCE(s.YearMonth,h.YearMonth) YearMonth,
       s.PharmacySoldPacks,s.PharmacyNetSalesUSD,h.ForecastPacks,h.ConsumedPacks,h.UnmetPacks,
       ROUND(100.0*s.PharmacySoldPacks/NULLIF(h.ConsumedPacks,0),2) AS SalesToConsumptionPct
FROM sales s FULL OUTER JOIN demand h USING(HospitalID,MedicineID,YearMonth)
ORDER BY YearMonth,HospitalID,MedicineID;
