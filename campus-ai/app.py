import os
import io
from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_api_key_here":
    try:
        from google import genai as genai_lib
        genai = genai_lib.Client(api_key=GEMINI_API_KEY)
    except Exception:
        genai = None


def load_data(uploaded_file):
    if uploaded_file is None:
        return None
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    else:
        st.error("Unable to read this file. Please upload a valid CSV or Excel file.")
        return None


def build_profile(df):
    profile = {
        "rows": int(len(df)),
        "columns": list(map(str, df.columns)),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isna().sum().to_dict(),
        "missing_percent": (df.isna().mean() * 100).round(1).to_dict(),
        "duplicates": int(df.duplicated().sum()),
    }
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        profile["numeric_summary"] = df[num_cols].describe().to_dict()
    return profile, num_cols


def compute_kpis(df):
    kpis = {"Total Students": int(len(df))}
    if "CGPA" in df.columns:
        kpis["Average CGPA"] = round(df["CGPA"].mean(), 2)
    if "Attendance" in df.columns:
        kpis["Average Attendance"] = round(df["Attendance"].mean(), 1)
    if "Placement" in df.columns:
        kpis["Placement Rate"] = round(df["Placement"].mean() * 100, 1)
    if "Salary" in df.columns:
        kpis["Average Salary"] = int(df["Salary"][df["Salary"] > 0].mean())
    if "Internship" in df.columns:
        try:
            kpis["Internship Rate"] = round(
                (df["Internship"].astype(str).str.lower().isin(["yes", "true", "1"]).mean()) * 100, 1
            )
        except Exception:
            pass
    if "CGPA" in df.columns and "Attendance" in df.columns:
        kpis["Students At Risk"] = int(((df["CGPA"] < 7) & (df["Attendance"] < 75)).sum())
    return kpis


def column_exists(df, *names):
    return [n for n in names if n in df.columns]


def make_charts(df):
    charts = []
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols = [c for c in cat_cols if df[c].nunique() <= 30]

    if cat_cols:
        c = cat_cols[0]
        counts = df[c].value_counts().reset_index()
        counts.columns = [c, "count"]
        charts.append(("Students by " + c, px.bar(counts, x=c, y="count", title="Students by " + c)))

    if "Department" in df.columns and "CGPA" in df.columns:
        g = df.groupby("Department")["CGPA"].mean().reset_index()
        charts.append(("Average CGPA by Department", px.bar(g, x="Department", y="CGPA", title="Average CGPA by Department")))

    if "Department" in df.columns and "Placement" in df.columns:
        g = (df.groupby("Department")["Placement"].mean() * 100).reset_index()
        g.columns = ["Department", "Placement Rate"]
        charts.append(("Placement Rate by Department", px.bar(g, x="Department", y="Placement Rate", title="Placement Rate by Department")))

    if "Department" in df.columns and "Salary" in df.columns:
        g = df[df["Salary"] > 0].groupby("Department")["Salary"].mean().reset_index()
        if not g.empty:
            charts.append(("Average Salary by Department", px.bar(g, x="Department", y="Salary", title="Average Salary by Department")))

    if "CGPA" in df.columns:
        charts.append(("CGPA Distribution", px.histogram(df, x="CGPA", nbins=20, title="CGPA Distribution")))

    if "Attendance" in df.columns:
        charts.append(("Attendance Distribution", px.histogram(df, x="Attendance", nbins=20, title="Attendance Distribution")))

    if "CGPA" in df.columns and "Attendance" in df.columns:
        charts.append(("CGPA vs Attendance", px.scatter(df, x="Attendance", y="CGPA", title="CGPA vs Attendance")))

    if "Salary" in df.columns:
        sal = df[df["Salary"] > 0]
        if not sal.empty:
            charts.append(("Salary Distribution", px.histogram(sal, x="Salary", nbins=20, title="Salary Distribution")))

    if num_cols and len(num_cols) >= 2:
        sel = num_cols[:4]
        charts.append(("Correlation Heatmap", px.imshow(df[sel].corr(), text_auto=True, title="Correlation Heatmap")))

    return charts


def build_analysis_context(df, profile, num_cols):
    lines = []
    lines.append("DATASET PROFILE")
    lines.append(f"Rows: {profile['rows']}")
    lines.append(f"Columns: {', '.join(profile['columns'])}")
    lines.append(f"Duplicates: {profile['duplicates']}")
    lines.append("Missing values: " + ", ".join(f"{k}={v}" for k, v in profile['missing_values'].items()))
    if num_cols:
        lines.append("\nNUMERIC SUMMARY")
        for col in num_cols:
            d = profile["numeric_summary"][col]
            lines.append(
                f"{col}: mean={d.get('mean'):.2f}, min={d.get('min'):.2f}, "
                f"max={d.get('max'):.2f}, std={d.get('std'):.2f}"
            )
            corr = None
    if len(num_cols) >= 2:
        lines.append("\nCORRELATION")
        lines.append(df[num_cols[:4]].corr().round(2).to_string())
    if "Department" in df.columns:
        lines.append("\nBY DEPARTMENT")
        for metric in ["CGPA", "Placement", "Salary"]:
            if metric in df.columns:
                if metric == "Salary":
                    g = df[df[metric] > 0].groupby("Department")[metric].mean()
                elif metric == "Placement":
                    g = df.groupby("Department")[metric].mean() * 100
                else:
                    g = df.groupby("Department")[metric].mean()
                lines.append(metric + ": " + ", ".join(f"{k}={v:.2f}" for k, v in g.items()))
    return "\n".join(lines)


INSIGHT_PROMPT = """You are an expert campus data analyst.

Analyze the supplied dataset profile and computed statistics.

Identify:
1. The most important findings
2. Major differences between groups
3. Potential anomalies
4. Student risk factors
5. Important correlations
6. Actionable recommendations
7. Useful visualizations

Use ONLY the supplied information.
Do not invent statistics.
Do not calculate values that are not provided.
Clearly distinguish observations from recommendations.

Return the result as structured JSON with exactly this shape:
{
  "summary": "string",
  "insights": [{"title": "string", "description": "string", "importance": "high|medium|low"}],
  "recommendations": ["string"],
  "suggested_charts": [{"type": "string", "x": "string", "y": "string", "reason": "string"}]
}

DATA:
{context}
"""


def get_insights(context):
    if not genai:
        return None
    try:
        resp = genai.models.generate_content(
            model="gemini-2.0-flash",
            contents=INSIGHT_PROMPT.format(context=context),
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        import json
        return json.loads(text)
    except Exception as e:
        st.warning(f"AI insights temporarily unavailable: {e}")
        return None


def answer_question(df, question):
    if not genai:
        return "AI is not configured. Add your Gemini API key to .env to enable 'Ask the Data'."
    q = question.lower()
    Q = genai

    result = None
    if "top" in q and any(c.isdigit() for c in q):
        import re
        m = re.search(r"top\s+(\d+)", q)
        n = int(m.group(1)) if m else 10
        if "CGPA" in df.columns:
            result = df.sort_values("CGPA", ascending=False).head(n)
    elif "department" in q and ("highest" in q or "placement" in q):
        if "Placement" in df.columns and "Department" in df.columns:
            g = (df.groupby("Department")["Placement"].mean() * 100).sort_values(ascending=False)
            result = g
    elif "department" in q and "cgpa" in q:
        if "CGPA" in df.columns and "Department" in df.columns:
            result = df.groupby("Department")["CGPA"].mean().sort_values(ascending=False)
    elif ("compare" in q or "vs" in q) and "Department" in df.columns:
        if "CGPA" in df.columns and "Placement" in df.columns:
            g = df.groupby("Department")[["CGPA"]].mean()
            p = (df.groupby("Department")["Placement"].mean() * 100)
            result = g.join(p.to_frame("Placement Rate"))
    elif "risk" in q and "CGPA" in df.columns and "Attendance" in df.columns:
        result = df[(df["CGPA"] < 7) & (df["Attendance"] < 75)]
    elif "salary" in q and "Salary" in df.columns:
        sal = df[df["Salary"] > 0]
        result = sal.groupby("Department")["Salary"].mean() if "Department" in df.columns else None
    elif "attendance" in q and "Attendance" in df.columns:
        result = df["Attendance"].describe().to_string()
    elif "cgpa" in q and "CGPA" in df.columns:
        result = df["CGPA"].describe().to_string()

    if result is None:
        try:
            resp = Q.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Answer this question about the dataset briefly, using only plausible general reasoning:\n{q}",
            )
            return resp.text.strip()
        except Exception as e:
            return f"Could not answer. Please check your question. ({e})"

    if hasattr(result, "to_string"):
        rendered = result.to_string()
    else:
        rendered = str(result)

    resp = Q.models.generate_content(
        model="gemini-2.0-flash",
        contents=(
            f"The user asked: '{question}'\n\n"
            f"Here is the actual calculated result from the dataset:\n{rendered}\n\n"
            "Explain this result clearly in natural language for a campus placement officer. "
            "Use only the numbers given. Be concise."
        ),
    )
    return resp.text.strip()


def main():
    st.set_page_config(page_title="AI Campus Data Analyst", layout="wide")
    st.title("🎓 AI Campus Data Analyst")
    st.caption("Upload data → Understand → Decide")

    col1, col2 = st.columns([2, 1])
    with col1:
        up = st.file_uploader("Upload CSV / Excel file", type=["csv", "xlsx", "xls"])
    with col2:
        st.write("")
        st.write("")
        if st.button("Use sample data"):
            up = "sample_data.csv"

    if up is None:
        st.info("Upload a CSV or Excel file to begin analysis.")
        return

    try:
        if isinstance(up, str):
            df = pd.read_csv(up)
        else:
            df = load_data(up)
    except Exception as e:
        st.error(f"Unable to read this file. Please upload a valid CSV or Excel file. ({e})")
        return

    if df is None or df.empty:
        st.error("The uploaded dataset contains no rows.")
        return

    df = df.copy()
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.title()
    df.columns = df.columns.str.replace("_(?=.)", "_", regex=False)

    profile, num_cols = build_profile(df)
    kpis = compute_kpis(df)

    # ---- DATASET OVERVIEW ----
    st.subheader("DATASET OVERVIEW")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", profile["rows"])
    c2.metric("Columns", len(profile["columns"]))
    total_missing = sum(profile["missing_values"].values())
    c3.metric("Missing Values", total_missing)
    c4.metric("Duplicates", profile["duplicates"])

    with st.expander("Data preview"):
        st.dataframe(df.head(20))

    # ---- KPIs ----
    st.subheader("KEY PERFORMANCE INDICATORS")
    kcol = st.columns(min(len(kpis), 4))
    for i, (k, v) in enumerate(kpis.items()):
        kcol[i % 4].metric(k, v)

    # ---- CHARTS ----
    st.subheader("VISUAL ANALYTICS")
    charts = make_charts(df)
    if not charts:
        st.info("No charts could be generated from this dataset.")
    for title, fig in charts:
        with st.expander(title, expanded=True):
            st.plotly_chart(fig, use_container_width=True)

    # ---- AI INSIGHTS ----
    st.subheader("🤖 AI INSIGHTS")
    context = build_analysis_context(df, profile, num_cols)
    with st.spinner("Generating AI insights..."):
        insights = get_insights(context)

    if insights:
        st.markdown("### Executive Summary")
        st.write(insights.get("summary", ""))
        st.markdown("### Key Insights")
        imp_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for ins in insights.get("insights", []):
            color = imp_colors.get(ins.get("importance", "low"), "🟢")
            st.markdown(f"**{color} {ins.get('title','')}**")
            st.write(ins.get("description", ""))
        st.markdown("### Recommendations")
        for i, rec in enumerate(insights.get("recommendations", []), 1):
            st.markdown(f"{i}. {rec}")
    else:
        st.write("AI insights are temporarily unavailable. The statistical dashboard is still available.")

    # ---- ASK THE DATA ----
    st.subheader("💬 Ask the Data")
    question = st.text_input("Ask a question about your dataset...")
    if question:
        with st.spinner("Analyzing..."):
            answer = answer_question(df, question)
        st.markdown("**Answer:**")
        st.write(answer)


if __name__ == "__main__":
    main()
