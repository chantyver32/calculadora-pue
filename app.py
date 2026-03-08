import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# 1. CONFIGURACIÓN E INICIALIZACIÓN DE ESTADO
st.set_page_config(page_title="PUE Champlitte", layout="centered")

# Inicializamos la lista de pesajes temporales si no existe
if "lista_pesajes" not in st.session_state:
    st.session_state.lista_pesajes = []
if "articulo_actual" not in st.session_state:
    st.session_state.articulo_actual = ""
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

def limpiar_formulario():
    st.session_state.form_key += 1
    st.session_state.lista_pesajes = []
    st.session_state.articulo_actual = ""

# 2. BASE DE DATOS
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registros_pue 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, articulo TEXT, total_pue REAL)''')
conn.commit()

# 3. PRODUCTOS
productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870, "BOLSA PAPEL CAFE #14": 1.364,
    "BOLSA PAPEL CAFE #20": 1.616, "CAJA TUTIS": 0.048, "TINTA EPSON 544": 0.078, "AGUA CIEL 20 LT": 1.0,
    "AZUCAR REFINADA": 1.0, "CLOROLIMP": 1.0, "ESCOBA": 1.0, "JABON MANOS": 1.0 # ... (agrega los demás)
}

# 4. INTERFAZ: CALCULADORA CON SUMATORIA
st.title("🍰 Calculadora PUE Acumulativa")

with st.expander("📝 Registrar Pesajes (Sumatoria)", expanded=True):
    # Formulario para un pesaje individual
    with st.form(key=f"form_{st.session_state.form_key}", clear_on_submit=True):
        art_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()))
        peso_t = st.number_input("Peso de este pesaje (kg):", value=None, format="%.3f", placeholder="Escribe el peso...")
        
        col1, col2 = st.columns(2)
        with col1:
            t_cont = st.checkbox("Contenedor (.045)")
            t_bis = st.checkbox("Bisagra (0.16)")
        with col2:
            t_man = st.number_input("Tara Manual:", value=None, format="%.3f", placeholder="0.000")
        
        btn_sumar = st.form_submit_button("➕ AGREGAR A LA SUMA")

    if btn_sumar:
        if art_sel != "" and peso_t is not None:
            pue_val = productos.get(art_sel, 1.0)
            tara_t = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + (t_man if t_man else 0)
            neto = peso_t - tara_t
            
            # Cálculo individual
            if "TINTA" in art_sel:
                res_ind = (neto - 0.03) / 0.078
            else:
                res_ind = neto / pue_val
            
            # Guardamos en la lista temporal
            st.session_state.lista_pesajes.append(res_ind)
            st.session_state.articulo_actual = art_sel
            st.success(f"Agregado: {res_ind:.2f}. Total acumulado: {sum(st.session_state.lista_pesajes):.2f}")
        else:
            st.warning("⚠️ Ingresa datos válidos.")

# 5. RESULTADO FINAL Y COMPARATIVA
if st.session_state.lista_pesajes:
    total_acumulado = sum(st.session_state.lista_pesajes)
    st.divider()
    st.subheader(f"Artículo: {st.session_state.articulo_actual}")
    st.metric("SUMA TOTAL DE PESAJES", f"{total_acumulado:.2f}")

    # Apartado para restar el número decidido por el usuario
    valor_a_restar = st.number_input("Escribe el valor para restar (Físico/Conteo):", value=None, placeholder="¿Cuánto quieres restar?")
    
    if valor_a_restar is not None:
        diferencia = total_acumulado - valor_a_restar
        st.metric("DIFERENCIA FINAL", f"{diferencia:.2f}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 GUARDAR Y ENVIAR WA"):
            h_act = datetime.now().strftime("%H:%M:%S")
            f_act = datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO registros_pue (fecha, hora, articulo, total_pue) VALUES (?,?,?,?)', 
                      (f_act, h_act, st.session_state.articulo_actual, total_acumulado))
            conn.commit()
            
            # WhatsApp 2283530069
            msg = f"PUE ACUMULADO\nArt: {st.session_state.articulo_actual}\nTotal Sumado: {total_acumulado:.2f}\nRestado: {valor_a_restar if valor_a_restar else 0}\nDif: {diferencia if valor_a_restar else 0}"
            url = f"https://wa.me/522283530069?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 ENVIAR A WHATSAPP]({url})")

    with col_b:
        st.button("🧹 LIMPIAR TODO (NUEVO ARTÍCULO)", on_click=limpiar_formulario)

# 6. HISTORIAL
st.divider()
st.subheader("Últimos totales guardados")
df = pd.read_sql("SELECT hora, articulo, total_pue FROM registros_pue ORDER BY id DESC LIMIT 5", conn)
st.table(df)
