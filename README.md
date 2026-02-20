# 🏎️ F1 Points Simulator

**What if history was written with different rules?** This interactive Streamlit application allows you to re-score any Formula 1 season from 1950 to 2025 using rulebooks from different eras. See how championship outcomes change when applying modern points to vintage seasons or vice-versa.

🔗 **Live App:** [f1-points-simulator.streamlit.app](https://f1-points-simulator.streamlit.app/)

## Features
* **Full Historical Database**: Coverage from the inaugural 1950 season to the current 2025 season.
* **Rulebook Swapping**: Apply scoring systems, drop-rules, and sprint points from any era to another.
* **Championship Analytics**: Interactive tables showing Rank Deltas (▲/▼) and season-long points progression charts.
* **Anomaly Handling**: Accounts for historical oddities like 1954's shared fastest laps and 1983's vacant podiums.

## Installation & Usage
1. **Clone the repository**:
   ```bash
   git clone [https://github.com/your-username/f1-points-simulator.git](https://github.com/your-username/f1-points-simulator.git)
   cd f1-points-simulator
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the App Locally**:
   ```bash
   streamlit run app.py
   ```

## Project Structure
* `app.py`: Main Streamlit application, session state management, and UI logic.
* `src/`: Core engine containing scoring logic and data loading utilities.
* `data/processed/`: Historical race data stored in optimized Parquet format.

## Requirements
* **Python**: 3.8+
* **Libraries**: `pandas`, `streamlit`, `plotly`, `pyarrow`, `numpy`