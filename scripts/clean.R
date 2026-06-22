#!/usr/bin/env Rscript
## Entry point: clean a raw Tier-1 survey export into the target schema.
##   make clean INPUT=raw_export.csv     |     Rscript scripts/clean.R raw_export.csv [output.csv]
.a    <- commandArgs(FALSE)
.dir  <- dirname(normalizePath(sub("^--file=", "", .a[grep("^--file=", .a)])))
.root <- dirname(.dir)
suppressPackageStartupMessages(library(jsonlite))
source(file.path(.dir, "lib", "clean_lib.R"))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1)
  stop("usage: Rscript scripts/clean.R <raw_export.csv> [output.csv]", call. = FALSE)

out <- if (length(args) >= 2) args[2] else {
  mp <- file.path(.root, "metadata.json")
  team <- if (file.exists(mp)) tryCatch(fromJSON(mp)$team_id, error = function(e) NULL) else NULL
  file.path(.root, "predictions",
            if (is.null(team)) "cleaned_T1.csv" else sprintf("%s_T1_primary_v1.csv", team))
}
clean_submission(args[1], out)
