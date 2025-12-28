import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import datetime
import base64
from PIL import Image

# --- PAGE CONFIG ---
st.set_page_config(page_title="Dialog Displays", layout="wide", page_icon="")

# --- SESSION STATE ---
if 'page' not in st.session_state:
    st.session_state.page = 'Übersicht'

if 'map_center' not in st.session_state:
    st.session_state.map_center = [51.16, 10.45] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

# State für die Detail-Ansicht (welcher Eintrag ist offen?)
if 'detail_id' not in st.session_state:
    st.session_state.detail_id = None

# State für den Ansichts-Modus (Liste oder Karte)
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Liste"

def set_page(page_name):
    st.session_state.page = page_name
    # Beim Seitenwechsel Details zurücksetzen
    st.session_state.detail_id = None

def set_map_focus(lat, lon):
    st.session_state.map_center = [lat, lon]
    st.session_state.map_zoom = 15

# --- HELPER: BILDER & ORDNER ---
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
    /* 1. GLOBAL */
    .stApp { background-color: #ffffff !important; }
    html, body, p, div, label, h1, h2, h3, .stMarkdown, span {
        color: #1d1d1f !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    header {visibility: hidden;}
    .block-container { padding-top: 1rem !important; max-width: 100% !important; padding-left: 1rem; padding-right: 1rem; }

    /* 2. HEADER & TITEL */
    .app-title {
        font-size: 24px; font-weight: 700; color: #1d1d1f;
        margin: 0; line-height: 1.5; white-space: nowrap;
    }

    div[data-testid="stHorizontalBlock"] button {
        white-space: nowrap !important; height: auto !important;
        padding-top: 8px !important; padding-bottom: 8px !important; margin-top: 0px !important;
    }
    
    /* Navigation Ausrichtung */
    div[data-testid="column"] {
        display: flex; align-items: center !important; justify-content: flex-start;
    }

    /* 3. LISTE STYLING (Card Look) */
    .list-item-container {
        border-bottom: 1px solid #f0f0f0;
        padding: 15px 0;
    }

    /* Buttons in der Liste (Transparent & Linksbündig) */
    div[data-testid="stVerticalBlock"] .stButton button {
        width: 100%; background-color: transparent; color: #0071e3; border: none;
        text-align: left !important; justify-content: flex-start !important; 
        padding-left: 0px !important; font-weight: 600 !important;
        font-size: 16px !important; margin: 0px !important; height: auto !important;
        box-shadow: none !important;
    }
    div[data-testid="stVerticalBlock"] .stButton button:hover {
        color: #005bb5; text-decoration: none;
    }
    
    .address-text {
        font-size: 13px; color: #86868b !important; 
        margin-top: -4px; margin-bottom: 0px; padding-left: 0px; line-height: 1.4; 
    }
    
    /* Bild in der Liste */
    div[data-testid="stImage"] img {
        border-radius: 8px; object-fit: cover; height: 60px !important; width: 100% !important;
    }

    /* 4. SEGMENTED CONTROL (Liste/Karte Switcher) */
    /* Wir stylen die Radio Buttons um, damit sie wie Tabs aussehen */
    div.row-widget.stRadio > div {
        flex-direction: row;
        background-color: #f5f5f7;
        padding: 4px;
        border-radius: 10px;
        width: 100%;
        justify-content: center;
    }
    div.row-widget.stRadio > div > label {
        background-color: transparent;
        border: none;
        padding: 6px 20px;
        border-radius: 8px;
        margin-right: 0px;
        width: 50%;
        text-align: center;
        justify-content: center;
        cursor: pointer;
        font-weight: 500;
        color: #666 !important;
    }
    /* Das ausgewählte Element */
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background-color: #ffffff;
        color: #000 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        font-weight: 600;
    }
    
    /* 5. BUTTONS */
    button[kind="primary"] {
        background-color: #0071e3 !important; color: white !important;
        border: none !important; border-radius: 8px !important;
    }
    button[kind="secondary"] {
        background-color: #f5f5f7 !important; color: #1d1d1f !important;
        border: none !important; border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
c_brand, c_nav1, c_nav2, c_nav3, c_spacer = st.columns([2, 1, 1, 1.3, 4])

with c_brand:
    st.markdown('<div class="app-title">Dialog Displays</div>', unsafe_allow_html=True)

with c_nav1:
    btn_type = "primary" if st.session_state.page == "Übersicht" else "secondary"
    if st.button("Übersicht", type=btn_type, use_container_width=True):
        set_page("Übersicht"); st.rerun()

with c_nav2:
    btn_type = "primary" if st.session_state.page == "Verwaltung" else "secondary"
    if st.button("Verwaltung", type=btn_type, use_container_width=True):
        set_page("Verwaltung"); st.rerun()

with c_nav3:
    btn_type = "primary" if st.session_state.page == "Neuer Eintrag" else "secondary"
    if st.button("Neuer Eintrag", type=btn_type, use_container_width=True):
        set_page("Neuer Eintrag"); st.rerun()

st.markdown("<div style='height: 1px; background-color: #e5e5ea; margin-top: 15px; margin-bottom: 20px;'></div>", unsafe_allow_html=True)


# --- DATEN LOGIK ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="dialog_app_mobile")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def load_data():
    cols = ["id", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad", "bild_pfad"]
    
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=cols).to_csv(CSV_FILE, index=False)
        return pd.DataFrame(columns=cols)
    
    df = pd.read_csv(CSV_FILE)
    for col in cols:
        if col not in df.columns: df[col] = ""
    
    if "letzte_kontrolle" in df.columns:
        df["letzte_kontrolle"] = pd.to_datetime(df["letzte_kontrolle"], errors='coerce').dt.date
    
    text_cols = ["nummer", "bundesnummer", "plz", "strasse", "stadt", "typ", "bild_pfad"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan", "").apply(lambda x: x.replace(".0", "") if x.endswith(".0") else x)

    return df

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

df = load_data()

# --- CONTENT ---

if st.session_state.page == 'Übersicht':
    
    # --- 1. DETAIL ANSICHT (Wenn ein Eintrag ausgewählt wurde) ---
    if st.session_state.detail_id is not None:
        # Button "Zurück zur Liste"
        if st.button("← Zurück zur Übersicht", type="secondary"):
            st.session_state.detail_id = None
            st.rerun()
            
        # Daten des gewählten Eintrags holen
        entry = df[df['id'] == st.session_state.detail_id].iloc[0]
        
        st.markdown(f"## {entry['nummer']} - {entry['bundesnummer']}")
        st.caption(f"{entry['strasse']}, {entry['plz']} {entry['stadt']}")
        
        # Grosses Bild
        if entry['bild_pfad'] and os.path.exists(entry['bild_pfad']):
            st.image(entry['bild_pfad'], use_container_width=True)
            
        st.markdown("---")
        
        # Details
        c_det1, c_det2 = st.columns(2)
        with c_det1:
            st.markdown(f"**Typ:** {entry['typ']}")
            st.markdown(f"**Letzte Kontrolle:** {entry['letzte_kontrolle']}")
        with c_det2:
            st.markdown(f"**Koordinaten:** {float(entry['breitengrad']):.5f}, {float(entry['laengengrad']):.5f}")

        # Mini-Map nur für diesen Standort
        if entry['breitengrad'] != 0:
            st.markdown("### Standort auf Karte")
            m_detail = folium.Map(location=[entry['breitengrad'], entry['laengengrad']], zoom_start=16, tiles="OpenStreetMap")
            folium.Marker(
                [entry['breitengrad'], entry['laengengrad']],
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m_detail)
            st_folium(m_detail, width="100%", height=300)

    # --- 2. NORMALE ANSICHT (Liste oder Karte) ---
    else:
        # UMSCHALTER: LISTE vs KARTE
        # Wir nutzen Radio Buttons, aber durch CSS sieht es aus wie ein Tab-Switcher
        mode = st.radio("Ansicht wählen", ["Liste", "Karte"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)

        if mode == "Liste":
            # --- LISTE ANZEIGEN ---
            if not df.empty:
                df_display = df.sort_values(by='nummer', ascending=True)
                
                for _, row in df_display.iterrows():
                    
                    # Container Styling via CSS (simuliert)
                    with st.container():
                        c_text, c_img = st.columns([3, 1])
                        
                        with c_text:
                            label_header = f"{row['nummer']} - {row['bundesnummer']}"
                            if label_header.strip() in ["-", " - "]: label_header = "Ohne Nummer"

                            # WICHTIG: Beim Klick setzen wir die detail_id
                            if st.button(label_header, key=f"list_{row['id']}"):
                                st.session_state.detail_id = row['id']
                                st.rerun()
                            
                            strasse = row['strasse'] if row['strasse'] else ""
                            plz_ort = f"{row['plz']} {row['stadt']}".strip()
                            
                            st.markdown(f"<div class='address-text'>{strasse}<br>{plz_ort}</div>", unsafe_allow_html=True)
                        
                        with c_img:
                            if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                                st.image(row['bild_pfad'], use_container_width=True)
                        
                        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            else:
                st.info("Keine Einträge vorhanden.")

        elif mode == "Karte":
            # --- KARTE ANZEIGEN ---
            m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
            
            # Auto-Zoom beim ersten Laden der Karte
            if st.session_state.map_zoom == 5 and not df.empty:
                valid_coords = df[(df['breitengrad'] != 0) & (df['breitengrad'].notnull())]
                if not valid_coords.empty:
                    sw = valid_coords[['breitengrad', 'laengengrad']].min().values.tolist()
                    ne = valid_coords[['breitengrad', 'laengengrad']].max().values.tolist()
                    if sw == ne:
                        m = folium.Map(location=sw, zoom_start=14, tiles="OpenStreetMap")
                    else:
                        m.fit_bounds([sw, ne])

            for _, row in df.iterrows():
                if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                    c = "blue" if row['typ'] == "Dialog Display" else "gray"
                    
                    # Popup Bild
                    img_html = ""
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        b64_str = get_image_base64(row['bild_pfad'])
                        if b64_str:
                            img_html = f'<img src="data:image/jpeg;base64,{b64_str}" style="width:100%; border-radius:8px; margin-bottom:10px;">'
                    
                    popup_content = f"""
                    <div style="font-family:-apple-system, sans-serif; width:200px;">
                        {img_html}
                        <b>{row['nummer']}</b><br>{row['strasse']}
                    </div>
                    """
                    folium.Marker(
                        [row['breitengrad'], row['laengengrad']],
                        popup=folium.Popup(popup_content, max_width=250),
                        icon=folium.Icon(color=c, icon="info-sign")
                    ).add_to(m)
            
            # Karte über volle Breite und Höhe (für Mobile wichtig)
            st_folium(m, width="100%", height=600)

elif st.session_state.page == 'Verwaltung':
    st.header("Verwaltung")
    
    st.caption("Daten editieren & löschen")
    
    edit_data = df.copy()
    edit_data["Löschen?"] = False 

    column_cfg = {
        "Löschen?": st.column_config.CheckboxColumn("🗑️", width="small"),
        "id": None, "bild_pfad": None,
        "typ": st.column_config.SelectboxColumn("Typ", options=["Dialog Display", "Ohne"]),
        "letzte_kontrolle": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        "strasse": st.column_config.TextColumn("Straße"), "plz": st.column_config.TextColumn("PLZ"), 
        "stadt": st.column_config.TextColumn("Stadt"), "nummer": st.column_config.TextColumn("Nr."),
        "bundesnummer": st.column_config.TextColumn("B-Nr."),
        "breitengrad": st.column_config.NumberColumn("Lat", format="%.5f"),
        "laengengrad": st.column_config.NumberColumn("Lon", format="%.5f")
    }

    col_order = ["Löschen?", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad"]

    edited_df = st.data_editor(edit_data, column_config=column_cfg, num_rows="dynamic", use_container_width=True, hide_index=True, column_order=col_order)
    
    if st.button("Speichern", type="primary"):
        rows_to_keep = edited_df[edited_df["Löschen?"] == False]
        final_df = rows_to_keep.drop(columns=["Löschen?"])
        save_data(final_df)
        st.success("Gespeichert!")
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Bild-Verwaltung")
    
    if not df.empty:
        df_sorted = df.sort_values('nummer')
        options = {f"{r['nummer']} - {r['strasse']}": r['id'] for i, r in df_sorted.iterrows()}
        sel_label = st.selectbox("Eintrag wählen:", options.keys())
        sel_id = options[sel_label]
        
        curr = df[df['id'] == sel_id].iloc[0]
        if curr['bild_pfad'] and os.path.exists(curr['bild_pfad']):
            st.image(curr['bild_pfad'], width=200)
            
        up = st.file_uploader("Bild ändern", type=['jpg','png'])
        if st.button("Bild speichern"):
            if up:
                new_p = save_uploaded_image(up, sel_id)
                idx = df.index[df['id'] == sel_id].tolist()[0]
                df.at[idx, 'bild_pfad'] = new_p
                save_data(df)
                st.success("Bild gespeichert!")
                st.rerun()

elif st.session_state.page == 'Neuer Eintrag':
    st.header("Neuer Eintrag")
    
    with st.form("new", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nummer = c1.text_input("Nummer")
        bundesnummer = c2.text_input("Bundesnummer")
        
        st.markdown("---")
        col_str, col_plz, col_stadt = st.columns([2, 1, 1])
        strasse = col_str.text_input("Straße", placeholder="Heerstr. 12")
        plz = col_plz.text_input("PLZ", placeholder="10115")
        stadt = col_stadt.text_input("Stadt", placeholder="Berlin")
        
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_img = st.file_uploader("Foto (Optional)", type=['png', 'jpg'])
        
        with st.expander("Manuelle Koordinaten"):
            gc1, gc2 = st.columns(2)
            manual_lat = gc1.number_input("Lat", value=0.0, format="%.6f")
            manual_lon = gc2.number_input("Lon", value=0.0, format="%.6f")
        
        st.markdown("---")
        c_typ, c_dat = st.columns(2)
        typ = c_typ.selectbox("Typ", ["Dialog Display", "Ohne"])
        letzte_kontrolle = c_dat.date_input("Datum", datetime.date.today())
        
        if st.form_submit_button("Speichern", type="primary"):
            final_lat, final_lon = 0.0, 0.0
            new_id = pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
            
            img_path = ""
            if uploaded_img: img_path = save_uploaded_image(uploaded_img, new_id)

            if manual_lat != 0.0:
                final_lat, final_lon = manual_lat, manual_lon
            else:
                full = f"{strasse}, {plz} {stadt}"
                if strasse and stadt:
                    try:
                        loc = geocode(full)
                        if loc: final_lat, final_lon = loc.latitude, loc.longitude
                    except: pass
            
            new_row = pd.DataFrame({
                "id": [new_id], "nummer": [nummer], "bundesnummer": [bundesnummer], 
                "strasse": [strasse], "plz": [plz], "stadt": [stadt],
                "typ": [typ], "letzte_kontrolle": [letzte_kontrolle],
                "breitengrad": [final_lat], "laengengrad": [final_lon], "bild_pfad": [img_path]
            })
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Gespeichert!"
