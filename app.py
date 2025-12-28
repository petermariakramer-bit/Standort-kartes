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

# State für Detail-Ansicht
if 'detail_id' not in st.session_state:
    st.session_state.detail_id = None

def set_page(page_name):
    st.session_state.page = page_name
    st.session_state.detail_id = None # Details resetten bei Seitenwechsel

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
    /* Weniger Padding oben für App-Feeling */
    .block-container { padding-top: 0.5rem !important; max-width: 100% !important; padding-left: 1rem; padding-right: 1rem; }

    /* 2. HEADER & TITEL */
    .app-title {
        font-size: 22px; font-weight: 700; color: #1d1d1f;
        margin: 0; line-height: 2.5rem; white-space: nowrap;
    }

    /* 3. NAVIGATION ICONS (RECHTS OBEN) */
    /* Wir machen die Buttons transparent und groß */
    div[data-testid="stHorizontalBlock"] button {
        background-color: transparent !important;
        border: none !important;
        padding: 0px !important;
        margin: 0px !important;
        font-size: 20px !important; /* Icon Größe */
        line-height: 1 !important;
        min-height: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        color: #0071e3 !important;
        background-color: transparent !important;
    }
    /* Das aktive Icon blau färben */
    button[kind="primary"] span {
        color: #0071e3 !important;
    }

    /* 4. LISTE STYLING MIT TRENNLINIEN */
    /* Container für einen Listeneintrag */
    .list-entry-container {
        padding-top: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid #d1d1d6; /* Deutliche Trennlinie (iOS Grau) */
    }

    /* Button Text Links */
    div[data-testid="stVerticalBlock"] .stButton button {
        width: 100%; background-color: transparent; color: #0071e3; border: none;
        text-align: left !important; justify-content: flex-start !important; 
        padding-left: 0px !important; font-weight: 600 !important;
        font-size: 17px !important; margin: 0px !important; height: auto !important;
        box-shadow: none !important;
    }
    
    .address-text {
        font-size: 13px; color: #86868b !important; 
        margin-top: -2px; line-height: 1.4; 
    }
    
    /* Bild in der Liste */
    div[data-testid="stImage"] img {
        border-radius: 8px; object-fit: cover; height: 55px !important; width: 100% !important;
    }

    /* 5. SEGMENTED CONTROL */
    div.row-widget.stRadio > div {
        flex-direction: row; background-color: #f2f2f7; padding: 3px;
        border-radius: 9px; width: 100%; justify-content: center; margin-top: 10px;
    }
    div.row-widget.stRadio > div > label {
        background-color: transparent; border: none; padding: 5px 10px;
        border-radius: 7px; margin: 0; width: 50%; text-align: center;
        justify-content: center; cursor: pointer; font-weight: 500; color: #666 !important;
    }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background-color: #ffffff; color: #000 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15); font-weight: 600;
    }

    /* Ausrichtung fixen */
    div[data-testid="column"] { align-items: center; display: flex; }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGATION (NEU: ICONS RECHTS) ---
# Layout: [Titel (groß), Spacer, Icon1, Icon2, Icon3]
# Wir geben dem Titel viel Platz (6), dann spacer (3), dann kleine Slots für Icons (1)
c_title, c_space, c_home, c_manage, c_add = st.columns([6, 2, 1, 1, 1])

with c_title:
    st.markdown('<div class="app-title">Dialog Displays</div>', unsafe_allow_html=True)

# Icon 1: Übersicht (Haus)
with c_home:
    btn_type = "primary" if st.session_state.page == "Übersicht" else "secondary"
    # Wir nutzen Emojis als Icons. Alternativ könnte man Material Icons via Markdown nutzen.
    if st.button("🏠", type=btn_type, help="Übersicht", use_container_width=True):
        set_page("Übersicht"); st.rerun()

# Icon 2: Verwaltung (Zahnrad oder Liste)
with c_manage:
    btn_type = "primary" if st.session_state.page == "Verwaltung" else "secondary"
    if st.button("⚙️", type=btn_type, help="Verwaltung", use_container_width=True):
        set_page("Verwaltung"); st.rerun()

# Icon 3: Neuer Eintrag (Plus)
with c_add:
    btn_type = "primary" if st.session_state.page == "Neuer Eintrag" else "secondary"
    if st.button("➕", type=btn_type, help="Neuer Eintrag", use_container_width=True):
        set_page("Neuer Eintrag"); st.rerun()

# Feine Linie unter dem Header
st.markdown("<div style='height: 1px; background-color: #e5e5ea; margin-top: 10px; margin-bottom: 10px;'></div>", unsafe_allow_html=True)


# --- DATEN LOGIK ---
CSV_FILE = 'data/locations.csv'
geolocator = Nominatim(user_agent="dialog_app_v5_icons")
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
    
    # --- DETAIL ANSICHT ---
    if st.session_state.detail_id is not None:
        if st.button("← Zurück", type="secondary"):
            st.session_state.detail_id = None
            st.rerun()
            
        entry = df[df['id'] == st.session_state.detail_id].iloc[0]
        
        st.markdown(f"## {entry['nummer']} - {entry['bundesnummer']}")
        st.caption(f"{entry['strasse']}, {entry['plz']} {entry['stadt']}")
        
        if entry['bild_pfad'] and os.path.exists(entry['bild_pfad']):
            st.image(entry['bild_pfad'], use_container_width=True)
            
        st.markdown("---")
        
        c_det1, c_det2 = st.columns(2)
        with c_det1:
            st.markdown(f"**Typ:** {entry['typ']}")
            st.markdown(f"**Hersteller:** {entry['hersteller']}")
            st.markdown(f"**Baujahr:** {entry['baujahr']}")
        with c_det2:
            st.markdown(f"**Kontrolle:** {entry['letzte_kontrolle']}")
            
        if entry['breitengrad'] != 0:
            st.markdown("### Karte")
            m_detail = folium.Map(location=[entry['breitengrad'], entry['laengengrad']], zoom_start=16, tiles="OpenStreetMap")
            folium.Marker(
                [entry['breitengrad'], entry['laengengrad']],
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m_detail)
            st_folium(m_detail, width="100%", height=250)

    # --- LISTE / KARTE ---
    else:
        mode = st.radio("Ansicht", ["Liste", "Karte"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Liste":
            if not df.empty:
                df_display = df.sort_values(by='nummer', ascending=True)
                
                # Container für die Liste
                with st.container():
                    for _, row in df_display.iterrows():
                        
                        # --- EIN LISTENEINTRAG ---
                        # Wir nutzen Columns für das Layout (Text links, Bild rechts)
                        # Das CSS .list-entry-container sorgt für die Linie unten
                        
                        col_content, col_img = st.columns([3.5, 1])
                        
                        with col_content:
                            label_header = f"{row['nummer']} - {row['bundesnummer']}"
                            if label_header.strip() in ["-", " - "]: label_header = "Ohne Nummer"

                            # Der Name ist der Button
                            if st.button(label_header, key=f"list_{row['id']}"):
                                st.session_state.detail_id = row['id']
                                st.rerun()
                            
                            strasse = row['strasse'] if row['strasse'] else ""
                            plz_ort = f"{row['plz']} {row['stadt']}".strip()
                            st.markdown(f"<div class='address-text'>{strasse}<br>{plz_ort}</div>", unsafe_allow_html=True)
                        
                        with col_img:
                            if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                                st.image(row['bild_pfad'], use_container_width=True)
                        
                        # Die Trennlinie wird nun hier eingefügt, aber wir nutzen besser 
                        # eine CSS Klasse im Loop oder einfach eine HR
                        st.markdown("<div style='border-bottom: 1px solid #e5e5ea; margin-top: 10px; margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            else:
                st.info("Keine Einträge.")

        elif mode == "Karte":
            m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
            
            if st.session_state.map_zoom == 5 and not df.empty:
                valid_coords = df[(df['breitengrad'] != 0) & (df['breitengrad'].notnull())]
                if not valid_coords.empty:
                    sw = valid_coords[['breitengrad', 'laengengrad']].min().values.tolist()
                    ne = valid_coords[['breitengrad', 'laengengrad']].max().values.tolist()
                    if sw != ne: m.fit_bounds([sw, ne])

            for _, row in df.iterrows():
                if pd.notnull(row['breitengrad']) and row['breitengrad'] != 0:
                    c = "blue" if row['typ'] == "Dialog Display" else "gray"
                    
                    img_html = ""
                    if row['bild_pfad'] and os.path.exists(row['bild_pfad']):
                        b64_str = get_image_base64(row['bild_pfad'])
                        if b64_str:
                            img_html = f'<img src="data:image/jpeg;base64,{b64_str}" style="width:100%; border-radius:8px; margin-bottom:10px;">'
                    
                    popup_content = f"""
                    <div style="font-family:-apple-system, sans-serif; width:180px;">
                        {img_html}
                        <b>{row['nummer']}</b><br>{row['strasse']}
                    </div>
                    """
                    folium.Marker(
                        [row['breitengrad'], row['laengengrad']],
                        popup=folium.Popup(popup_content, max_width=250),
                        icon=folium.Icon(color=c, icon="info-sign")
                    ).add_to(m)
            
            st_folium(m, width="100%", height=600)

elif st.session_state.page == 'Verwaltung':
    st.header("Verwaltung")
    
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
    
    if st.button("💾 Speichern", type="primary"):
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
            st.image(curr['bild_pfad'], width=150)
            
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
        
        col_str, col_plz, col_stadt = st.columns([2, 1, 1])
        strasse = col_str.text_input("Straße", placeholder="Heerstr. 12")
        plz = col_plz.text_input("PLZ", placeholder="10115")
        stadt = col_stadt.text_input("Stadt", placeholder="Berlin")
        
        c_her, c_bau = st.columns(2)
        hersteller = c_her.text_input("Hersteller")
        baujahr = c_bau.text_input("Baujahr")
        
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
                "breitengrad": [final_lat], "laengengrad": [final_lon], "bild_pfad": [img_path],
                "hersteller": [hersteller], "baujahr": [baujahr]
            })
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Gespeichert!")
