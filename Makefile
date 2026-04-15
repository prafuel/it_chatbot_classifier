SHELL := /bin/bash
.PHONY: dev-build dev-up dev-restart dev-down ps logs clean deep-clean

DOCKER_COM=docker compose -f docker-compose.yml
DOCKER_DEV=$(DOCKER_COM) -f docker-compose.dev.yml --env-file .env
PORT=3000

# Development
dev-build:
	@${DOCKER_DEV} build
dev-up: dev-build
	@${DOCKER_DEV} up -d
	@docker image prune -f
dev-restart:
	@${DOCKER_DEV} restart
dev-down:
	@${DOCKER_DEV} down

# Common
ps:
	@docker ps -a
logs:
	@docker compose logs -f
clean:
	@docker volume prune --force && docker network prune --force
deep-clean:
	@docker system prune -f -a
