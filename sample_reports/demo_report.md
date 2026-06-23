# semlint audit report

**Semantic Trust Score (v0 heuristic):** 89/100

- metrics audited: 7
- rules run: 8
- findings: 4 fail, 3 warn, 1 pass

| rule | severity | metric | finding | remediation |
|---|---|---|---|---|
| R1 duplicate definition | FAIL | revenue | metric 'revenue' is defined 2 times | keep one canonical definition of 'revenue' and remove or rename the duplicates |
| R2 definition collision | FAIL | revenue | metric 'revenue' has conflicting formulas: SUM(order_amount), SUM(order_amount) - SUM(refund_amount) | reconcile 'revenue' to a single agreed formula |
| R3 missing owner | PASS | - | no issues found | - |
| R4 missing description | WARN | active_users | metric 'active_users' has no description | add a description to 'active_users' |
| R5 undefined or ambiguous grain | FAIL | conversion_rate | metric 'conversion_rate' has no grain | declare a time grain for 'conversion_rate' |
| R6 orphaned dimension | FAIL | aov | metric 'aov' references undefined dimension 'store' | define dimension 'store' or remove it from 'aov' |
| R7 ai-readiness gaps | WARN | churn_rate | metric 'churn_rate' missing aliases/synonyms, access rule for AI grounding | add aliases/synonyms, access rule to 'churn_rate' |
| R8 non-portable construct | WARN | gmv | metric 'gmv' formula uses non-portable construct(s): IFF( | rewrite 'gmv' formula using ANSI/OSI-neutral SQL |
