import pandas as pd
import streamlit as st

# Seasons with shortened races (Half-Points awarded)
# Source: (Year, Round)
HALF_POINTS_RACES = {
    2021: [12],  # Belgium (Spa)
    2009: [2],   # Malaysia
    1991: [16],  # Australia
    1984: [6],   # Monaco
    1975: [4, 12] # Spain, Austria
}

BASE_SCORING = {
    2010: [25, 18, 15, 12, 10, 8, 6, 4, 2, 1],
    2003: [10, 8, 6, 5, 4, 3, 2, 1],
    1991: [10, 6, 4, 3, 2, 1],
    1961: [9, 6, 4, 3, 2, 1],
    1960: [8, 6, 4, 3, 2, 1],
    1950: [8, 6, 4, 3, 2]
}

DROP_RULES = {
    1991: "all", 1981: 11, 1980: "split_5_5", 1979: "split_4_4",
    1977: "split_8_7", 1976: "split_7_7", 1975: "split_6_6",
    1973: "split_7_6", 1972: "split_5_5", 1971: "split_5_4",
    1970: "split_6_5", 1969: "split_5_4", 1968: "split_5_5",
    1967: "split_5_4", 1966: 5, 1963: 6, 1961: 5, 1960: 6,
    1959: 5, 1958: 6, 1954: 5, 1950: 4
}

# ==========================================================
# Points Calculation Functions
# ==========================================================

def get_rule_for_year(year, rules_dict):
    valid_years = sorted([y for y in rules_dict.keys() if y <= year], reverse=True)
    return rules_dict[valid_years[0]]

def calculate_base_points(row, points_list, data_year, rule_year, total_rounds):
    if row.get('SessionType') != 'Race':
        return 0.0
    
    try:
        pos = int(float(row['ClassifiedPosition']))
        if 0 < pos <= len(points_list):
            pts = float(points_list[pos - 1])
            
            # 2014 Double Points (Finale only)
            if rule_year == 2014 and row['Round'] == total_rounds:
                pts *= 2
            
            # Half-Points Rule (Shortened Races)
            if data_year in HALF_POINTS_RACES and row['Round'] in HALF_POINTS_RACES[data_year]:
                pts *= 0.5
            factor = row.get('SharedFactor', 1.0)
            return round(pts * factor, 2)
    except:
        pass
    return 0.0

def calculate_bonus_points(row, rule_year, total_rounds, fl_counts, data_year):
    bonus = 0.0
    try:
        val = row.get('ClassifiedPosition')
        pos = int(float(val)) if str(val).replace('.','').isdigit() else 999
    except:
        pos = 999

    if row.get('SessionType') == 'Sprint':
        if rule_year == 2021:
            s_pts = [3, 2, 1]
            bonus = s_pts[pos-1] if pos <= 3 else 0.0
        elif rule_year >= 2022:
            s_pts = [8, 7, 6, 5, 4, 3, 2, 1]
            bonus = s_pts[pos-1] if pos <= 8 else 0.0
        return float(bonus) # Return immediately so Sprint drivers don't get FL points

    # FASTEST LAP HANDLING
    if row.get('SessionType') == 'Race' and row.get('IsFastestLap', False):
        # 1950-1959: Awarded even if Retired/DQ'd
        if 1950 <= rule_year <= 1959:
            sharing = fl_counts.get(row['Round'], 1)
            bonus += (1.0 / sharing)
            
        # 2019-2024: Awarded only for Top 10 finish
        elif (2019 <= rule_year <= 2024) and pos <= 10:
            # Handle 2021 Spa 0-point exception
            if not (data_year == 2021 and row['Round'] == 12):
                bonus += 1.0
                
    return round(float(bonus),2)
# ==========================================================
# Simulation Function
# ==========================================================

def simulate_season(df_raw, rule_year, data_year):
    if df_raw.empty:
        return pd.DataFrame(columns=['Driver', 'SimulatedPoints'])

    df = df_raw.copy()

    id_col = 'FullName' if 'FullName' in df.columns else 'Abbreviation'
    df[id_col] = df[id_col].fillna("Unknown Driver")

    total_rounds = df['Round'].max()
    points_list = get_rule_for_year(rule_year, BASE_SCORING)
    fl_counts = df[df['IsFastestLap'] == True].groupby('Round')['FullName'].nunique().to_dict()

    # Apply core calculations
    df['BasePoints'] = df.apply(lambda r: calculate_base_points(r, points_list, data_year, rule_year, total_rounds), axis=1)
    df['BonusPoints'] = df.apply(lambda r: calculate_bonus_points(r, rule_year, total_rounds, fl_counts, data_year), axis=1)
    df['TotalPoints'] = df['BasePoints'] + df['BonusPoints']

    # Apply Counting Rules (Drop Rules)
    rule = get_rule_for_year(rule_year, DROP_RULES)
    
    if rule == "all":
        standings = df.groupby(id_col)['TotalPoints'].sum()
    elif isinstance(rule, int):
        standings = (df.sort_values('TotalPoints', ascending=False)
                     .groupby(id_col)['TotalPoints']
                     .apply(lambda x: x.head(rule).sum()))
    elif "split" in rule:
        h1_lim, h2_lim = map(int, rule.split('_')[1:])
        mid = total_rounds // 2
        h1 = (df[df['Round'] <= mid].sort_values('TotalPoints', ascending=False)
              .groupby(id_col)['TotalPoints'].apply(lambda x: x.head(h1_lim).sum()))
        h2 = (df[df['Round'] > mid].sort_values('TotalPoints', ascending=False)
              .groupby(id_col)['TotalPoints'].apply(lambda x: x.head(h2_lim).sum()))
        standings = h1.add(h2, fill_value=0)

    # Format result
    standings_df = standings.sort_values(ascending=False).reset_index()
    standings_df.columns = ['Driver', 'SimulatedPoints']
    standings_df['SimulatedPoints'] = standings_df['SimulatedPoints'].astype(float).round(1)
    
    return standings_df

def get_actual_standings(df_raw, data_year):
    """
    Retrieves official season totals, but applies the historical 
    drop rules so the numbers match the record books.
    """
    if df_raw.empty:
        return pd.DataFrame(columns=['Driver', 'ActualPoints'])
    
    # Identify the rule that was active during that data year
    rule = get_rule_for_year(data_year, DROP_RULES)
    
    # We use 'Points' (the official column) but apply the drop logic
    if rule == "all":
        actual = df_raw.groupby('FullName')['Points'].sum()
    elif isinstance(rule, int):
        # Best N results
        actual = (df_raw.sort_values('Points', ascending=False)
                  .groupby('FullName')['Points']
                  .apply(lambda x: x.head(rule).sum()))
    elif "split" in rule:
        # Best X from H1, Best Y from H2
        h1_lim, h2_lim = map(int, rule.split('_')[1:])
        mid = df_raw['Round'].max() // 2
        h1 = (df_raw[df_raw['Round'] <= mid].sort_values('Points', ascending=False)
              .groupby('FullName')['Points'].apply(lambda x: x.head(h1_lim).sum()))
        h2 = (df_raw[df_raw['Round'] > mid].sort_values('Points', ascending=False)
              .groupby('FullName')['Points'].apply(lambda x: x.head(h2_lim).sum()))
        actual = h1.add(h2, fill_value=0)

    actual_df = actual.reset_index()
    actual_df.columns = ['Driver', 'ActualPoints']
    actual_df['ActualPoints'] = actual_df['ActualPoints'].astype(float).round(1)
    
    return actual_df

def merge_comparison_table(sim_results, act_results):
    comparison = pd.merge(
        sim_results, 
        act_results, 
        on='Driver', 
        how='outer'
    ).fillna(0)

    comparison['Actual_Rank'] = comparison['ActualPoints'].rank(ascending=False, method='min')
    comparison['Sim_Rank'] = comparison['SimulatedPoints'].rank(ascending=False, method='min')

    comparison['Pos_Delta'] = (comparison['Actual_Rank'] - comparison['Sim_Rank']).astype(int)

    def format_pos_delta(row):
        # Ignore drivers with no points in either system
        if row['ActualPoints'] == 0 and row['SimulatedPoints'] == 0:
            return "-"
        
        delta = row['Pos_Delta']
        if delta > 0:
            return f"▲ {delta}"
        elif delta < 0:
            return f"▼ {abs(delta)}"
        else:
            return "-"

    comparison['Change'] = comparison.apply(format_pos_delta, axis=1)

    final = comparison.sort_values(by='SimulatedPoints', ascending=False).reset_index(drop=True)
    final.insert(0, 'Rank', final.index + 1)

    final = final.rename(columns={
        'ActualPoints': 'Official Points',
        'SimulatedPoints': 'Simulated Points'
    })
    
    return final[['Rank','Driver', 'Simulated Points', 'Official Points', 'Change']]

@st.cache_data
def get_progression_data(df_raw, rule_year, data_year):
    rounds = sorted(df_raw['Round'].unique())
    
    actual_prog = []
    sim_prog = []
    
    for r in rounds:
        current_data = df_raw[df_raw['Round'] <= r]
        
        # Get simulated results up to this round
        sim_standings = simulate_season(current_data, rule_year, data_year)
        sim_standings['Round'] = r
        sim_prog.append(sim_standings)
        
        # Get actual results up to this round
        act_standings = get_actual_standings(current_data, data_year)
        act_standings['Round'] = r
        actual_prog.append(act_standings)

    return pd.concat(actual_prog), pd.concat(sim_prog)