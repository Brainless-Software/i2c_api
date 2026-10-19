#!/usr/bin/env -S just --justfile

set default-list := true

mkdocs:
    mkdocs build & sleep 1 & mkdocs gh-deploy

test-cov:
    pytest --cov=i2c_api --rootdir=src --cov-report=html & xdg-open htmlcov/index.html