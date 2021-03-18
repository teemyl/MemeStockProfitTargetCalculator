import os
import requests
import sqlite3
import sys
import getopt
import json
import datetime
from tabulate import tabulate

import settings
from const import CONSTANTS

class DBConnection:

  def __init__(self):
    self.sqlite3_filename = CONSTANTS.DB_FILENAME
    self.connection = self.connect()
    self.cursor = self.connection.cursor()
    # Sketchy to init every time, should probably check first if old db exists
    self.init_tables()

  def __del__(self):
    try:
      self.cursor.close()
      self.connection.close()
    except:
      pass

  def connect(self):
    try:
      return sqlite3.connect(self.sqlite3_filename)
    except sqlite3.Error as e:
      print('Database connection error: {}. Exiting...'.format(str(e)))
      sys.exit(2)
  
  def init_tables(self):
    try:
      self.cursor.execute('CREATE TABLE targets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, base_value FLOAT, target_value FLOAT)')
    except:
      pass

    try:
      self.cursor.execute('CREATE TABLE rates (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, eur FLOAT, usd FLOAT, gbp FLOAT)')
    except:
      pass

    self.connection.commit()

  def reset(self):
    self.cursor.execute('DROP TABLE targets')
    self.cursor.execute('DROP TABLE rates')
    self.init_tables()

  def update_rates(self, latest):
    today = datetime.date.today()
    self.cursor.execute(
      'INSERT INTO rates (date, eur, usd, gbp) VALUES (?, ?, ?, ?)',
      (today, latest['rates']['EUR'], float(1), latest['rates']['GBP'])
    )
    self.connection.commit()

  def update_targets(self, name, base_value, target_value):
    self.cursor.execute(
      'INSERT INTO targets (name,base_value,target_value) VALUES (?,?,?)',
      (name, base_value, target_value)
    )
    self.connection.commit()

  def get_targets(self):
    return self.cursor.execute('SELECT id, name, ROUND(base_value, 2), ROUND(target_value, 2) FROM targets').fetchall()

  def get_usd_eur_by_date(self, date):
    return self.cursor.execute('SELECT eur FROM rates WHERE date=?', (date,)).fetchone()

class OERApi:
  app_id = None
  base_url = None

  def __init__(self):
    # Get app_id from .env file
    self.app_id = os.getenv('OPEN_EXCHANGE_RATES_APP_ID')
    self.base_url = CONSTANTS.OER_API_BASE_URL

  def _get(self, url):
    res = requests.get(
      url,
      params = { 'app_id': self.app_id }
    )
    return res.json()
  
  def get_latest(self):
    url = self.base_url + 'latest.json'
    return self._get(url)


class ProfitTargetCalculator:
  # Targets: id, name, base_value, target_value
  # Rates: id, date, eur, usd, gbp
  db = None
  api = None
  opts = args = None

  def __init__(self, argv):
    self.db = DBConnection()
    self.api = OERApi()

    try:
      self.opts, self.args = getopt.getopt(argv, 'hpacri', ['help', 'print', 'add', 'calc', 'reset', 'info'])
    except getopt.GetoptError as e:
      print(e)
      print('main.py <-h --help> <-p --print> <-a --add> <-c --calc>')
      sys.exit(2)

  def __del__(self):
    try:
      self.api.delete()
      self.db.delete()
    except:
      pass

  def calculate_target(self, base_value, target_rate):
    base_with_additional = \
      base_value / (1 - CONSTANTS.ADDITIONAL_WITHHOLD * 0.01) \
      if CONSTANTS.ADDITIONAL_WITHHOLD \
      else base_value

    base_with_tax = \
      base_with_additional / (1 - CONSTANTS.TAX_RATE * 0.01) \
      if CONSTANTS.TAX_RATE \
      else base_with_additional

    return base_with_tax / target_rate

  def update_rates(self):
    latest = self.api.get_latest()
    
    if 'rates' in latest:
      self.db.update_rates(latest)
    else:
      return None

  def print_report(self):
    targets = self.db.get_targets()
    targets.append(('', 'TOTAL', sum([x[2] for x in targets]), sum([x[3] for x in targets])))
    print(tabulate(targets, headers=['id', 'Name', 'Base value (€)', 'Target value ($)']))

  def run(self):
    # run all given commands
    for opt, arg in self.opts:
      if opt in ['-h', '--help']:
        print('main.py <-h --help> <-p --print> <-a --add> name value')
        sys.exit(2)

      elif opt in ['-p', '--print']:
        self.print_report()
        sys.exit()

      elif opt in ['-c', '--calc']:
        if (not len(self.args) == 2):
          print('main.py <-c --calc> base_value target_rate')
          sys.exit(2)
        print(self.calculate_target(float(self.args[0]), float(self.args[1])))

      elif opt in ['-r', '--reset']:
        self.db.reset()

      elif opt in ['-i', '--info']:
        print('Active coefficients:')
        if CONSTANTS.TAX_RATE:
          print('TAX RATE: {:.2f}%'.format(float(CONSTANTS.TAX_RATE)))
        if CONSTANTS.ADDITIONAL_WITHHOLD:
          print('ADDITIONAL WITHHOLD: {:.2f}%'.format(float(CONSTANTS.ADDITIONAL_WITHHOLD)))
        today = datetime.date.today()
        usd_eur_today = self.get_usd_eur_by_date(today)
        if usd_eur_today:
          print('USD/EUR ({}): {:.2f}'.format(today, usd_eur_today[0]))

      elif opt in ['-a', '--add']:
        # If not enough args provided, exit with error message
        if (len(self.args) < 2):
          print('main.py <-a --add> name value')
          sys.exit(2)

        name = ' '.join(self.args[0:-1])
        base_value = float(self.args[-1])

        usd_eur_today = self.db.get_usd_eur_by_date(datetime.date.today())

        if usd_eur_today == None:
          self.db.update_rates(self.api.get_latest())
          usd_eur_today = self.db.get_usd_eur_by_date(datetime.date.today())

        usd_eur_today = usd_eur_today[0]
        
        target_value = self.calculate_target(base_value, usd_eur_today)

        self.db.update_targets(name, base_value, target_value)

if __name__ == "__main__":
  ptc = ProfitTargetCalculator(sys.argv[1:])
  ptc.run()