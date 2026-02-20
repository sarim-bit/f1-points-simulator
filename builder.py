import fastf1
import pandas as pd
import os
import time
import logging
from src.scoring_logic import get_rule_for_year, BASE_SCORING

logging.getLogger('fastf1').setLevel(logging.ERROR)
fastf1.Cache.enable_cache('data/f1_cache')
fastf1.Cache.offline_mode(True)

OUTPUT_DIR = "data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_safe_id(row):
    name = str(row['FullName']).strip()
    if name and name.lower() != 'nan':
        return name

def get_fastest_lap_data(session, year, round_num, points_list):
    res = session.results.copy()
    res['FullName'] = res['FullName'].fillna("Driver " + res['DriverNumber'].astype(str))
    
    # Pre-calculate shared factors to use in FL detection
    shared_counts = res[res['ClassifiedPosition'].astype(str).str.isdigit()].groupby('ClassifiedPosition').size().to_dict()

    def detect_vintage_fl(row):
        try:
            actual_pts = float(row['Points'])
            val = str(row['ClassifiedPosition'])
            pos = int(float(val)) if val.replace('.','').isdigit() else 999
            
            raw_base = points_list[pos-1] if pos <= len(points_list) else 0.0
            
            factor = 1.0
            if val in shared_counts and shared_counts[val] > 1:
                factor = 1.0 / shared_counts[val]
            shared_base = raw_base * factor
            # Small tolerance for floating point math
            return actual_pts > (shared_base + 0.1)
        except:
            return False

    res['has_extra'] = res.apply(detect_vintage_fl, axis=1)
    fl_drivers = res[res['has_extra'] == True]['FullName'].unique()
    return res['FullName'].isin(fl_drivers)  
  
def calculate_shared_drive_factors(res):
    """Identifies shared drives (multiple drivers in one position) and returns factors."""
    # Filter for numeric positions only to avoid grouping 'R' or 'D'
    numeric_positions = res[res['ClassifiedPosition'].astype(str).str.isnumeric()]
    shared_counts = numeric_positions.groupby('ClassifiedPosition').size().to_dict()

    def get_factor(row):
        pos = str(row['ClassifiedPosition'])
        if pos in shared_counts and shared_counts[pos] > 1:
            return 1.0 / shared_counts[pos]
        return 1.0

    return res.apply(get_factor, axis=1)

def clean_session_results(session, year, round_num, session_type):
    res = session.results.copy()
    points_list = get_rule_for_year(year, BASE_SCORING)

    res['FullName'] = res['FullName'].fillna("Driver " + res['DriverNumber'].astype(str))
    res['Abbreviation'] = res['Abbreviation'].fillna('')
    fl_flags = get_fastest_lap_data(session, year, round_num, points_list)
    res['IsFastestLap'] = fl_flags

    if session_type == 'Race' and year <= 1960:
        fl_drivers = res[res['IsFastestLap'] == True]['FullName'].unique()
        res.loc[res['FullName'].isin(fl_drivers), 'IsFastestLap'] = True

    if session_type == 'Race':
        res['SharedFactor'] = calculate_shared_drive_factors(res)
    else:
        res['SharedFactor'] = 1.0

    res['Round'] = round_num
    res['SessionType'] = session_type
    
    cols = ['FullName', 'Abbreviation', 'ClassifiedPosition', 'Status', 
            'Points', 'Round', 'SessionType', 'IsFastestLap', 'SharedFactor']
    return res[cols]

def fetch_and_clean_year(year):
    try:
        schedule = fastf1.get_event_schedule(year)
        races = schedule[schedule['RoundNumber'] > 0]
        all_data = []
        should_load_laps = True if year >= 1996 else False

        for _, event in races.iterrows():
            round_num = event['RoundNumber']
            print(f"  - Processing Round {round_num}...")
            
            session = fastf1.get_session(year, round_num, 'R')
            session.load(laps=should_load_laps, telemetry=False, weather=False, messages=False)
            race_res = clean_session_results(session, year, round_num, 'Race')
            all_data.append(race_res)

            if 'sprint' in str(event['EventFormat']).lower():
                s_session = fastf1.get_session(year, round_num, 'Sprint')
                s_session.load(laps=False, telemetry=False, weather=False, messages=False)
                
                sprint_res = clean_session_results(s_session, year, round_num, 'Sprint')
                all_data.append(sprint_res)
        
        return pd.concat(all_data, ignore_index=True)
        
    except Exception as e:
        print(f"  Error processing {year}: {e}")
        return None

if __name__ == "__main__":
    for year in range(1950, 2026):
        target_file = f"{OUTPUT_DIR}/season_{year}.parquet"
        
        # Skip if file exists
        if os.path.exists(target_file):
            continue
            
        print(f"Building {year}...")
        df = fetch_and_clean_year(year)
        if df is not None and not df.empty:
            # Check if we have a reasonable number of rows (e.g., at least 5 races)
            if df['Round'].max() >= 5 or year == 1950: 
                df.to_parquet(target_file, index=False)
                print(f" Saved {year}")
            else:
                print(f" {year} seems incomplete. Not saving.")
        
        # Pause between years to let the API breathe
        time.sleep(5)