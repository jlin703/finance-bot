import googutils
import argparse
from datetime import datetime, date, timedelta
import json

SPREADSHEET_ID = '1rzlwFJGb0E332vyNzRVB72BGIwmzGPDl9QaCtDYtWyk'
CURRENT_SHEET = 'Su19 Data'
ENTRIES_START_ROW = 9
DATES_RANGE = 'B{}:B'.format(ENTRIES_START_ROW)
STATS_RANGE = 'G3:G5'
DESCRIPTORS = ('TODAY', 'YESTERDAY', 'TOMORROW')

class FoodSpending():
    def __init__(self, get_stats=True):
        self.sheet_service = googutils.get_google_service('https://www.googleapis.com/auth/drive',
                                                 'tokens/drive_full', 'sheets', 'v4', flags=args)
        ranges = []
        ranges.append(DATES_RANGE)
        if get_stats:
            ranges.append(STATS_RANGE)
        results = googutils.batch_read_from_spreadsheet(SPREADSHEET_ID, ranges, self.sheet_service, majorDimension='COLUMNS')
        self.dates = results[0][0]
        if get_stats:
            self.stats = [float(r[1:]) for r in results[1][0]]

    def get_stats(self):
        stats = googutils.read_from_spreadsheet(SPREADSHEET_ID, "'{}'!{}".format(CURRENT_SHEET, STATS_RANGE), 
                                                self.sheet_service, 'COLUMNS')
        return (round(float(stat[1:]), 2) for stat in stats[0]) # total, avg, projected

    def descriptor_to_date(self, raw_date):
        date_obj = date.today()
        one_day = timedelta(days=1)
        if raw_date == 'YESTERDAY':
            date_obj -= one_day
        elif raw_date == 'TOMORROW':
            date_obj += one_day
        date_str = date.strftime(date_obj, '%m/%d')
        if date_str[0] == '0':
            date_str = date_str[1:]
        return date_str

    def get_row_for_date(self, date):
        if date.upper() in DESCRIPTORS:
            date = self.descriptor_to_date(date.upper())
        offset = self.dates.index(date)
        return offset + ENTRIES_START_ROW

    def add_meal(self, meal, name, amount, category, date, stats_change=True):
        row_num = self.get_row_for_date(date)
        if meal.upper() == 'LUNCH':
            start_col, end_col = 'C', 'E'
        elif meal.upper() == 'DINNER':
            start_col, end_col = 'F', 'H'
        entry_range = '{}{}:{}{}'.format(start_col, row_num, end_col, row_num)
        googutils.write_to_spreadsheet(SPREADSHEET_ID, "'{}'!{}".format(CURRENT_SHEET, entry_range), 
                                        [[name, amount, category]], self.sheet_service)
        print('Done!')
        if stats_change:
            _, avg0, proj0 = self.stats
            _, avg1, proj1 = self.get_stats()
            avg_diff, proj_diff = avg1 - avg0, proj1 - proj0
            sign = '+' if avg_diff >= 0 else '-'
            print('Average:     ${0:.2f} ({1}{2:.2f})'.format(avg1, sign, abs(avg_diff)))   
            print('Projected: ${0:.2f} ({1}{2:.2f})'.format(proj1, sign, abs(proj_diff))) 

    def add_shopping(self, store, amount, date):
        row_num = self.get_row_for_date(date)
        entry_range = 'I{}:K{}'.format(row_num, row_num)
        googutils.write_to_spreadsheet(SPREADSHEET_ID, "'{}'!{}".format(CURRENT_SHEET, entry_range), 
                                        [[store, None, amount]], self.sheet_service)

def fetch_meal_type():
    meal_types = ['Restaurant', 'Cooked/Home', 'Free']
    print('MEAL TYPES')
    for i, meal_type in enumerate(meal_types):
        print('({}) {}'.format(i+1, meal_type))
    i = int(input('Select meal type: '))
    return meal_types[i-1]
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('entry_type')
    parser.add_argument('name')
    parser.add_argument('amount', type=float)
    parser.add_argument('-d', '--date', default='TODAY')
    parser.add_argument('-s', '--stats', action='store_true')
    args = parser.parse_args()

    if args.entry_type.upper() in ('LUNCH', 'DINNER'):
        meal_type = fetch_meal_type()
        fs = FoodSpending(get_stats=args.stats)
        fs.add_meal(args.entry_type.upper(), args.name, args.amount, meal_type, args.date, stats_change=args.stats)
    elif args.entry_type.upper() == 'SHOPPING':
        fs = FoodSpending()
        fs.add_shopping(args.name, args.amount, args.date)
