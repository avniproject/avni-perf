# Load Tests for Avni Sync
`./gradlew gatlingRun`

## Configurations
Users for the simulation can be setup in resources/users.csv

### Environment variables
Can be overridden using `./gradlew gatlingRun -DBASE_URL=` etc.

`BASE_URL` default http://localhost:8021

`USER_COUNT` defaults to number of rows in resources/users.csv

`RAMP_PERIOD` defaults to number of rows in resources/users.csv * 3

`PAGE_SIZE` defaults to 100