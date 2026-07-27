# DVH Service (DICOM_solver)

A service that computes **Dose Volume Histograms (DVH)** from radiotherapy DICOM data.

It runs two things in one process:

1. **A RabbitMQ consumer** — the main path. Receives a `study_instance_uid`, looks up that study's DICOM files in Postgres, computes DVH curves for every structure, and writes the results to Postgres and GraphDB.
2. **A FastAPI HTTP server** on port `8000` — for on-demand single-structure queries and for re-running a study.

Repository: `mdw-nl/DVH_Consumer` · Image: `ghcr.io/mdw-nl/dvh_consumer`

---

## Table of contents

- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Database schema](#database-schema)
- [Configuration](#configuration)
- [Running the service](#running-the-service)
- [HTTP API](#http-api)
- [Dose handling and summation](#dose-handling-and-summation)
- [ROI combination and standardized names](#roi-combination-and-standardized-names)
- [DVH metrics produced](#dvh-metrics-produced)
- [File cleanup (`DELETE_END`)](#file-cleanup-delete_end)
- [Monitoring and troubleshooting](#monitoring-and-troubleshooting)
- [Development](#development)
- [Known gotchas](#known-gotchas)
- [Project layout](#project-layout)

---

## How it works

This service does **not** receive DICOM files directly. An upstream listener stores the files on a shared filesystem, records one row per file in the `dicom_insert` table, and then publishes the study UID to RabbitMQ. This service consumes that UID.

```
Upstream listener ──> writes DICOM files to shared disk
                 └──> INSERT rows into dicom_insert
                 └──> publish study_instance_uid ──> RabbitMQ queue "DICOM_Processor"
                                                          │
                                                          ▼
                                              ┌────────────────────────┐
                                              │  This service          │
                                              │  callback_tread()      │
                                              └────────────────────────┘
                                                          │
   1. ack message immediately, look up patient_id         │
   2. query dicom_insert by study_instance_uid            │
   3. verify required modalities are present              │
   4. group files into DicomBundles                       │
   5. triage / sum RT Doses                               │
   6. compute DVH per structure                           │
   7. write dvh_results + calculation_status              │
   8. upload JSON-LD to GraphDB                           │
   9. delete source files if DELETE_END                   │
```

### The bundle model

A **`DicomBundle`** is one unit of DVH calculation: one RT Plan + one RT Struct + one *effective dose* + optionally the CT series directory.

Bundles are built in [`collect_patients_dicom`](DICOM_solver/dicom_operation.py) by fanning out:

- Plan UIDs are collected from the `referenced_rt_plan_uid` of **RTDOSE rows only** (this is what links doses to their plan).
- For each plan UID, its RT Doses are triaged into one or more *effective doses* (see [dose summation](#dose-handling-and-summation)).
- The result is one bundle per **(plan × struct × effective dose)** combination.

So a study with 1 plan, 1 struct, and 2 independent PLAN doses produces 2 bundles → 2 sets of DVH rows, distinguishable by the `rt_plan_path` / `rt_dose_paths` / `effective_dose_type` columns.

### Modality verification

Before any calculation, [`verify_full`](DICOM_solver/dicom_operation.py) checks that each patient in the study has `RTSTRUCT`, `RTPLAN`, `RTDOSE`, and — if `dvh-settings.ct_required` is `true` — `CT`. If anything is missing, the study fails with a message listing which modalities *were* present.

### RTSTRUCT fallback

Some studies arrive without an RTSTRUCT because the struct lives under a different study UID for the same patient. [`get_all_uid`](DICOM_solver/utilities.py) handles this: if the study query returns no RTSTRUCT row, it pulls the **single most recent RTSTRUCT for that same `patient_id`** and appends it, logging a warning.

Everything else (RTPLAN, RTDOSE, CT) still comes strictly from the study UID query, and the result set is then filtered to rows matching the study's expected `patient_id`.

---

## Prerequisites

| Dependency | Purpose | Required |
|---|---|---|
| **PostgreSQL** | Reads `dicom_insert`; writes `dvh_results` and `calculation_status` | Yes |
| **RabbitMQ** | Source of study UIDs to process | Yes for the consumer; the HTTP API works without it |
| **Shared filesystem** | The DICOM files referenced by `dicom_insert.file_path` must be readable at the same paths inside this container | Yes |
| **GraphDB + upload API** | JSON-LD result upload | Optional — failures are logged and do not fail the calculation |

Python 3.12 (per the Dockerfile). `libgl1` and `libglib2.0-0` system packages are needed by `rt_utils`.

---

## Database schema

### `dicom_insert` (read-only — owned by the upstream listener)

The service queries these columns:

| Column | Used for |
|---|---|
| `study_instance_uid` | Primary lookup key |
| `patient_id` | Grouping and the patient-based API path |
| `modality` | `CT` / `RTSTRUCT` / `RTPLAN` / `RTDOSE` |
| `file_path` | Absolute path to the file on the shared disk |
| `sop_instance_uid` | Matching an RT Plan to a dose's `referenced_rt_plan_uid` |
| `referenced_rt_plan_uid` | Linking RT Doses to their plan (`"UNKNOWN"`/NULL are skipped) |
| `timestamp` | Ordering for the RTSTRUCT fallback |

### `dvh_results` (written)

```sql
CREATE TABLE IF NOT EXISTS dvh_results (
    id                  bigserial PRIMARY KEY,
    patient_id          text,
    study_uid           text,
    structure_name      text,
    min_dose_gy         double precision,
    mean_dose_gy        double precision,
    max_dose_gy         double precision,
    volume_cc           double precision,
    color               text,          -- "r,g,b"
    metrics             jsonb,         -- {"V10": 12.3, "D95": 45.6, ...}
    dvh_points          jsonb,         -- [{"d_point": .., "v_point": ..}, ...]
    payload             jsonb,         -- the full structure output object
    rt_plan_path        text,          -- which plan produced this row
    rt_dose_paths       jsonb,         -- which dose file(s) contributed
    effective_dose_type text,          -- SINGLE | PLAN | BEAM | FRACTION |
                                       -- SUMMED_BEAM | SUMMED_FRACTION | FALLBACK
    created_at          timestamptz DEFAULT now()
);
```

One row per structure per bundle. Rows are **appended, never replaced** — re-running a study adds a second generation of rows; distinguish them by `created_at`.

### `calculation_status` (written)

```sql
CREATE TABLE IF NOT EXISTS calculation_status (
    id         bigserial PRIMARY KEY,
    study_uid  text,
    status     boolean,      -- true = success, false = failure
    timestamp  timestamp,
    patient_id text,
    error      jsonb         -- {"type": ..., "message": ..., "traceback": ...} on failure
);
```

One row per processing attempt. The `error` column holds the exception type, message (truncated to 2000 chars), and traceback (truncated to 5000 chars).

### Migration for existing deployments

If you are upgrading from a version before dose summation landed, add the four new columns before starting the new build — otherwise every insert fails:

```sql
ALTER TABLE calculation_status ADD COLUMN IF NOT EXISTS error jsonb;
ALTER TABLE dvh_results
  ADD COLUMN IF NOT EXISTS rt_plan_path text,
  ADD COLUMN IF NOT EXISTS rt_dose_paths jsonb,
  ADD COLUMN IF NOT EXISTS effective_dose_type text;
```

`text` works instead of `jsonb` for the JSON columns — the code passes `json.dumps()` strings either way.

---

## Configuration

### `DICOM_solver/Config/config.yaml`

The single config file the service reads. It is **baked into the Docker image** and read from the package directory — there is no environment-variable override, so changing it means rebuilding the image or bind-mounting over the file.

```yaml
rabbitMQ:
  host: "host.docker.internal"
  port: "5672"
  username: "user"
  password: "password"
  queue_name: "DICOM_Processor"

postgres:
  host: "host.docker.internal"
  port: "5432"
  username: "postgres"
  password: "postgres"
  db: "postgres"

GraphDB:
  host: "host.docker.internal"
  port: "7200"
  repo: "protrait"

API:                      # the intermediate upload service that fronts GraphDB
  host: "host.docker.internal"
  port: "8666"

V-values: [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60]
D-values: [20, 30, 40, 50, 60, 95, 98]

dvh-settings:
  ct_required: true       # false = CT optional; ROI combination and renaming are then skipped

dvh-calculations:         # ROI combinations to create before calculating
  - P-LUNG:
      roi: "Lung_L + Lung_R"
  - MeanDoseIpsiLateralParotidGland:
      roi: "Parotid_Ipsilateral"
```

| Key | Meaning |
|---|---|
| `rabbitMQ` | Broker connection and queue name |
| `postgres` | Database connection |
| `GraphDB` | Target repository — the URL becomes `http://{host}:{port}/repositories/{repo}/statements` |
| `API` | The `/upload_json` service that actually posts to GraphDB |
| `V-values` | Which `Vx` metrics to compute (volume receiving ≥ x Gy) |
| `D-values` | Which `Dx` metrics to compute (dose to x% of volume) |
| `dvh-settings.ct_required` | Whether CT is mandatory for a study to be considered complete |
| `dvh-calculations` | ROI combination expressions — see below |

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `DELETE_END` | `false` in code, **`True` in the Dockerfile** | Delete all source DICOM files after a successful study |
| `PYTHONPATH` | set to `/DICOM_solver` in the image | Import resolution |

`DELETE_END` is truthy for `true`, `1`, or `yes` (case-insensitive).

### `DICOM_solver/Config/roi_name_mappings.yaml`

Maps vendor/site-specific ROI names onto standardized names. Format is `standard_name: [synonym, ...]`:

```yaml
Lung_R:
  - Lung-R
  - LungR
  - Lung R
  - lung_right
```

At runtime this is inverted into a `synonym -> standard_name` lookup. Any ROI in the RT Struct whose name matches a synonym gets a **duplicate ROI added** under the standard name (the original is left in place). This is what makes the `dvh-calculations` expressions portable across sites.

---

## Running the service

### Docker (recommended)

```bash
docker run -d --name dvh-service \
  -p 8000:8000 \
  -e DELETE_END=false \
  -v /path/to/dicom/storage:/path/to/dicom/storage \
  ghcr.io/mdw-nl/dvh_consumer:main
```

The volume mount matters: `dicom_insert.file_path` values must resolve to the same absolute paths inside the container as the upstream listener wrote them.

To override config without rebuilding:

```bash
  -v /path/to/your/config.yaml:/DICOM_solver/DICOM_solver/Config/config.yaml:ro
```

### Local

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

`main.py` starts the RabbitMQ consumer on a daemon thread and then runs uvicorn on `0.0.0.0:8000` in the foreground.

### Build

```bash
docker build -t dvh-service .
```

CI ([`.github/workflows/create-and-publish.yml`](.github/workflows/create-and-publish.yml)) builds and pushes to GHCR on every push to `main`, and can be triggered manually via `workflow_dispatch`.

---

## HTTP API

Interactive docs at `http://localhost:8000/docs`.

### `GET /calculate_DVH`

Compute the DVH for **one structure** of **one patient**, on demand. Synchronous — returns the result directly, writes nothing to Postgres or GraphDB.

| Parameter | Type | Description |
|---|---|---|
| `patient_id` | query, required | Patient identifier |
| `structure` | query, required | Exact structure name to compute |

```bash
curl "http://localhost:8000/calculate_DVH?patient_id=PAT001&structure=Lung_L"
```

Returns `200` with `application/ld+json`, or `404` if no DVH could be produced for that patient/structure pair.

Note this path looks the patient up by `patient_id` across **all** their studies (`QUERY_PATIENT`), not by study UID. It walks the resulting bundles and returns the **first** one that yields a result, skipping bundles that error.

### `POST /reprocess/{study_uid}`

Re-run the full pipeline for a study that was already ingested. Returns `202` immediately; the work happens in a FastAPI background task.

```bash
curl -X POST "http://localhost:8000/reprocess/1.2.840.113619.2.55.3.12345"
```

```json
{"study_uid": "1.2.840.113619.2.55.3.12345", "status": "reprocessing scheduled"}
```

The outcome lands in `calculation_status`. **This requires the original DICOM files to still exist on disk** — which means `DELETE_END` must have been `false` during the original run, or the data must have been re-uploaded. Since the Dockerfile defaults `DELETE_END=True`, you generally need to have overridden it for this endpoint to be useful.

Reprocessing is a full re-run: it writes a new generation of `dvh_results` rows, uploads to GraphDB again, and honours `DELETE_END` again.

---

## Dose handling and summation

Handled by [`DICOM_solver/DVH/dose_handler.py`](DICOM_solver/DVH/dose_handler.py). The goal is to turn an arbitrary set of RT Dose files into a list of **effective doses**, each being one grid ready for a single DVH calculation.

### Triage — `analyze_doses()`

Dispatch is on the DICOM `DoseSummationType` tag:

| Input | Result | `effective_dose_type` |
|---|---|---|
| A single dose file | Used as-is | `SINGLE` |
| One or more `PLAN` doses | One effective dose **per** PLAN, kept independent | `PLAN` |
| Multiple `BEAM` doses | Summed into one synthetic dose | `SUMMED_BEAM` |
| Multiple `FRACTION` doses | Summed into one synthetic dose | `SUMMED_FRACTION` |
| A lone `BEAM` / `FRACTION` with no PLAN sibling | Used as-is, with a warning | `BEAM` / `FRACTION` |
| Mixed PLAN + BEAM/FRACTION | PLANs untouched **plus** the summed BEAM/FRACTION group | both |
| Nothing recognizable | First dose, with a warning | `FALLBACK` |

PLAN doses are deliberately never summed with each other — each represents a complete plan dose, so summing them would double-count.

### Summation — `sum_doses()`

Three-way triage on spatial compatibility:

1. **Same `FrameOfReferenceUID` + identical grid** (shape, origin, and full spacing including `SliceThickness`) → direct voxel-wise sum in Gy. Fast path.
2. **Same `FrameOfReferenceUID`, different grids** → build a target grid using the **finest spacing per axis** covering the **union of all extents**, trilinearly resample each dose onto it (`scipy.ndimage.map_coordinates`, `order=1`, zero-fill outside), then sum.
3. **Different `FrameOfReferenceUID`** → `ValueError`. Doses in different frames of reference cannot be combined without spatial registration, which this service does not perform.

The summed array is re-encoded into `PixelData` with a fresh `DoseGridScaling` chosen to use the full integer range of `BitsAllocated` (16- or 32-bit), and `DoseSummationType` is set to `PLAN`. When resampling occurred, the synthetic dataset's geometry tags (`ImagePositionPatient`, `PixelSpacing`, `SliceThickness`, `Rows`, `Columns`, `NumberOfFrames`, `GridFrameOffsetVector`) are all rewritten to describe the new grid.

Summed doses are synthetic — they exist only in memory and correspond to no file on disk. This is why bundles carrying them are constructed with `read=False` and have their parsers assigned explicitly; `rt_dose_paths` records the *contributing* source files.

A failure to sum one group is logged and that group is dropped — other effective doses for the same plan still proceed.

---

## ROI combination and standardized names

[`combine()`](DICOM_solver/combination.py) runs before every DVH calculation and does two things:

1. **Standardized renaming** — adds duplicate ROIs under canonical names, per `roi_name_mappings.yaml`.
2. **ROI combination** — evaluates each `dvh-calculations` expression and adds the result as a new ROI, named after the expression.

Expression syntax is space-separated ROI names and operators:

```yaml
dvh-calculations:
  - P-LUNG:
      roi: "Lung_L + Lung_R"          # union
  - TestPTV_P-Vessels_P:
      roi: "PTV_P - Vessels_P"        # subtraction
```

Supported operators are `+` (logical OR of the masks) and `-` (logical AND NOT). Additions are always evaluated before subtractions, so operand order in the expression does not change the result. If **any** named ROI is missing from the struct, that combination is skipped with a log line and the rest continue.

Combination works on voxel masks via `rt_utils`, which requires the CT series geometry to rasterize contours. **With no CT available, both renaming and combination are skipped entirely** — the DVH math still runs against the native RT Struct, but you get only the original ROI names and no combined structures.

---

## DVH metrics produced

For every structure, the output object contains:

| Field | Unit | Meaning |
|---|---|---|
| `structureName` | — | ROI name |
| `min`, `mean`, `max` | Gy | Dose statistics |
| `volume` | cc | Structure volume |
| `color` | — | `"r,g,b"` from the struct |
| `dvh_curve.dvh_points` | — | `{d_point, v_point}` pairs — the cumulative curve |
| `V1`…`V60` | — | Per `V-values` config: volume receiving at least *x* Gy |
| `D20`…`D98` | Gy | Per `D-values` config: dose received by *x*% of the volume |

Curves are computed with `dicompyler-core` (`dvhcalc`), converted from differential to cumulative, and expressed in Gy. When the RT Plan carries a prescription dose (`rxdose`), it is passed through so relative metrics resolve correctly.

Metrics that cannot be computed for a given structure are **skipped rather than fatal** — they are omitted from the output and logged as warnings. Likewise, a structure that fails entirely is skipped and the remaining structures still process.

---

## File cleanup (`DELETE_END`)

When `DELETE_END` is truthy, source DICOM files are deleted after **all** bundles for a study have been processed successfully. Deletion is skipped if any bundle raised.

[`_cleanup_files`](DICOM_solver/dvh_processor.py) dedupes paths across bundles first — the fan-out means several bundles legitimately share the same plan, struct, or CT directory — so each file is removed exactly once. RT Plan, RT Struct, and RT Dose files are removed individually; CT directories have their contents removed.

Two consequences worth knowing:

- **Reprocessing becomes impossible** once files are gone. `POST /reprocess/{study_uid}` will fail.
- **When the RTSTRUCT fallback fired**, the borrowed struct belongs to a *different* study — and cleanup will delete it. If that other study has not been processed yet, it loses its RTSTRUCT.

The Dockerfile sets `DELETE_END=True`, so both apply by default in containerized deployments. Override with `-e DELETE_END=false` if you want either behaviour.

---

## Monitoring and troubleshooting

### Was a study processed?

```sql
SELECT study_uid, patient_id, status, timestamp,
       error->>'type' AS error_type,
       error->>'message' AS error_message
FROM calculation_status
ORDER BY timestamp DESC
LIMIT 20;
```

### What did a study produce?

```sql
SELECT structure_name, effective_dose_type, rt_plan_path,
       mean_dose_gy, volume_cc, created_at
FROM dvh_results
WHERE study_uid = '<study_uid>'
ORDER BY created_at DESC, structure_name;
```

### Full traceback for a failure

```sql
SELECT error->>'traceback'
FROM calculation_status
WHERE study_uid = '<study_uid>' AND status = false
ORDER BY timestamp DESC LIMIT 1;
```

### Common failures

| Symptom | Cause |
|---|---|
| `Study <uid> incomplete; modalities present: [...]` | Not all required modalities arrived. Either the upstream upload is incomplete, or set `ct_required: false` if CT genuinely isn't expected. |
| `Cannot sum doses: Frame of Reference UIDs differ` | Doses are in different spatial frames. Requires registration; not supported. |
| `No RTPLAN file found for referenced plan UID <uid>` | An RT Dose references a plan whose file is absent from the study. That plan is skipped. |
| Every insert fails with an undefined-column error | The [migration](#migration-for-existing-deployments) has not been applied. |
| `Failed to read RT Dose <path>` | File missing (likely already cleaned up) or corrupt. |
| GraphDB upload failed, DVH results still saved | The upload service is unreachable. Non-fatal by design — Postgres results are intact. |
| Repeated reconnection attempts, then consumer exits | RabbitMQ unreachable for 5 attempts × 5s. The HTTP API keeps serving; the container needs a restart to resume consuming. |

### Logging

Everything goes to stdout at `INFO` level, format `%(asctime)s - %(levelname)s - %(message)s`. `docker logs -f dvh-service`.

---

## Development

### Tests

```bash
pip install -r requirements.txt
python -m pytest tests/
```

[`tests/dvh_calc_test.py`](tests/dvh_calc_test.py) downloads a real DICOM fixture set from `mdw-nl/test-data` on first run and validates DVH numbers, ROI combination arithmetic, and name standardization. `tests/roi_handler_test.py` and `tests/roi_lookup_service_test.py` cover the mask algebra and the synonym lookup in isolation.

`Test/` (capital T) holds older scratch scripts and is not part of the pytest suite.

### Install as a package

```bash
pip install -e .
```

### Retry and connection behaviour

- **Postgres**: 5 connection attempts, 10s apart (`NUMBER_ATTEMPTS`, `RETRY_DELAY_IN_SECONDS` in [`global_var.py`](DICOM_solver/Config/global_var.py)), then raises.
- **RabbitMQ**: on a consume error, 5 reconnect attempts 5s apart; if all fail the consumer thread exits.

---

## Known gotchas

These are real behaviours of the current code, worth knowing before you debug something surprising.

- **Messages are acked before processing.** [`callback_tread`](DICOM_solver/dvh_processor.py) calls `basic_ack` immediately on receipt, before the calculation runs. A crash mid-calculation means the message is **not** redelivered — the study is lost from the queue's perspective and must be re-driven via `POST /reprocess/{study_uid}`. Failures are recorded in `calculation_status`, so they are visible; they just aren't retried.
- **The thread pool doesn't add concurrency.** The consumer creates a 5-worker `ThreadPoolExecutor`, but the callback submits one job and immediately calls `future.result()`, so studies are processed strictly one at a time.
- **`config-prod.yaml` is dead.** [`config_handler.read_config()`](DICOM_solver/config_handler.py) hard-codes `config.yaml`. `config-prod.yaml` is never loaded, and its ROI expressions sit under a `roi-combinations:` key that nothing reads — `combine()` looks for `dvh-calculations:`. Treat it as a reference sample, not live config.
- **Config is read once.** `read_config()` is `lru_cache`d, so config changes require a process restart.
- **`DELETE_END=True` in the image** while the code default is `false`. The container's behaviour is the opposite of a local run.
- **The `/calculate_DVH` endpoint is patient-scoped, not study-scoped**, and returns the first bundle that produces a result. With multiple studies or plans for a patient, which one you get is not something you control from the request.
- **`dvh_results` rows accumulate.** Nothing deduplicates or supersedes prior runs; queries against a reprocessed study need a `created_at` filter to avoid mixing generations.
- **The RTSTRUCT fallback can cross studies.** It takes the most recent RTSTRUCT for the patient regardless of which study it belongs to. Combined with `DELETE_END`, it can delete another study's struct.

---

## Project layout

```
main.py                          FastAPI app + consumer thread; entrypoint
Dockerfile                       Python 3.12-slim image
requirements.txt                 Dependencies (scipy is needed for dose resampling)

DICOM_solver/
├─ queue_processing.py           RabbitMQ consumer, reconnect logic
├─ dvh_processor.py              Orchestration: callback, process_message,
│                                reprocess_study, status writes, file cleanup
├─ dicom_operation.py            Modality verification, bundle construction/fan-out
├─ combination.py                ROI combination + standardized renaming
├─ roi_handler.py                Mask algebra (+ / -)
├─ roi_lookup_service.py         Synonym -> standard name resolution
├─ utilities.py                  DB connect, study query, RTSTRUCT fallback
├─ PostgresInterface.py          psycopg2 wrapper with retry
├─ graphdb.py                    JSON-LD upload via the intermediate API
├─ config_handler.py             YAML config loading (cached)
├─ loading_mask.py               Standalone mask-loading helper
├─ DVH/
│  ├─ dvh.py                     DVH calculation, metric extraction, output shaping
│  ├─ dose_handler.py            Dose triage, summation, resampling
│  ├─ dicom_bundle.py            DicomBundle container
│  ├─ db_writer.py               dvh_results inserts
│  └─ output.py                  JSON-LD document construction
├─ API/
│  └─ retrieve_Data.py           Patient-scoped DVH lookup for /calculate_DVH
└─ Config/
   ├─ config.yaml                The live config
   ├─ config-prod.yaml           Unused sample (see gotchas)
   ├─ roi_name_mappings.yaml     Synonym -> standard ROI names
   └─ global_var.py              SQL statements, retry constants, DELETE_END

tests/                           pytest suite (downloads DICOM fixtures)
Test/                            Older scratch scripts, not in the suite
```
