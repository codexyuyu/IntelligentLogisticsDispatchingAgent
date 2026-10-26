# Legacy B-01 service retained during team-framework migration

This directory is intentionally preserved from the B-01 CP-SAT V1.2 implementation.

Main entry point:
- `app/main.py`

Important endpoints:
- `GET /api/health`
- `GET /api/schedule/data`
- `POST /api/schedule/solve`
- `POST /api/schedule/reschedule`

This service is retained for B-01 verification and regression comparison. It is not the team's new
shared application boundary. New team-integrated work should use `backend/` and the shared contracts/ports.
