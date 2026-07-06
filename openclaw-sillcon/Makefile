PYTHON ?= python

.PHONY: test lint product-news-once

test:
	$(PYTHON) -m unittest discover -s tests

lint:
	PYTHONPYCACHEPREFIX=.pycache $(PYTHON) -m compileall scripts tests

product-news-once:
	$(PYTHON) scripts/send_product_news.py --dry-run
