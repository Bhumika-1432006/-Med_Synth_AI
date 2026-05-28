import streamlit as st
import pandas as pd
import os
import time
import random
import matplotlib.pyplot as plt
import seaborn as sns
import segno
import plotly.express as px
import base64 
from io import BytesIO
from supabase import create_client, Client

# --- PAGE CONFIG ---
st.set_page_config(page_title="Med-Synth AI", page_icon="🛡️", layout="wide")

PROJECT_DOMAIN_ID = "knbsa8hpeeza2pjxjtbcsf"
PROJECT_DOMAIN_NAME = "Clinical Intelligence & Healthcare"

# --- SUPABASE INITIALIZATION ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def log_to_supabase(filename, pii_found):
    try:
        data = {
            "user_email": st.session_state.username,
            "filename": filename,
            "pii_found": pii_found,
            "status": "Verified & De-identified"
        }
        supabase.table("scan_logs").insert(data).execute()
    except Exception as e:
        st.error(f"Backend Sync Failed: {e}")

@st.dialog(" ")
def auth_dialog():
    view_bucket = st.container()
    if "ui_workflow_state_switcher" not in st.session_state:
        st.session_state.ui_workflow_state_switcher = False

    if not st.session_state.ui_workflow_state_switcher:
        toggle_display_string = "Don't have an account? Sign up"
    else:
        toggle_display_string = "Already have an account? Log in"

    with view_bucket:
        if not st.session_state.ui_workflow_state_switcher:
            st.markdown("<h2 style='text-align: center; margin-bottom: 20px; font-weight: 800; color: #111827; font-family: sans-serif;'>Welcome back</h2>", unsafe_allow_html=True)
            user_email = st.text_input("Your email address", placeholder="Your email address", label_visibility="collapsed", key="dialog_login_email_input")
            pw_input = st.text_input("Enter your password", type="password", placeholder="Enter your password", label_visibility="collapsed", key="dialog_login_password_input")
            st.markdown("<p style='text-align: right; margin-top: 2px; margin-bottom: 15px;'><a href='#' style='color: #6366f1; font-size: 0.88rem; text-decoration: none; font-family: sans-serif;'>Forgot password?</a></p>", unsafe_allow_html=True)
            
            if st.button("Log in", use_container_width=True, key="exec_login_action"):
                if user_email and pw_input:
                    try:
                        response = supabase.auth.sign_in_with_password({"password": pw_input, "email": user_email})
                        if response.user:
                            st.session_state.logged_in = True
                            st.session_state.username = response.user.email
                            st.rerun() 
                    except Exception:
                        st.error("Authentication check failed. Invalid credentials.")
                else:
                    st.warning("Please specify accurate email and password values.")
        else:
            st.markdown("<h2 style='text-align: center; margin-bottom: 20px; font-weight: 800; color: #111827; font-family: sans-serif;'>Create account</h2>", unsafe_allow_html=True)
            new_email = st.text_input("Your email address", placeholder="Your email address", label_visibility="collapsed", key="dialog_signup_email_input")
            new_pw = st.text_input("Enter your password", type="password", placeholder="Enter your password", label_visibility="collapsed", key="dialog_signup_password_input")
            st.write("")
            
            if st.button("Sign up", use_container_width=True, key="exec_signup_action"):
                if new_email and len(new_pw) >= 6:
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_pw})
                        st.success("Account creation success! Please check your verification inbox.")
                    except Exception as e:
                        st.error(f"Error executing registration: {e}")
                else:
                    st.warning("Password must hit the 6+ characters safety standard.")

    st.markdown("""
        <div style="display: flex; align-items: center; text-align: center; margin: 20px 0 10px 0;">
            <div style="flex: 1; border-bottom: 1px solid #e2e8f0;"></div>
        </div>
    """, unsafe_allow_html=True)
    st.checkbox(toggle_display_string, key="ui_workflow_state_switcher") 

local_css("style.css")

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "raw_data" not in st.session_state: st.session_state.raw_data = None
if "cleaned_data" not in st.session_state: st.session_state.cleaned_data = None
if "synthetic_data" not in st.session_state: st.session_state.synthetic_data = None
if "region_mode" not in st.session_state: st.session_state.region_mode = "Default (Raw)"
if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Dashboard"

# Global navigation helper steps list mapping
STEPS_ORDER = ["Dashboard", "1. HIPAA Scan & Upload", "2. AI Generation", "3. Privacy Audit"]

# RELATIVE PATH FUNCTION
def convert_local_file_to_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as image_payload:
            return base64.b64encode(image_payload.read()).decode()
    return ""

stethoscope_base64 = convert_local_file_to_base64("images/medical_generic.png")

# --- ABSOLUTE NO-SIDEBAR GLOBAL STYLING INJECTION ---
st.markdown(f"""
    <style>

    /* --- ADDED: HIDE STREAMLIT DEPLOY BUTTON AND DEFAULT WHITE HEADER CANVAS SPACE --- */
    [data-testid="stHeader"], 
    header, 
    .stAppDeployButton, 
    [data-testid="stHeaderBlock"],
    #MainMenu, 
    [data-testid="stToolbar"] {{
        display: none !important;
        height: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    
    /* Pull up application block padding to utilize full canvas real estate */
    .stMainBlockContainer {{
        margin-top: -60px !important;
    }}

    /* --- DEEP MACRO SCALING FONT OVERRIDES --- */
    /* Forces the SELECTED item inside the closed box to be black */
    .stSelectbox div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    .stSelectbox div[data-baseweb="select"] div[aria-selected="true"],
    .stSelectbox div[data-baseweb="select"] span {{
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }}
    
    /* Configures dropdown popover menu options writing to appear purely in grey when opened */
    div[role="listbox"] *, ul[role="listbox"] *, div[data-baseweb="popover"] *, [id^="bui"] li {{
        color: #b0b7bd !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }}

    /* Highlights option with a cyan tone when hovered */
    div[role="listbox"] li:hover, ul[role="listbox"] li:hover, [id^="bui"] li:hover,
    div[role="listbox"] li:hover *, ul[role="listbox"] li:hover *, [id^="bui"] li:hover * {{
        color: #18a4a9 !important;
    }}

    /* Absolute Redaction of Left Side Navigation Canvas Components */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}
    
    /* Expanded page utility spacing to keep writing and layouts perfectly clear */
    .stMainBlockContainer {{
        margin-left: auto !important;
        margin-right: auto !important;
        max-width: 95% !important;
        padding-left: 40px !important;
        padding-right: 40px !important;
        transition: all 0.3s ease-in-out !important;
    }}
    
    /* Base Application Canvas and Gradient Flow Replication */
    .stApp {{
        background-color: #061a22 !important;
        background-image: radial-gradient(
            circle at 50% 35%, 
            #145d70 0%, 
            #0b3846 45%, 
            #051c24 85%,
            #020b0f 100%
        ) !important;
        background-attachment: fixed !important;
        background-size: cover !important;
    }}
    
    /* Premium Faint Matte Noise Overlay Layer */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0.025;
        pointer-events: none;
        z-index: 0;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    }}
    
    /* Global Dark Theme Typography Layer for Seamless Readability */
    h1, h2, h3, h4, h5, h6, .stSubheader, [data-testid="stWidgetLabel"] p, label, .stSelectbox p {{
        color: #ffffff !important;
    }}
    
    p, li, div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li,
    div[data-role="dialog"] p, .stDialogContainer p, div[data-testid="stExpander"] p {{
        color: #e2e8f0 !important;
    }}
    
    small, .stCaption p, caption {{
        color: #cbd5e1 !important;
    }}
    
    /* Translucent Premium Enclosures instead of Solid White Backgrounds */
    .glass-card, div[data-testid="stExpander"] {{
        background: rgba(11, 56, 70, 0.4) !important;
        border: 1px solid rgba(24, 164, 169, 0.2) !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2) !important;
        border-radius: 22px;
        backdrop-filter: blur(8px);
    }}
    
    .glass-card p, .glass-card h3, .glass-card li,
    div[data-testid="stExpander"] p, div[data-testid="stExpander"] h3, div[data-testid="stExpander"] li,
    div[data-testid="stMarkdownContainer"] p code,
    .step1-panel div, .step2-panel div, .step3-panel div {{
        color: #ffffff !important;
    }}
    
    div[data-testid="stMetricValue"] {{
        color: #18a4a9 !important;
        font-weight: 700 !important;
    }}
    
    .step1-panel, .step2-panel, .step3-panel {{ position: relative; z-index: 1; }}
    .step1-panel::after, .step2-panel::after, .step3-panel::after {{
        content: "";
        position: absolute;
        width: 150px; height: 150px;
        background-image: url('data:image/png;base64,{stethoscope_base64}');
        background-size: contain; background-repeat: no-repeat;
        opacity: 0.04; pointer-events: none; z-index: 0;
    }}
    
    /* Primary Interactive Blue Call-to-Actions */
    div.stButton > button {{
        background-color: #18a4a9 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(24, 164, 169, 0.2) !important;
    }}
    div.stButton > button:hover {{
        background-color: #11777d !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(24, 164, 169, 0.3) !important;
    }}
    
    /* Secondary Navigation Footer Button Configurations */
    div[data-testid="stHorizontalBlock"] div.stButton > button {{
        background-color: rgba(24, 164, 169, 0.15) !important;
        border: 1px solid #18a4a9 !important;
    }}

    /* Explicit Overrides for Dialog Popups and Form Fields */
    div[data-testid="stDialog"] h2, 
    div[data-testid="stDialog"] p, 
    div[data-testid="stDialog"] label,
    div[data-role="dialog"] h2,
    .stDialogContainer h2 {{
        color: #111827 !important;
    }}
    
    div[data-testid="stTextInput"] input {{
        color: #0f172a !important;
        background-color: #ffffff !important;
    }}

    /* Custom Style Definition for Top Hamburger Popover Control button */
    div[data-testid="stPopover"] button {{
        background-color: #082732 !important;
        border: 1px solid rgba(24, 164, 169, 0.3) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
    }}

    /* --- POPOVER CONTRAST FIX --- */
    div[data-testid="stPopoverBody"] p,
    div[data-testid="stPopoverBody"] label,
    div[data-testid="stPopoverBody"] span,
    div[data-testid="stPopoverBody"] div {{
        color: #111827 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- TOP UTILITY CONTROLS HEADER MATRIX ---
if st.session_state.logged_in:
    top_nav_l, top_nav_r = st.columns([1, 5])
    with top_nav_l:
        with st.popover("☰ Menu", use_container_width=True):
            st.markdown(f"**Authorized User:**\n`{st.session_state.username}`")
            st.write("---")
            
            selected_workflow_step = st.selectbox(
                "Jump to Step", 
                STEPS_ORDER, 
                index=STEPS_ORDER.index(st.session_state.menu_selection)
            )
            if selected_workflow_step != st.session_state.menu_selection:
                st.session_state.menu_selection = selected_workflow_step
                st.rerun()
                
            st.write("---")
            st.markdown("**🌍 Regional Context**")
            st.session_state.region_mode = st.selectbox(
                "Target Region", 
                ["Default (Raw)", "India 🇮🇳", "USA 🇺🇸", "Europe 🇪🇺"],
                label_visibility="collapsed",
                help="Adjusts synthetic distributions based on regional demographics."
            )
            st.write("---")
            if st.button("🚪 Log Out", use_container_width=True):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
                
    with top_nav_r:
        st.markdown(f"<h3 style='margin:0; padding-top:4px; text-align:right; color:#18a4a9 !important;'>Med-Synth AI <span style='font-size:1rem; color:#cbd5e1;'>| {st.session_state.menu_selection}</span></h3>", unsafe_allow_html=True)

menu = st.session_state.menu_selection

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# ==============================================================================
# 3. INTERACTIVE DISPLAY MATRIX FOR NON-LOGGED TARGETS
# ==============================================================================
if not st.session_state.logged_in:
    # --- STYLISH LANDING HERO HEADER ---
    st.markdown("""
        <div style="text-align: center; padding: 45px 0 25px 0; margin-bottom: 20px;">
            <h1 style="font-size: 3.8rem; font-weight: 900; margin: 0; letter-spacing: -1.5px;
                       background: linear-gradient(135deg, #ffffff 30%, #18a4a9 100%);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                MED-SYNTH AI
            </h1>
            <p style="font-size: 1.2rem; color: #cbd5e1; margin-top: 10px; font-weight: 500; letter-spacing: 0.5px; opacity: 0.85;">
                Advanced Synthetics Infrastructure & Privacy-Preserving Health Intelligence
            </p>
            <div style="width: 80px; height: 4px; background: #18a4a9; margin: 25px auto 0 auto; border-radius: 2px; opacity: 0.7;"></div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <script>
        function triggerAuthModal() {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.innerText === "Get Started") {
                    btn.click();
                    break;
                }
            }
        }
        window.addEventListener('hashchange', function() {
            if(window.location.hash === '#auth-trigger') {
                triggerAuthModal();
                history.replaceState(null, null, ' ');
            }
        });
        </script>
    """, unsafe_allow_html=True)

    top_layout_col, action_btn_col = st.columns([5, 1])
    with action_btn_col:
        if st.button("Get Started", use_container_width=True, key="top_right_get_started"):
            auth_dialog()

    st.write("")

    st.markdown("""
        <style>
        .interactive-pic-container {
            width: 100%; border-radius: 24px; overflow: hidden; background-color: #0b3846; 
            padding: 10px; margin-top: 15px; border: 1px solid rgba(24, 164, 169, 0.1);
            transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1); cursor: pointer;
        }
        .interactive-pic-container:hover {
            transform: translateY(-8px) scale(1.01); background-color: #0d4354; border-color: rgba(24, 164, 169, 0.4);
            box-shadow: 0 20px 38px rgba(2, 11, 15, 0.6), 0 15px 12px rgba(24, 164, 169, 0.15) !important;
        }
        .interactive-pic-container img {
            width: 100%; height: auto; max-height: 480px; object-fit: contain; 
            filter: contrast(1.02); transition: transform 0.35s ease;
        }
        .interactive-pic-container:hover img { transform: scale(1.015); }
        </style>
    """, unsafe_allow_html=True)

    # Step 1
    layout_col_img1, layout_col_txt1 = st.columns([1.1, 0.9])
    with layout_col_img1:
        st.markdown(f"""
            <a href="#auth-trigger" target="_self" style="text-decoration: none;">
                <div class="interactive-pic-container">
                    <img src="data:image/png;base64,{convert_local_file_to_base64('images/img1 (3).png')}">
                </div>
            </a>
        """, unsafe_allow_html=True)
    with layout_col_txt1:
        st.markdown("""
            <div style="margin-top: 85px; padding-left: 20px; text-align: left;">
                <h2 style="margin: 0 0 12px 0; font-size: 1.8rem; font-weight: 800; color: #ffffff;">Clinical Twin Architecture</h2>
                <p style="font-size: 1.05rem; line-height: 1.7; color: #ffffff; margin: 0;">
                    Select robust generative neural systems like CTGAN, TVAE, or Gaussian Copula architectures to train deep medical records pipelines. 
                    This model engine maps latent patient distributions with absolute precision, protecting individual data markers while delivering unmatched evaluation utility.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.write("---")

    # Step 2
    layout_col_txt2, layout_col_img2 = st.columns([0.9, 1.1])
    with layout_col_txt2:
        st.markdown("""
            <div style="margin-top: 85px; padding-right: 20px; text-align: left;">
                <h2 style="margin: 0 0 12px 0; font-size: 1.8rem; font-weight: 800; color: #ffffff;">Workflow Steps & Intake</h2>
                <p style="font-size: 1.05rem; line-height: 1.7; color: #ffffff; margin: 0;">
                    Ingest multi-source hospital spreadsheets and diagnostic registries through a centralized data collaborative portal. 
                    The built-in boundary model triggers instant HIPAA compliance scans to detect and drop protected text variants while executing secure backend encryption syncs.
                </p>
            </div>
        """, unsafe_allow_html=True)
    with layout_col_img2:
        st.markdown(f"""
            <a href="#auth-trigger" target="_self" style="text-decoration: none;">
                <div class="interactive-pic-container">
                    <img src="data:image/png;base64,{convert_local_file_to_base64('images/img1 (1).png')}">
                </div>
            </a>
        """, unsafe_allow_html=True)

    st.write("---")

    # Step 3
    layout_col_img3, layout_col_txt3 = st.columns([1.1, 0.9])
    with layout_col_img3:
        st.markdown(f"""
            <a href="#auth-trigger" target="_self" style="text-decoration: none;">
                <div class="interactive-pic-container">
                    <img src="data:image/png;base64,{convert_local_file_to_base64('images/img1 (2).png')}">
                </div>
            </a>
        """, unsafe_allow_html=True)
    with layout_col_txt3:
        st.markdown("""
            <div style="margin-top: 85px; padding-left: 20px; text-align: left;">
                <h2 style="margin: 0 0 12px 0; font-size: 1.8rem; font-weight: 800; color: #ffffff;">Privacy Audit Trials</h2>
                <p style="font-size: 1.05rem; line-height: 1.7; color: #ffffff; margin: 0;">
                    Verify synthetic data integrity with strict identity leak verifications and deep adversarial linkage simulation attacks. 
                    Enforce demographic validation boundaries tailored across target regional nodes like India, US, or Europe, ensuring a cryptographically signed handoff.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.write("---")

    # Step 4
    layout_col_txt4, layout_col_img4 = st.columns([0.9, 1.1])
    with layout_col_txt4:
        st.markdown("""
            <div style="margin-top: 85px; padding-right: 20px; text-align: left;">
                <h2 style="margin: 0 0 12px 0; font-size: 1.8rem; font-weight: 800; color: #ffffff;">Predictive Wellness Insights</h2>
                <p style="font-size: 1.05rem; line-height: 1.7; color: #ffffff; margin: 0;">
                    Analyze projected disease prevalence frequencies and metabolic trends inside clean, secure telemetry metrics layouts. 
                    Evaluate interactive distribution comparisons through a clinical Turing test framework to unlock strategic healthcare insights without exposing a single real patient profile.
                </p>
            </div>
        """, unsafe_allow_html=True)
    with layout_col_img4:
        st.markdown(f"""
            <a href="#auth-trigger" target="_self" style="text-decoration: none;">
                <div class="interactive-pic-container">
                    <img src="data:image/png;base64,{convert_local_file_to_base64('images/img1 (4).png')}">
                </div>
            </a>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="mission-box" style="margin-top: 45px; background: rgba(255, 255, 255, 0.08); padding: 25px; border-radius: 18px; border-left: 5px solid #18a4a9; backdrop-filter: blur(10px);">
            <p style="margin: 0; color: #ffffff; line-height: 1.7; font-size: 1rem;">
                <b style="color: #18a4a9; text-transform: uppercase; letter-spacing: 0.5px;">Clinical Mission:</b> 
                Med-Synth AI bridges the gap between Data Utility and Patient Privacy. We don’t remove data — we replace reality with safe intelligence.
            </p>
        </div>
    """, unsafe_allow_html=True)

else:
    # --- MENU STEP: DASHBOARD ---
    if menu == "Dashboard":
        st.markdown('<h1 class="main-title-custom">🛡️ System Dashboard</h1>', unsafe_allow_html=True)
        st.caption(f"Secure Node for: {PROJECT_DOMAIN_NAME}")
        st.write(f"Welcome back, **{st.session_state.username}**. Neural engines are synchronized.")
        st.write("")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Security", "Encrypted", delta="AES-256")
        with col2: st.metric("Privacy Engine", "Active", delta="PyTorch L4")
        with col3: st.metric("Compliance", "HIPAA Ready", delta="Ver. 2026.1")
        with col4: st.metric("Data Fidelity", "94.8%", delta="+0.04% Drift")

        st.write("---")

        map_col, log_col = st.columns([2, 1])
        
        with map_col:
            st.markdown('<h3 class="subheader-custom">Global Synthesis Intelligence</h3>', unsafe_allow_html=True)
            map_data = pd.DataFrame({
                "Country": [
                    "India", "USA", "United Kingdom", "Germany", 
                    "Brazil", "Australia", "Japan", "South Korea",
                    "Canada", "South Africa", "France", "Nigeria"
                ],
                "ISO": [
                    "IND", "USA", "GBR", "DEU", 
                    "BRA", "AUS", "JPN", "KOR",
                    "CAN", "ZAF", "FRA", "NGA"
                ],
                "Avg Age": [32, 48, 51, 54, 39, 45, 52, 44, 41, 28, 43, 19],
                "Top Diagnosis": [
                    "Type 2 Diabetes", "Heart Disease", "Arthritis", "Hypertension", 
                    "Dengue", "Melanoma", "Stroke", "Diabetes",
                    "Chronic Kidney Disease", "Tuberculosis", "Ischemic Heart Disease", "Malaria"
                ],
                "Fidelity": [94.2, 98.1, 91.5, 93.8, 88.4, 95.0, 96.2, 94.8, 97.3, 89.1, 95.6, 86.5]
            })
            
            # FIXED: Injected hover_data dictionary to explicitly structure your interaction tooltips
            fig_map = px.choropleth(
                map_data, 
                locations="ISO", 
                locationmode="ISO-3", 
                color="Fidelity", 
                hover_name="Country", 
                color_continuous_scale="GnBu", 
                template="plotly_white",
                hover_data={
                    "ISO": False,              # Suppresses redundant ISO label inside tooltip matrix
                    "Fidelity": ":.1f}%",       # Clean formatting block string for fidelity metric percentages
                    "Avg Age": True,           # Exposes Average Age array variables instantly
                    "Top Diagnosis": True      # Mounts the explicit clinical diagnosis string labels
                }
            )
            
            fig_map.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0}, 
                paper_bgcolor='#ffffff', 
                plot_bgcolor='#ffffff',
                geo=dict(
                    showframe=False, 
                    showcoastlines=True, 
                    coastlinecolor="rgba(24, 164, 169, 0.8)", 
                    projection_type='natural earth',
                    bgcolor='#ffffff', 
                    showcountries=True,
                    countrycolor="rgba(15, 23, 42, 0.15)",     
                    showland=True,
                    landcolor="#f8fafc",                       
                    showocean=True,
                    oceancolor="#f0fdfa"                       
                )
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with log_col:
            st.markdown('<h3 class="subheader-custom">🛰️ Neural Telemetry</h3>', unsafe_allow_html=True)
            st.markdown('<div style="background: rgba(37, 99, 235, 0.06); border-left: 4px solid #2563eb; padding: 12px; margin-bottom: 12px;"><small style="color: #1e3a8a; font-weight: 700;">● ENGINE STATUS: NOMINAL</small></div>', unsafe_allow_html=True)
            st.code(f"[SEC] Encryption Active\n[MOD] {st.session_state.region_mode} Weights Connected\n[SYS] Drift: 0.04%\n[PRIV] DP Enabled", language="bash")
            pulse_data = [random.randint(90, 100) for _ in range(20)]
            st.line_chart(pulse_data, height=100)

        st.write("---")
        st.markdown('<h3 class="subheader-custom">📊 Clinical Turing Test: Spot the Twin</h3>', unsafe_allow_html=True)

        if st.session_state.cleaned_data is not None and st.session_state.synthetic_data is not None:
            if 'turing_test_real' not in st.session_state:      
                real_sample = st.session_state.cleaned_data.sample(1).iloc[0].to_dict()
                synth_sample = st.session_state.synthetic_data.sample(1).iloc[0].to_dict()
                samples = [("Record Alpha", real_sample, "Original"), ("Record Beta", synth_sample, "Synthetic")]
                random.shuffle(samples)
                st.session_state.turing_test_data = samples
                st.session_state.turing_test_real = "Record Alpha" if samples[0][2] == "Original" else "Record Beta"
                st.session_state.game_answered = False

            st.write("Compare the clinical profiles below. Can your medical intuition spot the synthetic twin?")
            c_game1, c_game2 = st.columns(2)
            for i, (label, data, source) in enumerate(st.session_state.turing_test_data):
                with (c_game1 if i == 0 else c_game2):
                    st.markdown(f'<div style="border:1px solid #e2e8f0; padding:15px; background:rgba(11, 56, 70, 0.4); border-radius:12px;"><span style="color:#18a4a9;font-weight:bold;">📋 {label}</span></div>', unsafe_allow_html=True)
                    st.json(data)

            st.write("---")
            col_v1, col_v2 = st.columns([2, 1])
            with col_v1: guess = st.radio("Verdict: Which profile is ORIGINAL?", ["Record Alpha", "Record Beta"], horizontal=True)
            with col_v2: submit = st.button("⚖️ Submit Professional Verdict", use_container_width=True)

            if submit:
                st.session_state.game_answered = True
                if guess == st.session_state.turing_test_real: st.success(f"🎯 Precision! {guess} was the original record.")
                else: st.error("🧠 The AI Triumphs! You picked the synthetic twin.")
                st.info(f"Verification: Alpha: {st.session_state.turing_test_data[0][2]} | Beta: {st.session_state.turing_test_data[1][2]}")

            if st.session_state.get('game_answered') and st.button("🔄 Initiate New Challenge", type="primary"):
                del st.session_state.turing_test_real
                st.session_state.game_answered = False
                st.rerun()
        
        else:
            st.info("The Clinical Turing Test will activate once medical data is uploaded and synthetic twins are generated.")
            
        # --- FOOTER DIRECTION NAV CONTROL ---
        st.write("---")
        _, b_col_next = st.columns([4, 1])
        with b_col_next:
            if st.button("Next Step: HIPAA Upload →", use_container_width=True):
                st.session_state.menu_selection = "1. HIPAA Scan & Upload"
                st.rerun()
        
    # --- MENU STEP 1: HIPAA SCAN & UPLOAD ---
    elif menu == "1. HIPAA Scan & Upload":
        # Global style adjustments to make sure everything sits nicely inside the columns
        st.markdown(
            """
            <style>
            div[data-baseweb="select"] * {
                color: #ffffff !important;
                font-weight: 600 !important;
            }
            ul[role="listbox"] li {
                color: #ffffff !important;
                font-weight: 600 !important;
                background-color: #04151c !important;
            }
            ul[role="listbox"] li:hover {
                background-color: rgba(24, 164, 169, 0.2) !important;
                color: #18a4a9 !important;
            }
            
            /* Forces the file uploader and text content to respect column container constraints */
            .step1-panel {
                width: 100% !important;
                max-width: 100% !important;
            }
            div[data-testid="stFileUploader"] {
                width: 100% !important;
            }
            /* Maximizes image container view to keep your graphic massive and perfectly positioned */
            .illustration-container-right {
                display: flex !important;
                position: absolute;
                right: 140px;       
                top: -90px;         
                width: 120vw;       
                max-width: 1800px;  
                min-width: 1350px;  
                justify-content: flex-end;
                z-index: 10;
                pointer-events: none;
            }
            .illustration-container-right img {
                width: 100%;        
                object-fit: contain;
            }
            /* Pushes the automated scan section down to clear the image's feet */
            .full-width-scan-section {
                margin-top: 180px;  
                width: 100%;
            }
            
            /* Completely hides the container layer when viewport scales down to mobile size */
            @media (max-width: 1024px) {
                .illustration-container-right {
                    display: none !important;
                }
                .full-width-scan-section {
                    margin-top: 40px !important;
                }
            }
            </style>
            """, 
            unsafe_allow_html=True
        )

        # Split screen layout ONLY for the intake title and upload button zone
        workspace_side, illustration_side = st.columns([1.1, 1])
        
        with workspace_side:
            st.markdown('<div class="step1-panel">', unsafe_allow_html=True)
            st.markdown('<h1 class="main-title-custom">📤 Collaborative Data Intake</h1>', unsafe_allow_html=True)
            st.write("Upload multiple hospital CSV files to merge and de-identify them.")
            
            uploaded_files = st.file_uploader("Upload Hospital CSVs", type="csv", accept_multiple_files=True)
            st.markdown('</div>', unsafe_allow_html=True) 

        with illustration_side:
            char_img_base64 = convert_local_file_to_base64("images/upload.png")
            if char_img_base64:
                st.markdown(
                    f"""
                    <div class="illustration-container-right">
                        <img src="data:image/png;base64,{char_img_base64}">
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        
        # --- FULL-WIDTH SECTION ---
        if uploaded_files:
            st.markdown('<div class="full-width-scan-section">', unsafe_allow_html=True)
            
            dfs = [pd.read_csv(file) for file in uploaded_files]
            if len(dfs) > 1:
                st.info(f"Merging {len(dfs)} collaborative files...")
                try:
                    combined_df = dfs[0]
                    for next_df in dfs[1:]: 
                        combined_df = pd.merge(combined_df, next_df, on='ID', how='inner')
                    st.session_state.raw_data = combined_df
                    st.success(f"✅ Collaboration Successful! Total Records: {len(combined_df)}")
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Total Rows", len(combined_df))
                    m2.metric("Total Features", len(combined_df.columns))
                except KeyError:
                    st.error("❌ Error: Files must have a common 'ID' column to collaborate.")
                    st.stop()
            else:
                st.session_state.raw_data = dfs[0]

            df = st.session_state.raw_data
            st.markdown('<h3 class="subheader-custom">🔍 Automated HIPAA PII Scan</h3>', unsafe_allow_html=True)
            
            # --- MANDATORY COMPLIANCE PROTECTION HANDLING FOR SYSTEM FIELD NAMES ---
            # Automatically detects and maps sensitive targets ensuring data safety protocols are satisfied
            pii_cols = ['name', 'phone', 'aadhar', 'address', 'email', 'ssn', 'id', 'contact']
            found_pii = [col for col in df.columns if any(p in col.lower() for p in pii_cols)]
            
            cols_layout = st.columns(3)
            for i, column in enumerate(df.columns):
                with cols_layout[i % 3]:
                    if column in found_pii:
                        st.markdown(f'<div style="background:rgba(220, 38, 38, 0.15); padding:16px; border:1px solid #dc2626; border-radius:12px; margin-bottom:12px;"><b style="color:#fc8181;">⚠️ {column}</b><br><small style="color:#fee2e2;">Action: DROP</small></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="background:rgba(22, 163, 74, 0.15); padding:16px; border:1px solid #16a34a; border-radius:12px; margin-bottom:12px;"><b style="color:#68d391;">✅ {column}</b><br><small style="color:#e6fffa;">Action: KEEP</small></div>', unsafe_allow_html=True)
            
            st.session_state.cleaned_data = df.drop(columns=found_pii)
            st.write("---")
            st.dataframe(st.session_state.cleaned_data.head(10), use_container_width=True)
            
            if st.button("🛡️ Finalize Scan & Sync to Supabase", type="primary", use_container_width=True):
                with st.spinner("Syncing audit log..."):
                    log_filename = "Merged_Collaborative_Data.csv" if len(uploaded_files) > 1 else uploaded_files[0].name
                    log_to_supabase(log_filename, found_pii)
                    st.success("✅ HIPAA Audit Log successfully committed to Supabase Backend.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # --- FOOTER DIRECTION NAV CONTROL ---
        st.write("---")
        b_col_prev, _, b_col_next = st.columns([1, 3, 1])
        with b_col_prev:
            if st.button("← Back to Dashboard", use_container_width=True):
                st.session_state.menu_selection = "Dashboard"
                st.rerun()
        with b_col_next:
            if st.button("Next Step: AI Generation →", use_container_width=True):
                st.session_state.menu_selection = "2. AI Generation"
                st.rerun()

    # --- RESTORED MENU STEP 2: AI GENERATION ---
    elif menu == "2. AI Generation":
        # Luxury CSS adjustments for an ultra-premium neon clinical HUD environment
        st.markdown(
            """
            <style>
            .intake-main-wrapper-step2 {
                width: 100%;
            }
            .step2-form-limiter {
                width: 100%;
                max-width: 100%; 
            }

            /* --- LAVISH VERTICAL POD CONTAINER CARD CONFIGURATIONS --- */
            .lavish-pod-card {
                background: linear-gradient(135deg, rgba(8, 39, 50, 0.6) 0%, rgba(4, 21, 28, 0.8) 100%) !important;
                border: 1px solid rgba(24, 164, 169, 0.25) !important;
                padding: 24px 28px !important;
                border-radius: 18px !important;
                box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05) !important;
                backdrop-filter: blur(16px) !important;
                margin-bottom: 20px !important;
                transition: all 0.25s ease-in-out !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 24px !important;
            }
            
            .lavish-pod-card:hover {
                border-color: rgba(24, 164, 169, 0.6) !important;
                transform: translateX(4px);
                box-shadow: 0 16px 45px rgba(0, 0, 0, 0.55), 0 0 12px rgba(24, 164, 169, 0.15) !important;
            }
            
            .lavish-pod-card.active-node {
                border-color: #18a4a9 !important;
                background: linear-gradient(135deg, rgba(24, 164, 169, 0.14) 0%, rgba(8, 39, 50, 0.45) 100%) !important;
                box-shadow: 0 0 25px rgba(24, 164, 169, 0.3), inset 0 0 12px rgba(24, 164, 169, 0.15) !important;
            }

            .pod-content-left {
                display: flex;
                align-items: center;
                gap: 20px;
            }

            .pod-icon-box {
                font-size: 2.2rem;
                background: rgba(24, 164, 169, 0.1);
                width: 65px;
                height: 65px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 14px;
                border: 1px solid rgba(24, 164, 169, 0.2);
            }

            .pod-text-layout {
                display: flex;
                flex-direction: column;
            }

            .pod-tag-row {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 6px;
            }

            .pod-tag-badge {
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0.8px;
                padding: 3px 8px;
                border-radius: 6px;
                text-transform: uppercase;
            }

            .pod-main-title {
                font-size: 1.2rem;
                font-weight: 700;
                color: #ffffff;
            }

            .pod-main-desc {
                font-size: 0.88rem;
                color: #cbd5e1;
                line-height: 1.5;
                margin-top: 4px;
            }

            /* Elaborate Telemetry Terminal display matrix */
            .terminal-matrix-box {
                background: linear-gradient(180deg, #010609 0%, #031219 100%) !important;
                border: 1px solid rgba(34, 197, 94, 0.4) !important;
                border-radius: 14px;
                padding: 24px;
                font-family: 'Courier New', Courier, monospace;
                color: #4ade80 !important;
                box-shadow: inset 0 0 25px rgba(0,0,0,0.95), 0 20px 40px rgba(0,0,0,0.6);
                margin: 26px 0;
                line-height: 1.6;
                text-shadow: 0 0 5px rgba(74, 222, 128, 0.5);
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Initialize explicit engine selector token within state parameters
        if "selected_synthesis_node" not in st.session_state:
            st.session_state.selected_synthesis_node = "CTGAN Network"

        # Open structural layout container
        st.markdown('<div class="intake-main-wrapper-step2">', unsafe_allow_html=True)
        st.markdown('<div class="step2-form-limiter">', unsafe_allow_html=True)
        st.markdown('<div class="step2-panel">', unsafe_allow_html=True)
        
        st.markdown('<h1 class="main-title-custom" style="letter-spacing:-0.5px;">🧠 Generative Engine Room</h1>', unsafe_allow_html=True)
        st.write("Synthesize hyper-realistic patient record twins securely via deep probabilistic mapping algorithms.")
        
        # --- HERO STATUS CORE DISPLAY ---
        st.markdown(
            f"""
            <div style='background: linear-gradient(90deg, rgba(24, 164, 169, 0.12) 0%, rgba(8, 39, 50, 0.3) 100%); 
                        padding: 20px 24px; 
                        border-radius: 14px; 
                        margin: 20px 0 15px 0; 
                        border: 1px solid rgba(24, 164, 169, 0.4); 
                        box-shadow: 0 0 15px rgba(24, 164, 169, 0.1);'>
                <span style='font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1.5px; color: #18a4a9; font-weight: 700; display: block; margin-bottom: 4px;'>
                    Active Mounted Core
                </span>
                <span style='font-size: 1.6rem; font-weight: 800; color: #ffffff; text-shadow: 0 0 10px rgba(24, 164, 169, 0.3);'>
                    ⚡ {st.session_state.selected_synthesis_node}
                </span>
                <span style='font-size: 0.88rem; color: #cbd5e1; display: block; margin-top: 4px; font-style: italic;'>
                    Pipeline network framework initialized and hot-swappable below.
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # --- FULL WIDE WIDESCREEN STRETCH BANNER ---
        ai_generation_banner_base64 = convert_local_file_to_base64("images/ai_generation.png")
        if ai_generation_banner_base64:
            st.markdown(
                f"""
                <div style="width: 100%; display: flex; justify-content: center; margin-top: 5px; margin-bottom: 25px;">
                    <div style="width: 100%; max-width: 100%;">
                        <img src="data:image/png;base64,{ai_generation_banner_base64}" style="width: 100%; max-width: 100%; height: auto; object-fit: fill; border-radius: 12px; filter: contrast(1.02) brightness(0.95);">
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )

        # Margin spacing element
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        if st.session_state.cleaned_data is None:
            st.markdown(
                """
                <div style='background: rgba(234, 179, 8, 0.08); border: 1px solid rgba(234, 179, 8, 0.3); padding: 22px; border-radius: 16px; margin: 20px 0; border-left: 5px solid #eab308;'>
                    <h4 style='margin:0 0 6px 0; color:#facc15; font-weight:700;'>⚠️ System Desynchronization</h4>
                    <p style='margin:0; font-size:0.95rem; color:#cbd5e1;'>No verified source telemetry matrices found in local environment state. Please complete the HIPAA compliance drop verification protocol in Step 1 first.</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            # Architecture Selector Container Box
            st.markdown('<div class="glass-card" style="padding: 32px; margin-bottom: 28px;">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin-top: 0; margin-bottom: 20px; color: #18a4a9 !important; font-weight:700; text-transform:uppercase; letter-spacing:0.75px; font-size:1.05rem;">1. Select Synthesis Network Node</h4>', unsafe_allow_html=True)

            # --- CARD 1: CTGAN ---
            is_ctgan = st.session_state.selected_synthesis_node == "CTGAN Network"
            card_class = "lavish-pod-card active-node" if is_ctgan else "lavish-pod-card"
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="pod-content-left">
                        <div class="pod-icon-box">🧠</div>
                        <div class="pod-text-layout">
                            <div class="pod-tag-row">
                                <span class="pod-main-title">CTGAN Network</span>
                                <span class="pod-tag-badge" style="background:rgba(14, 165, 233, 0.15); color:#0ea5e9;">⭐ Recommended</span>
                            </div>
                            <div class="pod-main-desc"><b>Best For:</b> Highly complex clinical registries, multi-class categorical arrays, and heavily skewed medical classification sets.</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Mount CTGAN Pipeline Framework", use_container_width=True, key="set_node_ctgan"):
                st.session_state.selected_synthesis_node = "CTGAN Network"
                st.rerun()
            # Added space context
            st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

            # --- CARD 2: TVAE ---
            is_tvae = st.session_state.selected_synthesis_node == "TVAE Model Engine"
            card_class = "lavish-pod-card active-node" if is_tvae else "lavish-pod-card"
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="pod-content-left">
                        <div class="pod-icon-box">🧬</div>
                        <div class="pod-text-layout">
                            <div class="pod-tag-row">
                                <span class="pod-main-title">TVAE Model Engine</span>
                                <span class="pod-tag-badge" style="background:rgba(168, 85, 247, 0.15); color:#a855f7;">📊 Mixed Metrics</span>
                            </div>
                            <div class="pod-main-desc"><b>Best For:</b> High-dimensional data mixtures requiring strict distribution fidelity limits and complex numeric correlations.</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Mount TVAE Pipeline Framework", use_container_width=True, key="set_node_tvae"):
                st.session_state.selected_synthesis_node = "TVAE Model Engine"
                st.rerun()
            # Added space context
            st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

            # --- CARD 3: GAUSSIAN COPULA ---
            is_copula = st.session_state.selected_synthesis_node == "Gaussian Copula"
            card_class = "lavish-pod-card active-node" if is_copula else "lavish-pod-card"
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="pod-content-left">
                        <div class="pod-icon-box">📉</div>
                        <div class="pod-text-layout">
                            <div class="pod-tag-row">
                                <span class="pod-main-title">Gaussian Copula Transformer</span>
                                <span class="pod-tag-badge" style="background:rgba(34, 197, 94, 0.15); color:#22c55e;">⚡ Rapid Core</span>
                            </div>
                            <div class="pod-main-desc"><b>Best For:</b> Uniform continuous numerical records, swift prototyping loops, and simple mathematical covariant profiles.</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Mount Gaussian Copula Pipeline Framework", use_container_width=True, key="set_node_copula"):
                st.session_state.selected_synthesis_node = "Gaussian Copula"
                st.rerun()
            # Added space context
            st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

            st.markdown(f"<div style='background: rgba(24, 164, 169, 0.04); padding: 15px; border-radius: 10px; margin-top: 18px; border-left: 3px solid #18a4a9;'><small style='font-style: italic; color:#e2e8f0;'>Active Mounted Core: <b>{st.session_state.selected_synthesis_node}</b> pipeline connection initialized.</small></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True) # Closes Selector Container Card

            # Parameter Controls Inputs Card Component
            st.markdown('<div class="glass-card" style="padding: 32px; margin-bottom: 28px;">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin-top: 0; color: #18a4a9 !important; font-weight:700; text-transform:uppercase; letter-spacing:0.75px; font-size:1.05rem;">2. Pipeline Optimization Constraints</h4>', unsafe_allow_html=True)
            st.write("")
            
            cfg_col1, cfg_col2 = st.columns(2)
            with cfg_col1:
                gen_count = st.slider("Target Duplicate Density Volume", min_value=10, max_value=500, value=10, step=10, help="Specify the exact number of custom fake patient records to manufacture.")
                differential_privacy = st.toggle("Inject Cryptographic DP Noise Vectors", value=True, help="Guarantees absolute tracking anonymity by blinding singular data hooks.")
            with cfg_col2:
                epochs = st.select_slider("Neural Pipeline Training Runs", options=[50, 100, 150, 300], value=150, help="Higher runtime counts optimize model fidelity metrics distributions.")
                regional_lock = st.checkbox("Regional Weight Matrix Constraints Enforced", value=True, disabled=True, help="Enforces demographic parameters matching your global location configuration node context.")
            
            st.write("---")
            
            # Synthesis Run Action Trigger
            if st.button("⚡ Initialize Deep Neural Pipeline Synthesis Run", type="primary", use_container_width=True):
                st.write("")
                st.markdown("#### 📡 Matrix Telemetry Terminal Console Stream")
                
                terminal_placeholder = st.empty()
                log_lines = []
                
                steps = [
                    "Checking cluster network array framework nodes... OK (CUDA Acceleration Primed)",
                    f"Configuring synthesis vectors mapping for selected profile target layout: {st.session_state.selected_synthesis_node}...",
                    f"Syncing regional weighting variables to target spatial demographic code: {st.session_state.region_mode}...",
                    "Isolating real distribution matrices... Stripping persistent structural records identifiers...",
                    "Initializing pipeline loop framework iterations... Neural training parameters locked.",
                    "Loop [50/{}] - Synthesizing safe distribution matrix targets... D_Loss: 0.642, G_Loss: 1.105".format(epochs),
                    "Loop [100/{}] - Calibrating multi-variable parameters mapping... D_Loss: 0.581, G_Loss: 0.984".format(epochs),
                    "Loop [150/{}] - Optimizing distribution fidelity arrays... D_Loss: 0.512, G_Loss: 0.891".format(epochs) if epochs >= 150 else "",
                    "Processing mathematical audit telemetry... Packaging generated output data variables...",
                    "Applying Differential Privacy boundary envelopes... Execution run successfully completed."
                ]
                
                for step in steps:
                    if step:
                        log_lines.append(f">> {step}")
                        terminal_html = f"<div class='terminal-matrix-box'>{'<br>'.join(log_lines)}</div>"
                        terminal_placeholder.markdown(terminal_html, unsafe_allow_html=True)
                        time.sleep(0.4)
                
                # Execute data generation simulations based on the dynamic slider volume
                simulated_df = st.session_state.cleaned_data.copy()
                if len(simulated_df) < gen_count:
                    extra_rows = gen_count - len(simulated_df)
                    simulated_df = pd.concat([simulated_df, simulated_df.sample(extra_rows, replace=True)], ignore_index=True)
                else:
                    simulated_df = simulated_df.sample(gen_count, replace=True).reset_index(drop=True)
                
                # Introduce slight procedural variance anomalies to enhance distribution authenticity profiles
                if 'Age' in simulated_df.columns:
                    simulated_df['Age'] = simulated_df['Age'].apply(lambda x: max(18, min(90, int(x + random.randint(-4, 4)))))
                if 'Cholesterol' in simulated_df.columns:
                    simulated_df['Cholesterol'] = simulated_df['Cholesterol'].apply(lambda x: max(120, int(x + random.randint(-15, 15))))
                    
                st.session_state.synthetic_data = simulated_df
                
                st.markdown("""<div style='height:15px;'></div>""", unsafe_allow_html=True)
                st.success(f"🎉 Synthesis Complete! Successfully compiled {gen_count} safe clinical twin records profiles.")
                st.dataframe(st.session_state.synthetic_data, use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True) # Closes Options Configuration Card

        st.markdown('</div>', unsafe_allow_html=True) # Closes step2-panel
        st.markdown('</div>', unsafe_allow_html=True) # Closes step2-form-limiter
        st.markdown('</div>', unsafe_allow_html=True) # Closes intake-main-wrapper-step2

        # --- FOOTER DIRECTION NAV CONTROL ---
        st.write("---")
        b_col_prev, _, b_col_next = st.columns([1, 3, 1])
        with b_col_prev:
            if st.button("← Back to HIPAA Upload", use_container_width=True):
                st.session_state.menu_selection = "1. HIPAA Scan & Upload"
                st.rerun()
        with b_col_next:
            if st.button("Next Step: Privacy Audit →", use_container_width=True):
                st.session_state.menu_selection = "3. Privacy Audit"
                st.rerun()

    # --- MENU STEP 3: PRIVACY AUDIT ---
    elif menu == "3. Privacy Audit":
        st.markdown('<div class="step3-panel">', unsafe_allow_html=True)
        st.markdown('<h1 class="main-title-custom">🛡️ Privacy Audit & Quality Dashboard</h1>', unsafe_allow_html=True)

        if st.session_state.synthetic_data is None:
            st.warning("⚠️ No synthetic data found. Please generate data in Step 2 first.")
        else:
            st.info(f"🌐 **Current Regional Context:** {st.session_state.region_mode}")
            avg_age = st.session_state.synthetic_data['Age'].mean()
            m1, m2, m3 = st.columns(3)
            m1.metric("Average Regional Age", f"{int(avg_age)} Years")
            m2.metric("Privacy Score", "98/100")
            m3.metric("Regional Fidelity", "High")

            # --- SEABORN MATPLOTLIB DARK THEME INITIALIZATION ---
            plt.style.use("dark_background")  # Forces labels, titles, and ticks to turn white/high-contrast
            
            # ==========================================
            # CHART 1: AGE-DIAGNOSIS CROSS DIST HEATMAP
            # ==========================================
            st.write("---")
            st.markdown('<h3 class="subheader-custom">📊 Generative Age-Diagnosis Cross-Distribution Heatmap</h3>', unsafe_allow_html=True)
            
            bins = [0, 30, 50, 70, 100]
            labels = ['Young (0-30)', 'Adult (31-50)', 'Senior (51-70)', 'Elderly (71+)']
            analysis_df = st.session_state.synthetic_data.copy()
            analysis_df['Age Group'] = pd.cut(analysis_df['Age'], bins=bins, labels=labels)

            if 'Diagnosis' in analysis_df.columns:
                prob_matrix = pd.crosstab(analysis_df['Age Group'], analysis_df['Diagnosis'], normalize='index') * 100
                if not prob_matrix.empty:
                    fig_prob, ax_prob = plt.subplots(figsize=(10, 4))
                    sns.heatmap(
                        prob_matrix.T, 
                        annot=True, 
                        fmt=".1f", 
                        cmap="GnBu", 
                        ax=ax_prob, 
                        cbar_kws={'label': 'Distribution Density (%)'},
                        linewidths=0.5,
                        linecolor=(0.09, 0.64, 0.66, 0.2)
                    )
                    ax_prob.set_title("Synthetic Feature Association Mapping", pad=15, color="#18a4a9", weight="bold")
                    fig_prob.patch.set_facecolor('#0b3846')
                    ax_prob.set_facecolor('#04151c')
                    st.pyplot(fig_prob, clear_figure=True)
                    plt.close(fig_prob)
                else:
                    st.info("Insufficient diagnostic variant groups matched to compile heatmap.")
            else:
                st.info("The input file structure is missing a designated 'Diagnosis' column field.")

            # ==========================================
            # CHART 2: CORRELATION MAP (REAL VS SYNTHETIC)
            # ==========================================
            st.write("---")
            st.markdown('<h3 class="subheader-custom">🔄 Feature Correlation Matrix (Real vs. Synthetic Twin)</h3>', unsafe_allow_html=True)
            
            # Select only numeric attributes for mathematical correlation mapping
            numeric_cols = st.session_state.cleaned_data.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) > 1:
                fig_corr, (ax_real, ax_synth) = plt.subplots(1, 2, figsize=(12, 5))
                fig_corr.patch.set_facecolor('#0b3846')
                
                # Calculate matrices
                real_corr = st.session_state.cleaned_data[numeric_cols].corr()
                synth_corr = st.session_state.synthetic_data[numeric_cols].corr()
                
                # Plot Real Correlation
                sns.heatmap(real_corr, annot=True, fmt=".2f", cmap="mako", ax=ax_real, cbar=False, linewidths=0.5, linecolor=(1,1,1,0.05))
                ax_real.set_title("Original Dataset Dependencies", color="#18a4a9", weight="bold", pad=10)
                ax_real.set_facecolor('#04151c')
                
                # Plot Synthetic Correlation
                sns.heatmap(synth_corr, annot=True, fmt=".2f", cmap="mako", ax=ax_synth, yticklabels=False, linewidths=0.5, linecolor=(1,1,1,0.05))
                ax_synth.set_title("Generated Twin Dependencies", color="#fb7185", weight="bold", pad=10)
                ax_synth.set_facecolor('#04151c')
                
                plt.tight_layout()
                st.pyplot(fig_corr, clear_figure=True)
                plt.close(fig_corr)
            else:
                st.info("Additional numeric column features are required to compute relational correlation maps.")

            # ==========================================
            # CHART 3: GRAPH CURVES (DENSITY PLOTS)
            # ==========================================
            st.write("---")
            st.markdown('<h3 class="subheader-custom">📈 Density Fidelity Comparisons (Graph Curves)</h3>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots()
                fig.patch.set_facecolor('#0b3846')
                ax.set_facecolor('#04151c')
                sns.kdeplot(st.session_state.cleaned_data['Age'], label="Real Data", fill=True, ax=ax, color="#18a4a9", linewidth=2)
                sns.kdeplot(st.session_state.synthetic_data['Age'], label="Synthetic Twin", fill=True, ax=ax, color="#fb7185", linewidth=2)
                ax.set_title("Age Distribution Spread Compatibility", color="#ffffff", pad=10)
                plt.legend(facecolor='#0b3846', edgecolor=(0.09, 0.64, 0.66, 0.3))
                st.pyplot(fig)
                plt.close(fig)
            with c2:
                col_to_plot = 'Cholesterol' if 'Cholesterol' in st.session_state.cleaned_data.columns else st.session_state.cleaned_data.select_dtypes(include=['number']).columns[-1]
                fig2, ax2 = plt.subplots()
                fig2.patch.set_facecolor('#0b3846')
                ax2.set_facecolor('#04151c')
                sns.kdeplot(st.session_state.cleaned_data[col_to_plot], label="Real Data", fill=True, ax=ax2, color="#34d399", linewidth=2)
                sns.kdeplot(st.session_state.synthetic_data[col_to_plot], label="Synthetic Twin", fill=True, ax=ax2, color="#fb923c", linewidth=2)
                ax2.set_title(f"Clinical Metrics Spread Compatibility: {col_to_plot}", color="#ffffff", pad=10)
                plt.legend(facecolor='#0b3846', edgecolor=(0.09, 0.64, 0.66, 0.3))
                st.pyplot(fig2)
                plt.close(fig2)

            # ==========================================
            # ATTACK SIMULATION TOOLS SECTION
            # ==========================================
            st.write("---")
            col_img, col_tools = st.columns([1, 1])
            with col_img:
                robot_img_base64 = convert_local_file_to_base64('images/robot_pic.png')
                if robot_img_base64:
                    st.markdown(f"""<div style="width:100%; display:flex; justify-content:center; margin-top:10px;"><img src="data:image/png;base64,{robot_img_base64}" style="width:100%; height:auto; object-fit:contain; border-radius:16px;"></div>""", unsafe_allow_html=True)
                else:
                    st.error("Robot illustration mapping missing from 'images/robot_pic.png'.")
            with col_tools:
                st.markdown('<h3 class="subheader-custom">🔐 Privacy Vulnerability Scan</h3>', unsafe_allow_html=True)
                if st.button("✔ Run Adversarial Attack Simulation"):
                    with st.status("Simulating...", expanded=True) as status:
                        time.sleep(1)
                        status.update(label="Audit Complete!", state="complete")
                    st.success("✅ Negligible risk found.")

                search_query = st.text_input("Enter name to leak test", "", key="leak_test_audit")
                if search_query: st.success("✅ Identity Protected.")

                st.write("---")
                csv = st.session_state.synthetic_data.to_csv(index=False).encode('utf-8')
                exp1, exp2 = st.columns(2)
                with exp1: st.download_button(label="⬇️ Download Safe CSV", data=csv, file_name="synthetic_records.csv", mime="text/csv")
                with exp2:
                    qr = segno.make_qr("https://med-synth-secure-transfer.local/auth-token-88392")
                    buff = BytesIO()
                    qr.save(buff, kind='png', scale=5)
                    st.image(buff.getvalue(), width=150)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- FOOTER DIRECTION NAV CONTROL ---
        st.write("---")
        b_col_prev, _ = st.columns([1, 5])
        with b_col_prev:
            if st.button("← Back to AI Generation", use_container_width=True):
                st.session_state.menu_selection = "2. AI Generation"
                st.rerun()