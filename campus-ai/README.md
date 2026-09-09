# AI Campus Data Analyst

An AI Data Analyst for campus data that accepts CSV/Excel files and automatically:
- Understands the dataset
- Calculates reliable statistics and KPIs
- Generates useful charts
- Finds important trends, anomalies, and relationships
- Produces AI-generated insights and recommendations
- Answers natural-language questions about the data

**Core principle:** Pandas does the calculations. Gemini does the interpretation.

## Technology Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Data processing | Pandas |
| Excel support | OpenPyXL |
| Charts | Plotly |
| AI | Google Gemini (free tier) |
| Config | `.env` |

## Setup

1. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Add your Gemini API key:
```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY=your_key
```

3. Run the app:
```bash
streamlit run app.py
```

4. Upload a CSV/Excel file, or click "Use sample data" to demo with `sample_data.csv`.

## Usage

- **Dataset Overview**: rows, columns, missing values, duplicates
- **KPIs**: Total Students, Avg CGPA, Attendance, Placement Rate, and more (auto-detected from columns)
- **Visual Analytics**: interactive Plotly charts
- **AI Insights**: executive summary, key insights, recommendations (requires Google API key)
- **Ask the Data**: natural-language questions backed by Pandas

## Sample Questions

- Which department has the highest placement rate?
- Compare CSE and ECE.
- How many students are at risk?
- Which students have low attendance and low CGPA?
- Show me the top 10 students by CGPA.
