# Release and rollback playbook (fictional demo)

## Scope
This is an invented training policy for a fictional service called Hikari Orders. It is sample portfolio data, not a real employer policy or a record of the author's work.

## Release preparation
Before a release, the release coordinator records the change ticket, tested build identifier, database migration plan, monitoring owner, and rollback owner. Staging smoke tests must pass. The coordinator asks a second engineer to review the checklist before approving the release.

## Rollback decision
Rollback is considered when the error rate exceeds 2% for five consecutive minutes after a deployment, or when the order creation smoke test fails. The incident commander decides whether to rollback and records the reason in the incident ticket. A rollback is not automatically safe after an irreversible database migration; first consult the migration owner and use the recovery plan.

## Rollback procedure
The rollback owner restores the previous approved application build, checks health endpoints, and repeats the order creation smoke test. Keep the current database schema unless the reviewed recovery plan explicitly permits reversal. Record the deployed build identifiers and verification results in the change ticket.

## Release communication
For a customer-facing release, the coordinator posts a start notice, a completion or rollback notice, and the monitoring result in the change ticket. The operations lead receives a daily summary of open releases. This demo assistant cannot approve releases or send notices.

