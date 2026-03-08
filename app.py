import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import urllib.parse
from PIL import Image

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# Esto es lo que hace que los campos se vacíen de verdad al terminar
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

def reset_campos():
    st.session_state.form_key += 1

# 2. BASE DE DATOS
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registros_pue 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, articulo TEXT, resultado REAL)''')
conn.commit()

# 3. PRODUCTOS (Lista Completa)
productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870, "BOLSA PAPEL CAFE #14": 1.364,
    "BOLSA PAPEL CAFE #20": 1.616, "CAJA TUTIS": 0.048, "CAPACILLO CHINO": 0.00104,
    "CAPACILLO ROJO #72": 0.000436, "CONT BISAG P/5-6 TUTIS": 0.014, "CUCHARA MED DESCH": 0.00165,
    "ETIQUETA 4 X 4": 0.000328, "ETIQUETA 6 X 6": 0.00057, "EMPLAYE GRANDE ROLLO": 1.174,
    "PAPEL ALUMINIO": 1.342, "SERVILLETA PQ/500 HJ": 0.001192, "COFIA PQ/100": 0.238,
    "GUANTES POLIURETANO": 0.086, "HIGIENICO SCOTT ROLLO": 0.500, "TOALLA ROLLO 180M": 1.115,
    "BOLSA LOCK": 0.018, "CAJA DE GRAPAS": 0.176, "CINTA TRANSP EMPAQUE": 0.272, "CINTA DELIMITADORA": 0.346,
    "COMPROBANTE TRASLADO": 0.0086, "ETIQUETA BLANCA ADH": 0.050, "HOJAS BLANCAS PQ/500": 2.146,
    "TINTA EPSON 544": 0.078, "AGUA CIEL 20 LT": 1.0, "AZUCAR REFINADA": 1.0, "BOLSA CAMISETA CH": 1.0,
    "BOLSA CAMISETA GDE": 1.0, "BOLSA NATURAL": 1.0, "PAPEL ENVOLTURA": 1.0, "ROLLO POLIPUNTEADO": 1.0,
    "BOLSA 90X120": 1.0, "BOLSA 60X90": 1.0, "CLOROLIMP": 1.0, "FIBRA PREGON": 1.0, "FIBRA SCOTCH": 1.0,
    "FIBRA AZUL": 1.0, "JABON MANOS": 1.0, "LAVALOZA": 1.0, "PRO GEL": 1.0, "ROLLO TERMICO": 1.0,
    "CUBETA": 1.0, "ESCOBA": 1.0, "ESCURRIDOR": 1.0, "RECOGEDOR": 1.0, "MECHUDO": 1.0
}

# 4. LOGO
try:
    img = Image.open("champlitte.jpg")
    st.image(img, width=100)
except:
    st.write("### PASTELERÍA CHAMPLITTE")

# 5. TABS
tab1, tab2, tab3 = st.tabs(["📝 Calculadora", "📊 Comparativa / Restar", "⚠️ Historial"])

# --- TAB 1: CALCULADORA ---
with tab1:
    # Cambiar la key del form resetea los inputs a blanco
    with st.form(key=f"calc_{st.session_state.form_key}", clear_on_submit=True):
        articulo = st.selectbox("Seleccione Artículo:", sorted(productos.keys()))
        # value=None para que no aparezca el 0.000
        peso_t = st.number_input("Peso Total (kg):", value=None, format="%.3f", placeholder="Toque aquí para escribir...")
        
        col1, col2 = st.columns(2)
        with col1:
            t_cont = st.checkbox("Contenedor (.045)")
            t_bis = st.checkbox("Bisagra (0.16)")
        with col2:
            t_man = st.number_input("Tara Manual:", value=None, format="%.3f", placeholder="0.000")
        
        btn_calc = st.form_submit_button("CALCULAR Y REGISTRAR")

    if btn_calc:
        if articulo != "" and peso_t is not None:
            pue_val = productos.get(articulo, 1.0)
            tara_total = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + (t_man if t_man else 0)
            peso_neto = peso_t - tara_total
            
            if "TINTA" in articulo:
                res = (peso_neto - 0.03) / 0.078
            else:
                res = peso_neto / pue_val
            
            hora_act = datetime.now().strftime("%H:%M:%S")
            f_act = datetime.now().strftime("%Y-%m-%d")
            
            c.execute('INSERT INTO registros_pue (fecha, hora, articulo, resultado) VALUES (?,?,?,?)', (f_act, hora_act, articulo, res))
            conn.commit()
            
            st.metric("Resultado Final", f"{res:.2f}")
            
            # Enlace WhatsApp
            texto_wa = urllib.parse.quote(f"PUE {articulo}\nResultado: {res:.2f}\nHora: {hora_act}")
            st.markdown(f"### [📲 ENVIAR A WHATSAPP](https://wa.me/522283530069?text={texto_wa})")
            
            st.button("LIMPIAR PARA NUEVO PRODUCTO", on_click=reset_campos)
        else:
            st.warning("⚠️ Ingresa el peso y selecciona un producto.")

# --- TAB 2: COMPARATIVA (RESTAR) ---
with tab2:
    st.header("Restar a un valor asignado")
    try:
        df_comp = pd.read_sql("SELECT id, articulo, resultado FROM registros_pue ORDER BY id DESC LIMIT 10", conn)
        if not df_comp.empty:
            sel_art = st.selectbox("Elegir artículo del historial:", df_comp['articulo'] + " (ID: " + df_comp['id'].astype(str) + ")")
            id_real = int(sel_art.split(": ")[1].replace(")", ""))
            val_sistema = df_comp[df_comp['id'] == id_real]['resultado'].values[0]
            
            st.info(f"Valor en sistema: **{val_sistema:.2f}**")
            
            # Valor que tú asignas para restar
            valor_usuario = st.number_input("Valor que deseas restar (Físico/Asignado):", value=None, placeholder="Escribe aquí...")
            
            if valor_usuario is not None:
                diferencia = val_sistema - valor_usuario
                st.metric("Diferencia (Sistema - Tu valor)", f"{diferencia:.2f}")
                
                if st.button("Enviar Comparativa WA"):
                    texto_comp = urllib.parse.quote(f"COMPARATIVA\nArt: {sel_art}\nSistema: {val_sistema:.2f}\nAsignado: {valor_usuario:.2f}\nDiferencia: {diferencia:.2f}")
                    st.markdown(f"[📲 Enviar Comparativa](https://wa.me/522283530069?text={texto_comp})")
        else:
            st.write("No hay registros recientes para comparar.")
    except Exception as e:
        st.write("Error al cargar historial.")

# --- TAB 3: HISTORIAL ---
with tab3:
    if st.button("Actualizar Tabla"):
        st.rerun()
    df_hist = pd.read_sql("SELECT hora, articulo, resultado FROM registros_pue ORDER BY id DESC LIMIT 20", conn)
    st.table(df_hist)
    
    if st.button("BORRAR TODO EL HISTORIAL"):
        c.execute("DELETE FROM registros_pue")
        conn.commit()
        st.success("Historial borrado.")
        st.rerun()
