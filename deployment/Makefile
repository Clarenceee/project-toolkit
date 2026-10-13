.DEFAULT_GOAL := help

HELM ?= helm
ENV ?= dev

.PHONY: help lint render diff deploy

help:
	@echo "lint       Lint all example chart configurations"
	@echo "render     Render all example chart configurations"
	@echo "diff       Diff the $(ENV) App-of-Apps against the current cluster"
	@echo "deploy     Apply the $(ENV) App-of-Apps to the current cluster"

lint:
	$(HELM) lint charts/generic-helm -f values/generic-platform/dev-values.yaml
	$(HELM) lint charts/ray-service -f values/platform-example/dev-values.yaml
	$(HELM) lint charts/flink-helm -f charts/flink-helm/values.example.yaml

render:
	$(HELM) template platform-example charts/generic-helm -f values/generic-platform/dev-values.yaml
	$(HELM) template platform-example charts/ray-service -f values/platform-example/dev-values.yaml
	$(HELM) template example charts/flink-helm -f charts/flink-helm/values.example.yaml

diff:
	bash scripts/diff.sh $(ENV)

deploy:
	bash scripts/deploy.sh $(ENV)
