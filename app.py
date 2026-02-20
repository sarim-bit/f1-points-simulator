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
        # Run math once and store it
        sim_results = simulate_season(df_raw, rule_year, data_year)
        act_results = get_actual_standings(df_raw, data_year)
        
        st.session_state.sim_data = {
            'df_raw': df_raw,
            'sim_results': sim_results,
            'act_results': act_results,
            'data_year': data_year,
            'rule_year': rule_year
        }

# 3. Check if we have stored data to display (this keeps it visible during re-runs)
if st.session_state.sim_data is not None:
    # Retrieve from state
    d = st.session_state.sim_data
    
    tab1, tab2 = st.tabs(["📊 Standings", "📈 Season Progression"])
    
    with tab1:
        final_table = merge_comparison_table(d['sim_results'], d['act_results'])
        st.subheader(f"Comparison: {d['data_year']} (Rules: {d['rule_year']})")
        st.dataframe(style_table(final_table), width='stretch', hide_index=True)

    with tab2:
        st.subheader("Points Accumulation Throughout the Season")
        
        # 1. Get the data
        act_p, sim_p = get_progression_data(d['df_raw'], d['rule_year'], d['data_year'])
        
        # 2. FILTER: Only show drivers who scored at least 1 point in either scenario
        # This keeps the multiselect and the legend clean
        scoring_drivers_act = act_p.groupby('Driver')['ActualPoints'].max()
        scoring_drivers_sim = sim_p.groupby('Driver')['SimulatedPoints'].max()
        
        scorers = set(scoring_drivers_act[scoring_drivers_act > 0].index) | \
                set(scoring_drivers_sim[scoring_drivers_sim > 0].index)
        
        all_scorers = sorted(list(scorers))
        
        # 3. Setup Selection UI
        top_5_default = d['sim_results'].head(5)['Driver'].tolist()
        # Ensure default drivers are actually in the scorers list
        default_selection = [dr for dr in top_5_default if dr in all_scorers]
        
        selected_drivers = st.multiselect(
            "Select Scoring Drivers to Compare", 
            options=all_scorers, 
            default=default_selection
        )

        # 4. COLOR MAPPING: 50 distinct shades
        distinct_colors = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24
        color_map = {
            driver: distinct_colors[i % len(distinct_colors)] 
            for i, driver in enumerate(all_scorers)
        }

        # 5. Filter data for plots
        filtered_act = act_p[act_p['Driver'].isin(selected_drivers)]
        filtered_sim = sim_p[sim_p['Driver'].isin(selected_drivers)]

        if not filtered_act.empty or not filtered_sim.empty:
            # 6. Y-Axis Locking for "Apples-to-Apples" comparison
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