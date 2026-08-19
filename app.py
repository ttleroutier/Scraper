"""Streamlit UI: settings, live table, exports."""

import threading
import time
from datetime import datetime

import streamlit as st

import config
import storage
from geo import geocode_address
from models import RateSettings, SearchConfig
from scraper import ScrapeController, run_scrape
from website_enricher import enrich

st.set_page_config(page_title="Maps Lead Finder", layout="wide")
storage.init_db()


# ------------------------------------------------------- 1. APP STATE
def get_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


controller: ScrapeController = get_state("controller", ScrapeController())
get_state("thread", None)
get_state("run_id", None)


# --------------------------------------------------- 2. WORKER LAUNCH
def start_run(search: SearchConfig, rates: RateSettings, run_id: str, enrich_sites: bool):
    new_controller = ScrapeController()
    st.session_state.controller = new_controller
    st.session_state.run_id = run_id

    def on_result(place):
        if enrich_sites and place.website:
            email, description = enrich(place.website)
            place.email = email
            place.description = place.description or description
        storage.save_place(place, run_id)

    thread = threading.Thread(
        target=run_scrape,
        args=(search, rates, new_controller, on_result, storage.known_place_ids(run_id)),
        daemon=True,
    )
    thread.start()
    st.session_state.thread = thread


# ------------------------------------------------------- 3. SIDEBAR UI
with st.sidebar:
    st.header("Recherche")
    keyword = st.text_input("Mot-clé", "plombier")

    mode = st.radio("Point central", ["Adresse", "Coordonnées GPS"])
    if mode == "Adresse":
        address = st.text_input("Adresse", "Lyon, France")
        latitude = longitude = None
    else:
        latitude = st.number_input("Latitude", value=45.7640, format="%.6f")
        longitude = st.number_input("Longitude", value=4.8357, format="%.6f")
        address = None

    radius_km = st.slider("Rayon (km)", 1, 50, 10)
    max_results = st.number_input("Nombre max de fiches", 10, 2000, config.DEFAULT_MAX_RESULTS, step=10)

    st.header("Cadence")
    delay_min, delay_max = st.slider(
        "Délai entre fiches (s)", 0.5, 20.0,
        (config.DEFAULT_DELAY_MIN, config.DEFAULT_DELAY_MAX), step=0.5,
    )
    pause_every = st.number_input("Pause longue toutes les N fiches", 0, 200, config.DEFAULT_PAUSE_EVERY)
    pause_min, pause_max = st.slider(
        "Durée de la pause longue (s)", 5.0, 300.0,
        (config.DEFAULT_PAUSE_MIN, config.DEFAULT_PAUSE_MAX), step=5.0,
    )

    enrich_sites = st.checkbox("Chercher email + description sur le site", value=config.ENRICH_WEBSITES)


# ----------------------------------------------------- 4. CONTROL BAR
st.title("Maps Lead Finder")
col_start, col_pause, col_resume, col_stop = st.columns(4)

if col_start.button("▶ Start", use_container_width=True):
    if mode == "Adresse":
        geocoded = geocode_address(address)
        if not geocoded:
            st.error("Adresse introuvable.")
            st.stop()
        latitude, longitude, label = geocoded
        st.info(f"Point central : {label}")

    run_id = f"{keyword}_{datetime.now():%Y%m%d_%H%M%S}"
    start_run(
        SearchConfig(keyword, latitude, longitude, radius_km, int(max_results)),
        RateSettings(delay_min, delay_max, int(pause_every), pause_min, pause_max),
        run_id,
        enrich_sites,
    )

if col_pause.button("⏸ Pause", use_container_width=True):
    controller.pause()
if col_resume.button("⏵ Resume", use_container_width=True):
    controller.resume()
if col_stop.button("⏹ Stop", use_container_width=True):
    controller.stop()


# --------------------------------------------------------- 5. STATUS
controller = st.session_state.controller
stat_1, stat_2, stat_3, stat_4 = st.columns(4)
stat_1.metric("Statut", controller.status)
stat_2.metric("Fiches listées", controller.stats.found)
stat_3.metric("Enregistrées", controller.stats.saved)
stat_4.metric("Hors rayon", controller.stats.skipped_out_of_radius)

if controller.captcha_detected:
    st.warning("CAPTCHA détecté. Résolvez-le dans la fenêtre du navigateur, puis cliquez sur Resume.")


# ----------------------------------------------------- 6. LIVE TABLE
run_id = st.session_state.run_id
frame = storage.load_dataframe(run_id) if run_id else storage.load_dataframe()

visible_columns = [
    "name", "distance_km", "address", "phone", "email",
    "website", "category", "rating", "description",
]
if not frame.empty:
    st.dataframe(
        frame[[c for c in visible_columns if c in frame.columns]],
        use_container_width=True, height=520,
    )
else:
    st.info("Aucun résultat pour le moment.")


# --------------------------------------------------------- 7. EXPORT
if not frame.empty:
    export_1, export_2 = st.columns(2)
    export_1.download_button(
        "⬇ Excel", storage.dataframe_to_excel_bytes(frame),
        file_name=f"{run_id or 'results'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    export_2.download_button(
        "⬇ CSV", storage.dataframe_to_csv_bytes(frame),
        file_name=f"{run_id or 'results'}.csv",
        mime="text/csv", use_container_width=True,
    )

if controller.stats.errors:
    with st.expander(f"Erreurs ({len(controller.stats.errors)})"):
        st.write(controller.stats.errors[-50:])


# ----------------------------------------------------- 8. AUTO REFRESH
thread = st.session_state.thread
if thread is not None and thread.is_alive():
    time.sleep(3)
    st.rerun()
