import streamlit as st
from sqlalchemy import text
from datetime import datetime, timezone
from fpdf import FPDF
import tempfile
import pandas as pd
import matplotlib.pyplot as plt

if not st.session_state.get("logged_in") or st.session_state.get("user_role") != "HR":
    st.error("Access Denied !")
    st.stop()
    
## Seeing a list of people working today
conn = st.connection("postgresql", type="sql")
query = """SELECT u.full_name, a.clock_in, a.break_start, a.break_end, a.clock_out, a.total_billable_hours
            FROM users u, attendance a
                WHERE u.id = a.user_id AND a.date = CURRENT_DATE"""
df = conn.query(query,ttl = 0)
st.dataframe(df)


st.divider()
st.subheader("Leave Approvals")

query = """SELECT l.id as req_id, u.full_name, l.start_date, l.end_date, l.total_days, l.user_id
            FROM users u, leave_requests l
                WHERE u.id = l.user_id AND l.status='Pending' """

df_leave = conn.query(query,ttl = 0)
if not df_leave.empty:
    for index,row in df_leave.iterrows():
        
        user = row["user_id"]
        req_id = row["req_id"]
        days = row["total_days"]
        
        with st.container(border=True):
            st.write(f"{row['full_name']} wants {days} days off.")
            col1, col2 = st.columns(2)   
            
            with col1:
                if st.button("Approve", key=f"acc_{req_id}"):
                    with conn.session as s:
                        s.execute(
                            text(
                                """UPDATE leave_requests SET status = 'Approved' WHERE id = :req_id""",
                                
                            ),
                            {"req_id":req_id}
                        ) 
                        
                        s.execute(
                            text(
                                
                                """UPDATE users SET holidays_taken = holidays_taken + :days WHERE id = :user_id"""
                            ),
                            {"user_id":user, "days":days}
                        ) 
                        
                        s.commit() 
                    st.success("Leave accepted !") 
                    st.rerun()  
            with col2:
                if st.button("Reject",key=f"rej_{req_id}"):
                    with conn.session as s:
                        s.execute(
                            text(
                                """UPDATE leave_requests SET status = 'Rejected' WHERE id = :req_id """
                            ),
                            {"req_id":req_id}
                        )  
                        s.commit() 
                    st.success("Leave Rejected !") 
                    st.rerun() 
else:
    st.write("No Leave Requests !")


## PDF generation 

st.subheader("Generate Monthly Employee Report")
input_username = st.text_input("Enter the username of the employee to generate pdf")

if st.button("Generate Report"):
    if not input_username:
        st.error("Please enter a valid username !")
    else:
        username_query = "SELECT id, full_name, hourly_rate FROM users WHERE username = :user"
        user_match = conn.query(username_query, params={"user":input_username},ttl=0)
        
        if user_match.empty:
            st.error("Please enter a valid username !")
        else:
            selected_user_id = int(user_match.iloc[0]['id'])
            full_name = user_match.iloc[0]['full_name']
            hourly_rate = user_match.loc[0]['hourly_rate']
            
            
            ## Fetch last 30 days of attendance
            report_query = """
                SELECT date, clock_in, clock_out, total_billable_hours
                    FROM attendance
                        WHERE user_id = :uid 
                            ORDER BY date DESC
                                LIMIT 30 """
            
            report_data = conn.query(report_query,params={"uid":selected_user_id},ttl=0)
            
            ## adding a new dataframe for chart
            chart_df = report_data.iloc[::-1]
            
            if report_data.empty:
                st.error(f"No Data to display for {full_name}!")
            else:
                ## creating an object
                pdf = FPDF()
                pdf.add_page()
                
                pdf.set_font("Arial", 'B', 16)
                
                pdf.cell(200,10,txt=f"Monthly Attendance Report: {full_name}", ln=True, align='C')
                pdf.ln(10)
                
                # Add Table Headers
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(40, 10, "Date", border=1)
                pdf.cell(50, 10, "Clock In", border=1)
                pdf.cell(50, 10, "Clock Out", border=1)
                pdf.cell(40, 10, "Billable Hours", border=1)
                pdf.ln()
                
                
                # Add Table Data
                pdf.set_font("Arial", size=10)
                total_hours = 0.0
                
                for index, row in report_data.iterrows():
                    pdf.cell(40, 10, str(row['date']), border=1)
                    
                    
                    c_in = str(row['clock_in'])[11:16] if pd.notna(row['clock_in']) else "-"
                    c_out = str(row['clock_out'])[11:16] if pd.notna(row['clock_out']) else "-"
                    hours = float(row['total_billable_hours']) if pd.notna(row['total_billable_hours']) else 0.0
                    
                
            
                    pdf.cell(50, 10, c_in, border=1)
                    pdf.cell(50, 10, c_out, border=1)
                    pdf.cell(40, 10, str(hours), border=1)
                    pdf.ln()
                    
                    total_hours += hours
                total_earnings = hourly_rate * total_hours
                
                pdf.ln(10)
                pdf.set_font("Arial",'B',size=12)
                pdf.cell(200,10, txt=f"Total Billable Hours : {round(total_hours,2)}",ln=True)
                pdf.cell(200,10, txt=f"Total Earnings : {round(total_earnings,2)}",ln=True)
                
                ## Creating the chart 
                plt.figure(figsize=(8, 4))
                
                # Convert data to floats and strings so the chart doesn't crash
                x_dates = chart_df['date'].astype(str)
                y_hours = chart_df['total_billable_hours'].fillna(0).astype(float)
                
                plt.bar(x_dates,y_hours,color="green")
                plt.title("Daily Billable Hours")
                plt.xlabel("Date")
                plt.ylabel("Hours Worked")
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                ## saving the chart as a image
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    plt.savefig(tmp.name)
                    plt.close()
                    
                    ## pasting the image
                    pdf.ln(10) 
                    pdf.image(tmp.name, w=180)
                    
                ## Save to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    pdf.output(tmp.name)
                    with open(tmp.name, "rb") as f:
                        pdf_bytes = f.read()
                        
                ## Downloading the pdf
                st.success(f"Report generated successfully for {full_name}!")
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"Report_{input_username}.pdf",
                    mime="application/pdf"
                )
                
            
