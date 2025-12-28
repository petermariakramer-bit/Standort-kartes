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
st.set_page_config(
    page_title="Berlin Lichtenberg", 
    layout="wide", 
    page_icon="🐻",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE ---
if 'page' not in st.session_state:
    st.session_state.page = 'Übersicht'

if 'menu_open' not in st.session_state:
    st.session_state.menu_open = False

if 'map_center' not in st.session_state:
    st.session_state.map_center = [52.51, 13.48] # Berlin Lichtenberg Koordinaten ca.
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 13

if 'detail_id' not in st.session_state:
    st.session_state.detail_id = None

def set_page(page_name):
    st.session_state.page = page_name
    st.session_state.detail_id = None
    st.session_state.menu_open = False

def toggle_menu():
    st.session_state.menu_open = not st.session_state.menu_open

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

# --- CSS DESIGN (STICKY HEADER) ---
st.markdown("""
    <style>
    /* 1. GLOBAL RESET */
    .stApp { background-color: #ffffff !important; }
    html, body, p, div, label, h1, h2, h3, .stMarkdown, span, button {
        color: #1d1d1f !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Header (Standard Streamlit) ausblenden */
    header {visibility: hidden;}
    
    /* 2. INHALT NACH UNTEN SCHIEBEN */
    /* Da der Header jetzt "fixed" ist (schwebt), muss der Inhalt Platz machen */
    .block-container { 
        padding-top: 5rem !important; /* Platz für den Sticky Header */
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
        max-width: 100% !important; 
    }

    /* 3. STICKY HEADER CONTAINER DEFINIEREN */
    /* Wir zielen auf den ERSTEN Container im Hauptbereich */
    div[data-testid="stVerticalBlock"] > div:first-child {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: rgba(255, 255, 255, 0.98); /* Fast deckendes Weiß */
        z-index: 99999; /* Immer ganz oben */
        border-bottom: 1px solid #e5e5ea;
        padding-top: 15px;
        padding-bottom: 10px;
        padding-left: 15px;
        padding-right: 15px;
    }

    /* 4. HEADER ELEMENTE */
    .app-title {
        font-size: 22px; 
        font-weight: 700; 
        color: #000000 !important;
        margin: 0;
        line-height: 2.5rem;
    }

    /* Menü Button Styling */
    div.stButton > button {
        border: none;
        background: transparent;
        box-shadow: none;
        float: right; /* Rechtsbündig */
        font-size: 24px !important;
        padding-top: 0px;
        padding-bottom: 0px;
        color: #0071e3 !important;
    }
    div.stButton > button:hover {
        color: #005bb5 !important;
    }

    /* 5. MENÜ BOX (DROPDOWN) */
    .menu-box {
        background-color: #fbfbfd;
        border-radius: 0 0 12px 12px;
        padding: 15px;
        margin-top: -10px; /* Verbindet sich optisch mit Header */
        border-bottom: 1px solid #e5e5ea;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* 6. LISTE STYLING */
    .address-text {
        font-size: 13px; color: #86868b !important; 
        margin-top: -5px; line-height: 1.3; 
    }
    hr { margin: 0; border-color: #e5e5ea; }
    
    /* Segmented Control Fix */
    div.row-widget.stRadio > div {
        flex-direction: row; background-color: #f2f2f7; padding: 2px;
        border-radius: 9px; width: 100%; justify-content: center; margin-top: 5px;
    }
    
    /* Sidebar weg */
    section[data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)


# --- HEADER ---
# Dieser Container wird durch das CSS oben "fixed" gemacht
c_head_container = st.container()

with c_head_container:
    # Layout: Titel (Links) ----- Button (Rechts)
    # [8, 1] sorgt dafür, dass der Button ganz rechts klebt
    col1, col2 = st.columns([8, 1])
    
    with col1:
        st.markdown('<div class="app-title">Berlin Lichtenberg</div>', unsafe_allow_html=True)
    
    with col2:
        # Toggle Button
        icon = "✖️" if st.session_state.menu_open else "☰"
        if st.button(icon, key="menu_btn"):
            toggle_menu()
            st.rerun()

    # --- MENÜ INHALT (Wird direkt unter dem Header angezeigt) ---
    if st.session_state.menu_open:
        st.markdown('<div class="menu-box">', unsafe_allow_html=True)
        
        # Navigation Buttons
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            if st.button("🏠 Übersicht", use_container_width=True): set_page("Übersicht"); st.rerun()
        with c_m2:
            if st.button("⚙️ Verwaltung", use_container_width=True): set_page("Verwaltung"); st.rerun()
        with c_m3:
            if st.button("➕ Neu", use_container_width=True): set_page("Neuer Eintrag"); st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


# --- DATEN ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="berlin_app_sticky")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

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


# --- HAUPTINHALT ---

if st.session_state.page == 'Übersicht':
    
    if st.session_state.detail_id is not None:
        # DETAIL ANSICHT
        if st.button("← Zurück zur Liste", use_container_width=True):
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
        # ÜBERSICHT (Liste / Karte)
        mode = st.radio("Ansicht", ["Liste", "Karte"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Liste":
            if not df.empty:
                df_display = df.sort_values(by='nummer', ascending=True)
                for _, row in df_display.iterrows():
                    with st.container():
                        col_txt, col_img = st.columns([3.5, 1])
                        with col_txt:
                            label = f"{row['nummer']} - {row['bundesnummer']}"
                            if label.strip() in ["-", " - "]: label = "Ohne Nummer"
                            
                            if st.button(label, key=f"l_{row['id']}"):
                                st.session_state.detail_id = row['id']
                                st.rerun()
                            
                            addr = f"{row['strasse']}<br>{row['plz']} {row['stadt']}".strip()
                            st.markdown(f"<div class='address-text'>{addr}</div>", unsafe_allow_html=True)
                        
                        with col_img:
                            if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                                st.image(row['bild_pfad'], use_container_width=True)
                                
                    st.markdown("<hr style='margin: 8px 0; border-color: #f0f0f0;'>", unsafe_allow_html=True)
            else:
                st.info("Keine Einträge.")

        elif mode == "Karte":
            m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
            if st.session_state.map_zoom == 13 and not df.empty:
                valid = df[(df['breitengrad'] != 0) & (df['breitengrad'].notnull())]
                if not valid.empty:
                    sw = valid[['breitengrad', 'laengengrad']].min().values.tolist()
                    ne = valid[['breitengrad', 'laengengrad']].max().values.tolist()
                    if sw != ne: m.fit_bounds([sw, ne])

            for _, row in df.iterrows():
                if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                    c = "blue" if row['typ'] == "Dialog Display" else "gray"
                    img_html = ""
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        b64 = get_image_base64(row['bild_pfad'])
                        if b64: img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:6px; margin-bottom:5px;">'
                    
                    popup = f"<div style='width:160px; font-family:sans-serif;'>{img_html}<b>{row['nummer']}</b><br>{row['strasse']}</div>"
                    folium.Marker([row['breitengrad'], row['laengengrad']], popup=folium.Popup(popup, max_width=200), icon=folium.Icon(color=c, icon="info-sign")).add_to(m)
            
            st_folium(m, width="100%", height=600)

elif st.session_state.page == 'Verwaltung':
    st.header("Verwaltung")
    
    with st.expander("📂 Datei importieren (Excel / ODS)", expanded=True):
        uploaded_file = st.file_uploader("Datei auswählen", type=["ods", "xlsx", "csv"])
        if uploaded_file and st.button("Import starten"):
            try:
                if uploaded_file.name.endswith(".csv"): df_new = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(".ods"): df_new = pd.read_excel(uploaded_file, engine="odf")
                else: df_new = pd.read_excel(uploaded_file)
                
                file_cols = [c.lower() for c in df_new.columns]
                def get_col(kws):
                    for i, c in enumerate(file_cols):
                        for kw in kws:
                            if kw in c: return df_new.iloc[:, i]
                    return None

                imp_nr = get_col(["nummer", "nr.", "standort"])
                imp_b = get_col(["bundes", "b-nr"])
                imp_s = get_col(["straße", "strasse", "adr"])
                imp_plz = get_col(["plz", "post"])
                imp_ort = get_col(["stadt", "ort", "bezirk"])
                imp_bau = get_col(["baujahr", "jahr"])
                imp_her = get_col(["hersteller", "firma"])
                
                for idx in range(len(df_new)):
                    nid = pd.Timestamp.now().strftime('%Y%m%d') + f"{idx:04d}"
                    v_nr = str(imp_nr.iloc[idx]) if imp_nr is not None else ""
                    v_b = str(imp_b.iloc[idx]) if imp_b is not None else ""
                    v_s = str(imp_s.iloc[idx]) if imp_s is not None else ""
                    v_p = str(imp_plz.iloc[idx]) if imp_plz is not None else ""
                    v_o = str(imp_ort.iloc[idx]) if imp_ort is not None else "Berlin"
                    v_bau = str(imp_bau.iloc[idx]) if imp_bau is not None else ""
                    v_her = str(imp_her.iloc[idx]) if imp_her is not None else ""
                    if v_nr == "nan": v_nr = ""
                    
                    lat, lon = 0.0, 0.0
                    if v_s and v_o:
                        try:
                            loc = geocode(f"{v_s}, {v_p} {v_o}")
                            if loc: lat, lon = loc.latitude, loc.longitude
                        except: pass
                    
                    new_row = pd.DataFrame({"id": [nid], "nummer": [v_nr], "bundesnummer": [v_b], "strasse": [v_s], "plz": [v_p], "stadt": [v_o], "typ": ["Dialog Display"], "letzte_kontrolle": [datetime.date.today()], "breitengrad": [lat], "laengengrad": [lon], "bild_pfad": [""], "baujahr": [v_bau], "hersteller": [v_her]})
                    df = pd.concat([df, new_row], ignore_index=True)
                
                save_data(df)
                st.success("Import fertig!")
                st.rerun()
            except Exception as e: st.error(f"Fehler: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    
    edit_data = df.copy()
    edit_data["Löschen?"] = False 
    column_cfg = {
        "Löschen?": st.column_config.CheckboxColumn("🗑️", width="small"),
        "id": None, "bild_pfad": None,
        "typ": st.column_config.SelectboxColumn("Typ", options=["Dialog Display", "Ohne"]),
        "letzte_kontrolle": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        "strasse": st.column_config.TextColumn("Str"), "nummer": st.column_config.TextColumn("Nr."),
        "bundesnummer": st.column_config.TextColumn("B-Nr"),
        "breitengrad": st.column_config.NumberColumn("Lat", format="%.4f"),
        "laengengrad": st.column_config.NumberColumn("Lon", format="%.4f")
    }
    col_order = ["Löschen?", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "hersteller", "baujahr", "letzte_kontrolle", "breitengrad", "laengengrad"]
    edited_df = st.data_editor(edit_data, column_config=column_cfg, num_rows="dynamic", use_container_width=True, hide_index=True, column_order=col_order)
    
    if st.button("💾 Speichern", type="primary", use_container_width=True):
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
        if curr['bild_pfad'] and os.path.exists(curr['bild_pfad']): st.image(curr['bild_pfad'], width=150)
        up = st.file_uploader("Foto", type=['jpg','png'])
        if st.button("Foto speichern", use_container_width=True):
            if up:
                np = save_uploaded_image(up, sel_id)
                idx = df.index[df['id'] == sel_id].tolist()[0]
                df.at[idx, 'bild_pfad'] = np
                save_data(df)
                st.success("Gespeichert!")
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
        with st.expander("Koordinaten"):
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
            new_row = pd.DataFrame({"id": [new_id], "nummer": [nummer], "bundesnummer": [bundesnummer], "strasse": [strasse], "plz": [plz], "stadt": [stadt], "typ": [typ], "letzte_kontrolle": [letzte_kontrolle], "breitengrad": [final_lat], "laengengrad": [final_lon], "bild_pfad": [img_path], "hersteller": [hersteller], "baujahr": [baujahr]})
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Gespeichert!")
