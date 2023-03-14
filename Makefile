build:
	./gradlew build

run_perf:
	./gradlew gatlingRun

run_perf_local:
	./gradlew gatlingRun -DBASE_URL=http://localhost:8021