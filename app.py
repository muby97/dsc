import streamlit as st
import pandas as pd
import os
import json
from datetime import date, timedelta

# Helper functions
def load_data(filepath, columns):
    """Load data from a CSV file or initialize a new one."""
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        # Deserialize 'Assignments' column if it exists and is a string
        if "Assignments" in df.columns:
            df["Assignments"] = df["Assignments"].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.strip() else []
            )
        return df
    return pd.DataFrame(columns=columns)

def save_data(df, filepath):
    """Save data to a CSV file."""
    if "Assignments" in df.columns:
        df["Assignments"] = df["Assignments"].apply(json.dumps)  # Serialize Assignments
    df.to_csv(filepath, index=False)

def update_team_members(staffs_df, teams_df):
    """Update team members in teams based on the staffs DataFrame."""
    for index, team in teams_df.iterrows():
        team_name = team["Team Name"]
        members = staffs_df[staffs_df["Team"] == team_name]["Name"].tolist()
        teams_df.at[index, "Members"] = ",".join(members)
    return teams_df

# File paths
STAFFS_FILE = "data/staffs.csv"
TEAMS_FILE = "data/teams.csv"
SCHEDULES_FILE = "data/schedules.csv"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Initialize session state
if "staffs" not in st.session_state:
    st.session_state["staffs"] = load_data(STAFFS_FILE, ["ID", "Name", "Phone", "Team"])
if "teams" not in st.session_state:
    st.session_state["teams"] = load_data(TEAMS_FILE, ["ID", "Team Name", "Location", "Leader", "Members"])
if "schedules" not in st.session_state:
    st.session_state["schedules"] = load_data(SCHEDULES_FILE, ["ID", "Name", "Team", "Team Leader", "Start Date", "End Date", "Assignments"])

# Relational updates: Sync teams with staffs
st.session_state["teams"] = update_team_members(st.session_state["staffs"], st.session_state["teams"])

# Streamlit UI
st.set_page_config(page_title="Holiday Manager", layout="wide")
st.sidebar.image("logo.png", use_container_width=True)
menu = st.sidebar.radio("Navigation", ["Home", "Staffs", "Teams", "Weekend Schedule", "Users", "My Account"])

if menu == "Home":
    st.title("Welcome to the Holiday Manager")
    st.markdown("### Dashboard Overview")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Staff", len(st.session_state["staffs"]))
    col2.metric("Total Teams", len(st.session_state["teams"]))

    if not st.session_state["schedules"].empty:
        all_weekend_dates = []
        today = pd.Timestamp.today()

        for _, schedule in st.session_state["schedules"].iterrows():
            assignments = schedule["Assignments"]
            if isinstance(assignments, str):
                assignments = json.loads(assignments)
            for assignment in assignments:
                if isinstance(assignment, dict):
                    weekend_date = pd.to_datetime(assignment.get("Weekend Date"))
                    if weekend_date > today:
                        all_weekend_dates.append((weekend_date, assignment.get("Team Member"), schedule["Team"]))

        if all_weekend_dates:
            next_holiday = min(all_weekend_dates, key=lambda x: x[0])
            next_holiday_date, next_holiday_staff, next_holiday_team = next_holiday
            col3.metric("Next upcoming Holiday", next_holiday_date.strftime("%Y-%m-%d"))
            col4.metric("Next Weekend Off Staff", f"{next_holiday_staff} ({next_holiday_team})")
        else:
            col3.metric("Next upcoming Holiday", "No Schedule")
            col4.metric("Next Weekend Off Staff", "No Staff Assigned")
    else:
        col3.metric("Next upcoming Holiday", "No Schedule")
        col4.metric("Next Weekend Off Staff", "No Staff Assigned")

elif menu == "Staffs":
    st.title("Manage Staffs")

    # Ensure the Phone column is treated as text
    if "Phone" in st.session_state["staffs"].columns:
        st.session_state["staffs"]["Phone"] = st.session_state["staffs"]["Phone"].astype(str)

    st.write(st.session_state["staffs"])

    with st.form("add_staff"):
        st.subheader("Add New Staff")
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        team = st.selectbox("Team", [""] + list(st.session_state["teams"]["Team Name"]))
        
        # Remove commas from phone number input
        phone = phone.replace(",", "")
        
        submit = st.form_submit_button("Add Staff")
        if submit:
            new_id = len(st.session_state["staffs"]) + 1
            new_staff = pd.DataFrame([{"ID": new_id, "Name": name, "Phone": phone, "Team": team}])
            st.session_state["staffs"] = pd.concat([st.session_state["staffs"], new_staff], ignore_index=True)
            save_data(st.session_state["staffs"], STAFFS_FILE)
            st.session_state["teams"] = update_team_members(st.session_state["staffs"], st.session_state["teams"])
            save_data(st.session_state["teams"], TEAMS_FILE)
            st.success("Staff added successfully!")
            st.experimental_rerun()

elif menu == "Teams":
    st.title("Manage Teams")
    st.write(st.session_state["teams"])

    with st.form("add_team"):
        st.subheader("Create a New Team")
        team_name = st.text_input("Team Name")
        location = st.text_input("Location")
        leader = st.selectbox("Team Leader", [""] + list(st.session_state["staffs"]["Name"]))
        submit = st.form_submit_button("Create Team")
        if submit:
            new_id = len(st.session_state["teams"]) + 1
            st.session_state["teams"] = pd.concat(
                [st.session_state["teams"], pd.DataFrame([{
                    "ID": new_id, "Team Name": team_name, "Location": location,
                    "Leader": leader, "Members": ""
                }])], ignore_index=True
            )
            save_data(st.session_state["teams"], TEAMS_FILE)
            st.success("Team created successfully!")
            st.experimental_rerun()

elif menu == "Weekend Schedule":
    st.title("Weekend Schedules")
    st.markdown("### Existing Schedules")
    if st.session_state["schedules"].empty:
        st.info("No schedules created yet.")
    else:
        for _, schedule in st.session_state["schedules"].iterrows():
            st.markdown(f"**Schedule ID {schedule['ID']}** - {schedule['Team']} ({schedule['Start Date']} to {schedule['End Date']})")
            if st.button(f"View Schedule {schedule['ID']}", key=f"view_{schedule['ID']}"):
                st.markdown(f"## Schedule: {schedule['Name']}")
                st.markdown(f"- **Team:** {schedule['Team']}")
                st.markdown(f"- **Team Leader:** {schedule['Team Leader']}")
                st.markdown(f"- **Time Frame:** {schedule['Start Date']} to {schedule['End Date']}")
                st.markdown("### Weekend Assignments")
                assignments = schedule["Assignments"]
                if isinstance(assignments, str):
                    assignments = json.loads(assignments)
                if assignments:
                    st.write(pd.DataFrame(assignments))
                else:
                    st.info("No assignments available for this schedule.")

    st.markdown("### Create a New Schedule")
    with st.form("create_schedule"):
        schedule_name = st.text_input("Schedule Name")
        team = st.selectbox("Select Team", st.session_state["teams"]["Team Name"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        submit = st.form_submit_button("Generate Schedule")

        if submit:
            if start_date >= end_date:
                st.error("End date must be after the start date.")
            else:
                team_data = st.session_state["teams"][st.session_state["teams"]["Team Name"] == team].iloc[0]
                team_members = team_data["Members"].split(",")
                weekend_dates = pd.date_range(start=start_date, end=end_date, freq="W-SAT").to_list()
                assignments = []

                for i, saturday in enumerate(weekend_dates):
                    sunday = saturday + pd.Timedelta(days=1)  # Calculate Sunday
                    staff_member = team_members[i % len(team_members)]  # Assign staff member in a round-robin way
                    assignments.append({"Team Member": staff_member, "Weekend Date": saturday.strftime("%Y-%m-%d"), "Day": "Saturday"})
                    assignments.append({"Team Member": staff_member, "Weekend Date": sunday.strftime("%Y-%m-%d"), "Day": "Sunday"})

                new_schedule = {
                    "ID": len(st.session_state["schedules"]) + 1,
                    "Name": schedule_name,
                    "Team": team,
                    "Team Leader": team_data["Leader"],
                    "Start Date": start_date.strftime("%Y-%m-%d"),
                    "End Date": end_date.strftime("%Y-%m-%d"),
                    "Assignments": assignments,
                }
                st.session_state["schedules"] = pd.concat([st.session_state["schedules"], pd.DataFrame([new_schedule])], ignore_index=True)
                save_data(st.session_state["schedules"], SCHEDULES_FILE)
                st.success(f"Schedule '{schedule_name}' created successfully!")
                st.experimental_rerun()

