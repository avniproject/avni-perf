build_perf:
	./gradlew build

run_perf:
	./gradlew gatlingRun

## Regenerate docs/run-log.md from the artefacts bucket. Idempotent; back-fills.
## BUCKET=... to override the default avni-loadtest-<account>.
run_log:
	./tools/update-run-log.sh $(if $(BUCKET),--bucket $(BUCKET))

run_perf_local:
	./gradlew gatlingRun -DBASE_URL=http://localhost:8021

provision_org: ## Create an org and install a bundle through the server's APIs. URL=... BUNDLE=x.zip ORG_NAME=...
	@test -n "$(URL)" -a -n "$(BUNDLE)" -a -n "$(ORG_NAME)" || (echo "usage: make provision_org URL=https://host BUNDLE=~/Downloads/Tanuh.zip ORG_NAME=tanuh-load [ADMIN=admin]" && exit 2)
	@./tools/provision-org.sh --url "$(URL)" --bundle "$(BUNDLE)" --name "$(ORG_NAME)" $(if $(ADMIN),--admin "$(ADMIN)",)

bootstrap_user: ## SQL for one syncable user, no dataset needed. ORG=1 USERNAME=x [AUDIT_USER=1]
	@test -n "$(ORG)" -a -n "$(USERNAME)" || (echo "usage: make bootstrap_user ORG=1 USERNAME=loadtest@openchs [AUDIT_USER=1]" && exit 2)
	@cd tools/data-generator && python3 bootstrap_user.py --organisation "$(ORG)" --username "$(USERNAME)" $(if $(AUDIT_USER),--audit-user "$(AUDIT_USER)",)

teardown_org: ## SQL to empty an org between scenarios. DATASET=datasets/x.json [SCOPE=data|all]
	@test -n "$(DATASET)$(ORG)" || (echo "usage: make teardown_org DATASET=tools/data-generator/datasets/tanuh-small.json [SCOPE=data|all]\n   or: make teardown_org ORG=3 ID_BASE=1000000" && exit 2)
# DATASET is the recipe that was generated, or a build's manifest.json. It carries the
# organisations and the id_base, so neither is retyped - a wrong id_base is the one input here
# that fails quietly, taking the bundle's own rows or none at all.
#
# It prints SQL rather than running it. This deletes, and the one thing worse than a slow reset is
# a fast one against the wrong database - so the connection string is chosen by whoever runs it:
#   make teardown_org DATASET=tools/data-generator/datasets/tanuh-small.json > /tmp/teardown.sql
#   psql -d <db> -v ON_ERROR_STOP=1 -f /tmp/teardown.sql
	@cd tools/data-generator && python3 teardown_org.py \
		$(if $(DATASET),--dataset "$(abspath $(DATASET))",) \
		$(if $(ORG),--organisation "$(ORG)",) \
		$(if $(ID_BASE),--id-base "$(ID_BASE)",) $(if $(SCOPE),--scope "$(SCOPE)",)

check_environment: ## Is an environment ready for a run? URL=... [SYNC_USER=...] [DB=conninfo] [WAF=1]
	@test -n "$(URL)" || (echo "usage: make check_environment URL=https://host [SYNC_USER=name] [DB=conninfo] [WAF=1]" && exit 2)
# SYNC_USER, not USER: USER is set in every login shell, so Make would inherit it and the check
# would silently run against your own login name, reporting "no such user" as an environment
# failure. Named so it cannot be inherited by accident.
	@./tools/environment-check.sh --url "$(URL)" $(if $(SYNC_USER),--user "$(SYNC_USER)",) $(if $(DB),--db "$(DB)",) $(if $(WAF),--waf,)

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

test_tools: ## F7's calibration gate and anything else under tools/tests
	@cd tools/data-generator && test -d .venv || python3 -m venv .venv
	@tools/data-generator/.venv/bin/pip install -q pytest
# Runs from the repo root so calibrate.py resolves the way it does in use. It shares the
# generator's venv rather than growing a second one for one dependency.
	@tools/data-generator/.venv/bin/python -m pytest tools/tests -q

validate_dataset: ## Run the H5 statistical gate. STATS=stats.json from validate.sql
	@test -n "$(STATS)" || (echo "usage: make validate_dataset STATS=stats.json" && exit 1)
	@cd tools/data-generator && python3 validate.py "$(abspath $(STATS))"


structural_check: ## H5 steps 1-2: can the client read this dataset? USERS=path [URL=...]
	@test -n "$(USERS)" || (echo "usage: make structural_check USERS=path/to/sync-users.csv [URL=http://host:port]" && exit 1)
	@./tools/data-generator/structural_check.sh --users "$(USERS)" $(if $(URL),--url "$(URL)",) $(if $(OUT),--out "$(OUT)",)
