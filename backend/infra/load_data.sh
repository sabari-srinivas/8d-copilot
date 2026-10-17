#!/usr/bin/env bash
# Loads the synthetic plant (lots, process, maintenance, complaints) into BigQuery so
# PLANT_BACKEND=bigquery reads the same scenario as PLANT_BACKEND=csv (agent/tools/
# plant_data.py). Idempotent: safe to re-run — `bq mk --force` skips dataset creation if
# the dataset already exists, and every table load uses `--replace`, so a re-run
# overwrites rather than appends or duplicates rows.
#
# The GCS bucket, the docs/ prefix and the RAG corpus are already provisioned by earlier
# tasks (the bucket by infra/build_rag.py, which also uploaded data/docs/*.md) and are
# not touched here. The app never reads data/images from GCS — photos are uploaded by
# the user at investigation time through PLANT_BACKEND-independent multipart POSTs — so
# this script's job is the five BigQuery tables only. `capa_lots` is the historical
# CAPA-effectiveness seed table (data/constants.py HISTORICAL_CAPA_*, agent/tools/
# capa_check.py) — never joined with lots/process, so it carries no risk to the planted
# WO-388 drift story.
set -euo pipefail
: "${GCP_PROJECT:?}" "${GCP_REGION:?}" "${BQ_DATASET:?}"

OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../data/out" && pwd)"

echo "dataset: $GCP_PROJECT:$BQ_DATASET ($GCP_REGION)"
bq --location="$GCP_REGION" mk --dataset --force "$GCP_PROJECT:$BQ_DATASET"

for table in lots process maintenance complaints capa_lots; do
  csv="$OUT/$table.csv"
  [ -f "$csv" ] || { echo "missing $csv — run \`python -m data.generate_plant\` first" >&2; exit 1; }
  bq load --location="$GCP_REGION" --replace --autodetect --source_format=CSV \
     --skip_leading_rows=1 "$GCP_PROJECT:$BQ_DATASET.$table" "$csv"
  echo "loaded $table"
done

echo
echo "verification: average reflow peak temp by line (Line 2 should read visibly higher"
echo "— the planted drift, data/constants.py DRIFT_LOT_IDS, is all Line 2 lots)"
bq query --location="$GCP_REGION" --use_legacy_sql=false --format=pretty \
  "SELECT line, COUNT(*) AS lots, ROUND(AVG(p.reflow_peak_temp_c), 1) AS avg_peak_c
   FROM \`$GCP_PROJECT.$BQ_DATASET.lots\` l
   JOIN \`$GCP_PROJECT.$BQ_DATASET.process\` p USING (lot_id)
   GROUP BY line ORDER BY line"
