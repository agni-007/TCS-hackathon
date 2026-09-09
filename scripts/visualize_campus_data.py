"""
visualize_campus_data.py

Reads combined_campus_data_cleaned.csv and produces a set of matplotlib
charts summarizing student demographics, academics, and placements.

Usage:
    python visualize_campus_data.py

Requires:
    pandas, matplotlib

Output:
    campus_data_visuals.png  (a single figure with 6 subplots)
    Individual PNGs for each chart are also saved in the same folder.
"""

import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
CSV_PATH = "combined_campus_data_cleaned.csv"
df = pd.read_csv(CSV_PATH)

# ---------------------------------------------------------------------------
# 2. Style
# ---------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-whitegrid")
COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860"]

# ---------------------------------------------------------------------------
# 3. Build a combined dashboard figure (2 rows x 3 cols)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle("Campus Data Overview", fontsize=18, fontweight="bold")

# --- (1) Students per department ---
dept_counts = df["department_name"].value_counts()
axes[0, 0].bar(dept_counts.index, dept_counts.values, color=COLORS)
axes[0, 0].set_title("Students per Department")
axes[0, 0].set_ylabel("Number of Students")
axes[0, 0].tick_params(axis="x", rotation=45)

# --- (2) Gender distribution (pie chart) ---
gender_counts = df["gender"].value_counts()
axes[0, 1].pie(
    gender_counts.values,
    labels=gender_counts.index,
    autopct="%1.1f%%",
    colors=COLORS[:2],
    startangle=90,
)
axes[0, 1].set_title("Gender Distribution")

# --- (3) CGPA distribution (histogram) ---
axes[0, 2].hist(df["cgpa"], bins=15, color=COLORS[2], edgecolor="white")
axes[0, 2].set_title("CGPA Distribution")
axes[0, 2].set_xlabel("CGPA")
axes[0, 2].set_ylabel("Number of Students")

# --- (4) Attendance vs CGPA (scatter) ---
axes[1, 0].scatter(
    df["attendance_percentage"], df["cgpa"], alpha=0.5, color=COLORS[3], s=20
)
axes[1, 0].set_title("Attendance vs CGPA")
axes[1, 0].set_xlabel("Attendance (%)")
axes[1, 0].set_ylabel("CGPA")

# --- (5) Placement status breakdown ---
placement_counts = df["placement_status"].value_counts()
axes[1, 1].bar(placement_counts.index, placement_counts.values, color=COLORS[4])
axes[1, 1].set_title("Placement Status")
axes[1, 1].set_ylabel("Number of Students")

# --- (6) Average package by department (placed students only) ---
placed = df[df["placement_status"] == "Placed"]
avg_package = placed.groupby("department_name")["package_lpa"].mean().sort_values()
axes[1, 2].barh(avg_package.index, avg_package.values, color=COLORS[5])
axes[1, 2].set_title("Avg Package by Department (Placed Students)")
axes[1, 2].set_xlabel("Package (LPA)")

plt.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("campus_data_visuals.png", dpi=150, bbox_inches="tight")
print("Saved combined dashboard: campus_data_visuals.png")

plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Also save each chart individually (useful for reports/slides)
# ---------------------------------------------------------------------------

def save_single(fig_func, filename, figsize=(8, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    fig_func(ax)
    fig.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {filename}")


save_single(
    lambda ax: (
        ax.bar(dept_counts.index, dept_counts.values, color=COLORS),
        ax.set_title("Students per Department"),
        ax.set_ylabel("Number of Students"),
        ax.tick_params(axis="x", rotation=45),
    ),
    "chart_students_per_department.png",
)

save_single(
    lambda ax: (
        ax.pie(
            gender_counts.values,
            labels=gender_counts.index,
            autopct="%1.1f%%",
            colors=COLORS[:2],
            startangle=90,
        ),
        ax.set_title("Gender Distribution"),
    ),
    "chart_gender_distribution.png",
)

save_single(
    lambda ax: (
        ax.hist(df["cgpa"], bins=15, color=COLORS[2], edgecolor="white"),
        ax.set_title("CGPA Distribution"),
        ax.set_xlabel("CGPA"),
        ax.set_ylabel("Number of Students"),
    ),
    "chart_cgpa_distribution.png",
)

save_single(
    lambda ax: (
        ax.scatter(
            df["attendance_percentage"], df["cgpa"], alpha=0.5, color=COLORS[3], s=20
        ),
        ax.set_title("Attendance vs CGPA"),
        ax.set_xlabel("Attendance (%)"),
        ax.set_ylabel("CGPA"),
    ),
    "chart_attendance_vs_cgpa.png",
)

save_single(
    lambda ax: (
        ax.bar(placement_counts.index, placement_counts.values, color=COLORS[4]),
        ax.set_title("Placement Status"),
        ax.set_ylabel("Number of Students"),
    ),
    "chart_placement_status.png",
)

save_single(
    lambda ax: (
        ax.barh(avg_package.index, avg_package.values, color=COLORS[5]),
        ax.set_title("Avg Package by Department (Placed Students)"),
        ax.set_xlabel("Package (LPA)"),
    ),
    "chart_avg_package_by_department.png",
)

print("\nAll charts generated successfully.")
