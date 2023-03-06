# Load Tests for Avni Sync
`./gradlew gatlingRun`

## Configurations
Users for the simulation can be setup in resources/users.csv

### Environment variables
Can be overridden using `./gradlew gatlingRun -DBASE_URL=` etc.

`BASE_URL` default https://perf.avniproject.org

`USER_COUNT` defaults to number of rows in resources/users.csv

`RAMP_PERIOD` defaults to number of rows in resources/users.csv * 3

`PAGE_SIZE` defaults to 100

`NOW` defaults to 2023-02-28T14:37:59.686Z