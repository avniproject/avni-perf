build_perf:
	./gradlew build

run_perf:
	./gradlew gatlingRun

run_perf_local:
	./gradlew gatlingRun -DBASE_URL=http://localhost:8021

unit_test: ## Unit tests for the simulation's pure logic - push distribution and page parsing
	@./gradlew unitTest

smoke_closed_port: ## D8.5: the simulation must fail fast against a port with nothing behind it
	@./tools/closed-port-check.sh

generate_entities:
	cd tools/entity-metadata && npm install --silent && npm run generate

check_entities_current: generate_entities
	@git ls-files --error-unmatch src/gatling/resources/avni-entities.json > /dev/null 2>&1 \
	  || (echo "avni-entities.json is not tracked - commit it, or this check silently passes" && exit 1)
	@git diff --exit-code HEAD -- src/gatling/resources/avni-entities.json \
	  || (echo "avni-entities.json is stale - run 'make generate_entities' and commit the result" && exit 1)

survey_bundle: ## Report what an implementation bundle can generate. BUNDLE=/path/to/bundle
	@test -n "$(BUNDLE)" || (echo "usage: make survey_bundle BUNDLE=/path/to/bundle" && exit 1)
	@python3 tools/data-generator/survey.py "$(BUNDLE)"

test_data_generator: ## Run the data generator's tests
	@cd tools/data-generator && \
		test -d .venv || python3 -m venv .venv; \
		.venv/bin/pip install -q pytest && .venv/bin/python -m pytest tests -q

validate_dataset: ## Run the H5 statistical gate. STATS=stats.json from validate.sql
	@test -n "$(STATS)" || (echo "usage: make validate_dataset STATS=stats.json" && exit 1)
	@cd tools/data-generator && python3 validate.py "$(abspath $(STATS))"


structural_check: ## H5 steps 1-2: can the client read this dataset? USERS=path [URL=...]
	@test -n "$(USERS)" || (echo "usage: make structural_check USERS=path/to/sync-users.csv [URL=http://host:port]" && exit 1)
	@./tools/data-generator/structural_check.sh --users "$(USERS)" $(if $(URL),--url "$(URL)",) $(if $(OUT),--out "$(OUT)",)
