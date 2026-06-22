.PHONY: help check clean

help:
	@echo "make check                  validate this submission (files, metadata, data)"
	@echo "make clean INPUT=raw.csv    clean a raw Tier-1 survey export into predictions/"

check:
	Rscript scripts/check.R

clean:
	@test -n "$(INPUT)" || (echo "usage: make clean INPUT=your_raw_export.csv" && exit 1)
	Rscript scripts/clean.R "$(INPUT)"
