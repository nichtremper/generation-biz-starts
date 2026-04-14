# Session 2 — Analysis Findings
Date: 2026-04-14

## Research question
Are people 35 and younger starting businesses at higher rates than historical averages?

## Short answer: No — and the more striking finding is structural

Young adults (20–35) are not starting businesses at elevated rates relative to their own history. But more notably, they enter self-employment at **consistently lower rates than 36–64-year-olds** — a structural gap that has held across the entire 2005–2025 series and has not narrowed recently.

---

## Quantitative summary (recent period: Oct 2023–present)

### Month-over-month (MOM) — 3-month rolling average
| Age group | Combined SE entry rate | Incorporated only |
|---|---|---|
| 20–35 | 0.54% / month | 0.46% / month |
| 36–50 | 0.75% / month | 0.62% / month |
| 51–64 | 0.74% / month | 0.59% / month |

### Year-over-year (YOY) — quarterly
| Age group | Combined SE entry rate | Incorporated only |
|---|---|---|
| 20–35 | 2.1% / year | 1.8% / year |
| 36–50 | 3.0% / year | 2.6% / year |
| 51–64 | 2.9% / year | 2.6% / year |

The 20–35 group runs roughly **40% below** the 36–64 groups in both methods. This holds in the recent period and across the full baseline.

---

## What the time series shows

**No recent elevation.** Post-Oct 2023, entry rates for 20–35 are near or slightly below the 2005–2019 historical range. Neither MOM nor YOY shows a post-pandemic surge sustaining into the recent period.

**COVID spike is real but reversed.** All age groups show elevated entry rates during 2020–2022, most visibly in 36–50 and 51–64. Post-2022 rates returned to pre-COVID levels. The CI bands also blow up during COVID due to two compounding factors: higher entry rates (which widens the binomial CI) and smaller matched-pair samples from survey non-response.

**Secular decline is visible in MOM (36–50, 51–64).** There is a gradual downward drift in entry rates from 2006 to approximately 2012–2014, consistent with the post-GFC entrepreneurship decline documented in Kauffman Foundation research. Rates stabilized after 2014.

---

## Methodological notes

**MOM understates unincorporated SE entry.** In MOM, combined SE and incorporated-only rates are very close (~0.08pp gap). YOY shows a wider gap (~0.27pp). Unincorporated SE workers (gig, freelance) have high turnover — they often don't survive the month-to-month link, so short MOM pairs disproportionately capture the stable incorporated workers. YOY catches more durable unincorporated transitions. Any claim about gig/informal SE trends should lean on YOY rather than MOM.

**CIs are workable.** Median n_at_risk per month per age group is ~15–17k (MOM), giving ±0.11% median CI width. The "few hundred observations" caveat in the original project plan appears to have been written with a narrower age filter in mind. At the 20–35 grouping the sample is large enough for reasonable inference.

**2024 Q1–Q3 missing from YOY.** The extract skips Jan–Sep 2023, so the T0 observations needed to produce 2024 Q1–Q3 YOY pairs don't exist. A supplemental extract covering those 9 months would close the gap.

---

## Figures
- `figures/entry_rates_mom.png` — full MOM time series, all age groups, shared y-axis
- `figures/entry_rates_yoy.png` — full YOY time series, all age groups, shared y-axis
