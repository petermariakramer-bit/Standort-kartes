import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import datetime
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Dialog Displays", layout="wide", page_icon="")

# --- SESSION STATE ---
if 'page' not in st.session_state:
    st.session_state.page = 'Übersicht'

if 'map_center' not in st.session_state:
    st.session_state.map_center = [51.16, 10.45] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

if 'detail_id' not in st.session_state:
    st.session_state.detail_id = None

def set_page(page_name):
    st.session_state.page = page_name
    st.session_state.detail_id = None

def set_map_focus(lat, lon):
    st.session_state.map_center = [lat, lon]
    st.session_state.map_zoom = 15

# --- HELPER ---
DATA_FOLDER = 'data'
IMAGE_FOLDER = 'data/images'
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

def save_uploaded_image(uploaded_file, entry_id):
    if uploaded_file is None: return None
    file_ext = uploaded_file.name.split('.')[-1]
    file_name = f"{entry_id}.{file_ext}"
    file_path = os.path.join(IMAGE_FOLDER, file_name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def get_image_base64(file_path):
    if not file_path or not os.path.exists(file_path): return None
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- CSS DESIGN ---
st.markdown("""
    <style>
    /* 1. GLOBAL RESET */
    .stApp { background-color: #ffffff !important; }
    html, body, p, div, label, h1, h2, h3, .stMarkdown, span, button {
        color: #1d1d1f !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Header ausblenden und Platz oben schaffen */
    header {visibility: hidden;}
    .block-container { 
        padding-top: 1rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
        max-width: 100% !important; 
    }

    /* 2. STICKY HEADER CONTAINER */
    /* Dieser Container klebt oben und hält Titel und Icons */
    div[data-testid="stVerticalBlock"] > div:first-child {
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px); /* Apple Milchglas-Effekt */
        border-bottom: 1px solid #e5e5ea;
        padding-top: 10px;
        padding-bottom: 10px;
        margin-top: -60px; /* Zieht es ganz nach oben in den Hidden Header Bereich */
    }

    /* 3. MOBILE LAYOUT FIX (Kein Umbruch der Icons!) */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* WICHTIG: Zwingt Elemente nebeneinander */
        align-items: center !important;
        white-space: nowrap !important;
    }

    /* 4. TITEL */
    .app-title {
        font-size: 22px; 
        font-weight: 700; 
        color: #000000 !important;
        margin: 0;
        padding-left: 5px;
    }

    /* 5. NAVIGATION ICONS BUTTONS */
    /* Wir stylen die Buttons im Header speziell */
    .nav-btn button {
        background-color: transparent !important;
        border: none !important;
        color: #0071e3 !important; /* Blau */
        font-size: 22px !important;
        padding: 0px 5px !important;
        margin: 0 !important;
        line-height: 1 !important;
        box-shadow: none !important;
    }
    .nav-btn button:hover {
        color: #005bb5 !important;
    }
    /* Aktiver Button (optional dunkler) */
    .nav-btn-active button {
        background-color: #f0f0f0 !important;
        border-radius: 50%;
    }

    /* 6. LISTE (Einträge) */
    .address-text {
        font-size: 13px; color: #86868b !important; 
        margin-top: -2px; line-height: 1.3; 
    }
    
    /* Buttons in der Liste (Linksbündig) */
    div[data-testid="stVerticalBlock"] button {
        text-align: left !important;
    }

    /* Trennlinie */
    hr { margin: 0; border-color: #e5e5ea; }
    
    /* 7. SEGMENTED CONTROL (Liste/Karte) */
    div.row-widget.stRadio > div {
        flex-direction: row; background-color: #f2f2f7; padding: 2px;
        border-radius: 9px; width: 100%; justify-content: center; margin-top: 5px;
    }
    div.row-widget.stRadio > div > label {
        background-color: transparent; border: none; padding: 5px 0px;
        border-radius: 7px; margin: 0; width: 50%; text-align: center;
        justify-content: center; cursor: pointer; font-weight: 500; color: #666 !important;
    }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background-color: #ffffff; color: #000 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15); font-weight: 600;
    }

    /* Verhindert horizontales Scrollen */
    div[data-testid="stAppViewContainer"] {
        overflow-x: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER NAVIGATION ---
# Container für den Sticky Header
with st.container():
    # Spaltenverhältnis: Titel bekommt viel Platz, Icons rechts festen kleinen Platz.
    # [5, 1, 1, 1] verhindert, dass sie zu breit werden.
    c_title, c_home, c_manage, c_add = st.columns([5, 0.8, 0.8, 0.8])

    with c_title:
        st.markdown('<div class="app-title">Dialog Displays</div>', unsafe_allow_html=True)

    # Funktion für Button-Styling (Klasse hinzufügen hacky über leeren Container)
    def nav_button(emoji, page_target, col):
        with col:
            # Container trick für CSS Klasse
            st.markdown(f'<div class="nav-btn">', unsafe_allow_html=True)
            if st.button(emoji, key=f"nav_{page_target}", use_container_width=True):
                set_page(page_target)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    nav_button("🏠", "Übersicht", c_home)
    nav_button("⚙️", "Verwaltung", c_manage)
    nav_button("➕", "Neuer Eintrag", c_add)

# Kleiner Abstand nach dem Header
st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)


# --- DATEN LOGIK ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="dialog_app_mobile_final")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def load_data():
    cols = ["id", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad", "bild_pfad", "baujahr", "hersteller"]
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=cols).to_csv(CSV_FILE, index=False)
        return pd.DataFrame(columns=cols)
    
    df = pd.read_csv(CSV_FILE)
    for col in cols:
        if col not in df.columns: df[col] = ""
    
    if "letzte_kontrolle" in df.columns:
        df["letzte_kontrolle"] = pd.to_datetime(df["letzte_kontrolle"], errors='coerce').dt.date
    
    text_cols = ["nummer", "bundesnummer", "plz", "strasse", "stadt", "typ", "bild_pfad", "baujahr", "hersteller"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan", "").apply(lambda x: x.replace(".0", "") if x.endswith(".0") else x)

    return df

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

df = load_data()

# --- CONTENT ---

if st.session_state.page == 'Übersicht':
    
    if st.session_state.detail_id is not None:
        # DETAIL ANSICHT
        if st.button("← Zurück", type="secondary", use_container_width=True):
            st.session_state.detail_id = None
            st.rerun()
            
        entry = df[df['id'] == st.session_state.detail_id].iloc[0]
        
        st.markdown(f"## {entry['nummer']} - {entry['bundesnummer']}")
        st.caption(f"{entry['strasse']}, {entry['plz']} {entry['stadt']}")
        
        if entry['bild_pfad'] and os.path.exists(entry['bild_pfad']):
            st.image(entry['bild_pfad'], use_container_width=True)
            
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Typ:** {entry['typ']}")
            st.markdown(f"**Hersteller:** {entry['hersteller']}")
            st.markdown(f"**Baujahr:** {entry['baujahr']}")
        with c2:
            st.markdown(f"**Kontrolle:** {entry['letzte_kontrolle']}")
            
        if entry['breitengrad'] != 0:
            st.markdown("### Karte")
            m_detail = folium.Map(location=[entry['breitengrad'], entry['laengengrad']], zoom_start=16, tiles="OpenStreetMap")
            folium.Marker([entry['breitengrad'], entry['laengengrad']], icon=folium.Icon(color="blue", icon="info-sign")).add_to(m_detail)
            st_folium(m_detail, width="100%", height=250)

    else:
        # LISTE / KARTE SWITCH
        mode = st.radio("Ansicht", ["Liste", "Karte"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Liste":
            if not df.empty:
                df_display = df.sort_values(by='nummer', ascending=True)
                for _, row in df_display.iterrows():
                    # LISTENEINTRAG
                    with st.container():
                        col_txt, col_img = st.columns([3.5, 1])
                        
                        with col_txt:
                            label = f"{row['nummer']} - {row['bundesnummer']}"
                            if label.strip() in ["-", " - "]: label = "Ohne Nummer"
                            
                            # Button mit CSS Styling für Link-Look
                            if st.button(label, key=f"l_{row['id']}"):
                                st.session_state.detail_id = row['id']
                                st.rerun()
                            
                            addr = f"{row['strasse']}<br>{row['plz']} {row['stadt']}".strip()
                            st.markdown(f"<div class='address-text'>{addr}</div>", unsafe_allow_html=True)
                        
                        with col_img:
                            if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                                st.image(row['bild_pfad'], use_container_width=True)
                                
                    # Trennlinie
                    st.markdown("<hr style='margin: 8px 0; border-color: #f0f0f0;'>", unsafe_allow_html=True)
            else:
                st.info("Keine Einträge.")

        elif mode == "Karte":
            m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
            
            if st.session_state.map_zoom == 5 and not df.empty:
                valid = df[(df['breitengrad'] != 0) & (df['breitengrad'].notnull())]
                if not valid.empty:
                    sw = valid[['breitengrad', 'laengengrad']].min().values.tolist()
                    ne = valid[['breitengrad', 'laengengrad']].max().values.tolist()
                    if sw != ne: m.fit_bounds([sw, ne])

            for _, row in df.iterrows():
                if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                    c = "blue" if row['typ'] == "Dialog Display" else "gray"
                    # Kleines Bild im Popup
                    img_html = ""
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        b64 = get_image_base64(row['bild_pfad'])
                        if b64: img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:6px; margin-bottom:5px;">'
                    
                    popup = f"<div style='width:160px; font-family:sans-serif;'>{img_html}<b>{row['nummer']}</b><br>{row['strasse']}</div>"
                    folium.Marker([row['breitengrad'], row['laengengrad']], popup=folium.Popup(popup, max_width=200), icon=folium.Icon(color=c, icon="info-sign")).add_to(m)
            
            st_folium(m, width="100%", height=600)

elif st.session_state.page == 'Verwaltung':
    st.header("Verwaltung")
    
    # Tabelle
    edit_data = df.copy()
    edit_data["Löschen?"] = False 
    column_cfg = {
        "Löschen?": st.column_config.CheckboxColumn("🗑️", width="small"),
        "id": None, "bild_pfad": None,
        "typ": st.column_config.SelectboxColumn("Typ", options=["Dialog Display", "Ohne"]),
        "letzte_kontrolle": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        "strasse": st.column_config.TextColumn("Str"), "plz": st.column_config.TextColumn("PLZ"), 
        "stadt": st.column_config.TextColumn("Ort"), "nummer": st.column_config.TextColumn("Nr."),
        "bundesnummer": st.column_config.TextColumn("B-Nr"),
        "breitengrad": st.column_config.NumberColumn("Lat", format="%.4f"),
        "laengengrad": st.column_config.NumberColumn("Lon", format="%.4f")
    }
    col_order = ["Löschen?", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "hersteller", "baujahr", "letzte_kontrolle", "breitengrad", "laengengrad"]
    edited_df = st.data_editor(edit_data, column_config=column_cfg, num_rows="dynamic", use_container_width=True, hide_index=True, column_order=col_order)
    
    if st.button("💾 Tabelle speichern", type="primary", use_container_width=True):
        rows_to_keep = edited_df[edited_df["Löschen?"] == False]
        save_data(rows_to_keep.drop(columns=["Löschen?"]))
        st.success("Gespeichert!")
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Bild ändern")
    if not df.empty:
        opts = {f"{r['nummer']}": r['id'] for i, r in df.sort_values('nummer').iterrows()}
        sel_label = st.selectbox("Eintrag:", opts.keys())
        sel_id = opts[sel_label]
        
        curr = df[df['id'] == sel_id].iloc[0]
        if curr['bild_pfad'] and os.path.exists(curr['bild_pfad']):
            st.image(curr['bild_pfad'], width=150)
            
        up = st.file_uploader("Neues Foto", type=['jpg','png'])
        if st.button("Foto speichern", use_container_width=True):
            if up:
                np = save_uploaded_image(up, sel_id)
                idx = df.index[df['id'] == sel_id].tolist()[0]
                df.at[idx, 'bild_pfad'] = np
                save_data(df)
                st.success("Foto gespeichert!")
                st.rerun()

elif st.session_state.page == 'Neuer Eintrag':
    st.header("Neuer Eintrag")
    with st.form("new"):
        c1, c2 = st.columns(2)
        nummer = c1.text_input("Nummer")
        bundesnummer = c2.text_input("Bundesnummer")
        col_str, col_plz, col_stadt = st.columns([2, 1, 1])
        strasse = col_str.text_input("Straße")
        plz = col_plz.text_input("PLZ")
        stadt = col_stadt.text_input("Stadt")
        c_her, c_bau = st.columns(2)
        hersteller = c_her.text_input("Hersteller")
        baujahr = c_bau.text_input("Baujahr")
        
        uploaded_img = st.file_uploader("Foto", type=['png', 'jpg'])
        
        with st.expander("Koordinaten (Optional)"):
            g1, g2 = st.columns(2)
            mlat = g1.number_input("Lat", value=0.0, format="%.5f")
            mlon = g2.number_input("Lon", value=0.0, format="%.5f")
        
        c_typ, c_dat = st.columns(2)
        typ = c_typ.selectbox("Typ", ["Dialog Display", "Ohne"])
        letzte_kontrolle = c_dat.date_input("Datum", datetime.date.today())
        
        if st.form_submit_button("Speichern", type="primary", use_container_width=True):
            final_lat, final_lon = 0.0, 0.0
            new_id = pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
            img_path = save_uploaded_image(uploaded_img, new_id) if uploaded_img else ""

            if mlat != 0.0: final_lat, final_lon = mlat, mlon
            else:
                try:
                    loc = geocode(f"{strasse}, {plz} {stadt}")
                    if loc: final_lat, final_lon = loc.latitude, loc.longitude
                except: pass
            
            new_row = pd.DataFrame({
                "id": [new_id], "nummer": [nummer], "bundesnummer": [bundesnummer], 
                "strasse": [strasse], "plz": [plz], "stadt": [stadt],
                "typ": [typ], "letzte_kontrolle": [letzte_kontrolle],
                "breitengrad": [final_lat], "laengengrad": [final_lon], "bild_pfad": [img_path],
                "hersteller": [hersteller], "baujahr": [baujahr]
            })
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Gespeichert!")
