## ---------------------------------------------------------------------------
## submission_spec.R — canonical schema for Silicon Sample Benchmark submissions
##
## Single source of truth shared by clean_lib.R, check_lib.R, and
## the example-data generator. Sourcing this file defines the `sst` list.
##
## Condition labels are the 16 text-intervention titles + "control", i.e. the
## titles in data/interventions.csv minus the 4 interactive arms (3 LLM-chatbot
## conditions + the "Value similarity" quiz). Edit here and nowhere else.
## ---------------------------------------------------------------------------

sst <- local({

  interventions <- c(
    "Corporate reliance",
    "Social justice",
    "Interview Prof. Maraun",
    "Funding",
    "Oil industry misinformation",
    "Measurement & modeling (1)",
    "Former skeptics",
    "High public trust",
    "Measurement & modeling (2)",
    "Peer-review",
    "Scientist community helpers",
    "Consensus",
    "Portrait Prof. Cherry",
    "Model accuracy",
    "Interview Prof. Sebille",
    "Extreme weather predictions"
  )

  conditions <- c("control", interventions)

  trust_items <- c(
    paste0("trust_competence_",  1:3),
    paste0("trust_integrity_",   1:3),
    paste0("trust_benevolence_", 1:3),
    paste0("trust_openness_",    1:3)
  )

  ## 13 preregistered outcomes (the 12 trust items are sub-components of the
  ## primary, shipped in Tier 1 but not counted among the 13).
  outcomes <- c(
    "trust_multidimensional",
    "trust_post", "distrust_post", "funding_perceptions",
    "policy_role_mean", "inst_trust_mean",
    "belief_post", "concern_mean", "policy_general",
    "policy_specific_mean", "behavior_mean",
    "donation_ams", "newsletter_signup"
  )

  ## scale type per outcome (drives value-sanity checks)
  scale_0_100 <- c(
    "trust_multidimensional", "trust_post", "distrust_post",
    "funding_perceptions", "policy_role_mean", "inst_trust_mean",
    "belief_post", "concern_mean", "policy_general",
    "policy_specific_mean", "behavior_mean"
  )

  moderators <- list(
    gender    = c("Male", "Female", "Other"),
    age_band  = c("18-29", "30-44", "45-59", "60+"),
    race      = c("White / Caucasian", "Black / African American",
                  "Hispanic / Latino", "Asian / Asian American", "Other"),
    education = c("Less than high school",
                  "High school diploma / GED",
                  "Some college or Associate's degree",
                  "Bachelor's degree",
                  "Master's degree / Professional degree",
                  "Doctorate degree / Ph.D."),
    income    = c("Less than $30,000", "$30,000 to $55,999",
                  "$56,000 to $99,999", "$100,000 to $167,999",
                  "$168,000 or more"),
    party     = c("Republican", "Democrat", "Independent", "Other")
  )

  ## Tier-1 required columns (one row per synthetic respondent)
  tier1_required <- c(
    "profile_id", "condition", names(moderators),
    "trust_multidimensional", trust_items,
    "trust_post", "distrust_post", "funding_perceptions",
    "policy_role_mean", "inst_trust_mean",
    "belief_post", "concern_mean", "policy_general",
    "policy_specific_mean", "behavior_mean",
    "donation_ams", "newsletter_signup"
  )

  tier2_main_cols <- c("condition", "outcome", "mean", "sd", "n_eff")
  tier2_mod_cols  <- c("condition", "moderator", "moderator_level",
                       "outcome", "mean", "sd", "n_eff")
  tier3_cols      <- c("condition", "outcome", "ate", "pi_lower", "pi_upper")

  list(
    interventions   = interventions,
    conditions      = conditions,
    trust_items     = trust_items,
    outcomes        = outcomes,
    scale_0_100     = scale_0_100,
    donation_range  = c(0, 10),
    moderators      = moderators,
    tier1_required  = tier1_required,
    tier2_main_cols = tier2_main_cols,
    tier2_mod_cols  = tier2_mod_cols,
    tier3_cols      = tier3_cols
  )
})
