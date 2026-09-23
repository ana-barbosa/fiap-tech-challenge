.PHONY: setup seed run down logs qa drop-price

SHELL := /bin/bash

SERVICES := $(notdir $(wildcard services/*))

setup:
	test -f .env || cp .env.example .env
	cp services/agent_backend/.env.example services/agent_backend/.env
	cp services/telegram_bot/.env.example services/telegram_bot/.env
	cp services/crm/.env.example services/crm/.env
	cp services/etl/.env.example services/etl/.env

	# stop pods so they release databases before we wipe them
	docker compose down

	# Hard reset on databases
	find data/chroma -mindepth 1 ! -name '.gitkeep' -delete
	rm -f services/agent_backend/db/conversations.sqlite
	rm -f services/crm/db/listings.sqlite
	rm -f services/telegram_bot/data/last_update_id.txt

	docker compose build

seed:
	docker compose run --rm crm python seed_data/seed_crm.py
	docker compose run --rm agent_backend python seed_data/seed_conversations.py

run:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f $(SERVICE)

qa:
	@status=0; \
	for name in $(SERVICES); do \
		docker compose run --rm $$name python -m pytest tests | sed "s/^/[$$name] /"; \
		if [ $${PIPESTATUS[0]} -ne 0 ]; then status=1; fi; \
	done; \
	exit $$status

drop-price:
	@test -n "$(PROPERTY_ID)" -a -n "$(PRICE)" || (echo "Usage: make drop-price PROPERTY_ID=<id> PRICE=<new_price>" && exit 1)
	curl -s -X PATCH http://localhost:8000/properties/$(PROPERTY_ID) -H "Content-Type: application/json" -d '{"price": $(PRICE)}'
	@echo
