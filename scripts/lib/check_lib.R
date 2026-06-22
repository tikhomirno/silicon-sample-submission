## ---------------------------------------------------------------------------
## check_lib.R — self-assess a Silicon Sample Benchmark submission
## Library sourced by check.R (`make check`); not run directly.
##
## Checks a submission against the published spec: metadata.json schema, file
## naming, SHA-256 integrity, per-tier data structure / coverage, and value
## sanity. Every team can run this before depositing.
##
## Usage:
##   source("check_lib.R")                     # also sources submission_spec.R
##   check_submission("metadata.json", dir = ".")
##
## Returns (invisibly) a tibble of checks; prints a report and an overall
## verdict (PASS / PASS WITH WARNINGS / FAIL) and writes <metadata>_check_report.txt.
## ---------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(tidyverse); library(jsonlite); library(digest)
})

if (!exists("sst")) {
  .here <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
  source(file.path(if (is.null(.here)) "." else .here, "submission_spec.R"))
}

.check_bundle <- function(mpath, dir = ".") {
  res <- tibble(check = character(), status = character(), detail = character())
  add <- function(check, status, detail = "") {
    res <<- add_row(res, check = check, status = status, detail = detail); invisible()
  }
  ok   <- function(cond, check, bad, good = "") if (isTRUE(cond)) add(check, "PASS", good) else add(check, "FAIL", bad)
  warn <- function(cond, check, bad, good = "") if (isTRUE(cond)) add(check, "PASS", good) else add(check, "WARN", bad)
  rng  <- function(x, lo, hi) sum(!is.na(x) & (x < lo | x > hi))

  if (!file.exists(mpath)) { add("metadata.json present", "FAIL", mpath); return(res) }
  m <- tryCatch(fromJSON(mpath), error = function(e) NULL)
  if (is.null(m)) { add("metadata.json parses", "FAIL", "invalid JSON"); return(res) }
  add("metadata.json parses", "PASS")

  ## ---- metadata schema ----
  ok(is.character(m$team_id) && nzchar(m$team_id), "team_id present", "missing/empty")
  ok(is.character(m$team_name) && nzchar(m$team_name), "team_name present", "missing/empty")
  ok(is.character(m$contact) && nzchar(m$contact), "contact present", "missing/empty")
  tier <- suppressWarnings(as.integer(m$tier))
  ok(!is.na(tier) && tier %in% 1:3, "tier in {1,2,3}", paste("got", m$tier))
  ok(is.character(m$entry) && grepl("^(primary|secondary-\\d+)$", m$entry %||% ""),
     "entry is primary|secondary-k", paste("got", m$entry))
  ok(length(m$models) >= 1, "models listed", "none listed")
  ok(is.character(m$approach_family) && nzchar(m$approach_family), "approach_family present", "missing")
  dc <- m$disclosure_class
  ok(isTRUE(dc %in% c("A", "B", "C")), "disclosure_class in {A,B,C}", paste("got", dc))
  if (isTRUE(dc == "A"))
    warn(is.null(m$escrow_doi) || is.na(m$escrow_doi), "escrow_doi null for Class A", "set but class A")
  if (isTRUE(dc %in% c("B", "C")))
    warn(!is.null(m$escrow_doi) && !is.na(m$escrow_doi), "escrow_doi set for Class B/C", "missing escrow_doi")
  ok(isTRUE(m$blinding_attestation), "blinding_attestation == true", "must be true")
  ok(!is.null(m$coverage$interventions) && !is.null(m$coverage$outcomes),
     "coverage declared", "coverage.interventions/outcomes missing")
  pf <- m$prediction_files
  if (is.null(pf) || nrow(as.data.frame(pf)) < 1) {
    add("prediction_files listed", "FAIL", "none"); return(res)
  }
  pf <- as.data.frame(pf)
  add("prediction_files listed", "PASS", paste(nrow(pf), "file(s)"))

  team <- m$team_id %||% ""
  ## One repo = one entry: a Tier-2 entry has 2 files (main + moderator cells),
  ## every other tier has 1. Extra entries belong in their own repo/deposit.
  n_expected <- if (isTRUE(tier == 2)) 2L else 1L
  warn(nrow(pf) == n_expected, paste0("file count for Tier ", tier),
       paste0("expected ", n_expected, " for one entry, got ", nrow(pf),
              " — a repo holds one entry; put extra entries in their own repo"))

  ## ---- per-file: name, hash, structure ----
  for (i in seq_len(nrow(pf))) {
    f <- pf$file[i]; sha <- pf$sha256[i]; fp <- file.path(dir, f)
    pat <- if (isTRUE(tier == 2))
      sprintf("^%s_T2_(primary|secondary-\\d+)_v\\d+_cells_(main|moderator)\\.csv$", team)
    else
      sprintf("^%s_T%s_(primary|secondary-\\d+)_v\\d+\\.csv$", team, tier)
    ok(grepl(pat, basename(f)), paste0("filename ok: ", basename(f)),
       "does not match <team_id>_T<tier>_<entry>_v<n>[...].csv")

    if (!file.exists(fp)) { add(paste0("file present: ", f), "FAIL", "not found"); next }
    add(paste0("file present: ", f), "PASS")
    actual <- digest(file = fp, algo = "sha256")
    ok(identical(tolower(actual), tolower(sha %||% "")), paste0("sha256 matches: ", f),
       paste0("metadata=", substr(sha, 1, 10), "… actual=", substr(actual, 1, 10), "…"))

    d <- tryCatch(suppressWarnings(read_csv(fp, show_col_types = FALSE)), error = function(e) NULL)
    if (is.null(d)) { add(paste0("readable CSV: ", f), "FAIL", "could not parse"); next }

    if (isTRUE(tier == 1))                  .check_t1(d, f, add, ok, warn, rng)
    else if (isTRUE(tier == 3))             .check_t3(d, f, add, ok, warn)
    else if (grepl("_cells_moderator", f))  .check_t2_mod(d, f, add, ok, warn, rng)
    else                                    .check_t2_main(d, f, add, ok, warn, rng)
  }
  res
}

## ---------------- public entry points ----------------

## Validate a single deposited bundle (metadata.json + its prediction files in `dir`).
check_submission <- function(metadata = "metadata.json", dir = ".") {
  .finish(.check_bundle(file.path(dir, metadata), dir), metadata, dir)
}

## Validate a whole cloned submission repository: presence-of-files first, then
## the metadata + per-file checks above.
check_repo <- function(root = ".") {
  res <- tibble(check = character(), status = character(), detail = character())
  add  <- function(check, status, detail = "")
    res <<- add_row(res, check = check, status = status, detail = detail)
  ok   <- function(cond, check, bad) if (isTRUE(cond)) add(check, "PASS") else add(check, "FAIL", bad)
  warn <- function(cond, check, bad) if (isTRUE(cond)) add(check, "PASS") else add(check, "WARN", bad)

  has <- function(p) file.exists(file.path(root, p))
  ok(has("metadata.json"),   "metadata.json present", "missing at repo root")
  ok(has("registration.md"), "registration.md present", "missing at repo root")
  ok(has("codebook.csv"),    "codebook.csv present", "missing at repo root")
  ok(dir.exists(file.path(root, "survey")), "survey/ present", "missing")
  warn(has(file.path("survey", "survey.qsf")), "survey/survey.qsf present",
       "not present yet (provided on invitation)")

  preds <- list.files(file.path(root, "predictions"), pattern = "\\.csv$")
  ok(length(preds) >= 1, "predictions/ has a CSV", "no prediction file in predictions/")

  if (has("registration.md")) {
    blank <- sum(grepl("\\*\\* [—-] .*:\\s*$", readLines(file.path(root, "registration.md"), warn = FALSE)))
    warn(blank == 0, "registration.md filled in", paste(blank, "checklist item(s) still blank"))
  }

  is_example <- TRUE
  if (has("metadata.json")) {
    m <- tryCatch(fromJSON(file.path(root, "metadata.json")), error = function(e) NULL)
    if (!is.null(m)) {
      is_example <- identical(m$team_id, "example")
      warn(!is_example, "team_id set (not the example)",
           "still 'example' — edit metadata.json before submitting")
      cr <- m$code_repository
      warn(!is.null(cr) && nzchar(cr) && !grepl("your-team/your-repo", cr),
           "code_repository set",
           "link your generation code in metadata.json (code_repository / code_doi)")
    }
  }
  leftover <- list.files(file.path(root, "predictions"), pattern = "^example_.*\\.csv$")
  if (!is_example && length(leftover))
    warn(FALSE, "example files removed from predictions/",
         paste("delete before depositing:", paste(leftover, collapse = ", ")))
  if (!is_example && has(file.path("raw_data_deposit", "example_raw_export.csv")))
    warn(FALSE, "example raw export removed from raw_data_deposit/",
         "delete raw_data_deposit/example_raw_export.csv before depositing")

  res <- bind_rows(res, .check_bundle(file.path(root, "metadata.json"), root))
  .finish(res, "metadata.json", root)
}

## ---------------- per-tier structural checks ----------------

.range_warn <- function(d, f, add, rng) {
  for (o in intersect(sst$scale_0_100, names(d)))
    if (rng(d[[o]], 0, 100) > 0) add(paste0(o, " in [0,100]: ", f), "WARN",
                                     paste(rng(d[[o]], 0, 100), "value(s) out of range"))
}

.check_t1 <- function(d, f, add, ok, warn, rng) {
  miss <- setdiff(sst$tier1_required, names(d))
  ok(length(miss) == 0, paste0("Tier-1 required columns: ", f),
     paste("missing:", paste(miss, collapse = ", ")))
  if ("condition" %in% names(d)) {
    bad <- setdiff(unique(as.character(d$condition)), sst$conditions)
    ok(length(bad) == 0, paste0("condition labels valid: ", f),
       paste("unknown:", paste(bad, collapse = ", ")))
    pres <- intersect(sst$conditions, unique(as.character(d$condition)))
    warn(length(pres) == length(sst$conditions), paste0("all 17 conditions present: ", f),
         paste(length(pres), "of", length(sst$conditions), "present"))
  }
  for (mod in names(sst$moderators)) if (mod %in% names(d)) {
    bad <- setdiff(na.omit(unique(as.character(d[[mod]]))), sst$moderators[[mod]])
    warn(length(bad) == 0, paste0(mod, " levels valid: ", f),
         paste("unknown:", paste(bad, collapse = ", ")))
  }
  if ("profile_id" %in% names(d))
    warn(!any(duplicated(d$profile_id)), paste0("profile_id unique: ", f),
         paste(sum(duplicated(d$profile_id)), "duplicate(s)"))
  .range_warn(d, f, add, rng)
  if ("donation_ams" %in% names(d))
    warn(rng(d$donation_ams, sst$donation_range[1], sst$donation_range[2]) == 0,
         paste0("donation_ams in [0,10]: ", f), "value(s) out of range")
  if ("newsletter_signup" %in% names(d)) {
    vals <- unique(na.omit(as.character(d$newsletter_signup)))
    warn(all(vals %in% c("0", "1", "TRUE", "FALSE")), paste0("newsletter_signup binary: ", f),
         paste("unexpected:", paste(setdiff(vals, c("0","1","TRUE","FALSE")), collapse = ", ")))
  }
}

.check_cells <- function(d, f, add, ok, warn, rng, cols) {
  ok(all(cols %in% names(d)), paste0("columns present: ", f),
     paste("missing:", paste(setdiff(cols, names(d)), collapse = ", ")))
  if ("outcome" %in% names(d))
    ok(length(setdiff(unique(d$outcome), sst$outcomes)) == 0, paste0("outcome labels valid: ", f),
       paste("unknown:", paste(setdiff(unique(d$outcome), sst$outcomes), collapse = ", ")))
  if ("condition" %in% names(d))
    ok(length(setdiff(unique(as.character(d$condition)), sst$conditions)) == 0,
       paste0("condition labels valid: ", f),
       paste("unknown:", paste(setdiff(unique(as.character(d$condition)), sst$conditions), collapse = ", ")))
  if ("sd" %in% names(d))
    warn(rng(d$sd, 0, Inf) == 0, paste0("sd >= 0: ", f), "negative sd present")
  if ("n_eff" %in% names(d))
    warn(all(d$n_eff == floor(d$n_eff), na.rm = TRUE), paste0("n_eff integer: ", f), "non-integer n_eff")
}

.check_t2_main <- function(d, f, add, ok, warn, rng) {
  .check_cells(d, f, add, ok, warn, rng, sst$tier2_main_cols)
  warn(nrow(d) == length(sst$conditions) * length(sst$outcomes),
       paste0("full condition x outcome coverage: ", f),
       paste(nrow(d), "rows; expected", length(sst$conditions) * length(sst$outcomes)))
}

.check_t2_mod <- function(d, f, add, ok, warn, rng) {
  .check_cells(d, f, add, ok, warn, rng, sst$tier2_mod_cols)
  if ("moderator" %in% names(d))
    ok(length(setdiff(unique(d$moderator), names(sst$moderators))) == 0,
       paste0("moderator labels valid: ", f),
       paste("unknown:", paste(setdiff(unique(d$moderator), names(sst$moderators)), collapse = ", ")))
  if (all(c("moderator", "moderator_level") %in% names(d))) {
    bad <- d |> distinct(moderator, moderator_level) |>
      filter(!map2_lgl(moderator, moderator_level,
                       ~ .y %in% sst$moderators[[.x]]))
    warn(nrow(bad) == 0, paste0("moderator_level values valid: ", f),
         paste(nrow(bad), "invalid moderator/level pair(s)"))
  }
}

.check_t3 <- function(d, f, add, ok, warn) {
  ok(all(sst$tier3_cols %in% names(d)), paste0("Tier-3 columns present: ", f),
     paste("missing:", paste(setdiff(sst$tier3_cols, names(d)), collapse = ", ")))
  if ("condition" %in% names(d)) {
    ok(!("control" %in% d$condition), paste0("no control row (ATEs are vs control): ", f),
       "control present")
    ok(length(setdiff(unique(as.character(d$condition)), sst$interventions)) == 0,
       paste0("intervention labels valid: ", f),
       paste("unknown:", paste(setdiff(unique(as.character(d$condition)), sst$interventions), collapse = ", ")))
  }
  if ("outcome" %in% names(d))
    ok(length(setdiff(unique(d$outcome), sst$outcomes)) == 0, paste0("outcome labels valid: ", f),
       paste("unknown:", paste(setdiff(unique(d$outcome), sst$outcomes), collapse = ", ")))
  if (all(c("pi_lower", "pi_upper") %in% names(d)))
    ok(all(d$pi_lower <= d$pi_upper, na.rm = TRUE), paste0("pi_lower <= pi_upper: ", f),
       paste(sum(d$pi_lower > d$pi_upper, na.rm = TRUE), "row(s) inverted"))
  warn(nrow(d) <= length(sst$interventions) * length(sst$outcomes),
       paste0("row count <= 208: ", f), paste(nrow(d), "rows"))
}

## ---------------- reporting ----------------

.finish <- function(res, metadata, dir) {
  verdict <- if (any(res$status == "FAIL")) "FAIL"
             else if (any(res$status == "WARN")) "PASS WITH WARNINGS" else "PASS"
  mark <- c(PASS = "[ok]  ", WARN = "[warn]", FAIL = "[FAIL]")
  lines <- c(
    "Silicon Sample Benchmark — submission self-check",
    paste0(rep("-", 52), collapse = ""),
    sprintf("%s %s%s", mark[res$status], res$check,
            if_else(nzchar(res$detail), paste0("  — ", res$detail), "")),
    paste0(rep("-", 52), collapse = ""),
    sprintf("OVERALL: %s   (%d pass, %d warn, %d fail)", verdict,
            sum(res$status == "PASS"), sum(res$status == "WARN"), sum(res$status == "FAIL"))
  )
  cat(lines, sep = "\n"); cat("\n")
  out <- file.path(dir, paste0(tools::file_path_sans_ext(metadata), "_check_report.txt"))
  writeLines(lines, out)
  invisible(res)
}

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0) b else a
