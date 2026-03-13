import pandas as pd
import re

def extract_gwg(df):
    """Dynamically extracts team abbreviations and scores from event data"""
    # Extract team abbreviations from the first event
    first_event = df['Event'].iloc[0]
    team_match = re.search(r'Goal! ([A-Z]{3}) \d+ - \d+ ([A-Z]{3})', first_event)
    
    if not team_match:
        raise ValueError("Could not identify team abbreviations in event format")
    
    home_team, away_team = team_match.groups()
    
    # Create dynamic regex pattern for score extraction
    score_pattern = rf'Goal! {re.escape(home_team)} (\d+) - (\d+) {re.escape(away_team)}'
    
    # Extract scores using the dynamic pattern
    scores = df['Event'].str.extract(score_pattern)
    
    # Convert to integers and handle potential missing values
    df['Home Score'] = scores[0].astype(int)
    df['Away Score'] = scores[1].astype(int)
    df['Home Score MAX'] = df['Home Score'].max()
    df['Away Score MAX'] = df['Away Score'].max()
    # GWG: the unique goal that makes the score exactly one ahead of the opponent's final score.
    # Home Score is monotonically non-decreasing, so this condition matches exactly once.
    df['Game Winning Goal'] = (
        (df['Home Score'] == df['Away Score MAX'] + 1) |
        (df['Away Score'] == df['Home Score MAX'] + 1)
    ).astype(int)
    df.drop(columns=['Home Score MAX', 'Away Score MAX', 'Home Score', 'Away Score'], inplace=True)
    
    return df