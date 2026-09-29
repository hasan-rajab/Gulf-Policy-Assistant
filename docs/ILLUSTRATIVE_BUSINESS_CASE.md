# NEXUS — Illustrative Business Case

## Purpose

This model demonstrates how I would quantify a NEXUS-style deployment during an AI consulting engagement.

> **Important:** All business inputs below are fictional assumptions for portfolio demonstration. They are not results from a real customer.

## Base-case assumptions

| Assumption | Value |
|---|---:|
| Knowledge-intensive employees in initial scope | 500 |
| Policy lookups per employee per week | 8 |
| Working weeks per year | 46 |
| Average time saved per lookup | 5 minutes |
| Estimated fully loaded value of employee time | BHD 12/hour |
| Adoption / realized-utilization factor | 60% |
| Illustrative initial implementation cost | BHD 35,000 |
| Illustrative annual run cost | BHD 24,000 |

## Capacity-value calculation

Annual policy lookups:

```text
500 employees × 8 lookups/week × 46 weeks
= 184,000 lookups/year
```

Gross hours potentially saved:

```text
184,000 × 5 minutes ÷ 60
= 15,333 hours/year
```

Gross time value:

```text
15,333 × BHD 12/hour
≈ BHD 184,000/year
```

Apply 60% adoption / realization factor:

```text
BHD 184,000 × 60%
≈ BHD 110,400/year realized capacity value
```

Less annual run cost:

```text
BHD 110,400 - BHD 24,000
= BHD 86,400 annual net recurring value
```

Illustrative simple payback on a BHD 35,000 implementation:

```text
BHD 35,000 ÷ (BHD 86,400 / 12)
≈ 4.9 months
```

## Interpretation

This is **capacity value**, not automatically cash savings. A real client engagement must distinguish among:

- direct headcount cost reduction;
- avoided future hiring;
- increased employee throughput;
- reduced support demand;
- faster onboarding;
- better compliance outcomes;
- improved service quality.

Treating all saved time as cashable savings would overstate the business case.

---

## Sensitivity analysis

### Annual realized capacity value before run cost

| Time saved / lookup | 40% realization | 60% realization | 80% realization |
|---|---:|---:|---:|
| 3 minutes | BHD 44,160 | BHD 66,240 | BHD 88,320 |
| 5 minutes | BHD 73,600 | BHD 110,400 | BHD 147,200 |
| 7 minutes | BHD 103,040 | BHD 154,560 | BHD 206,080 |

This shows why a pilot should measure actual usage and time saved instead of relying on optimistic assumptions.

---

## Benefits beyond productivity

A full business case should also test:

### Risk reduction
- fewer unsupported policy answers;
- stronger evidence traceability;
- lower unauthorized-information exposure risk;
- controlled action execution.

### Employee experience
- faster access to bilingual policy information;
- fewer hand-offs to HR, compliance, or operations;
- better self-service.

### Operational resilience
- auditable answers;
- consistent escalation when evidence is insufficient;
- measurable quality gates before release.

---

## Pilot economics

Rather than approve an enterprise-wide rollout immediately, I would recommend a narrowly scoped pilot with:

- one or two policy domains;
- clearly defined employee groups;
- 50–100 bilingual golden questions;
- baseline time-on-task measurement;
- explicit quality and security thresholds;
- adoption measurement;
- go/no-go criteria.

The business-case decision after the pilot should be based on **observed** value, not the fictional assumptions used in this portfolio model.
