#!/bin/sh
pip install lxml
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.in-project true # for caching
poetry install --no-interaction --no-ansi
