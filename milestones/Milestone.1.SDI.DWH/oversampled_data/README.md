# Oversampled SDI source data

## What “oversampled” means here

We kept the original SDI records and added synthetic demonstration records for January and February 2026. We did this to extend the data over more months so the warehouse queries and refresh demonstration have new periods to show. This is a synthetic time extension; it is not a statistical class-balancing method. The medicine master was not expanded.

## Record counts

| Dataset | Original rows | Added synthetic rows | Complete snapshot rows |
| --- | ---: | ---: | ---: |
| Medicine master | 63 | 0 | 63 |
| Pharmacy sales | 500,000 | 2,000 | 502,000 |
| Hospital demand | 27,216 | 1,512 | 28,728 |

Each generated month adds 1,000 sales rows and 756 hospital-demand rows. Existing records are retained.

## Folder contents

```text
oversampled_data/
  README.md
  manifest.json
  Milestone.1.SDI.DWH.Data.Dictionary.csv
  complete_snapshot/
    01_master_data.csv
    06_hospital_demand_data.csv
    sales_parts/                 11 ordered pieces of the complete sales file
      part-001.csv
      ...
      part-011.csv
  generated_demo_rows/           Only the synthetic rows, for inspection
    05_pharmacy_sales_data.csv
    06_hospital_demand_data.csv
  refresh_history/               Notes about the two included demo refreshes
    demo_state.json
    refresh_1_method.json
    refresh_2_method.json
```

The full sales snapshot is divided into 11 CSV pieces so each file stays within GitHub’s file-size limit. `manifest.json` lists their correct order, row counts and SHA-256 checksums. The restore script joins the pieces and verifies the reconstructed files.

`generated_demo_rows` is a separate inspection copy. Those rows are already included in `complete_snapshot`; do not append them again. The data dictionary explains the source columns, types, units, examples and generation rules.

## Restore the source files

From the project root, run:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\restore_oversampled_data.py
```

The script rebuilds the three pipeline input CSVs under `Project.Data.And.Results/data/demo_source`. It requires that destination not already contain those CSVs.
