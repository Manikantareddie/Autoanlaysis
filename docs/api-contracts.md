# API contracts

## Dataset management

All Phase 2 endpoints use the /api/v1 prefix.

| Method | Path | Description |
| --- | --- | --- |
| POST | /datasets | Multipart field file; validates, stores, profiles, and registers a CSV. |
| GET | /datasets | Lists uploaded datasets and persisted metadata. |
| GET | /datasets/{dataset_id} | Returns dataset metadata and the complete profile. |
| GET | /datasets/{dataset_id}/profile | Returns schema, statistics, and quality warnings. |
| GET | /datasets/{dataset_id}/preview?limit=20 | Returns a bounded source-data preview; limit is 1–100. |

Upload errors are explicit: 415 for a non-CSV extension, 413 for configured
file/row limits, 422 for empty, malformed, non-UTF-8, or structurally invalid
CSV content, and 500 for an unexpected processing error. The API never returns
server storage paths or generated DuckDB paths.

