import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide", page_icon="⚖️")

# Estilos CSS para el botón de WhatsApp (Limpio, pequeño y profesional)
st.markdown("""
    <style>
    .btn-wa {
        background-color: #25D366;
        color: white !important;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none !important;
        display: inline-block;
        font-size: 13px;
        font-weight: bold;
        font-style: normal !important;
        border-radius: 5px;
        transition: 0.3s;
        border: none;
        margin-top: 10px;
    }
    .btn-wa:hover {
        background-color: #128C7E;
        color: white !important;
        text-decoration: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. BASE DE DATOS (v3 para asegurar que las columnas nuevas existan)
conn = sqlite3.connect("pue_champlitte_v3.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              fecha_hora TEXT, 
              articulo TEXT, 
              peso_bruto REAL, 
              tara REAL, 
              pue REAL, 
              resultado_pue REAL, 
              detalle_formula TEXT)''')
conn.commit()

# 3. DICCIONARIO DE PRODUCTOS
productos = {
    "": 0, "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO ROJO #72 POR PZA A": 0.000436,
    "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
    "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
    "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
    "HIGIENICO SCOTT ROLLO POR PZA M": 0.500, "TOALLA ROLLO 180M POR PZA M": 1.115, "BOLSA LOCK POR PZA A": 0.018,
    "CAJA DE GRAPAS POR PZA M": 0.176, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
    "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
    "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, "BOLSA CAMISETA LOGO GDE POR KG A": 1.0,
    "BOLSA NATURAL 18 X 25 POR KG A": 1.0, "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0,
    "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0,
    "CLOROLIMP POR L A": 1.0, "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
    "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "JABON LIQUIDO PARA MANOS POR L M": 1.0, "LAVALOZA POR L A": 1.0,
    "PRO GEL POR L B": 1.0, "ROLLO TERMICO P/TPV POR PZA A": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0,
    "ESCURRIDOR POR PZA M": 1.0, "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0,
}

# 4. INTERFAZ
tab_calc, tab_historial = st.tabs(["⚖️ Registro de Pesaje", "📂 Auditoría y Reportes"])

# --- TAB 1: REGISTRO ---
with tab_calc:
    st.subheader("Registrar Pesaje Individual")
    
    nuevo_art = st.checkbox("➕ Artículo NO listado (Asignar nombre y PUE manualmente)")
    
    with st.form(key="form_pesaje", clear_on_submit=True):
        col_a, col_b = st.columns([2,1])
        
        if not nuevo_art:
            with col_a: art_sel = st.selectbox("Artículo:", sorted(productos.keys()))
            pue_base = productos.get(art_sel, 1.0)
        else:
            with col_a: art_sel = st.text_input("Nombre del nuevo artículo:", placeholder="Ej. BOLSA PERSONALIZADA")
            pue_base = st.number_input("Asignar PUE:", value=1.000, format="%.4f")
            
        with col_b: peso_bruto = st.number_input("Peso Bruto (kg):", value=None, format="%.3f", placeholder="0.000")
        
        st.write("Taras:")
        c1, c2, c3 = st.columns(3)
        with c1: t_cont = st.checkbox("Contenedor (0.045)")
        with c2: t_bis = st.checkbox("Bisagra (0.160)")
        with c3: t_manual = st.number_input("Manual:", value=None, format="%.3f", placeholder="0.000")
        
        btn_save = st.form_submit_button("💾 GUARDAR PESAJE")

    if btn_save:
        if art_sel and peso_bruto is not None:
            tm = t_manual if t_manual is not None else 0.0
            tara_total = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + tm
            peso_neto = peso_bruto - tara_total
            
            # Lógica de cálculo
            if "TINTA" in art_sel:
                resultado = (peso_neto - 0.030) / pue_base
                formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T - 0.03Env) / {pue_base}"
            else:
                resultado = peso_neto / pue_base
                formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T) / {pue_base}"
            
            # Hora México
            zona_mexico = pytz.timezone('America/Mexico_City')
            fecha_mexico = datetime.now(zona_mexico).strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("""INSERT INTO pesajes_individuales 
                         (fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                         VALUES (?,?,?,?,?,?,?)""",
                      (fecha_mexico, art_sel, peso_bruto, tara_total, pue_base, resultado, formula))
            conn.commit()
            st.success(f"Registrado: {resultado:.2f} de {art_sel}")
        else:
            st.warning("⚠️ Faltan datos obligatorios.")

# --- TAB 2: AUDITORÍA ---
with tab_historial:
    st.subheader("Auditoría Detallada de Operaciones")
    
    df = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    
    if not df.empty:
        articulos_en_db = sorted(df['articulo'].unique())
        art_filtro = st.selectbox("Seleccione artículo para consolidar reporte:", articulos_en_db)
        
        df_art = df[df['articulo'] == art_filtro]
        total_real = df_art['resultado_pue'].sum()
        
        st.markdown(f"### Desglose de cálculos para: **{art_filtro}**")
        
        # TABLA CON TODOS LOS DETALLES MATEMÁTICOS
        columnas_visibles = ['fecha_hora', 'peso_bruto', 'tara', 'pue', 'detalle_formula', 'resultado_pue']
        st.table(df_art[columnas_visibles])
        
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.metric("SUMA TOTAL REAL", f"{total_real:.2f}")
        with col_res2:
            stock_teorico = st.number_input("Stock Teórico (Sistema):", value=None, placeholder="0.00")
        
        if stock_teorico is not None:
            diferencia = total_real - stock_teorico
            with col_res3:
                st.metric("DIFERENCIA", f"{diferencia:.2f}", delta=round(diferencia, 2), delta_color="inverse")
            
            # Mensaje WA con desglose detallado
            calculos_lista = "\n".join([f"- {f} = {r:.2f}" for f, r in zip(df_art['detalle_formula'], df_art['resultado_pue'])])
            msg = (f"*AUDITORÍA CHAMPLITTE*\n"
                   f"*Art:* {art_filtro}\n"
                   f"*Total Real:* {total_real:.2f}\n"
                   f"*Stock:* {stock_teorico:.2f}\n"
                   f"*Dif:* {diferencia:.2f}\n\n"
                   f"*DESGLOSE:*\n{calculos_lista}")
            
            url_wa = f"https://wa.me/522283530069?text={urllib.parse.quote(msg)}"
            st.markdown(f'<a href="{url_wa}" target="_blank" class="btn-wa">ENVIAR REPORTE DETALLADO WA</a>', unsafe_allow_html=True)

        st.divider()
        if st.checkbox("Ver base de datos global"):
            st.dataframe(df)
            if st.button("🗑️ Limpiar toda la base de datos"):
                c.execute("DELETE FROM pesajes_individuales")
                conn.commit()
                st.rerun()
    else:
        st.info("No hay pesajes registrados aún.")
