## To build ##
1. Run `pipenv install`
2. Set up a `.env` file with AWS credentials
3. In terminal run `source env` to marry credentials
4. Write scraper in `scraper_file.py`
5. Update `zappa_setings.json` with project name, description and interval

## To deploy to lambda ##
1. Run `zappa deploy`

## To update to lambda ##
1. Run `zappa update`
