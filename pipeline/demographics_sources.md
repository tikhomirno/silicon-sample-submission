# Demographic distributions — sources & provenance

The persona generator (`pipeline/make_personas.py`) samples each synthetic
respondent's demographics from the marginal distributions below. This file
records **exactly where every number comes from**, the mapping/interpolation
applied, and the known limitations — so the choices are reproducible and citable
in `registration.md`.

**Population target:** U.S. adults (the survey is US-framed; the real study
quota-samples on race).

**Sampling method:** each variable is drawn **independently** from its marginal
(see *Limitations*). Conditions are assigned balanced (equal n per condition).

**Reference date:** all figures accessed **2026-06-29**.

---

## Primary source — U.S. Census Bureau, ACS 2023 1-year

American Community Survey (ACS) **2023 1-year estimates**, U.S. total, pulled
from the Census Bureau Data API (`https://api.census.gov/data/2023/acs/acs1`,
table group queries; an API key was used and is **not** stored in the repo).
Citation:

> U.S. Census Bureau. *2023 American Community Survey 1-Year Estimates*, tables
> B01001, B03002, B15003, B19001. Retrieved 2026-06-29 from the Census Bureau
> Data API, https://api.census.gov/data/.

### age band — table **B01001** (Sex by Age), adults 18+ (denominator 262,266,460)
Composed from the 5-year sex×age cells (both sexes) into the survey's bands:

| Band | Share |
|---|---|
| 18-29 | 0.200 |
| 30-44 | 0.260 |
| 45-59 | 0.232 |
| 60+ | 0.309 |

(`clean.R` derives `age_band` from `year_birth`; we sample a band, then a uniform
age within it, then set `year_birth = 2026 − age`.)

### sex (Male/Female) — table **B01001**, adults 18+
ACS measures sex as binary. Among adults: **Male 0.490 / Female 0.510**. These are
then scaled to 99% to leave room for the survey's "Other" option (below), giving
the values used: **Male 0.485 / Female 0.505 / Other 0.010**.

### race / ethnicity — table **B03002** (Hispanic Origin by Race), all ages (denominator 334,914,896)
Mapped to the survey's 5 mutually-exclusive categories:

| Survey category | ACS components | Share |
|---|---|---|
| White | Not-Hispanic White alone (B03002_003) | 0.571 |
| Black | Not-Hispanic Black alone (_004) | 0.118 |
| Hispanic | Hispanic or Latino, any race (_012) | 0.194 |
| Asian | Not-Hispanic Asian alone (_006) | 0.059 |
| Other | NH AIAN (_005) + NH NHPI (_007) + NH other (_008) + NH two-or-more (_009) | 0.057 |

*Caveat:* B03002 is **all ages**, not 18+ (an adult-only race table would require
iterating B01001A–I). Adult shares differ only slightly (adults skew marginally
less Hispanic / more White).

### education — table **B15003** (Educational Attainment), adults 25+ (denominator 231,791,117)

| Survey category | ACS components | Share |
|---|---|---|
| Less than high school | _002…_016 (no schooling → 12th grade, no diploma) | 0.102 |
| High school diploma / GED | _017 (HS diploma) + _018 (GED) | 0.259 |
| Some college or Associate's | _019 + _020 (some college) + _021 (associate's) | 0.277 |
| Bachelor's degree | _022 | 0.218 |
| Master's degree / Professional | _023 (master's) + _024 (professional) | 0.126 |
| Doctorate degree / Ph.D. | _025 | 0.017 |

*Caveat:* B15003 is **25+** (the survey is 18+). 18–24-year-olds are still in
school, so this slightly understates "some college" and overstates degree
completion; acceptable for the first pass.

### household income — table **B19001**, all households (denominator 131,332,360)
ACS reports 16 income brackets; the survey uses 5 with boundaries at $30k, $56k,
$100k, $168k. Where a survey boundary falls inside an ACS bracket, we split that
bracket by **linear interpolation (uniform within bracket)**:

| Survey bracket | Derivation from B19001 cells | Share |
|---|---|---|
| < $30,000 | _002…_006 (exact, ≤ $30k) | 0.184 |
| $30,000–$55,999 | _007+_008+_009+_010 + 0.60·_011 (50–60k → 50–56k) | 0.179 |
| $56,000–$99,999 | 0.40·_011 + _012 + _013 | 0.248 |
| $100,000–$167,999 | _014+_015 + 0.36·_016 (150–200k → 150–168k) | 0.207 |
| ≥ $168,000 | 0.64·_016 + _017 | 0.182 |

*Caveat:* this is **household** income (the survey item is household income), and
the interpolation assumes a uniform distribution within the two split brackets.

---

## party identification — Gallup, 2024 annual

Census does not measure party. We use Gallup's 2024 **annual average** of initial
party identification (asked **before** independent leaners are reallocated), which
matches the survey's single-choice Republican/Democrat/Independent/Other item:

| Party | Share |
|---|---|
| Republican | 0.28 |
| Democrat | 0.28 |
| Independent | 0.43 |
| Other | 0.01 (residual; Gallup R+I+D ≈ 99%) |

> Gallup. *GOP Holds Edge in Party Affiliation for Third Straight Year* (2024
> annual averages, >14,000 U.S. adults). Retrieved 2026-06-29 from
> https://news.gallup.com/poll/655157/gop-holds-edge-party-affiliation-third-straight-year.aspx

---

## gender "Other" — Pew Research Center, 2022

ACS sex is binary, but the survey offers Male/Female/**Other**. We allocate **1.0%**
to "Other" as an approximate share of adults who are **nonbinary** (a subset of
the 1.6% of U.S. adults Pew found to be transgender or nonbinary), then scale
Male/Female to the remaining 99% at their ACS adult ratio.

> Pew Research Center (2022). *About 5% of young adults in the U.S. say their
> gender is different from their sex assigned at birth.* Retrieved 2026-06-29 from
> https://www.pewresearch.org/short-reads/2022/06/07/about-5-of-young-adults-in-the-u-s-say-their-gender-is-different-from-their-sex-assigned-at-birth/

*Caveat:* 1.0% is a reasoned approximation of the nonbinary share (Pew gives ~3%
among under-30 and ~0.3% among 50+, no single all-adult nonbinary figure), not a
directly published number.

---

## Limitations (first-pass; refinement targets)

1. **Independence.** Variables are drawn independently, so real correlations
   (age×education×income×party) are not preserved — some implausible individuals
   result. Fix: draw **joint** profiles from ACS PUMS microdata (or the GSS, which
   the benchmark itself used for its reference clones).
2. **Mixed universes.** age/sex use 18+, education uses 25+, race/income use all
   ages / all households — standard ACS table universes, not perfectly aligned to
   the 18+ target.
3. **Two non-Census variables** (party, gender "Other") come from different
   sources/years than the ACS demographics.
