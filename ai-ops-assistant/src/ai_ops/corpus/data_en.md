# Data quality and backup handbook (fictional demo)

## Scope
This is invented portfolio sample data for Hikari Orders. The rules are illustrative operational exercises and should not be used as real security or compliance advice.

## Data quality checks
The daily order pipeline checks duplicate order IDs, missing timestamps, invalid currency codes, and negative item quantities. A batch with more than 0.5% invalid rows is quarantined for review rather than published. The data owner records validation counts and the approved corrective action in the pipeline ticket.

## Backup restore tests
Database backups run every night at 02:00 JST. The operations engineer performs a backup restore test in an isolated test environment once a month. Verify record counts and referential integrity, and record elapsed restore time in the backup ticket. Never restore a test backup over the live database.

## Access and retention
The sample policy retains application logs for thirty days and incident decision records for one year. The data owner approves access based on operational need. Use synthetic or anonymized data in demonstrations; do not copy customer records or secrets into the portfolio corpus.

## Reporting and improvement
The weekly operations dashboard reports rejected-row percentage, pipeline delay, open incidents, and overdue corrective actions. Before automating a manual step, document its input, decision rule, owner, failure cases, and rollback procedure. Measure improvement against the recorded baseline instead of inventing savings.

