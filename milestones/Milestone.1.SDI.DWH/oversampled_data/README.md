# Oversampled SDI data

This folder contains the complete final source snapshot and a separate copy of only the generated rows. The added rows extend time coverage into January and February 2026. The method uses existing row templates and new IDs and dates. Each new month adds 1,000 sales and 756 hospital demand records. The medicine master remains at 63 medicines.

| Dataset | Original rows | Added rows | Final rows |
| --- | ---: | ---: | ---: |
| Medicine master | 63 | 0 | 63 |
| Pharmacy sales | 500000 | 2000 | 502000 |
| Hospital demand | 27216 | 1512 | 28728 |

The full sales snapshot is split into ordered parts of at most 50,000 rows so each CSV stays below GitHub's single-file limit. Read the parts in manifest order. Each part has the same header. The demand and master CSVs are stored as single files. generated_only repeats only the synthetic rows for inspection. Do not append generated_only to the complete snapshot because those rows are already included.

Milestone.1.SDI.DWH.Data.Dictionary.csv explains every source column, its type, units, a real example and the generation rule. manifest.json records expected counts and SHA256 hashes for checking the parts. generation contains the two recorded generation methods and completed refresh numbers. Reference fields and hospital context are reused from the original templates. The scope is the three selected SDI sources.

Run python restore_submission_data.py from the project root to rebuild the pipeline input CSVs in data/demo_source. This command verifies checksums, headers, row counts and a content hash before publishing the reconstructed files. It requires a destination with no existing source CSVs. Existing project users already have the full files in data/demo_source and can keep using those.
