# Meme Stock Profit Target Calculator

MSPTC is a command line tool for critical space mission preparation. Displays the amount you have to gain to achieve targeted net value after taxes and other withholdings. It uses [Open Exchance Rates API](https://openexchangerates.org) to fetch the USD/EUR rate. You can create an free account for limited usage [here](https://openexchangerates.org/signup/free).

## Installation

1. Clone the repository to your machine
2. Create virtual environment
```
python venv -m <venv-name>
```
3. Activate virtual environment
```
./<venv-name>/Scripts/activate
```
4. Install requirements
```
pip install -r freeze.txt
```
5. Create `.env` file to project root and add your personal `app_id`:
```
app_id = <copy your OER app id here>
```
6. Adjust variables to fit your needs in `const.py`
```python
TAX_RATE = 30
ADDITIONAL_WITHHOLD = 10
DB_FILENAME = 'db.sqlite'
```

## Usage

1. Add profit targets
```
python ./main.py -a tendies 40
```

2. Print report
```
python ./main -p
```


## Contributing
Go ahead.

## License
[MIT](https://choosealicense.com/licenses/mit/)