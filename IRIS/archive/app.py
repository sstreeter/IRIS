import streamlit as st
import pandas as pd
import plotly.express as px

# U.S. population estimate (2024)
us_population = 336_000_000

# Define data
data = {
    "Country": ["Venezuela", "Syria", "Afghanistan", "DR Congo", "Myanmar", "Ukraine", "Mexico", "Canada"],
    "Population (2024 est.)": [28_000_000, 22_000_000, 41_000_000, 100_000_000, 54_000_000, 36_000_000, 129_000_000, 40_000_000],
    "Displaced / Refugees": [7_700_000, 6_000_000, 5_800_000, 2_300_000, 1_200_000, 5_100_000, 189_000, 0],
    "US Resettled (2024)": [13_000, 11_000, 14_700, 20_000, 7_300, 5_000, 1_000, 0]
}

# Create DataFrame
df = pd.DataFrame(data)

# Compute percentages
df["% Displaced"] = (df["Displaced / Refugees"] / df["Population (2024 est.)"]) * 100
df["% of Displaced Resettled in US"] = (df["US Resettled (2024)"] / df["Displaced / Refugees"].replace(0, 1)) * 100
df["% of US Population (2024)"] = (df["US Resettled (2024)"] / us_population) * 100

# Round values for readability
df["% Displaced"] = df["% Displaced"].round(2)
df["% of Displaced Resettled in US"] = df["% of Displaced Resettled in US"].round(3)
df["% of US Population (2024)"] = df["% of US Population (2024)"].round(6)

# Streamlit interface
st.title("🌎 Global Displacement & U.S. Resettlement Dashboard")
st.write("This dashboard visualizes refugee displacement by country, their resettlement in the United States, and how much of the US population they represent.")

# Plotly bar chart
fig = px.bar(
    df,
    x="Country",
    y="% Displaced",
    color="% of Displaced Resettled in US",
    hover_data=["Population (2024 est.)", "Displaced / Refugees", "US Resettled (2024)", "% of US Population (2024)"],
    title="% of Country's Population Displaced (2024) with US Resettlement"
)

fig.update_layout(
    yaxis_title="% of Country's Population Displaced",
    coloraxis_colorbar_title="% Resettled in U.S."
)

st.plotly_chart(fig)

# Show data table
st.subheader("📊 Data Table")
st.dataframe(df[["Country", "US Resettled (2024)", "% of US Population (2024)"]])
