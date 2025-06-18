NAME		:= git.figntigger.io/chrismc/myair-to-mqtt
TAG			:= $$(git describe --abbrev=0)
IMG			:= ${NAME}:${TAG}
LATEST		:= ${NAME}:latest

define find.functions
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
endef

help:
	@echo 'The following commands can be used.'
	@echo ''
	$(call find.functions)

build: ## Build the Docker image
build:
	@echo "building (includes tagging)"
	docker build --tag ${IMG} .

push: ## Push the Docker image to the package registry
push:
	@echo "pushing to package registry"
	# push this recent tag
	@docker build --push --tag ${IMG} .
	# push this recent as latest
	@docker build --push --tag ${LATEST} .

.PHONY: help build push

# END OF FILE
