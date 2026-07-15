# PSM External Validation Roadmap V0.261 to V0.262

## Completed V0.261

1. Submit only the authorized synthetic, non-private frozen annotation contract to an independent external model.
2. Retain the initial `fail` result instead of overwriting or relabeling it.
3. Convert policy-only boundaries into a closed-world V2 contract with executable rejection rules.
4. Pass local alias, leakage, leaf-type, malformed-object, time-boundary, group-crossing, disagreement, backflow, and authority mutation checks.
5. Re-submit the repaired contract without exposing prior review conclusions to the judge prompt.
6. Pass all five external review questions with no remaining failed checks, critical findings, or repairs.
7. Re-run unit, browser, real-backend, Docker, and project verification before promotion.

## V0.262 Gate

V0.262 is an external-user trial protocol stage, not an automatic release stage. It cannot begin until the user supplies or approves:

- participant scope and exclusion rules;
- allowed and prohibited data classes;
- privacy notice and explicit consent requirements;
- retention, deletion, access-control, and incident-response rules;
- deployment mode, budget, and stop conditions;
- an explicit statement that passing synthetic/model judgment does not constitute privacy compliance, professional authority, or public-release approval.

Until that gate is approved, local single-user chat remains available and all external-user/public authorities remain false.
