"""
app.py — Loopbaanoriëntatie

Authenticatie via JWT-token van bovenbouwsucces.nl portaal.
Rol-logica:
  - leerling  → student
  - docent/beheerder → teacher (docenten-dashboard)
  - lob_coordinator in app_rollen.lob → ook teacher
"""

import streamlit as st
import jwt
import os
import db

JWT_SECRET    = os.environ.get("JWT_SECRET", "verander-dit-naar-een-lang-geheim")
JWT_ALGORITHM = "HS256"

st.set_page_config(
    page_title="Loopbaanoriëntatie",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.task-card { padding:18px;border-radius:12px;text-align:center;margin-bottom:8px; }
.task-card h4 { margin:0 0 6px 0; }
.task-card p  { margin:0;font-size:0.85em; }
.dot-green  { color:#27ae60;font-size:1.3em; }
.dot-grey   { color:#bdc3c7;font-size:1.3em; }
.progress-full { color:#27ae60;font-weight:bold; }
.progress-half { color:#e67e22;font-weight:bold; }
.progress-none { color:#e74c3c;font-weight:bold; }
</style>
""", unsafe_allow_html=True)

db.init_db()

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("eckid", None), ("naam", None), ("role", None),
    ("mentorgroep", None), ("current_task", "home"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def logout():
    st.session_state.clear()
    st.rerun()


# ── SSO token verwerken ───────────────────────────────────────────────────────

def _verwerk_sso_token():
    if st.session_state.eckid:
        return

    token = st.query_params.get("token")
    if not token:
        return

    try:
        payload    = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        eckid      = payload.get("eckid")
        naam       = payload.get("naam", "Onbekend")
        klas       = payload.get("klas")
        portal_rol = payload.get("rol", "")
        app_rollen = payload.get("app_rollen", {})

        # Rol-logica
        if portal_rol == "leerling":
            role = "student"
        elif portal_rol in ("docent", "beheerder") or app_rollen.get("lob") == "lob_coordinator":
            role = "teacher"
        else:
            role = None

        if not eckid or not role:
            st.query_params.clear()
            st.warning("Je hebt geen toegang tot de LOB-app. Neem contact op met je mentor.")
            return

        if role == "student":
            student = db.sso_upsert_student(eckid=eckid, naam=naam, klas=klas)
            st.session_state.mentorgroep = student["mentorgroep"]

        st.session_state.eckid        = eckid
        st.session_state.naam         = naam
        st.session_state.role         = role
        st.session_state.current_task = "home"
        st.query_params.clear()
        st.rerun()

    except jwt.ExpiredSignatureError:
        st.query_params.clear()
        st.warning("Je sessie is verlopen. Ga terug naar het portaal en probeer opnieuw.")
    except jwt.InvalidTokenError:
        st.query_params.clear()
        st.error("Ongeldig token. Neem contact op met de beheerder.")

_verwerk_sso_token()

# ── Geen toegang ──────────────────────────────────────────────────────────────

if not st.session_state.eckid:
    st.title("Loopbaanoriëntatie")
    st.warning(
        "Je hebt geen directe toegang tot deze pagina. "
        "Log in via het portaal op [bovenbouwsucces.nl](https://bovenbouwsucces.nl)."
    )
    st.stop()

# ── Student view ──────────────────────────────────────────────────────────────

if st.session_state.role == "student":
    eckid = st.session_state.eckid

    TASKS = [
        ("home",  "Home"),
        ("task1", "Vervolgopleiding"),
        ("task2", "Oriëntatie"),
        ("task3", "Open Dagen"),
        ("task4", "Interviews"),
    ]

    with st.sidebar:
        st.markdown(f"**{st.session_state.naam}**")
        if st.session_state.mentorgroep:
            st.caption(f"Mentorgroep: {st.session_state.mentorgroep}")
        st.divider()

        completion = db.task_completion(eckid)
        for key, label in TASKS:
            if key == "home":
                if st.button("Home", use_container_width=True):
                    st.session_state.current_task = "home"
                    st.rerun()
            else:
                icon = "🟢" if completion[key] else "⚪"
                if st.button(f"{icon}  {label}", use_container_width=True, key=f"nav_{key}"):
                    st.session_state.current_task = key
                    st.rerun()

        st.divider()
        if st.button("Uitloggen", use_container_width=True):
            logout()

    task = st.session_state.current_task

    if task == "home":
        completion = db.task_completion(eckid)
        naam_kort  = st.session_state.naam.split()[0]
        done       = sum(completion.values())

        st.title(f"Hallo {naam_kort}!")
        st.write(f"Je hebt **{done} van de 4** taken afgerond.")

        CARDS = [
            ("task1", "Vervolgopleiding", "Vul in wat je wilt worden en gaan studeren.", "#2980b9"),
            ("task2", "Oriëntatie",       "Ontdek welke beroepen bij jou passen.",       "#8e44ad"),
            ("task3", "Open Dagen",        "Plan en noteer open dag bezoeken.",            "#16a085"),
            ("task4", "Interviews",         "Interview 3 mensen over hun werk.",            "#c0392b"),
        ]

        cols = st.columns(4)
        for col, (key, label, desc, color) in zip(cols, CARDS):
            done_task  = completion[key]
            bg         = color if done_task else "#ecf0f1"
            text_color = "#fff" if done_task else "#2c3e50"
            with col:
                st.markdown(f"""
                <div class="task-card" style="background:{bg};color:{text_color};">
                    <h4>{"✓ " if done_task else ""}{label}</h4>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Open", key=f"card_{key}", use_container_width=True):
                    st.session_state.current_task = key
                    st.rerun()

    elif task == "task1":
        st.header("Vervolgopleiding")
        st.write("Vul in wat je plannen zijn na de havo.")
        data = db.get_task("task1", eckid)

        with st.form("task1_form"):
            beroep    = st.text_input("Beoogd beroep",         value=data.get("beoogd_beroep", ""))
            opleiding = st.text_input("Beoogde opleiding",     value=data.get("beoogde_opleiding", ""))
            stad      = st.text_input("Stad van de opleiding", value=data.get("stad", ""))
            st.divider()
            st.write("**Mijlpalen**")
            c1, c2, c3    = st.columns(3)
            open_dag      = c1.checkbox("Open dag bezocht",   value=bool(data.get("open_dag", 0)))
            meeloopdag    = c2.checkbox("Meeloopdag bezocht", value=bool(data.get("meeloopdag", 0)))
            ingeschreven  = c3.checkbox("Ingeschreven",       value=bool(data.get("ingeschreven", 0)))

            if st.form_submit_button("Opslaan", type="primary"):
                db.save_task1(eckid, {
                    "beoogd_beroep": beroep, "beoogde_opleiding": opleiding, "stad": stad,
                    "open_dag": open_dag, "meeloopdag": meeloopdag, "ingeschreven": ingeschreven,
                })
                st.success("Opgeslagen!")
                st.rerun()

    elif task == "task2":
        st.header("Oriëntatie")
        st.info("Maak eerst de beroepskeuzetest via de link hieronder. Vul daarna de velden in.")
        st.markdown("**[Doe de beroepskeuzetest op 123test.nl](https://www.123test.nl/beroepskeuzetest/)**")
        st.divider()

        data = db.get_task("task2", eckid)
        with st.form("task2_form"):
            beroepen    = st.text_area("Beroepen die bij mij passen (één per regel)",        value=data.get("beroepen", ""),    height=120)
            opleidingen = st.text_area("Opleidingen die ik interessant vind (één per regel)", value=data.get("opleidingen", ""), height=120)
            reflectie   = st.text_area("Mijn reflectie — wat vond ik van de uitkomsten?",    value=data.get("reflectie", ""),   height=160)

            if st.form_submit_button("Opslaan", type="primary"):
                db.save_task2(eckid, {"beroepen": beroepen, "opleidingen": opleidingen, "reflectie": reflectie})
                st.success("Opgeslagen!")
                st.rerun()

    elif task == "task3":
        st.header("Open Dagen")
        st.info("Noteer hieronder je open dag bezoeken.")

        with st.expander("Bekende open dagen (wordt uitgebreid)"):
            st.markdown("""
| School | Type | Datum | Inschrijven voor |
|--------|------|-------|-----------------|
| Hogeschool Utrecht | HBO | Nov 2026 | 1 mei |
| Windesheim Zwolle | HBO | Okt 2026 | 1 mei |
| ROC Midden Nederland | MBO | Doorlopend | — |
| Hogeschool van Amsterdam | HBO | Nov 2026 | 1 mei |
""")

        st.divider()
        data = db.get_task("task3", eckid)
        with st.form("task3_form"):
            notities = st.text_area(
                "Mijn open dag bezoeken — welke school, wanneer, wat vond je ervan?",
                value=data.get("notities", ""), height=220,
            )
            if st.form_submit_button("Opslaan", type="primary"):
                db.save_task3(eckid, {"notities": notities})
                st.success("Opgeslagen!")
                st.rerun()

    elif task == "task4":
        st.header("Beroepsinterviews")
        st.write("Interview drie mensen uit je omgeving over hun werk. Schrijf per persoon een verslag van **minimaal 300 woorden**.")

        VOORBEELD_VRAGEN = (
            "**Voorbeeldvragen:**  \n"
            "- Wat is een typische werkdag voor jou?  \n"
            "- Wat vind je het leukst aan je werk?  \n"
            "- Wat zijn de moeilijkste kanten?  \n"
            "- Welke opleiding heb je gedaan?  \n"
            "- Wat zou je anders doen als je opnieuw mocht kiezen?  \n"
            "- Welke eigenschappen heb je nodig in jouw beroep?"
        )

        interviews = db.get_task4(eckid)
        for nr in [1, 2, 3]:
            iv              = interviews.get(nr, {})
            reflectie_saved = iv.get("reflectie", "")
            wc              = len(reflectie_saved.split()) if reflectie_saved.strip() else 0
            done            = wc >= 300
            naam_display    = iv.get("naam_persoon") or f"Interview {nr}"
            status          = "✅" if done else f"({wc}/300 woorden)"

            with st.expander(f"Interview {nr} — {naam_display}  {status}", expanded=not done):
                st.markdown(VOORBEELD_VRAGEN)
                st.divider()
                with st.form(f"task4_{nr}"):
                    naam    = st.text_input("Naam van de persoon",             value=iv.get("naam_persoon", ""))
                    beroep  = st.text_input("Beroep",                          value=iv.get("beroep", ""))
                    relatie = st.text_input("Relatie (bijv. moeder, buurman)", value=iv.get("relatie", ""))
                    verslag = st.text_area("Jouw verslag", value=reflectie_saved, height=250, help="Minimaal 300 woorden.")
                    wc_live = len(verslag.split()) if verslag.strip() else 0
                    kleur   = "#27ae60" if wc_live >= 300 else "#e74c3c"
                    st.markdown(f"<span style='color:{kleur};font-weight:bold;'>{wc_live} / 300 woorden</span>", unsafe_allow_html=True)
                    if st.form_submit_button("Opslaan", type="primary"):
                        db.save_task4_interview(eckid, nr, {"naam_persoon": naam, "beroep": beroep, "relatie": relatie, "reflectie": verslag})
                        st.success("Opgeslagen!")
                        st.rerun()


# ── Teacher view ──────────────────────────────────────────────────────────────

elif st.session_state.role == "teacher":
    with st.sidebar:
        st.markdown(f"**{st.session_state.naam}**")
        st.caption("Docent")
        st.divider()
        menu = st.radio("Weergave", ["Voortgang klas"], label_visibility="collapsed")
        st.divider()
        if st.button("Uitloggen", use_container_width=True):
            logout()

    if menu == "Voortgang klas":
        st.title("Voortgang Loopbaanoriëntatie")

        students = db.get_all_students()
        groepen  = sorted({s["mentorgroep"] for s in students if s["mentorgroep"]})
        selected = st.selectbox("Mentorgroep", ["Alle groepen"] + groepen)

        if selected != "Alle groepen":
            students = [s for s in students if s["mentorgroep"] == selected]

        st.write(f"**{len(students)} leerling(en)**")
        st.divider()

        TASK_LABELS = ["Vervolgopleiding", "Oriëntatie", "Open Dagen", "Interviews"]
        TASK_KEYS   = ["task1", "task2", "task3", "task4"]

        h_cols = st.columns([3, 1, 1, 1, 1, 1])
        h_cols[0].markdown("**Naam**")
        for i, label in enumerate(TASK_LABELS):
            h_cols[i + 1].markdown(f"**{label}**")
        h_cols[5].markdown("**Totaal**")
        st.divider()

        for student in students:
            eckid      = student["eckid"]
            completion = db.task_completion(eckid)
            done_count = sum(completion.values())

            row_cols = st.columns([3, 1, 1, 1, 1, 1])
            row_cols[0].write(f"{student['naam']}  \n*{student['mentorgroep']}*")
            for i, key in enumerate(TASK_KEYS):
                if completion[key]:
                    row_cols[i + 1].markdown("<span class='dot-green'>●</span>", unsafe_allow_html=True)
                else:
                    row_cols[i + 1].markdown("<span class='dot-grey'>●</span>", unsafe_allow_html=True)

            if done_count == 4:
                row_cols[5].markdown("<span class='progress-full'>4/4</span>", unsafe_allow_html=True)
            elif done_count >= 2:
                row_cols[5].markdown(f"<span class='progress-half'>{done_count}/4</span>", unsafe_allow_html=True)
            else:
                row_cols[5].markdown(f"<span class='progress-none'>{done_count}/4</span>", unsafe_allow_html=True)

            with st.expander(f"Bekijk invullingen — {student['naam']}"):
                t1 = db.get_task("task1", eckid)
                t2 = db.get_task("task2", eckid)
                t3 = db.get_task("task3", eckid)
                t4 = db.get_task4(eckid)

                dc1, dc2, dc3, dc4 = st.tabs(TASK_LABELS)
                with dc1:
                    if t1:
                        st.write(f"**Beroep:** {t1.get('beoogd_beroep') or '—'}")
                        st.write(f"**Opleiding:** {t1.get('beoogde_opleiding') or '—'}")
                        st.write(f"**Stad:** {t1.get('stad') or '—'}")
                        st.write(f"Open dag: {'✅' if t1.get('open_dag') else '⬜'}  Meeloopdag: {'✅' if t1.get('meeloopdag') else '⬜'}  Ingeschreven: {'✅' if t1.get('ingeschreven') else '⬜'}")
                    else:
                        st.write("Nog niets ingevuld.")
                with dc2:
                    if t2:
                        st.write("**Beroepen:**"); st.write(t2.get("beroepen") or "—")
                        st.write("**Opleidingen:**"); st.write(t2.get("opleidingen") or "—")
                        st.write("**Reflectie:**"); st.write(t2.get("reflectie") or "—")
                    else:
                        st.write("Nog niets ingevuld.")
                with dc3:
                    st.write(t3.get("notities") or "—") if t3 else st.write("Nog niets ingevuld.")
                with dc4:
                    if t4:
                        for nr, iv in sorted(t4.items()):
                            wc = len(iv.get("reflectie", "").split())
                            st.markdown(f"**Interview {nr} — {iv.get('naam_persoon','?')} ({iv.get('beroep','?')}, {iv.get('relatie','?')})** — {wc} woorden")
                            st.write(iv.get("reflectie") or "—")
                            st.divider()
                    else:
                        st.write("Nog geen interviews ingevuld.")
            st.write("")
