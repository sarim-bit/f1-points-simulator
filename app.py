import streamlit as st
from src.data_loader import load_processed_season
from src.scoring_logic import simulate_season, get_actual_standings, merge_comparison_table, get_progression_data
import plotly.express as px

def color_delta(val):
    if '▲' in str(val): return 'color: green'
    if '▼' in str(val): return 'color: red'
    return 'color: gray'

def style_table(df):
    return (df.style
    .format({'Official Points': '{:g}', 'Simulated Points': '{:g}'})
    .apply(lambda x: ['background-color: #FFF3CD; font-weight: bold;' if x.name == 0 else '' for _ in x], axis=1)
    .set_properties(subset=['Rank', 'Driver'], **{'font-weight': 'bold'})
    .map(color_delta, subset=['Change'])
    )

st.set_page_config(page_title="F1 Points Simulator", layout="wide")

st.title("🏎️ F1 Points Simulator")
st.markdown("What if history was written with different rules?")

if 'sim_data' not in st.session_state:
    st.session_state.sim_data = None

with st.sidebar:
    st.header("Simulation Settings")
    
    # Wrap everything in a form
    with st.form("settings_form"):
        data_year = st.selectbox("Select Race Season", range(2025, 1949, -1), index=0)
        rule_year = st.selectbox("Apply Rulebook from Year", range(2025, 1949, -1), index=0)
        
        submitted = st.form_submit_button("Run Simulation")

if submitted:
    df_raw = load_processed_season(data_year)
    if not df_raw.empty:

        sim_results = simulate_season(df_raw, rule_year, data_year)
        act_results = get_actual_standings(df_raw, data_year)
        
        st.session_state.sim_data = {
            'df_raw': df_raw,
            'sim_results': sim_results,
            'act_results': act_results,
            'data_year': data_year,
            'rule_year': rule_year
        }


if st.session_state.sim_data is not None:
    d = st.session_state.sim_data
    tab1, tab2 = st.tabs(["📊 Standings", "📈 Season Progression"])

    with tab1:
        final_table = merge_comparison_table(d['sim_results'], d['act_results'])
        st.subheader(f"Comparison: {d['data_year']} (Rules: {d['rule_year']})")
        st.dataframe(style_table(final_table), width='stretch', hide_index=True)

        # We trigger specific notes based on the data_year selected
        year = d['data_year']

        if year == 1983:
            st.info("""
            **Historical Note: 1983 Brazilian GP**
            Keke Rosberg (2nd) was disqualified for an illegal push-start in the pits. 
            Uniquely, the stewards chose **not** to promote the drivers behind him, leaving 2nd place and its 6 points officially unawarded.
            """)

        elif year == 1954:
            st.info("""
            **Historical Note: 1954 British GP**
            Seven different drivers set the identical fastest lap time (1:50.0). 
            Under the rules of the era, the 1-point bonus was split equally among them, resulting in each driver receiving roughly **0.14 points**.
            """)

        elif year == 1984:
            st.info("""
            **Historical Note: 1984 Monaco GP**
            The race was stopped early due to heavy rain. 
            Because less than 75% of the race distance was completed, **Half-Points** were awarded to the top finishers.
            """)

        elif year == 2021:
            st.info("""
            **Historical Note: 2021 Belgian GP**
            Due to extreme weather, the race was classified after only two laps behind the Safety Car. 
            This resulted in **Half-Points** being awarded for only the sixth time in F1 history.
            """)

    with tab2:
        st.subheader("Points Accumulation Throughout the Season")
        act_p, sim_p = get_progression_data(d['df_raw'], d['rule_year'], d['data_year'])
        
        # FILTER: Only show drivers who scored at least 1 point in either scenario
        scoring_drivers_act = act_p.groupby('Driver')['ActualPoints'].max()
        scoring_drivers_sim = sim_p.groupby('Driver')['SimulatedPoints'].max()
        
        scorers = set(scoring_drivers_act[scoring_drivers_act > 0].index) | \
                set(scoring_drivers_sim[scoring_drivers_sim > 0].index)
        
        all_scorers = sorted(list(scorers))
        top_5_default = d['sim_results'].head(5)['Driver'].tolist()
        default_selection = [dr for dr in top_5_default if dr in all_scorers]
        
        selected_drivers = st.multiselect(
            "Select Scoring Drivers to Compare", 
            options=all_scorers, 
            default=default_selection
        )

        distinct_colors = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24
        color_map = {
            driver: distinct_colors[i % len(distinct_colors)] 
            for i, driver in enumerate(all_scorers)
        }

        filtered_act = act_p[act_p['Driver'].isin(selected_drivers)]
        filtered_sim = sim_p[sim_p['Driver'].isin(selected_drivers)]

        if not filtered_act.empty or not filtered_sim.empty:
            y_act_range = [0, filtered_act['ActualPoints'].max() * 1.1]
            y_sim_range = [0, filtered_sim['SimulatedPoints'].max() * 1.1]

            fig_sim = px.line(filtered_sim, x="Round", y="SimulatedPoints", color="Driver", 
                            title=f"Simulated Progression ({d['rule_year']} Rules)", 
                            color_discrete_map=color_map, markers=True, template="plotly_white")
            fig_sim.update_yaxes(range=y_sim_range)
            st.plotly_chart(fig_sim, width='stretch')

            fig_act = px.line(filtered_act, x="Round", y="ActualPoints", color="Driver", 
                            title="Official Progression", color_discrete_map=color_map,
                            markers=True, template="plotly_white")
            fig_act.update_yaxes(range=y_act_range)
            st.plotly_chart(fig_act, width='stretch')
            
            
        else:
            st.warning("Select at least one driver to view the progression plots.")
    
elif not submitted:
    st.info("Adjust the settings in the sidebar and click 'Run Simulation' to start.")