from bs4 import BeautifulSoup
import pandas as pd
from other_stats_scraper_selenium import extract_other_stats


def extract_all_stats(url_playbyplay, url_statistics):
    # Load both pages in a single Selenium session.
    # Using Selenium for the stats page avoids HTTP 403 blocks that affect plain
    # requests.get() calls from datacenter IPs (e.g. Render).
    stats_html, others_df, match_score_home, match_score_away = extract_other_stats(url_playbyplay, url_statistics)

    soup = BeautifulSoup(stats_html, 'html.parser')

    teams = ['s-team--home', 's-team--away']
    player_stats_names = {
                            'Position': 's-cell--pos',
                            'Goals': 's-cell--g',
                            'Assists': 's-cell--a',
                            'Points': 's-cell--p',
                            'Penalty Minutes': 's-cell--pim',
                            'Plus Minus': 's-cell--dynamic'}
    goalies_stats_names = {
                            'Goals Against': 's-cell--ga',
                            'Saves': 's-cell--svs'}

    player_list = []
    goalies_list = []
    stats_list = []
    players_df = pd.DataFrame()
    players_away_df = pd.DataFrame()
    goalies_df = pd.DataFrame()
    goalies_away_df = pd.DataFrame()

    for team in teams:
        team_name_soup = soup.find('div', class_=team)
        if team_name_soup is None:
            raise ValueError(f"Stats HTML missing div.{team} — page may not have loaded. "
                             f"HTML length: {len(str(soup))}")
        players_table_soup = team_name_soup.find_all('div', class_='s-tables')[0]
        players_info_soup = players_table_soup.find_all('tbody', class_='s-table__body')[0]
        player_names_soup = players_info_soup.find_all('td', class_='s-cell--name')
        for player in player_names_soup:
            name_of_player = player.find('span', class_='js-table-cell-value').text
            player_list.append(name_of_player)
        if team == 's-team--home':
            players_df['Player'] = player_list
            players_df['Team'] = 'home'
        else:
            players_away_df['Player'] = player_list
            players_away_df['Team'] = 'away'
        player_list = []

        stats_info_soup = players_table_soup.find_all('tbody', class_='s-table__body')[1]
        for stat_name, stat_class in player_stats_names.items():
            player_stats_soup = stats_info_soup.find_all('td', class_=stat_class)
            for stat in player_stats_soup:
                stats_list.append(stat.find('span', class_='js-table-cell-value').text)
            if team == 's-team--home':
                players_df[stat_name] = stats_list
            else:
                players_away_df[stat_name] = stats_list
            stats_list = []

        goalies_table_soup = team_name_soup.find_all('div', class_='s-tables')[1]
        goalies_info_soup = goalies_table_soup.find_all('tbody', class_='s-table__body')[0]
        goalies_names_soup = goalies_info_soup.find_all('td', class_='s-cell--name')
        for goalie in goalies_names_soup:
            name_of_goalie = goalie.find('span', class_='js-table-cell-value').text
            goalies_list.append(name_of_goalie)
        if team == 's-team--home':
            goalies_df['Player'] = goalies_list
        else:
            goalies_away_df['Player'] = goalies_list
        goalies_list = []

        stats_goalies_info_soup = goalies_table_soup.find_all('tbody', class_='s-table__body')[1]
        for stat_name, stat_class in goalies_stats_names.items():
            goalies_stats_soup = stats_goalies_info_soup.find_all('td', class_=stat_class)
            for stat in goalies_stats_soup:
                stats_list.append(stat.find('span', class_='js-table-cell-value').text)
            if team == 's-team--home':
                goalies_df[stat_name] = stats_list
            else:
                goalies_away_df[stat_name] = stats_list
            stats_list = []

    players_df = pd.concat([players_df, players_away_df], ignore_index=True)
    goalies_df = pd.concat([goalies_df, goalies_away_df], ignore_index=True)
    players_df = players_df.merge(goalies_df, on='Player', how='left')
    for col in ['Goals', 'Assists', 'Points', 'Penalty Minutes', 'Plus Minus', 'Goals Against', 'Saves']:
        if col in players_df.columns:
            players_df[col] = pd.to_numeric(players_df[col], errors='coerce').fillna(0).astype(int)

    if not others_df.empty:
        fin_df = players_df.merge(others_df, on='Player', how='left')
        for col in ['Shorthanded Goal', 'Power Play Goal', 'Game Winning Goal']:
            fin_df[col] = fin_df[col].fillna(0).astype(int)
        fin_df['Event'] = fin_df['Event'].fillna('')
        home_wins = int(match_score_home) > int(match_score_away)
        fin_df['Win'] = [1 if (x == 'home') == home_wins else 0 for x in fin_df['Team']]
        fin_df['Event'] = fin_df.pop('Event') # Move Event column to the end
    else:
        fin_df = players_df
        fin_df['Shorthanded Goal'] = 0
        fin_df['Power Play Goal'] = 0
        fin_df['Game Winning Goal'] = 0
        home_wins = int(match_score_home) > int(match_score_away)
        fin_df['Win'] = [1 if (x == 'home') == home_wins else 0 for x in fin_df['Team']]
        fin_df['Event'] = ''

    # Set all stats for goalies with 0 saves to 0
    goalies_mask = (fin_df['Position'] == 'GK') & (fin_df['Saves'].astype(int) == 0)
    if goalies_mask.any():
        # Zero out only numeric stat columns (skip string columns like Event)
        stats_columns = fin_df.select_dtypes(include='number').columns
        fin_df.loc[goalies_mask, stats_columns] = 0
        print("Reset stats for goalkeepers with 0 saves to 0")

    print(fin_df)
    return fin_df

if __name__ == "__main__":
    extract_all_stats('https://www.iihf.com/en/events/2026/wm20/gamecenter/playbyplay/68798/','https://www.iihf.com/en/events/2026/wm20/gamecenter/statistics/68798/')
