# SLO and SLA - Engenharia CAD

## Objective

Define measurable reliability targets for API and async job processing.

## Service Level Objectives (SLO)

1. API availability (monthly): >= 99.9%
2. P95 latency for core API routes: <= 800 ms
3. Async job success rate: >= 99.0%
4. Critical incident MTTR: <= 60 minutes

## Service Level Indicators (SLI)

1. Availability SLI:
   successful_requests / total_requests
2. Latency SLI:
   p95 request duration for /generate, /projects, /jobs
3. Job success SLI:
   completed_jobs / submitted_jobs
4. Recovery SLI:
   incident recovery elapsed time

## Error Budget

For API availability 99.9%, monthly error budget is about 43 minutes.

## Alert Thresholds

1. API availability below 99.9% over rolling 24h
2. P95 latency above 800 ms for 10 minutes
3. Job failure rate above 2% for 15 minutes
4. Queue lag above agreed threshold per environment

## SLA (Commercial)

1. Production uptime commitment: 99.5% (contract baseline)
2. Critical incident response: up to 30 minutes
3. Incident communication cadence: every 30 minutes until recovery
4. Postmortem delivery: up to 3 business days

## Notes

SLA is customer-facing. SLO is internal and should be stricter than SLA.
