import numpy as np
import pandas as pd
import streamlit as st
from database_v0 import get_data
import plotly.express as px
from ydata_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report
from streamlit.components.v1 import html
import plotly.graph_objects as go

from PIL import Image

image = Image.open("c2smarter_logo.png")

# Set page title and layout
st.set_page_config(page_title="BSafe-360 Dashboard", page_icon=":bike:", layout="wide")

bar = """
.st-emotion-cache-6qob1r {
    background-color: #121212;
}
"""

st.markdown(f"<style>{bar}</style>", unsafe_allow_html=True)

with st.sidebar:
    # st.markdown(bar, unsafe_allow_html=True)
    with st.container():
        st.image(image)


@st.cache_data
def load_data():
    df = get_data()
    return df


with st.spinner("Loading data..."):
    df_v1 = load_data()

# Title
st.title(":bike: BSafe-360 Dashboard")

# Sidebar with selection options
# rides_to_select = np.array(
select_country = st.sidebar.radio(
    "Selected country", np.insert(df_v1["country"].astype(object).unique(), 0, "All")
)
if select_country == "All":
    selected_rides = st.sidebar.multiselect(
        "Select Ride", np.insert(df_v1["ride"].astype(object).unique(), 0, "All")
    )
else:
    selected_rides = st.sidebar.multiselect(
        "Select Ride",
        np.insert(
            df_v1[df_v1["country"] == select_country]["ride"]
            .sort_values()
            .astype(object)
            .unique(),
            0,
            "All",
        ),
    )
data_options = ["All", "Unsafe Only"]
selected_data = st.sidebar.radio("Show:", data_options)
map_range = st.sidebar.slider(
    "Distance Left Threshold (cm)", min_value=50, max_value=200, value=100, step=10
)

if selected_rides:
    # Filter data based on user selection
    if select_country == "All" and selected_rides == ["All"]:
        filtered_df = df_v1
    elif select_country != "All" and selected_rides == ["All"]:
        filtered_df = df_v1[df_v1["country"] == select_country]
    elif select_country == "All" and selected_rides != ["All"]:
        filtered_df = df_v1[df_v1["ride"].isin(selected_rides)]
    else:
        filtered_df = df_v1[
            (df_v1["ride"].isin(selected_rides)) & (df_v1["country"] == select_country)
        ]

    filtered_df.reset_index(drop=True, inplace=True)

    filtered_df["time"] = pd.to_datetime(filtered_df["dtg"])
    filtered_df = filtered_df.sort_values(by="time")
    filtered_df.reset_index(inplace=True, drop=True)

    filtered_df["interval"] = filtered_df.groupby("ride", as_index=False)["time"].diff()
    filtered_df["interval"] = filtered_df["interval"].dt.total_seconds()
    filtered_df["interval"] = filtered_df["interval"].fillna(0)

    # Calculate the cumulative sum of the difference
    filtered_df["DT"] = filtered_df.groupby("ride", as_index=False)["interval"].cumsum()

    # Fill NaN values with 0 in the CumulativeSum column
    filtered_df["DT"].fillna(0, inplace=True)

    with st.container():
        col1, col2, col3 = st.columns([0.2, 0.2, 0.6])

        dur_sec = filtered_df["interval"].sum()
        hours = int(dur_sec // 3600)
        minutes = int((dur_sec / 3600 - hours) * 60)
        seconds = int(((dur_sec / 3600 - hours) * 60 - minutes))

        tooltip_dur = "Durations might vary slightly from those presented on papers and dissertation because of additional data processing steps taken by the researchers, \
            read [(Bernardes and Ozbay, 2023)](https://www.mdpi.com/1424-8220/23/14/6471) for more information."

        # Display basic ride information
        # st.markdown(f'**Date:** {filtered_df["dtg"].iloc[0]}')
        col1.markdown(
            f'**Start Time:** {filtered_df["dtg"].iloc[0].strftime("%a, %m/%d/%Y %I:%M %p")}'
        )
        col2.markdown(
            f'**End Time:** {filtered_df["dtg"].iloc[-1].strftime("%a, %m/%d/%Y %I:%M %p")}'
        )
        col3.markdown(f"**Duration:** {hours}h {minutes}m and {seconds}s", help=tooltip_dur)

    filtered_df["dis_100_left"] = map_range - filtered_df["dist_left"]
    filtered_df["is_event_left"] = filtered_df["dist_left"].apply(
        lambda x: 1 if (x <= map_range) else 0
    )

    event = []
    event_temp = 0
    # event.append(event_temp)
    for i in range(1, filtered_df.shape[0]):
        if i - 1 == 0:
            if (
                (filtered_df.loc[i, "is_event_left"] == 1)
                & (filtered_df.loc[i - 1, "is_event_left"] == 0)
            ) | (
                (filtered_df.loc[i, "is_event_left"] == 1)
                & (filtered_df.loc[i - 1, "is_event_left"] == 1)
            ):
                event_temp = event_temp + 1
            else:
                event_temp = event_temp
        else:
            if (filtered_df.loc[i, "is_event_left"] == 1) & (
                filtered_df.loc[i - 1, "is_event_left"] == 0
            ):
                event_temp = event_temp + 1
            else:
                event_temp = event_temp
        event.append(event_temp)
    if filtered_df.loc[0, "is_event_left"] == 0:
        event.insert(0, 0)
    else:
        event.insert(0, 1)

    filtered_df["event"] = event
    filtered_df.loc[filtered_df.is_event_left == 0, "event"] = 0

    
    summ = filtered_df[filtered_df["event"] != 0]["event"].nunique()

    col1, col2, col3, col4 = st.columns(4)

    # Display average values
    col1.metric("**Number of unsafe events (left):** ", f"{summ}")

    if selected_data == "Unsafe Only":
        filtered_df = filtered_df[filtered_df["dist_left"] <= map_range]

    col2.metric("**Average Speed:**", f'{filtered_df["speed"].mean():.2f} m/s')
    col3.metric(
        "**Average Distance Left:**", f'{filtered_df["dist_left"].mean():.2f} cm'
    )
    col4.metric(
        "**Average Distance Right:**", f'{filtered_df["dist_right"].mean():.2f} cm'
    )

    tab1, tab2, tab3 = st.tabs(["Mapped Ride", "Distribution Plots", "Data Profile"])

    with tab1:
        # Plot bike map
        max_bound = (
            max(
                abs(filtered_df["longitude"].max() - filtered_df["longitude"].min()),
                abs(filtered_df["latitude"].max() - filtered_df["latitude"].min()),
            )
            * 111
        )
        zoom = 10.5 - np.log(max_bound)
        st.plotly_chart(
            px.scatter_mapbox(
                filtered_df,
                lat="latitude",
                lon="longitude",
                color="dist_left",
                color_continuous_scale="Viridis",
                size_max=15,
                zoom=zoom,
                height=800
            ).update_layout(mapbox_style="carto-positron"), use_container_width = True
        )

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Plot distance distribution
            st.plotly_chart(
                px.histogram(filtered_df, x="dist_left", title="Distance Distribution")
            )

            fig = go.Figure()


            if selected_rides == ['All']:
                rides_plot = filtered_df['ride'].unique()
            else:
                rides_plot = selected_rides

            for rid in rides_plot:
                df_subset = filtered_df[filtered_df['ride'] == rid]

                # Add a scatter trace for this ride to the figure
                fig.add_trace(go.Scatter(
                    x=df_subset["DT"],
                    y=df_subset["altitude"],
                    name=f"Ride {rid}",  # Giving a name to the trace to differentiate in the legend
                    fill='tozeroy'
                ))
            # Update the layout if needed
            fig.update_layout(title="Altitude Profile")

            st.plotly_chart(fig)

        with col2:
            # Plot acceleration distribution
            st.plotly_chart(
                px.histogram(filtered_df, x="acce_x", title="Acceleration Distribution")
            )

            # Plot speed distribution
            st.plotly_chart(
                px.histogram(filtered_df, x="speed", title="Speed Distribution")
            )

    with tab3:
        with st.spinner("Loading data profile..."):
            if "profile" not in st.session_state:
                st.session_state["profile"] = ProfileReport(filtered_df)

            st_profile_report(st.session_state["profile"])
else:
    st.write("Please select at least one ride to start")
