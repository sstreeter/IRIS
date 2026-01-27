import pandas as pd
import plotly.express as px

# Define the data
data = {
    "Country": ["Venezuela", "Syria", "Afghanistan", "DR Congo", "Myanmar", "Ukraine"],
    "Population (2024 est.)": [28_000_000, 22_000_000, 41_000_000, 100_000_000, 54_000_000, 36_000_000],
    "Displaced / Refugees": [7_700_000, 6_000_000, 5_800_000, 2_300_000, 1_200_000, 5_100_000],
    "US Resettled (2024)": [13_000, 11_000, 14_700, 20_000, 7_300, 5_000]
}
# Mexico data
df.loc[len(df)] = {
    "Country": "Mexico",
    "Population (2024 est.)": 129_000_000,
    "Displaced / Refugees": 189_000,  # US asylum applicants (approx)
    "US Resettled (2024)": 1_000,     # Few formally resettled
    "% Displaced": round((189_000 / 129_000_000) * 100, 2),
    "% of Displaced Resettled in US": round((1_000 / 189_000) * 100, 3)
}

# Canada data
df.loc[len(df)] = {
    "Country": "Canada",
    "Population (2024 est.)": 40_000_000,
    "Displaced / Refugees": 0,
    "US Resettled (2024)": 0,
    "% Displaced": 0,
    "% of Displaced Resettled in US": 0
}

df = pd.DataFrame(data)
df["% Displaced"] = (df["Displaced / Refugees"] / df["Population (2024 est.)"]) * 100
df["% of Displaced Resettled in US"] = (df["US Resettled (2024)"] / df["Displaced / Refugees"]) * 100
df = df.round(2)

# Create interactive chart
fig = px.bar(df, 
             x="Country", 
             y="% Displaced", 
             hover_data=["US Resettled (2024)", "% of Displaced Resettled in US"],
             title="Displacement & U.S. Resettlement by Country",
             labels={"% Displaced": "% of Country's Population Displaced"})

fig.show()
