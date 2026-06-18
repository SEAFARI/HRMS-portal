import streamlit as st

# Must be the very first Streamlit command
st.set_page_config(page_title="HRMS Portal", page_icon="🏢", layout="centered")

# Initialize session state variables to track who is logged in
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_id = None
    st.session_state.full_name = None

def login():
    st.title(" HRMS Cloud Portal")
    st.markdown("Please log in with your credentials.")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login", use_container_width=True):
        # 1. Connect to the database using the secrets.toml file
        conn = st.connection("postgresql", type="sql")
        
        # 2. Safely query the database (parameters prevent SQL injection)
        query = "SELECT id, role, password, full_name FROM users WHERE username = :user"
        user_data = conn.query(query, params={"user": username})
        
        # 3. Verify credentials
        if not user_data.empty and user_data.iloc[0]['password'] == password:
            st.session_state.logged_in = True
            st.session_state.user_role = user_data.iloc[0]['role']
            st.session_state.user_id = int(user_data.iloc[0]['id'])
            st.session_state.full_name = user_data.iloc[0]['full_name']
            
            st.success(f"Login successful! Welcome, {st.session_state.full_name}.")
            st.rerun() # Refreshes the app to clear the login screen
        else:
            st.error(" Invalid username or password.")

# Routing Logic
if not st.session_state.logged_in:
    login()
else:
    # This is what they see AFTER logging in
    st.title(f"Welcome to the portal, {st.session_state.full_name}!")
    st.info(f"Assigned Role: **{st.session_state.user_role}**")
    st.write(" Please use the sidebar menu to navigate to your specific dashboard.")
    
    if st.button("Log Out"):
        st.session_state.clear()
        st.rerun()  