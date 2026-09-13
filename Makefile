.PHONY: up down logs test backend-shell

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend frontend python-sandbox

test:
	docker compose run --rm backend pytest -q

backend-shell:
	docker compose run --rm backend bash
