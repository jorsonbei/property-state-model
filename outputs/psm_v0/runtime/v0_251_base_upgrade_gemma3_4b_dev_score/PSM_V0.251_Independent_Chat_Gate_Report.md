# PSM V0.251 Independent Chat Gate Report

- Passed: `False`
- NoTargetRead retained: `True`
- Source-family split retained: `True`
- Safety/usefulness separated: `True`

## Split Results

| Split | Rows | Usefulness | Safety | Critical FN | Correctness | Relevance | Hallucination control |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 0 | 0.0000 | 0.0000 | 0 | n/a | n/a | n/a |
| dev | 20 | 0.9000 | 1.0000 | 0 | 0.9583 | 1.0000 | 1.0000 |
| blind | 0 | 0.0000 | 0.0000 | 0 | n/a | n/a | n/a |

## Blind Gate

- blind_rows: `False`
- blind_usefulness_pass_rate: `False`
- blind_correctness: `False`
- blind_relevance: `False`
- blind_hallucination_control: `False`
- blind_safety_pass_rate: `False`
- critical_safety_false_negatives: `True`

## Blind Failures

- Usefulness: none
- Safety: none

This is an authored marker-and-contract gate, not an external human study, open-domain proof, clinical/legal validation, or external release approval.
