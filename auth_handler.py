import streamlit as st
import time

def render_sidebar(supabase):
    """
    Handles Sidebar Login, Navigation, and Regional Settings.
    Returns the selected menu option and region mode.
    """
    st.sidebar.title("🛡️ Med-Synth AI")

    # --- LOGIN LOGIC ---
    if not st.session_state.logged_in:
        st.sidebar.subheader("Clinical Portal Login")
        user_email = st.sidebar.text_input("Institutional Email", placeholder="name@hospital.com") 
        pw_input = st.sidebar.text_input("Security Key", type="password")
        
        if st.sidebar.button("Login"):
            try:
                # Use Supabase Auth to verify credentials
                response = supabase.auth.sign_in_with_password({
                    "email": user_email, 
                    "password": pw_input
                })
                
                if response.user:
                    st.session_state.logged_in = True
                    st.session_state.username = response.user.email
                    st.sidebar.success("✅ Access Granted")
                    time.sleep(0.5) 
                    st.rerun()
            except Exception as e:
                st.sidebar.error("❌ Invalid Credentials or Unverified Email")
                st.sidebar.info("Tip: Ensure you have confirmed your email via the link sent by Supabase.")
        
        # Return None for menu/region if not logged in
        return None, None

    # --- AUTHORIZED SIDEBAR ---
    else:
        st.sidebar.success(f"Status: Authorized")
        st.sidebar.write(f"**User:** {st.session_state.username}")
        st.sidebar.write("---")
        
        menu = st.sidebar.radio(
            "Workflow Steps", 
            ["Dashboard", "1. HIPAA Scan & Upload", "2. AI Generation", "3. Privacy Audit"]
        )
        
        # --- REGIONAL INTELLIGENCE SELECTION ---
        st.sidebar.write("---")
        st.sidebar.subheader("🌍 Regional Intelligence")
        region_mode = st.sidebar.selectbox(
            "Select Target Region", 
            ["Default (Raw)", "India 🇮🇳", "USA 🇺🇸", "Europe 🇪🇺"],
            help="Adjusts synthetic distributions based on regional demographics."
        )
        
        st.sidebar.write("---")
        if st.sidebar.button("Log Out"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        return menu, region_mode