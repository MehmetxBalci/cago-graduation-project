# CAGO Oracle v1 reproduction audit (baseline SR1-SR5)

Garments evaluated: 47522 (published: 47522)

| rule | computed | % | published | % | diff | match |
|---|---|---|---|---|---|---|
| SR1 | 17303 | 36.41 | 17303 | 36.41 | 0 | yes |
| SR2 | 9504 | 20.0 | 9504 | 20.0 | 0 | yes |
| SR3 | 8228 | 17.31 | 8228 | 17.31 | 0 | yes |
| SR4 | 6515 | 13.71 | 6515 | 13.71 | 0 | yes |
| SR5 | 3878 | 8.16 | 3878 | 8.16 | 0 | yes |
| ANY | 23908 | 50.31 | 23908 | 50.31 | 0 | yes |

All counts match published: **True**

## violation_count distribution

| violations | garments |
|---|---|
| 0 | 23614 |
| 1 | 10540 |
| 2 | 6210 |
| 3 | 6191 |
| 4 | 940 |
| 5 | 27 |

## SR1 reasons

| value | n |
|---|---|
| supported_mono | 17503 |
| supported_binary | 12716 |
| more_than_two_fibres | 9504 |
| unsupported_binary | 7080 |
| unsupported_mono | 719 |

## Readable component source

| value | n |
|---|---|
| surface_component | 47048 |
| first_component_fallback | 474 |

## SR5 surface reference source

| value | n |
|---|---|
| surface_component | 46808 |
| first_component_fallback | 474 |
| surface_coating | 240 |

violation_count = number of triggered baseline rule indicators; not a circularity or recyclability score.
