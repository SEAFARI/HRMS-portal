import streamlit as st
from sqlalchemy import text
from datetime import datetime, timezone

if not st.session_state.get("logged_in"):
    st.error("[ERROR] Please log in !")
    st.stop()
    
## establishing the connection with the database
conn = st.connection("postgresql", type="sql")

uid = st.session_state.user_id
query = "SELECT clock_in, break_start, break_end, clock_out FROM attendance WHERE user_id = :user AND date = CURRENT_DATE"
today_log = conn.query(query, params = {"user":uid}, ttl=0)


## checking ig log is empty. If empty then only show clock in 
if today_log.empty:
    st.subheader("Status: Not clocked in")
    if st.button("Start Shift"):
        with conn.session as s:
            s.execute(text (
                "INSERT into attendance (user_id, date, clock_in) VALUES (:user, CURRENT_DATE, CURRENT_TIMESTAMP)"),
                    {"user":uid}
                )
            s.commit()
        st.success("Shift Started !")
        st.rerun()
    
else:
    ## check the first row 
    row = today_log.iloc[0]
    
    if row["clock_out"] is not None:
        st.subheader("Shift Completed !")
    
    elif row["break_start"] is not None and row["break_end"] is None:
        st.subheader("On Break !")
        if st.button("End Break"):
            with conn.session as s:
                    s.execute(text (
                        "UPDATE attendance SET break_end = CURRENT_TIMESTAMP WHERE user_id = :user AND date = CURRENT_DATE"),
                        {"user":uid}
                    )
                    s.commit()
            st.success("Break Ended !")
            st.rerun()
            
    else:
        st.subheader("Actively Working !")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Start Break"):
                with conn.session as s:
                    s.execute(text (
                        "UPDATE attendance SET break_start =  CURRENT_TIMESTAMP WHERE user_id = :user AND date = CURRENT_DATE"),
                        {"user":uid}
                    )
                    s.commit()
                st.success("Break Started !")
                st.rerun()
            
        with col2:
            if st.button("End Shift"):
                clock_in = row["clock_in"]
                current_time = datetime.now(timezone.utc)
                worked_seconds = (current_time - clock_in).total_seconds()
                break_time = 0
                if row["break_start"] is not None and row["break_end"]  is not None:
                    break_time = (row["break_end"] - row["break_start"]  ).total_seconds()
                working_hours = round((worked_seconds - break_time)/3600.0,2)
                    
                
                with conn.session as s:
                    s.execute (text(
                        """
                        UPDATE attendance SET clock_out =  CURRENT_TIMESTAMP,
                            total_billable_hours = :hours
                                WHERE user_id = :user AND date = CURRENT_DATE
                        """),
                        {"hours":working_hours,"user":uid}
                    )
                    s.commit()
                st.success("Shift Completed !")
                st.rerun()
        
    
## Leave UI

st.divider()
st.subheader("Request Leave")

query = "SELECT holidays_assigned, holidays_taken FROM users WHERE id = :user"
data = conn.query(query, params={"user":uid}, ttl=0).iloc[0]

assigned = data["holidays_assigned"]
taken = data["holidays_taken"]
remaining = assigned - taken

st.info(f"You have {remaining} holidays out of {assigned} holidays.")

st.subheader("Request Leave")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")
  
if st.button("submit leave request"):
    total_days = (end_date - start_date).days + 1
    
    if total_days <=0:
        st.error("[ERROR] Please recheck the dates")
    elif total_days > remaining:
         st.error(f"You only have {remaining} holidays left.")
    else:
        with conn.session as s:
            s.execute(text(
                """INSERT INTO leave_requests (user_id, start_date, end_date, total_days, status) 
                VALUES (:user, :start, :end, :days, 'Pending') """),
                {"user":uid,"start":start_date,"end":end_date,"days":total_days}
            )
            s.commit()
        st.success(f"You have successfully request {total_days} days off. It is now pending HR approval. ")


