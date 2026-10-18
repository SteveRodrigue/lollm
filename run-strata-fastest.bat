@echo off
rem Profile "fastest": defined in configs\profiles.json (model, options, why). Extra options are passed on, e.g. --always-start or --no-fast.
call "%~dp0run-strata-fit.bat" --profile fastest %*
