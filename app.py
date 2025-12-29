import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import datetime
import base64
import textwrap

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
    st.session_state.map_center = [52.51, 13.48] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 12
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

# --- CSS DESIGN (STATUS COLORS) ---
st.markdown("""
    <style>
    :root {
        --primary-color: #0071e3;
        --background-color: #ffffff;
        --text-color: #000000;
        --font: sans-serif;
        
        /* Status Farben */
        --status-ok: #34c759; /* Apple Green */
        --status-defekt: #ff3b30; /* Apple Red */
    }
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important;
        overflow-x: hidden !important; 
    }
    
    header {visibility: hidden;}
    
    .block-container { 
        padding-top: 1rem !important; 
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    /* --- BUTTONS --- */
    
    /* 1. STANDARD (SECONDARY) -> Für "Funktionstüchtig" */
    /* Wir machen diese Grün um "OK" zu signalisieren */
    div.stButton > button:not([kind="primary"]) {
        background-color: #ffffff !important;
        color: #34c759 !important; /* Grün */
        border: 1px solid #34c759 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        padding: 10px 0px !important;
        margin: 0 !important;
        text-align: center !important;
        justify-content: center !important;
        display: flex !important;
        width: 100% !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }
    div.stButton > button:not([kind="primary"]):hover {
        background-color: #e8f5e9 !important;
    }

    /* 2. PRIMARY -> Für "Defekt" (Rot) */
    /* Wir nutzen den Primary Button Type für defekte Einträge und Aktionen */
    div.stButton > button[kind="primary"] {
        background-color: #ff3b30 !important; /* Rot */
        color: #ffffff !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #d70015 !important;
    }

    /* --- EXTRAS --- */
    
    /* Menu Button right (muss neutral bleiben) */
    div[data-testid="column"]:last-child button:not([kind="primary"]) {
        float: right; 
        font-size: 24px !important; 
        color: #000000 !important; /* Schwarz statt Grün */
        border: none !important; 
        background: transparent !important; 
        width: auto !important;
    }

    /* Menu Box Buttons (müssen neutral bleiben) */
    .menu-box { background: #ffffff; border: 1px solid #e5e5ea; border-radius: 12px; padding: 10px; margin-bottom: 20px; }
    
    /* Hier überschreiben wir die grüne Farbe für das Menü zurück auf Schwarz/Blau */
    .menu-box button { 
        width: 100% !important; 
        border: none !important;
        border-bottom: 1px solid #f0f0f0 !important; 
        border-radius: 0px !important; 
        text-align: left !important; 
        background: white !important;
        color: #000000 !important; /* Text Schwarz */
    }
    .menu-box button:hover {
        color: #0071e3 !important;
    }

    /* "Zurück" Button in Detailansicht */
    /* Wir wollen nicht, dass der Zurück Button grün oder rot schreit */
    /* Da er secondary ist, wäre er grün. Wir machen ihn grau/schwarz */
    
    .app-title { font-size: 24px; font-weight: 700; color: #000000 !important; margin: 0; white-space: nowrap; }
    hr { margin: 15px 0; border-color: #f0f0f0; }
    section[data-testid="stSidebar"] { display: none; }
    div.row-widget.stRadio > div { flex-direction: row; background-color: #f2f2f7; padding: 2px; border-radius: 9px; justify-content: center; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)


# --- HEADER ---
c1, c2 = st.columns([6, 1])
with c1:
    st.markdown('<div class="app-title">Berlin Lichtenberg</div>', unsafe_allow_html=True)
with c2:
    label = "✖️" if st.session_state.menu_open else "☰"
    # Menü Button ist secondary -> würde grün werden. CSS oben fixiert das auf schwarz.
    if st.button(label, key="menu_main"):
        toggle_menu()
        st.rerun()

# --- MENÜ ---
if st.session_state.menu_open:
    st.markdown('<div class="menu-box">', unsafe_allow_html=True)
    if st.button("🏠  Übersicht", key="nav_home", use_container_width=True): set_page("Übersicht"); st.rerun()
    if st.button("⚙️  Verwaltung", key="nav_admin", use_container_width=True): set_page("Verwaltung"); st.rerun()
    if st.button("➕  Neuer Eintrag", key="nav_add", use_container_width=True): set_page("Neuer Eintrag"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='border-bottom: 1px solid #e5e5ea; margin-top: 5px; margin-bottom: 15px;'></div>", unsafe_allow_html=True)


# --- LOGIK ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="berlin_status_v1")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

def load_data():
    # Neue Spalte: status
    cols = ["id", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad", "bild_pfad", "baujahr", "hersteller", "status"]
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=cols).to_csv(CSV_FILE, index=False)
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(CSV_FILE)
    for col in cols:
        if col not in df.columns: df[col] = ""
    
    # Standardwert für Status setzen, falls leer
    if "status" in df.columns:
        df["status"] = df["status"].fillna("Funktionstüchtig").replace("", "Funktionstüchtig")
    
    if "letzte_kontrolle" in df.columns:
        df["letzte_kontrolle"] = pd.to_datetime(df["letzte_kontrolle"], errors='coerce').dt.date
    text_cols = ["nummer", "bundesnummer", "plz", "strasse", "stadt", "typ", "bild_pfad", "baujahr", "hersteller", "status"]
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
        c_back, c_x = st.columns([1,3])
        with c_back:
            # Hier nutzen wir keinen speziellen Typ, also wird er "grün" (Secondary).
            # Das ist okay, oder wir könnten CSS injecten um ihn grau zu machen.
            # Lassen wir ihn als "OK" button stehen.
            if st.button("← Zurück", key="back_btn"): 
                st.session_state.detail_id = None
                st.rerun()
            
        entry = df[df['id'] == st.session_state.detail_id].iloc[0]
        
        # Status Anzeige im Detail
        status_color = "red" if entry['status'] == "Defekt" else "green"
        st.markdown(f"## {entry['nummer']} <span style='color:{status_color}; font-size:0.6em;'>● {entry['status']}</span>", unsafe_allow_html=True)
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
            st.markdown(f"**Bundesnr:** {entry['bundesnummer']}")
            
        if entry['breitengrad'] != 0:
            st.markdown("### Karte")
            # Marker Farbe basierend auf Status
            m_color = "red" if entry['status'] == "Defekt" else "green"
            m_detail = folium.Map(location=[entry['breitengrad'], entry['laengengrad']], zoom_start=16, tiles="OpenStreetMap")
            folium.Marker([entry['breitengrad'], entry['laengengrad']], icon=folium.Icon(color=m_color, icon="info-sign")).add_to(m_detail)
            st_folium(m_detail, width="100%", height=250)

    else:
        # LISTE
        mode = st.radio("Ansicht", ["Liste", "Karte"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Liste":
            if not df.empty:
                # Sortieren
                df_display = df.sort_values(by='nummer', ascending=True)
                
                for _, row in df_display.iterrows():
                    with st.container():
                        # 1. BUTTON (FARBE NACH STATUS)
                        label = f"{row['nummer']} - {row['bundesnummer']}"
                        if label.strip() in ["-", " - "]: label = "Ohne Nummer"
                        
                        # LOGIK: 
                        # Wenn DEFEKT -> type="primary" (Rot durch CSS)
                        # Wenn OK -> type="secondary" (Grün durch CSS)
                        btn_type = "primary" if row['status'] == "Defekt" else "secondary"
                        
                        if st.button(label, key=f"l_{row['id']}", type=btn_type, use_container_width=True):
                            st.session_state.detail_id = row['id']
                            st.rerun()
                        
                        # 2. ADRESSE & BILD (HTML)
                        addr_text = f"{row['strasse']}<br>{row['plz']} {row['stadt']}".strip()
                        
                        img_html = ""
                        if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                            b64 = get_image_base64(row['bild_pfad'])
                            if b64:
                                img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:60px; height:60px; object-fit:cover; border-radius:6px; flex-shrink:0; margin-left:10px;">'
                        
                        html_code = textwrap.dedent(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px; padding: 0 5px; width: 100%;">
                                <div style="font-size: 13px; color: #666; line-height: 1.3; flex-grow: 1; word-wrap: break-word;">
                                    {addr_text}
                                </div>
                                {img_html}
                            </div>
                        """)
                        
                        st.markdown(html_code, unsafe_allow_html=True)
                                
                    st.markdown("<hr>", unsafe_allow_html=True)
            else:
                st.info("Keine Einträge.")

        elif mode == "Karte":
            m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
            if st.session_state.map_zoom == 12 and not df.empty:
                valid = df[(df['breitengrad'] != 0) & (df['breitengrad'].notnull())]
                if not valid.empty:
                    sw = valid[['breitengrad', 'laengengrad']].min().values.tolist()
                    ne = valid[['breitengrad', 'laengengrad']].max().values.tolist()
                    if sw != ne: m.fit_bounds([sw, ne])
            for _, row in df.iterrows():
                if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                    # KARTE FARBE
                    c = "red" if row['status'] == "Defekt" else "green"
                    
                    img_html = ""
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        b64 = get_image_base64(row['bild_pfad'])
                        if b64: img_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:6px; margin-bottom:5px;">'
                    popup = f"<div style='width:160px; font-family:sans-serif;'>{img_html}<b>{row['nummer']}</b><br>{row['strasse']}<br>Status: {row['status']}</div>"
                    folium.Marker([row['breitengrad'], row['laengengrad']], popup=folium.Popup(popup, max_width=200), icon=folium.Icon(color=c, icon="info-sign")).add_to(m)
            st_folium(m, width="100%", height=600)

elif st.session_state.page == 'Verwaltung':
    st.header("Verwaltung")
    with st.expander("📂 Datei importieren (Excel / ODS)", expanded=True):
        uploaded_file = st.file_uploader("Datei auswählen", type=["ods", "xlsx", "csv"])
        if uploaded_file and st.button("Import starten", type="secondary"): # Secondary ist hier Grün (OK)
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
                
                count = 0
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
                    
                    # Status Default
                    new_row = pd.DataFrame({
                        "id": [nid], "nummer": [v_nr], "bundesnummer": [v_b], "strasse": [v_s], "plz": [v_p], "stadt": [v_o], 
                        "typ": ["Dialog Display"], "letzte_kontrolle": [datetime.date.today()], 
                        "breitengrad": [lat], "laengengrad": [lon], "bild_pfad": [""], 
                        "baujahr": [v_bau], "hersteller": [v_her],
                        "status": ["Funktionstüchtig"]
                    })
                    df = pd.concat([df, new_row], ignore_index=True)
                    count += 1
                save_data(df)
                st.success(f"{count} Einträge importiert!")
                st.rerun()
            except Exception as e: st.error(f"Fehler: {e}")
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # EDITOR
    edit_data = df.copy()
    edit_data["Löschen?"] = False 
    column_cfg = {
        "Löschen?": st.column_config.CheckboxColumn("🗑️", width="small"),
        "id": None, "bild_pfad": None,
        "typ": st.column_config.SelectboxColumn("Typ", options=["Dialog Display", "Ohne"]),
        # NEU: Status Spalte
        "status": st.column_config.SelectboxColumn("Status", options=["Funktionstüchtig", "Defekt"], required=True),
        "letzte_kontrolle": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        "strasse": st.column_config.TextColumn("Str"), "plz": st.column_config.TextColumn("PLZ"), 
        "stadt": st.column_config.TextColumn("Ort"), "nummer": st.column_config.TextColumn("Nr."),
        "bundesnummer": st.column_config.TextColumn("B-Nr"),
        "breitengrad": st.column_config.NumberColumn("Lat", format="%.4f"),
        "laengengrad": st.column_config.NumberColumn("Lon", format="%.4f")
    }
    col_order = ["Löschen?", "status", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "hersteller", "baujahr", "letzte_kontrolle", "breitengrad", "laengengrad"]
    edited_df = st.data_editor(edit_data, column_config=column_cfg, num_rows="dynamic", use_container_width=True, hide_index=True, column_order=col_order)
    
    # Speichern Button Rot (Primary)
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
        if st.button("Foto speichern", type="primary", use_container_width=True):
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
        
        # Neue Status Auswahl
        c_typ, c_dat, c_stat = st.columns(3)
        typ = c_typ.selectbox("Typ", ["Dialog Display", "Ohne"])
        status_input = c_stat.selectbox("Status", ["Funktionstüchtig", "Defekt"])
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
                "breitengrad": [final_lat], "laengengrad": [final_lon], 
                "bild_pfad": [img_path], "hersteller": [hersteller], "baujahr": [baujahr],
                "status": [status_input]
            })
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Gespeichert!")
