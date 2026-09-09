import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
import json
from django.conf import settings
from google import genai as genai_lib

class FileService:
    @staticmethod
    def load_dataframe(file_path):
        if file_path.endswith(".csv"):
            return pd.read_csv(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            return pd.read_excel(file_path)
        return None

    @staticmethod
    def normalize_columns(df):
        df = df.copy()
        df.columns = df.columns.str.strip().str.replace(" ", "_").str.title()
        df.columns = df.columns.str.replace("_(?=.)", "_", regex=False)
        return df

class ProfilingService:
    @staticmethod
    def generate_profile(df):
        num_cols = df.select_dtypes(include="number").columns.tolist()
        profile = {
            "rows": int(len(df)),
            "columns": list(map(str, df.columns)),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isna().sum().to_dict(),
            "missing_percent": (df.isna().mean() * 100).round(1).to_dict(),
            "duplicates": int(df.duplicated().sum()),
        }
        if num_cols:
            # Convert describe() dataframe to a serializable dictionary
            profile["numeric_summary"] = df[num_cols].describe().to_dict()

        return profile, num_cols

class KPIService:
    @staticmethod
    def calculate_kpis(df):
        kpis = {"Total Students": int(len(df))}
        if "CGPA" in df.columns:
            kpis["Average CGPA"] = round(float(df["CGPA"].mean()), 2)
        if "Attendance" in df.columns:
            kpis["Average Attendance"] = round(float(df["Attendance"].mean()), 1)
        if "Placement" in df.columns:
            kpis["Placement Rate"] = round(float(df["Placement"].mean() * 100), 1)
        if "Salary" in df.columns:
            kpis["Average Salary"] = int(df["Salary"][df["Salary"] > 0].mean()) if not df["Salary"][df["Salary"] > 0].empty else 0
        if "Internship" in df.columns:
            try:
                kpis["Internship Rate"] = round(
                    float((df["Internship"].astype(str).str.lower().isin(["yes", "true", "1"]).mean()) * 100), 1
                )
            except Exception:
                pass
        if "CGPA" in df.columns and "Attendance" in df.columns:
            kpis["Students At Risk"] = int(((df["CGPA"] < 7) & (df["Attendance"] < 75)).sum())
        return kpis

class ChartingService:
    @staticmethod
    def get_chart_json(df, chart_id):
        """
        Returns a JSON string of the Plotly figure for a given chart_id.
        """
        fig = None
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        cat_cols = [c for c in cat_cols if df[c].nunique() <= 30]

        if chart_id == "generic_cat" and cat_cols:
            c = cat_cols[0]
            counts = df[c].value_counts().reset_index()
            counts.columns = [c, "count"]
            fig = px.bar(counts, x=c, y="count", title="Students by " + c)

        elif chart_id == "cgpa_dept" and "Department" in df.columns and "CGPA" in df.columns:
            g = df.groupby("Department")["CGPA"].mean().reset_index()
            fig = px.bar(g, x="Department", y="CGPA", title="Average CGPA by Department")

        elif chart_id == "placement_dept" and "Department" in df.columns and "Placement" in df.columns:
            g = (df.groupby("Department")["Placement"].mean() * 100).reset_index()
            g.columns = ["Department", "Placement Rate"]
            fig = px.bar(g, x="Department", y="Placement Rate", title="Placement Rate by Department")

        elif chart_id == "salary_dept" and "Department" in df.columns and "Salary" in df.columns:
            g = df[df["Salary"] > 0].groupby("Department")["Salary"].mean().reset_index()
            if not g.empty:
                fig = px.bar(g, x="Department", y="Salary", title="Average Salary by Department")

        elif chart_id == "cgpa_dist" and "CGPA" in df.columns:
            fig = px.histogram(df, x="CGPA", nbins=20, title="CGPA Distribution")

        elif chart_id == "attendance_dist" and "Attendance" in df.columns:
            fig = px.histogram(df, x="Attendance", nbins=20, title="Attendance Distribution")

        elif chart_id == "cgpa_attendance_scatter" and "CGPA" in df.columns and "Attendance" in df.columns:
            fig = px.scatter(df, x="Attendance", y="CGPA", title="CGPA vs Attendance")

        elif chart_id == "salary_dist" and "Salary" in df.columns:
            sal = df[df["Salary"] > 0]
            if not sal.empty:
                fig = px.histogram(sal, x="Salary", nbins=20, title="Salary Distribution")

        elif chart_id == "correlation" and num_cols and len(num_cols) >= 2:
            sel = num_cols[:4]
            fig = px.imshow(df[sel].corr(), text_auto=True, title="Correlation Heatmap")

        if fig:
            return pio.to_json(fig)
        return None

class AIService:
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        self.client = None
        if self.api_key and self.api_key != "your_api_key_here":
            try:
                self.client = genai_lib.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def build_analysis_context(self, df, profile, num_cols):
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
                    f"{col}: mean={d.get('mean', 0):.2f}, min={d.get('min', 0):.2f}, "
                    f"max={d.get('max', 0):.2f}, std={d.get('std', 0):.2f}"
                )
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

    def get_insights(self, context):
        if not self.client:
            return None

        prompt = """You are an expert campus data analyst.
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
        try:
            resp = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt.replace("{context}", context),
            )
            text = resp.text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception:
            return None

    def ask_ai(self, df, question):
        if not self.client:
            return "AI is not configured. Add your Gemini API key to .env to enable 'Ask the Data'."

        q = question.lower()
        result = None

        if "top" in q and any(c.isdigit() for c in q):
            import re
            m = re.search(r"top\s+(\d+)", q)
            n = int(m.group(1)) if m else 10
            if "CGPA" in df.columns:
                result = df.sort_values("CGPA", ascending=False).head(n)
        elif "department" in q and ("highest" in q or "placement" in q):
            if "Placement" in df.columns and "Department" in df.columns:
                result = (df.groupby("Department")["Placement"].mean() * 100).sort_values(ascending=False)
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
                resp = self.client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=f"Answer this question about the dataset briefly, using only plausible general reasoning:\n{q}",
                )
                return resp.text.strip()
            except Exception as e:
                return f"Could not answer. ({e})"

        rendered = result.to_string() if hasattr(result, "to_string") else str(result)

        try:
            resp = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=(
                    f"The user asked: '{question}'\n\n"
                    f"Here is the actual calculated result from the dataset:\n{rendered}\n\n"
                    "Explain this result clearly in natural language for a campus placement officer. "
                    "Use only the numbers given. Be concise."
                ),
            )
            return resp.text.strip()
        except Exception as e:
            return f"Error explaining result: {e}"
