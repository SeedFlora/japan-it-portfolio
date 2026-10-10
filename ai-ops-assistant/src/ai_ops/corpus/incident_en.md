# Incident response handbook (fictional demo)

## Scope
This handbook is invented sample data for Hikari Orders, a fictional service. Names of roles describe a training scenario; they do not establish actual employees or work experience.

## Severity and escalation
A complete inability to create orders or suspected customer-data exposure is a SEV1 incident. Page the on-call engineer immediately. If the on-call engineer has not acknowledged within ten minutes, escalate to the operations lead. The operations lead assigns an incident commander and a communication owner.

## Recovery responsibilities
The incident commander coordinates recovery, tracks the current hypothesis, and records decisions. Engineers isolate the failing component and verify recovery with the order creation smoke test. Do not delete audit logs during recovery. Suspected customer-data exposure requires an additional review by the privacy contact before closing the incident.

## Incident updates
During a SEV1 incident, the communication owner records an internal status update every fifteen minutes, including impact, action in progress, and next update time. External communication requires the operations lead's approval. This demo does not page staff, send messages, or resolve incidents.

## Post-incident review
Within two business days of recovery, prepare a review with timeline, root-cause evidence, customer impact, and follow-up actions. Every follow-up action needs an owner and a target date. Discuss contributing process factors without blaming individuals; track overdue actions at the weekly operations meeting.

