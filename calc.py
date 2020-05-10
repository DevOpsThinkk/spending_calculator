import os
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
import argparse
import csv
import jinja2


templateLoader = jinja2.FileSystemLoader('./templates')
templateEnv = jinja2.Environment(loader=templateLoader)


def main(args) -> None:
    if args.use_mock_data:
        df = gen_fake_dataframe()
        generate_chase_stmt(df, args.chase_stmt_out)
    elif args.chase_stmt_path:
        df = get_dataframe(args.chase_stmt_path)
        generate_chase_stmt(df, args.chase_stmt_out)
    else:
        print('Missing chase stmt path')
        exit(1)


def create_out_dir() -> None:
    if not os.path.exists('./out'):
        os.makedirs('./out')


def get_dataframe(path: str) -> pd.DataFrame:
    with open(path, 'r') as f:
        reader = csv.DictReader(f, skipinitialspace=True, delimiter=',')
        stmt_list = [{k: v for k, v in row.items()} for row in reader]

    df = pd.DataFrame(stmt_list)
    df['amount'] = df['Amount'].dropna()
    df['amount'] = pd.to_numeric(df['amount'])
    df['date'] = pd.to_datetime(df['Posting Date'])
    df.set_index('date', inplace=True)

    df['amount'] = -df['amount']
    return df.loc[df['amount'] > 0]


def gen_fake_dataframe() -> pd.DataFrame:
    df = pd.DataFrame()
    end = date.today().replace(day=1) - relativedelta(days=1)
    year_ago = end - relativedelta(years=1)
    # One row per day
    date_range = pd.date_range(year_ago, end, freq='D')
    df['date'] = date_range
    df['amount'] = pd.Series(np.random.uniform(50, 300, size=len(df.index)))
    df.set_index('date', inplace=True)
    return df


def generate_chase_stmt(df: pd.DataFrame, output: str) -> None:
    """
    Expects a dataframe with columns index and `amount`.
    The index is the date.
    Amount should be only positive numbers representing expedatures.
    """

    # TODO: remove the first month if account was opened midway through month.
    # This would throw off the average burn, if there was a partial month.

    # Beggining of month, 1 year ago
    beginning_of_month = date.today().replace(day=1)
    end_of_prev = beginning_of_month - relativedelta(days=1)
    n_months_ago = (beginning_of_month - relativedelta(years=1))
    df_year = df[
        (df.index > n_months_ago.isoformat()) &
        (df.index <= end_of_prev.isoformat())
        ]

    # Get last 12 months only
    monthly = df_year.groupby(pd.Grouper(freq='M')).sum()

    create_out_dir()

    plot = monthly.plot()
    fig = plot.get_figure()
    fig.tight_layout()
    fig.savefig('./out/chase_monthly.png')

    monthly_list = [
        {
            'date': val.name.strftime('%B %Y'),
            'spend': round(val.amount, 2),
        }
        for idx, val in monthly.iterrows()
    ]

    avg_burn = round(monthly.mean().iloc[0], 2)
    template = templateEnv.get_template('chase_stmt.html.j2')
    output_html = template.render({
        'monthly_data': monthly_list,
        'average_burn': avg_burn,
    })

    if not output:
        path = './out/chase_stmt.html'
        print(f'Writing statement to {path}')
        with open(path, 'w') as f:
            f.write(output_html)
    else:
        with open(output, 'w') as f:
            f.write(output_html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate finances.')
    parser.add_argument('--chase', dest='chase_stmt_path', type=str,
                        help='Chase account statement (1 Yr)')
    parser.add_argument('--chase-out', dest='chase_stmt_out', type=str,
                        help='Chase account statement html output path',
                        required=False)
    parser.add_argument('--mock', dest='use_mock_data', type=bool,
                        help='Generate fake data for calculations.')
    args = parser.parse_args()
    main(args)
