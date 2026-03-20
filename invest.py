import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime


def initialize_session_state():
    if "contributions" not in st.session_state:
        st.session_state.contributions = [
            {
                "amount": 100.0,
                "interval": "monthly",
                "start_year": 0,
                "end_year": None,
                "until_end": True,
            }
        ]


def add_contribution():
    st.session_state.contributions.append(
        {
            "amount": 100.0,
            "interval": "monthly",
            "start_year": 0,
            "end_year": None,
            "until_end": True,
        }
    )


def remove_contribution(index):
    if 0 <= index < len(st.session_state.contributions):
        st.session_state.contributions.pop(index)


def build_contribution_list_from_inputs(timeframe_years):
    contributions = []
    for i, existing in enumerate(st.session_state.contributions):
        amount = st.session_state.get(f"contrib_amt_{i}", existing["amount"])
        interval = st.session_state.get(f"contrib_interval_{i}", existing["interval"])
        start_year = st.session_state.get(f"contrib_start_{i}", existing["start_year"])
        until_end = st.session_state.get(f"contrib_until_end_{i}", existing.get("until_end", True))

        if until_end:
            end_year = timeframe_years - 1
        else:
            end_year = st.session_state.get(f"contrib_end_{i}", existing.get("end_year", timeframe_years - 1))

        # sanitize bounds
        start_year = max(0, min(timeframe_years - 1, int(start_year)))
        if end_year is not None:
            end_year = max(start_year, min(timeframe_years - 1, int(end_year)))

        contributions.append(
            {
                "amount": float(amount),
                "interval": interval,
                "start_year": start_year,
                "end_year": end_year,
                "until_end": until_end,
            }
        )

    st.session_state.contributions = contributions
    return contributions


def simulate_portfolio(
    initial_amount, annual_rate_pct, timeframe_years, contributions
):
    months = timeframe_years * 12
    annual_rate = annual_rate_pct / 100.0

    balance = float(initial_amount)
    cumulative_contributions = float(initial_amount)
    cumulative_interest = 0.0

    history = []
    one_time_applied = set()

    for month_idx in range(months + 1):
        year_idx = month_idx // 12
        month_of_year = month_idx % 12
        # record state at month start (including initial at month 0)
        history.append(
            {
                "month": month_idx,
                "year": year_idx + 1,
                "total_value": balance,
                "cumulative_contributions": cumulative_contributions,
                "total_interest": cumulative_interest,
            }
        )

        if month_idx == months:
            break

        active_contribution = 0.0
        for cid, item in enumerate(contributions):
            amount = item["amount"]
            if amount <= 0:
                continue

            start = item["start_year"]
            end = item["end_year"] if item["end_year"] is not None else timeframe_years - 1

            if year_idx < start or year_idx > end:
                continue

            interval = item["interval"]
            contribution_this_month = 0.0

            if interval == "monthly":
                contribution_this_month = amount
            elif interval == "weekly":
                contribution_this_month = amount * 4
            elif interval == "quarterly" and month_of_year in (0, 3, 6, 9):
                contribution_this_month = amount
            elif interval == "annually" and month_of_year == 0:
                contribution_this_month = amount
            elif interval == "one-time" and month_of_year == 0 and year_idx == start and cid not in one_time_applied:
                contribution_this_month = amount

            if contribution_this_month > 0:
                active_contribution += contribution_this_month
                if interval == "one-time":
                    one_time_applied.add(cid)

        balance += active_contribution
        cumulative_contributions += active_contribution

        # Apply interest once per year (annual compounding)
        if (month_idx + 1) % 12 == 0:
            interest = balance * annual_rate
            balance += interest
            cumulative_interest += interest

    df = pd.DataFrame(history)
    return df


def format_money(x):
    return f"${x:,.2f}"


def main():
    st.set_page_config(page_title="Investment Growth Calculator", layout="wide")
    st.title("Investment Growth Calculator")
    st.write("Simulate recurring and one-time contributions with annual compound interest.")
    current_year = datetime.now().year

    initialize_session_state()

    with st.sidebar:
        st.header("Inputs")
        annual_rate = st.number_input(
            "Fixed annual interest rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=5.0,
            step=0.1,
            key="annual_rate",
        )
        initial_investment = st.number_input(
            "Initial investment amount ($)",
            min_value=0.0,
            value=1000.0,
            step=100.0,
            key="initial_investment",
        )
        timeframe_years = st.slider(
            "Timeframe (years)",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            key="timeframe_years",
        )
        chart_display = st.selectbox(
            "Chart display",
            ["Monthly", "Annual"],
            index=0,
            key="chart_display",
        )

        st.markdown("---")
        st.header("Contribution entries")

        # contribution forms
        for idx, contribution in enumerate(list(st.session_state.contributions)):
            with st.expander(f"Contribution {idx + 1}", expanded=True):
                st.number_input(
                    "Contribution amount ($)",
                    min_value=0.0,
                    value=contribution.get("amount", 0.0),
                    step=50.0,
                    key=f"contrib_amt_{idx}",
                )
                st.selectbox(
                    "Interval",
                    ["weekly", "monthly", "quarterly", "annually", "one-time"],
                    index=["weekly", "monthly", "quarterly", "annually", "one-time"].index(contribution.get("interval", "monthly")),
                    key=f"contrib_interval_{idx}",
                )
                st.number_input(
                    f"Start year (0 = {current_year})",
                    min_value=0,
                    max_value=timeframe_years - 1,
                    value=contribution.get("start_year", 0),
                    step=1,
                    key=f"contrib_start_{idx}",
                )
                until_end_key = f"contrib_until_end_{idx}"
                st.checkbox("Until end", value=contribution.get("until_end", True), key=until_end_key)
                if not st.session_state.get(until_end_key, True):
                    st.number_input(
                        "End year",
                        min_value=st.session_state.get(f"contrib_start_{idx}", 0),
                        max_value=timeframe_years - 1,
                        value=contribution.get("end_year", timeframe_years - 1),
                        step=1,
                        key=f"contrib_end_{idx}",
                    )

                if st.button("Remove contribution", key=f"remove_{idx}"):
                    remove_contribution(idx)
                    st.rerun()

        st.button("+ Add Contribution", on_click=add_contribution)

    # build current contributions from sidebar widget state
    contributions = build_contribution_list_from_inputs(timeframe_years)

    df = simulate_portfolio(initial_investment, annual_rate, timeframe_years, contributions)
    df["simulation_year_index"] = (df["month"] // 12).astype(int)
    df["calendar_year"] = current_year + df["simulation_year_index"]

    if chart_display == "Annual":
        df_plot = df[df["month"] % 12 == 0].copy()
        x_col = "calendar_year"
        x_label = "Calendar Year"
    else:
        df_plot = df
        x_col = "month"
        x_label = "Month"

    st.subheader("Investment growth over time")
    fig = px.line(
        df_plot,
        x=x_col,
        y=["total_value", "cumulative_contributions", "total_interest"],
        line_shape="spline",
        labels={
            x_col: x_label,
            "value": "Amount",
            "total_value": "Portfolio Value",
            "cumulative_contributions": "Cumulative Contributions",
            "total_interest": "Total Interest",
        },
    )
    try:
        fig.update_traces(smoothing=0.7, line=dict(width=3))
    except Exception:
        # Fallback for Plotly builds that do not support trace-level smoothing.
        fig.update_traces(line=dict(width=3))
    fig.update_layout(legend_title_text="Series")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    final = df.iloc[-1]
    final_portfolio = final["total_value"]
    final_contributions = final["cumulative_contributions"]
    final_interest = final["total_interest"]
    roi_pct = 0.0
    if final_contributions > 0:
        roi_pct = (final_portfolio - final_contributions) / final_contributions * 100.0

    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Final portfolio value", format_money(final_portfolio))
    col2.metric("Total contributed", format_money(final_contributions))
    col3.metric("Total interest earned", format_money(final_interest))
    col4.metric("Overall ROI", f"{roi_pct:.2f}%")

    st.subheader("Year index guide")
    st.caption("Use this mapping when entering start/end years for contributions.")
    year_guide = pd.DataFrame(
        {
            "Simulation year": list(range(100)),
            "Calendar year": [current_year + i for i in range(100)],
        }
    )
    st.dataframe(year_guide, use_container_width=True, hide_index=True, height=320)


if __name__ == "__main__":
    main()
