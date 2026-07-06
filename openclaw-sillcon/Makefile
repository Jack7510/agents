PYTHON ?= python

.PHONY: test lint qq-mail-dry-run product-news-once tech-papers-once strategy-intel-once

test:
	$(PYTHON) -m unittest discover -s tests

lint:
	PYTHONPYCACHEPREFIX=.pycache $(PYTHON) -m compileall scripts tests

qq-mail-dry-run:
	$(PYTHON) scripts/qq_mail_tool.py --subject "OpenClaw 测试邮件" --to "test@example.com" --from "sender@example.com" --body "这是一封本地 dry-run 测试邮件。" --dry-run

product-news-once:
	$(PYTHON) scripts/send_product_news.py --dry-run

tech-papers-once:
	$(PYTHON) scripts/send_tech_papers.py --dry-run

strategy-intel-once:
	$(PYTHON) scripts/send_product_news.py --config agents/strategy-intel/sources.json --archive-root data/strategy-intel --lookback-hours 96 --limit 8 --dry-run
