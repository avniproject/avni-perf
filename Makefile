build_perf:
	./gradlew build

run_perf:
	./gradlew gatlingRun

run_perf_local:
	./gradlew gatlingRun -DBASE_URL=http://localhost:8021

generate_entities:
	cd tools/entity-metadata && npm install --silent && npm run generate

check_entities_current: generate_entities
	@git ls-files --error-unmatch src/gatling/resources/avni-entities.json > /dev/null 2>&1 \
	  || (echo "avni-entities.json is not tracked - commit it, or this check silently passes" && exit 1)
	@git diff --exit-code HEAD -- src/gatling/resources/avni-entities.json \
	  || (echo "avni-entities.json is stale - run 'make generate_entities' and commit the result" && exit 1)
