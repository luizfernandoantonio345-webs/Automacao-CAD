# Runbook - Incident Response

## Purpose

Standardize response for incidents affecting API, job processing, or data integrity.

## Severity Levels

1. SEV-1: full outage or data corruption risk
2. SEV-2: major degradation impacting critical flows
3. SEV-3: partial degradation with workaround

## Immediate Actions (First 15 minutes)

1. Confirm incident and severity.
2. Open war-room channel and assign incident commander.
3. Freeze risky deployments until stabilization.
4. Capture baseline telemetry (errors, latency, queue lag, failed jobs).

## Technical Triage Checklist

1. API health endpoints:
   /live, /ready, /health
2. Queue status and worker connectivity.
3. Database connectivity and write/read behavior.
4. Recent deploys, config changes, and secret rotations.
5. Error spikes in logs and tracing.

## Containment

1. Roll back latest deployment if correlated.
2. Disable unstable feature flag if available.
3. Route traffic to stable path when possible.

## Recovery Validation

1. Core routes respond without errors.
2. Async jobs are consumed and completed normally.
3. Error and latency metrics return to normal thresholds.
4. Business-critical user flow validated end-to-end.

## Communication

1. Internal update every 30 minutes.
2. External customer update by SLA commitments.
3. Final incident summary with timeline and impact.

## Postmortem (Up to 3 business days)

1. Root cause analysis.
2. Corrective and preventive actions.
3. Owner and due date for each action.
4. Verification plan to avoid recurrence.
