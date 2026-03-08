import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide")

if "pesajes_detallados" not in st.session_state:
    st.session_state.pesajes_detallados = [] # Guarda el texto de la operación
if "valores_pesajes" not in st.session_state:
    st.session_state.valores_pesajes = []    # Guarda los números para sumar
if "articulo_actual" not in st.session_state:
    st.session_state.articulo_actual = ""
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

def finalizar_y_limpiar():
    st.session_state.form_key += 1
    st.session_state.pesajes_detallados = []
    st.session_state.valores_pesajes = []
    st.session_state.articulo_actual = ""

# 2. BASE DE DATOS
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registro_auditoria 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, articulo TEXT, 
              suma_total REAL, valor_restado REAL, diferencia REAL, detalle_operacion TEXT)''')
conn.commit()

# 3. PRODUCTOS
productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870, "BOLSA PAPEL CAFE #14": 1.364,
    "BOLSA PAPEL CAFE #20": 1.616, "CAJA TUTIS": 0.048, "TINTA EPSON 544": 0.078, "AGUA CIEL 20 LT": 1.0,
    "AZUCAR REFINADA": 1.0, "CLOROLIMP": 1.0, "ESCOBA": 1.0, "JABON MANOS": 1.0
}

# 4. INTERFAZ DE TABS
tab_calc, tab_db = st.tabs(["🧮 Calculadora y Sumatoria", "📂 Base de Datos Histórica"])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    st.title("🍰 Control de Pesajes Acumulados")
    
    with st.form(key=f"f_{st.session_state.form_key}", clear_on_submit=True):
        col_art, col_peso = st.columns([2, 1])
        with col_art:
            art_sel = st.selectbox("Artículo:", sorted(productos.keys()))
        with col_peso:
            peso_t = st.number_input("Peso Total (kg):", value=None, format="%.3f", placeholder="0.000")
        
        c1, c2, c3 = st.columns(3)
        with c1: t_cont = st.checkbox("Contenedor (.045)")
        with c2: t_bis = st.checkbox("Bisagra (0.16)")
        with c3: t_man = st.number_input("Tara Manual:", value=None, format="%.3f", placeholder="0.000")
        
        btn_add = st.form_submit_button("➕ AGREGAR PESAJE A LA LISTA")

    if btn_add:
        if art_sel != "" and peso_t is not None:
            pue = productos.get(art_sel, 1.0)
            tara = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + (t_man if t_man else 0)
            neto = peso_t - tara
            
            # Cálculo y Detalle
            if "TINTA" in art_sel:
                res = (neto - 0.03) / 0.078
                detalle = f"({peso_t:.3f}t - {tara:.3f}tara - 0.03 envase) / 0.078 = {res:.2f}"
            else:
                res = neto / pue
                detalle = f"({peso_t:.3f}t - {tara:.3f}tara) / {pue}pue = {res:.2f}"
            
            st.session_state.valores_pesajes.append(res)
            st.session_state.pesajes_detallados.append(detalle)
            st.session_state.articulo_actual = art_sel
        else:
            st.error("⚠️ Datos incompletos.")

    # Mostrar Acumulado y Operación detallada
    if st.session_state.valores_pesajes:
        st.divider()
        st.subheader(f"Resumen Actual: {st.session_state.articulo_actual}")
        
        for i, p in enumerate(st.session_state.pesajes_detallados):
            st.caption(f"Pesaje {i+1}: {p}")
        
        total_s = sum(st.session_state.valores_pesajes)
        st.metric("SUMA TOTAL ACUMULADA", f"{total_s:.2f}")

        # Sección de Resta
        val_restar = st.number_input("Valor a restar (Número decidido):", value=None, placeholder="Escribe aquí...")
        
        if val_restar is not None:
            dif_final = total_s - val_restar
            st.metric("DIFERENCIA FINAL", f"{dif_final:.2f}")
            
            if st.button("✅ FINALIZAR, GUARDAR Y ENVIAR WA"):
                h_act = datetime.now().strftime("%H:%M:%S")
                f_act = datetime.now().strftime("%Y-%m-%d")
                detalles_str = " | ".join(st.session_state.pesajes_detallados)
                
                # Guardar en DB (Tab 2)
                c.execute('''INSERT INTO registro_auditoria 
                             (fecha, hora, articulo, suma_total, valor_restado, diferencia, detalle_operacion) 
                             VALUES (?,?,?,?,?,?,?)''', 
                          (f_act, h_act, st.session_state.articulo_actual, total_s, val_restar, dif_final, detalles_str))
                conn.commit()
                
                # WA
                msg = f"*REPORTE PUE*\nArt: {st.session_state.articulo_actual}\nSuma: {total_s:.2f}\nResta: {val_restar:.2f}\n*Dif: {dif_final:.2f}*\nDetalle: {detalles_str}"
                st.markdown(f"### [📲 ENVIAR A WHATSAPP](https://wa.me/522283530069?text={urllib.parse.quote(msg)})")
                
                st.button("🧹 INICIAR NUEVO ARTÍCULO", on_click=finalizar_y_limpiar)

# --- TAB 2: BASE DE DATOS ---
with tab_db:
    st.header("📂 Historial de Operaciones Realizadas")
    if st.button("🔄 Actualizar Base de Datos"):
        st.rerun()
        
    df = pd.read_sql("SELECT * FROM registro_auditoria ORDER BY id DESC", conn)
    if not df.empty:
        # Mostramos la tabla con el detalle de cada pesaje incluido
        st.dataframe(df, use_container_width=True)
        
        # Opción para descargar
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Excel (CSV)", data=csv, file_name="auditoria_pue.csv", mime="text/csv")
    else:
        st.info("No hay registros en la base de datos todavía.")
    
    if st.checkbox("Zona de Peligro: Borrar Base de Datos"):
        if st.button("CONFIRMAR BORRADO TOTAL"):
            c.execute("DELETE FROM registro_auditoria")
            conn.commit()
            st.rerun()
