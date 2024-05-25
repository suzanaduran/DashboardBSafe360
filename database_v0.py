import sqlalchemy
from urllib.parse import quote_plus
import pandas as pd


def get_data():
    try:
        print('Connecting to the PostgreSQL database...')

        cred = open("credentials.json", "r")
        user = cred["user"]
        pw = cred["password"]
        host = cred["host"]
        port = cred["port"]
        db = cred["database"]

        engine = sqlalchemy.create_engine('postgresql+pg8000://%s:%s@{%s}:{%s}/{%s}' % (user,quote_plus(pw), host, port,db))

        connpg = engine.connect().execution_options(autocommit=True)

        sql = "select * from bike_safety.bsafe07"

        df_raw = pd.read_sql(sql, connpg)

        engine.dispose()
        print('Connection Closed')
    except (Exception) as error:
        print(error)

    df = df_raw.copy()
    df.reset_index(inplace=True, drop=True)

    rides = pd.read_csv('20231105_rides.csv')

    for i in range(len(df.columns)):
        if i == 0:
            pass
        elif i in [1, 4, 5]:
            df[df.columns[i]] = pd.to_datetime(df[df.columns[i]])
        else:
            df[df.columns[i]] = pd.to_numeric(df[df.columns[i]], errors='coerce')

    df.drop_duplicates(inplace=True)

    df['distance left'] = df['usreading_l'] - 21
    df['distance right'] = df['usreading_r'] - 21

    df = df[(df['latitude'] != 0) & (df['longitude'] != 0) & (~df['latitude'].isna()) & (~df['longitude'].isna())]
    
    df['ride'] = 0
    df['country'] = 0
    for i in range(rides.shape[0]):
            r = rides.iloc[i]["ride"]
            c = rides.iloc[i]["country"]
            start = pd.to_datetime(rides.iloc[i]["start"])
            end = pd.to_datetime(rides.iloc[i]["end"])

            df.loc[(df["dtg"] > start) & (df["dtg"] < end), "ride"] = list(df[(df["dtg"] > start) & (df["dtg"] < end)].loc[:, "ride"].replace(0, r))
            df.loc[(df["dtg"] > start) & (df["dtg"] < end), "country"] = list(df[(df["dtg"] > start) & (df["dtg"] < end)].loc[:, "country"].replace(0, c))

    df_v1 = df[df['ride'].isin(rides['ride'].unique())].copy()

    df_v1['dist_left'] = df_v1['distance left']
    df_v1['dist_left'] = df_v1['dist_left'].apply(lambda x: x if x <= 400 else 400)

    df_v1['dist_right'] = df_v1['distance right']
    df_v1['dist_right'] = df_v1['dist_right'].apply(lambda x: x if x <= 400 else 400)
    df_v1 = df_v1[df_v1['dist_left'] >= 10]

    return df_v1

