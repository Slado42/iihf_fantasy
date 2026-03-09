import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import pandas as pd
from game_winning_goals import extract_gwg
import tempfile
from selenium.webdriver.chrome.options import Options

def extract_other_stats(url_name):
    options = Options()
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    # Required for running Chrome in a headless server environment (e.g. Render)
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Allow overriding Chrome binary path via env var (e.g. CHROME_BIN=/usr/bin/chromium-browser)
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    # Use Chromium driver if CHROME_BIN points to chromium, otherwise standard Chrome
    chrome_type = ChromeType.CHROMIUM if chrome_bin and "chromium" in chrome_bin else ChromeType.GOOGLE
    service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # Load the game page
        driver.get(url_name)
        
        # Wait for timeline events to load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 's-timeline-event.js-timeline-event')))
        
        # Get all timeline events
        events = driver.find_elements(By.CLASS_NAME, 's-timeline-event.js-timeline-event')

        # Parse game result
        match_score_home = driver.find_elements(By.CLASS_NAME, 's-team-score')[0].text
        match_score_away = driver.find_elements(By.CLASS_NAME, 's-team-score')[1].text
        
        # Parse goal events
        goal_data = []
        for event in events:
            # Extract description cell
            description = event.find_element(By.CLASS_NAME, 's-cell--description')
            
            # Get event title
            title = description.find_element(By.CLASS_NAME, 's-title').text
            
            # Check if it's a goal event (has player info)
            player_elements = description.find_elements(By.CLASS_NAME, 's-player')
            if player_elements:
                # Extract scorer name
                scorer = player_elements[0].find_element(By.CLASS_NAME, 's-name').text
                goal_data.append({
                    'Event': title.strip(),
                    'Player': scorer.strip()
                })

        # Create and display DataFrame
        df = pd.DataFrame(goal_data)
        # Create Shorthanded and Power Play columns
        if not df.empty:
            df = df[df.Event.str.contains('Goal!')]
            df['Shorthanded Goal'] = df['Event'].str.contains('\(SH').astype(int)
            df['Power Play Goal'] = df['Event'].str.contains('\(PP').astype(int)

            df = extract_gwg(df) # Extract GWG
            df['Event'] = df.pop('Event') # Move Event column to the end
            df = df.groupby('Player').agg({
                                    'Shorthanded Goal': 'sum',
                                    'Power Play Goal': 'sum',
                                    'Game Winning Goal': 'sum',
                                    'Event': list
                                    }).reset_index()
        return df, match_score_home, match_score_away

    finally:
        # Clean up browser instance
        driver.quit()