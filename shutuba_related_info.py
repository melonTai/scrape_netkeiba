from selenium.webdriver.remote.webdriver import WebDriver
from selenium import webdriver
from mypackage import scrape, const, utils
from mypackage.page import race
import os
import time
import sys
import pandas as pd
import pathlib
import signal

def scrape_odds_and_save(race_id, folder):
    res = scrape.scrape_odds(race_id)
    data = res["data"]
    for key, df in data.items():
        path = f"{folder}/{key}.csv"
        df.to_csv(path)

def scrape_related_racehistory(race_id):
    root_path = pathlib.WindowsPath(r'G:\マイドライブ\Keiba\data\race')
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    race_const = const.Race(race_id)
    # フォルダ作成
    folder = f"{root_path}/{race_const.place}"
    if not os.path.exists(folder):
        os.makedirs(folder)
    # 過去に同様のデータを取得済みの場合はスキップ
    file_path = f"{folder}/{race_const.year}_all.csv"
    if os.path.exists(file_path):
        df_b = pd.read_csv(file_path, index_col=0)
        if df_b["race_id"].astype(str).isin([race_id]).any():
            return None
    res = scrape.scrape_race(race_id)
    if res["status"]:
        # 重複を避けて保存
        df = res["data"]
        if os.path.exists(file_path):
            df_b = df_b.append(df)
            df_b.drop_duplicates(inplace=True)
            df_b.to_csv(file_path)
        else:
            df.to_csv(file_path)

def main():
    if len(sys.argv) < 2:
        print("引数が足りません")
        print("raceid")
        sys.exit()
    shutuba_id = sys.argv[1]
    shutuba_res = scrape.scrape_shutuba(shutuba_id)
    if shutuba_res["status"]:
        # フォルダ生成
        title = shutuba_res["title"]
        race_const = const.Race(shutuba_id)
        date = shutuba_res["date"]
        date = date.replace("/","月")
        date = date + "" if "日" in date else date + "日"
        shutuba_path = pathlib.WindowsPath(r'G:\マイドライブ\Keiba\data\shutuba')
        place = utils.place_decoder(race_const.place)
        root = f"{shutuba_path}/{race_const.year}/{race_const.year}年{date}{place}{race_const.r}R{race_const.kai}回{race_const.day}日目{title}"
        if not os.path.exists(root):
            os.makedirs(root)
        sub_folder = f"{root}/related_histories"
        if not os.path.exists(sub_folder):
            os.makedirs(sub_folder)
        odds_folder = f"{root}/odds"
        if not os.path.exists(odds_folder):
            os.makedirs(odds_folder)
        # 出馬データ保存
        df = shutuba_res["data"]
        path = f"{root}/shutuba.csv"
        df.to_csv(path)
        # オッズ保存
        scrape_odds_and_save(shutuba_id,odds_folder)
        # 馬の戦歴をスクレイピング
        horse_id_list = df["horse_id"].unique()
        for res in scrape.scrape_racehistories(horse_id_list):
            if res["status"]:
                horse_id = res["horse_id"]
                print(horse_id)
                df = res["data"]
                race_info_list = []
                #レース直前にスクレイプする場合は[0:3]つけたほうが効率よし
                for race_id in df["race_id"].tolist()[0:3]:
                    print(f" {race_id}")
                    scrape_related_racehistory(race_id)
                    race_page = race.RacePage(f"https://db.netkeiba.com/race/{race_id}/")
                    race_info = race_page.get_race_info()
                    race_info_list.append(race_info)
                    time.sleep(1)
                df_race_info = pd.DataFrame(race_info_list)
                df = pd.concat([df, df_race_info], axis = 1)
                path = f"{sub_folder}/{horse_id}.csv"
                df.to_csv(path)
            time.sleep(1)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()