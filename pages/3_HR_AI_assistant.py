import streamlit as st
from langchain_groq import ChatGroq
import os

if not st.session_state.get("logged_in") or st.session_state.get("user_role") != "HR":
    st.error("Access Denied !")
    st.stop()
    
    
conn = st.connection("postgresql", type="sql")
query = """SELECT u.full_name, a.clock_in, a.break_start, a.break_end, a.clock_out, a.total_billable_hours
            FROM users u, attendance a
                WHERE u.id = a.user_id AND a.date = CURRENT_DATE"""
df = conn.query(query,ttl = 0)

if df.empty:
    context_string = "No employees have clocked in today yet."
else:
    context_string = df.to_csv(index=False)
    
if st.button("Generate Summary"):
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    llm = ChatGroq(model="llama-3.1-8b-instant")
    
    with st.spinner("AI crew is generating the summary..."):
        try:
            ## AI prompt
            prompt = f"""
                You are an HR Assistant. Read this CSV data:
                
                {context_string}
                
                Write a 2-sentence summary. 
                If the 'clock_out' column has a time, the employee finished their shift. 
                If the 'clock_out' column is blank or empty, they are still active.
                Don't mention about CSV files. Say that - according to the data.
                """
                
            response = llm.invoke(prompt)
                
            st.success("Analysis Completed!")
            st.info(response.content)
        except Exception as e:
            st.error(f"Error : {e}")

                
    
