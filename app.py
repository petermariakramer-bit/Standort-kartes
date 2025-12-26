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

def set_page(page_name):
    st.session_state.page = page_name

def set_map_focus(lat, lon):
    st.session_state.map_center = [lat, lon]
    st.session_state.map_zoom = 15

# --- HELPER: BILDER ---
IMAGE_FOLDER = 'data/images'
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

def save_uploaded_image(uploaded_file, entry_id):
    """Speichert ein hochgeladenes Bild und gibt den Pfad zurück."""
    if uploaded_file is None:
        return None
    
    file_ext = uploaded_file.name.split('.')[-1]
    file_name = f"{entry_id}.{file_ext}"
    file_path = os.path.join(IMAGE_FOLDER, file_name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def get_image_base64(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- CSS DESIGN ---
st.markdown("""
    <style>
    /* 1. GLOBAL */
    .stApp { background-color: #ffffff !important; }
    html, body, p, div, label, h1, h2, h3, .stMarkdown {
        color: #1d1d1f !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    header {visibility: hidden;}
    .block-container { padding-top: 1.5rem !important; max-width: 98% !important; }

    /* 2. HEADER */
    .app-title {
        font-size: 26px; font-weight: 700; color: #1d1d1f;
        margin: 0; line-height: 1.5; white-space: nowrap;
    }

    div[data-testid="stHorizontalBlock"] button {
        white-space: nowrap !important; height: auto !important;
        padding-top: 8px !important; padding-bottom: 8px !important; margin-top: 0px !important;
    }
    
    div[data-testid="column"] {
        display: flex; align-items: center !important; justify-content: flex-start;
    }

    /* 3. LISTE LINKS */
    div[data-testid="stVerticalBlock"] .stButton button {
        width: 100%; background-color: transparent; color: #0071e3; border: none;
        text-align: left !important; justify-content: flex-start !important; 
        padding-left: 0px !important; font-weight: 600 !important;
        font-size: 15px !important; margin: 0px !important; height: auto !important;
        box-shadow: none !important;
    }
    div[data-testid="stVerticalBlock"] .stButton button:hover {
        color: #005bb5; text-decoration: none;
    }
    
    .address-text {
        font-size: 13px; color: #86868b !important; 
        margin-top: -4px; margin-bottom: 12px; padding-left: 0px; line-height: 1.4; 
    }
    
    div[data-testid="stImage"] img {
        border-radius: 6px; object-fit: cover; height: 50px !important; width: 100% !important;
    }

    hr {
        margin-top: 5px !important; margin-bottom: 10px !important; border-color: #f5f5f7;
    }

    div[data-testid="column"]:nth-of-type(1) {
        border-right: 1px solid #e5e5ea; padding-right: 15px; 
    }
    
    /* 4. BUTTONS */
    button[kind="primary"] {
        background-color: #0071e3 !important; color: white !important;
        border: none !important; border-radius: 8px !important;
    }
    button[kind="secondary"] {
        background-color: #f5f5f7 !important; color: #1d1d1f !important;
        border: none !important; border-radius: 8px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #e5e5ea !important; color: #000 !important;
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

st.markdown("<div style='height: 1px; background-color: #e5e5ea; margin-top: 15px; margin-bottom: 25px;'></div>", unsafe_allow_html=True)


# --- DATEN LOGIK ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="dialog_app_image_edit")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def load_data():
    cols = ["id", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad", "bild_pfad"]
    if not os.path.exists(CSV_FILE):
        os.makedirs('data', exist_ok=True)
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
    
    col_list, col_map = st.columns([1, 3.5], gap="small")
    
    with col_list:
        if not df.empty:
             df_display = df.sort_values(by='nummer', ascending=True)
        else:
             df_display = df

        with st.container(height=750):
            if df_display.empty: st.caption("Keine Daten.")
            
            for _, row in df_display.iterrows():
                
                c_text, c_img = st.columns([3, 1])
                with c_text:
                    label_header = f"{row['nummer']} - {row['bundesnummer']}"
                    if label_header.strip() in ["-", " - "]: label_header = "Ohne Nummer"

                    if st.button(label_header, key=row['id']):
                         if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                            set_map_focus(row['breitengrad'], row['laengengrad'])
                            st.rerun()
                    
                    strasse = row['strasse'] if row['strasse'] else ""
                    plz_ort = f"{row['plz']} {row['stadt']}".strip()
                    
                    adress_html = f"""
                    <div class='address-text'>
                        {strasse}<br>
                        {plz_ort}
                    </div>
                    """
                    st.markdown(adress_html, unsafe_allow_html=True)
                
                with c_img:
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        st.image(row['bild_pfad'], use_container_width=True)
                
                st.markdown("<hr>", unsafe_allow_html=True)

    with col_map:
        m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
        
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
                
                img_html = ""
                if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                    b64_str = get_image_base64(row['bild_pfad'])
                    if b64_str:
                        img_html = f'<img src="data:image/jpeg;base64,{b64_str}" style="width:100%; border-radius:8px; margin-bottom:10px;">'
                
                popup = f"""
                <div style="font-family:-apple-system, sans-serif; width:220px; font-size:13px;">
                    {img_html}
                    <strong style="font-size:14px;">{row['nummer']} - {row['bundesnummer']}</strong><br>
                    <div style="color:#666; margin-top:4px;">
                        {row['strasse']}<br>
                        {row['plz']} {row['stadt']}
                    </div>
                    <hr style="border:0; border-top:1px solid #eee; margin:8px 0;">
                    <span style="color:#888;">Letzte Kontrolle: {row['letzte_kontrolle']}</span>
                </div>
                """
                
                folium.Marker(
                    [row['breitengrad'], row['laengengrad']],
                    popup=folium.Popup(popup, max_width=250),
                    tooltip=f"{row['nummer']}",
                    icon=folium.Icon(color=c, icon="info-sign")
                ).add_to(m)
        st_folium(m, width="100%", height=750)

elif st.session_state.page == 'Verwaltung':
    st.header("Datenbank Verwaltung")
    
    # 1. TABELLE ANZEIGEN (Daten bearbeiten)
    st.caption("Hier können Textdaten direkt bearbeitet werden.")
    
    edit_data = df.copy()
    edit_data["Löschen?"] = False 

    column_cfg = {
        "Löschen?": st.column_config.CheckboxColumn("🗑️", width="small"),
        "id": None,
        "bild_pfad": None,
        "typ": st.column_config.SelectboxColumn("Typ", options=["Dialog Display", "Ohne"]),
        "letzte_kontrolle": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        "strasse": st.column_config.TextColumn("Straße & Nr."),
        "plz": st.column_config.TextColumn("PLZ"), 
        "stadt": st.column_config.TextColumn("Stadt"),
        "nummer": st.column_config.TextColumn("Nummer"),
        "bundesnummer": st.column_config.TextColumn("Bundes-Nr."),
        "breitengrad": st.column_config.NumberColumn("Lat", format="%.5f"),
        "laengengrad": st.column_config.NumberColumn("Lon", format="%.5f")
    }

    col_order = ["Löschen?", "nummer", "bundesnummer", "strasse", "plz", "stadt", "typ", "letzte_kontrolle", "breitengrad", "laengengrad"]

    edited_df = st.data_editor(
        edit_data, 
        column_config=column_cfg,
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_order=col_order
    )
    
    col_save, col_dummy = st.columns([1, 4])
    with col_save:
        if st.button("Tabellen-Änderungen speichern", type="primary"):
            rows_to_keep = edited_df[edited_df["Löschen?"] == False]
            final_df = rows_to_keep.drop(columns=["Löschen?"])
            save_data(final_df)
            st.success("Tabelle gespeichert!")
            st.rerun()

    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
    
    # 2. BILD NACHTRÄGLICH HOCHLADEN
    st.subheader("📸 Bild für Eintrag hinzufügen / ändern")
    
    if not df.empty:
        # Dropdown Liste vorbereiten: "Nummer - Straße" für einfachere Auswahl
        # Wir erstellen ein Dictionary: "Label" -> "ID"
        df_sorted = df.sort_values('nummer')
        options = {f"{r['nummer']} - {r['strasse']} ({r['stadt']})": r['id'] for i, r in df_sorted.iterrows()}
        
        selected_label = st.selectbox("Wähle einen Standort aus:", options.keys())
        selected_id = options[selected_label]
        
        # Zeige aktuelles Bild falls vorhanden
        current_entry = df[df['id'] == selected_id].iloc[0]
        if current_entry['bild_pfad'] and os.path.exists(current_entry['bild_pfad']):
            st.image(current_entry['bild_pfad'], width=300, caption="Aktuelles Bild")
        else:
            st.info("Kein Bild vorhanden.")
            
        # Upload
        uploaded_update = st.file_uploader("Neues Bild hochladen", type=['png', 'jpg', 'jpeg'], key="update_img")
        
        if st.button("Bild speichern"):
            if uploaded_update:
                new_path = save_uploaded_image(uploaded_update, selected_id)
                
                # DataFrame aktualisieren
                # Wir müssen den Index der Zeile mit der ID finden
                idx = df.index[df['id'] == selected_id].tolist()[0]
                df.at[idx, 'bild_pfad'] = new_path
                
                save_data(df)
                st.success("Bild erfolgreich aktualisiert!")
                st.rerun()
            else:
                st.error("Bitte erst eine Datei auswählen.")
    else:
        st.info("Noch keine Einträge vorhanden.")

elif st.session_state.page == 'Neuer Eintrag':
    st.header("Neuer Eintrag")
    
    with st.form("new_entry_form", clear_on_submit=False):
        st.caption("Identifikation")
        c1, c2 = st.columns(2)
        nummer = c1.text_input("Nummer")
        bundesnummer = c2.text_input("Bundesnummer")
        
        st.markdown("---")
        st.caption("Adresse & Bild")
        
        col_str, col_plz, col_stadt = st.columns([2, 1, 1])
        strasse = col_str.text_input("Straße & Hausnummer", placeholder="Heerstr. 12")
        plz = col_plz.text_input("PLZ", placeholder="10115")
        stadt = col_stadt.text_input("Stadt", placeholder="Berlin")
        
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_img = st.file_uploader("Standort-Foto hochladen (Optional)", type=['png', 'jpg', 'jpeg'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📍 Koordinaten manuell eingeben (Optional)", expanded=False):
            gc1, gc2 = st.columns(2)
            manual_lat = gc1.number_input("Breitengrad (Lat)", value=0.0, format="%.6f")
            manual_lon = gc2.number_input("Längengrad (Lon)", value=0.0, format="%.6f")
        
        st.markdown("---")
        c_typ, c_dat = st.columns(2)
        typ = c_typ.selectbox("Typ", ["Dialog Display", "Ohne"])
        letzte_kontrolle = c_dat.date_input("Letzte Kontrolle", datetime.date.today())
        
        if st.form_submit_button("Speichern", type="primary"):
            final_lat, final_lon = 0.0, 0.0
            new_id = pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
            
            img_path = ""
            if uploaded_img is not None:
                img_path = save_uploaded_image(uploaded_img, new_id)

            if manual_lat != 0.0 or manual_lon != 0.0:
                final_lat = manual_lat
                final_lon = manual_lon
            else:
                full_address = f"{strasse}, {plz} {stadt}"
                if strasse and stadt:
                    try:
                        loc = geocode(full_address)
                        if loc: 
                            final_lat, final_lon = loc.latitude, loc.longitude
                            st.success(f"Gefunden: {loc.address}")
                    except: pass
            
            new_row = pd.DataFrame({
                "id": [new_id],
                "nummer": [nummer], "bundesnummer": [bundesnummer], 
                "strasse": [strasse], "plz": [plz], "stadt": [stadt],
                "typ": [typ], "letzte_kontrolle": [letzte_kontrolle],
                "breitengrad": [final_lat], "laengengrad": [final_lon],
                "bild_pfad": [img_path]
            })
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Standort & Bild gespeichert!")
