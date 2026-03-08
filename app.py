import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide", page_icon="⚖️")

# Estilos CSS Avanzados para mejorar el diseño
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    
    .btn-wa {
        background-color: #25D366;
        color: white !important;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none !important;
        display: block;
        font-size: 14px;
        font-weight: bold;
        font-style: normal !important;
        border-radius: 8px;
        margin: 10px 0;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; transform: translateY(-1px); }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    </style>
""", unsafe_allow_html=True)

# 2. BASE DE DATOS (v4 para asegurar estructura limpia)
conn = sqlite3.connect("pue_champlitte_v4.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, articulo TEXT, 
              peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)''')
conn.commit()

# 3. DICCIONARIO DE PRODUCTOS
productos = {
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
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
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada", "📋 Auditoría y Reportes"])

# --- TAB 1: REGISTRO ---
with tab_calc:
    st.title("⚖️ Registro de Pesaje")
    
    nuevo_art = st.toggle("Modo: Artículo NO listado", value=False)
    
    with st.form(key="form_pesaje", clear_on_submit=True):
        if not nuevo_art:
            art_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()), index=None, placeholder="Elija un producto...")
            pue_final = productos.get(art_sel, 1.0)
        else:
            c_n1, c_n2 = st.columns([2,1])
            with c_n1:
                art_sel = st.text_input("Nombre del Nuevo Artículo:", value=None, placeholder="Ej. CAJA PERSONALIZADA")
            with c_n2:
                pue_final = st.number_input("Asignar PUE:", value=None, format="%.4f", placeholder="0.0000")
        
        st.divider()
        peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=None, format="%.3f", placeholder="0.000")
        
        with st.expander("🛠️ Configuración de Taras", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: t_cont = st.checkbox("Contenedor (0.045)")
            with c2: t_bis = st.checkbox("Bisagra (0.016)") # Corregido a 0.016 según tu código previo
            with c3: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f", placeholder="0.000")
        
        btn_save = st.form_submit_button("📥 GUARDAR PESAJE")

    if btn_save:
        # Validación de campos vacíos
        if art_sel and peso_bruto is not None and pue_final is not None:
            tm = t_manual if t_manual is not None else 0.0
            tara_total = (0.045 if t_cont else 0) + (0.016 if t_bis else 0) + tm
            peso_neto = peso_bruto - tara_total
            
            # Lógica de cálculo (Tinta Epson / Otros)
            is_tinta = "TINTA" in str(art_sel).upper()
            offset = 0.030 if is_tinta else 0.0
            resultado = (peso_neto - offset) / pue_final
            
            formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"
            
            # Hora México
            zona_mexico = pytz.timezone('America/Mexico_City')
            fecha_mexico = datetime.now(zona_mexico).strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("""INSERT INTO pesajes_individuales 
                         (fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                         VALUES (?,?,?,?,?,?,?)""",
                      (fecha_mexico, art_sel, peso_bruto, tara_total, pue_final, resultado, formula))
            conn.commit()
            st.balloons()
            st.success(f"✅ Registrado con éxito: {resultado:.2f} de {art_sel}")
        else:
            st.error("❌ Error: Debes seleccionar/escribir el Artículo, el PUE y el Peso.")

# --- TAB 2: AUDITORÍA ---
with tab_historial:
    st.title("📋 Consolidación de Auditoría")
    
    df = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    
    if not df.empty:
        art_filtro = st.selectbox("Seleccione el Artículo a Consultar:", sorted(df['articulo'].unique()), index=None, placeholder="Seleccione para ver desglose...")
        
        if art_filtro:
            df_art = df[df['articulo'] == art_filtro]
            total_real = df_art['resultado_pue'].sum()
            
            st.subheader(f"{art_filtro}")
            
            # TABLA DETALLADA (Corregida para que no falten columnas)
            st.table(df_art[['fecha_hora', 'peso_bruto', 'tara', 'pue', 'detalle_formula', 'resultado_pue']].rename(columns={
                'fecha_hora': 'Fecha/Hora', 'peso_bruto': 'P. Bruto', 'tara': 'Tara Total', 'pue': 'PUE Usado', 'detalle_formula': 'Operación', 'resultado_pue': 'Resultado'
            }))
            
            st.divider()
            
            c_res1, c_res2, c_res3 = st.columns(3)
            with c_res1:
                st.metric("TOTAL CALCULADO", f"{total_real:.2f}")
            with c_res2:
                stock_teorico = st.number_input("Valor en Sistema (Stock):", value=None, placeholder="Ingrese stock...")
            
            if stock_teorico is not None:
                diferencia = total_real - stock_teorico
                with c_res3:
                    st.metric("DIFERENCIA", f"{diferencia:.2f}", delta=round(diferencia, 2), delta_color="inverse")
                
                # Reporte WA detallado
                desglose_txt = "\n".join([f"• {f} = {r:.2f}" for f, r in zip(df_art['detalle_formula'], df_art['resultado_pue'])])
                msg = (f"*REPORTE DE AUDITORÍA PUE*\n"
                       f"------------------------------\n"
                       f"*Producto:* {art_filtro}\n"
                       f"*Suma Real:* {total_real:.2f}\n"
                       f"*Stock Sistema:* {stock_teorico:.2f}\n"
                       f"*Diferencia:* {diferencia:.2f}\n"
                       f"------------------------------\n"
                       f"*OPERACIONES DETALLADAS:*\n{desglose_txt}")
                
                url_wa = f"https://wa.me/522283530069?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{url_wa}" target="_blank" class="btn-wa">📲 ENVIAR REPORTE COMPLETO A WHATSAPP</a>', unsafe_allow_html=True)

        st.divider()
        with st.expander("🗑️ Administración de Base de Datos"):
            st.dataframe(df, use_container_width=True)
            if st.button("LIMPIAR TODA LA BASE DE DATOS"):
                c.execute("DELETE FROM pesajes_individuales")
                conn.commit()
                st.rerun()
    else:
        st.info("No hay pesajes registrados aún.")
