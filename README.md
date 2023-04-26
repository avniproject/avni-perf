# Load Tests for Avni Sync
`./gradlew gatlingRun`

## Configurations
Users for the simulation can be setup in resources/sync-users.csv
The csv expects the following columns:
- `userName`
- `lastModifiedDateTime`
- `password`
- `token`

Either one of `password` or `token` can be provided. If `password` is provided, the token is generated during the simulation. Token generation during simulation requires AWS CLI to be installed with credentials setup on the machine executing the simulation. 

### Environment variables
Can be overridden using `./gradlew gatlingRun -DBASE_URL=` etc.

`BASE_URL` default https://perf.avniproject.org

`USER_COUNT` defaults to number of rows in resources/sync-users.csv

`RAMP_PERIOD` defaults to number of rows in resources/sync-users.csv * 20

`PAGE_SIZE` defaults to 100

`NOW` defaults to current time at start of simulation