#!/bin/bash
export PYTHONPATH=.
pytest --cov=app --cov-report=term-missing tests/