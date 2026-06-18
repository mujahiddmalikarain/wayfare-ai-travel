# One-command operations. Requires Docker + Docker Compose v2.
.DEFAULT_GOAL := help
.PHONY: help up seed reembed logs ps down reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

up: ## Build and start db, redis, api
	docker compose up -d --build

seed: ## Run the ingestion pipeline once (needs ./data/<city>/*.csv.gz)
	docker compose --profile seed run --rm ingest

reembed: ## Re-run only the embedding + review-summary stages
	docker compose --profile seed run --rm ingest \
		python -m ingestion --from embeddings

logs: ## Tail the API logs
	docker compose logs -f api

ps: ## Show running services
	docker compose ps

down: ## Stop services (keep data)
	docker compose down

reset: ## Stop services and wipe the database volume
	docker compose down -v
