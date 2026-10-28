# Recompute published contrasts from archived posterior draws, without refitting.
# Run upstream preprocessing in an isolated output directory. Base R + jsonlite;
# upstream preprocessing additionally requires tidyverse.
args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(if (length(args) >= 1) args[[1]] else "build/hybrid/sources")
out <- if (length(args) >= 2) args[[2]] else "build/hybrid/reproduction"
dir.create(out, recursive = TRUE, showWarnings = FALSE)
out <- normalizePath(out)
summarise_draws <- function(x) {
  ci <- quantile(x * 1000, c(.025, .5, .975))
  pd <- max(mean(x > 0), mean(x < 0))
  list(estimate_ms = unname(ci[2]), lower_ms = unname(ci[1]), upper_ms = unname(ci[3]),
       probability_direction = pd, evidence_ratio = if (pd < 1) pd / (1 - pd) else NULL)
}
reports <- list()
original <- getwd()
for (study in 1:4) {
  directory <- file.path(root, paste0("study", study), "Data and analysis")
  destination <- file.path(out, paste0("study", study))
  dir.create(file.path(destination, "Data"), recursive = TRUE, showWarnings = FALSE)
  data_name <- paste0("S", study, "_data.csv")
  script_name <- paste0("S", study, "_preprocessing.R")
  file.copy(file.path(directory, "Data", data_name), file.path(destination, "Data", data_name), overwrite = TRUE)
  file.copy(file.path(directory, script_name), file.path(destination, script_name), overwrite = TRUE)
  setwd(destination)
  source(script_name, local = new.env())
  setwd(original)
  result_name <- paste0("S", study, "_data_preprocessed.csv")
  original_data <- read.csv(file.path(directory, "Data", result_name))
  reproduced_data <- read.csv(file.path(destination, "Data", result_name))
  agreement <- isTRUE(all.equal(original_data, reproduced_data, tolerance = 1e-7, check.attributes = FALSE))
  fit <- readRDS(file.path(directory, "Fitted models", "fit.rds"))
  # Reading a stored stanfit attribute does not require loading rstan's class methods.
  simulation <- attr(fit$fit, "sim")
  draws <- do.call(rbind, lapply(seq_along(simulation$samples), function(chain) {
    columns <- simulation$samples[[chain]]
    wanted <- c(grep("^b_", names(columns), value = TRUE), "sigma", "ndt")
    as.data.frame(columns[wanted])[(simulation$warmup2[chain] + 1):simulation$n_save[chain], , drop = FALSE]
  }))
  coefficients <- grep("^b_", names(draws), value = TRUE)
  cells <- list()
  for (column in coefficients) {
    parts <- strsplit(sub("^b_", "", column), ":")[[1]]
    condition <- sub("^condition", "", parts[grepl("^condition", parts)])
    condition <- switch(condition, exp = "experimental", con = "control", condition)
    factor <- parts[!grepl("^condition", parts)]
    factor <- sub("^(pattern|constituent)", "", factor)
    factor <- gsub("nonMconstituent", "non-constituent", factor)
    key <- paste(c(condition, factor), collapse = ":")
    cells[[key]] <- draws$ndt + exp(draws[[column]] + draws$sigma^2 / 2)
  }
  contrasts <- list()
  for (name in grep("^experimental", names(cells), value = TRUE)) {
    control <- sub("^experimental", "control", name)
    contrasts[[name]] <- cells[[name]] - cells[[control]]
  }
  if (study == 2) {
    contrasts[["experimental_vs_reverse"]] <- cells$experimental - cells$reverse
    contrasts[["reverse_vs_control"]] <- cells$reverse - cells$control
  }
  if (study == 3) {
    contrasts[["moderation"]] <- contrasts[["experimental:constituent"]] - contrasts[["experimental:non-constituent"]]
  }
  write.csv(as.data.frame(cells), file.path(destination, "expected-draws-seconds.csv"), row.names = FALSE)
  reports[[study]] <- list(study = study, preprocessing_matches = agreement,
    posterior_draws = nrow(draws), posterior_source = "archived fitted model; not a new fit",
    expectation = "ndt + exp(cell_coefficient + sigma^2/2); population level, random effects zero",
    conditions = lapply(cells, summarise_draws), contrasts = lapply(contrasts, summarise_draws))
  cat("Study", study, "preprocessing matches:", agreement, "posterior draws:", nrow(draws), "\n")
}
jsonlite::write_json(list(schema = 1, studies = reports, R_version = R.version.string),
                     file.path(out, "posterior-reproduction.json"), pretty = TRUE, auto_unbox = TRUE, digits = 12)
if (!all(vapply(reports, function(r) r$preprocessing_matches, logical(1)))) stop("Preprocessing mismatch")
