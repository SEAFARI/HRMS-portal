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
    context_string = df.to_string(index=False)
    
if st.button("Generate Summary"):
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    llm = ChatGroq(model="llama-3.1-8b-instant")
    
    with st.spinner("AI crew is generating the summary..."):
        try:
            ## AI prompt
            prompt = f"""
                You are an expert HR Communications Specialist. 
                Analyze this live attendance data:
                {context_string}
                
                Write a short, polished 3-sentence summary of today's workforce status. 
                Mention who is currently active, who finished their shift, and if no one is here yet.
                Do not include raw tables or bullet points.
                """
                
            response = llm.invoke(prompt)
                
            st.success("Analysis Completed!")
            st.info(response.content)
        except Exception as e:
            st.error(f"Error : {e}")

                
    
