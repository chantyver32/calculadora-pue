import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
import pytz
import urllib.parse
import io
import speech_recognition as sr
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re  
import os
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="Insumos", page_icon="⚖️", layout="wide")

with st.spinner('Iniciando sistema Champlitte... 🥐'):
    zona_mx = pytz.timezone('America/Mexico_City')
    fecha_hoy_mx = datetime.now(zona_mx).date()

# Estilos CSS Modernos
st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 1rem; }
    .main { background-color: #f5f7f9; }
    .stButton > button, .stFormSubmitButton > button { 
        width: 100%; border-radius: 8px; font-weight: bold; transition: none !important;
    }
    div[data-testid="stToastContainer"] { top: 2rem !important; right: 2rem !important; }
    div[data-baseweb="select"] > div { background-color: #1a1a1c !important; border-radius: 8px !important; }
    .btn-wa {
        background-color: #25D366; color: white !important; padding: 10px 20px;
        text-align: center; text-decoration: none !important; display: block;
        font-size: 14px; font-weight: bold; border-radius: 8px; margin: 10px 0;
    }
    .btn-wa:hover { background-color: #128C7E; }
    </style>
""", unsafe_allow_html=True)

if "show_toast" in st.session_state:
    st.toast(st.session_state.show_toast)
    del st.session_state.show_toast

# 2. CONEXIÓN A LA BASE DE DATOS SUPABASE
db_url = os.environ.get("SUPABASE_URL")
if not db_url:
    try:
        db_url = st.secrets["SUPABASE_URL"]
    except (FileNotFoundError, KeyError):
        st.error("🚨 Error crítico: No se encontró 'SUPABASE_URL'.")
        st.stop() 

conn = st.connection("supabase", type="sql", url=db_url)

with conn.session as s:
    s.execute(text('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS pesajes_guardados 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS auditoria_stock 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, articulo TEXT, 
                 total_real REAL, stock REAL, diferencia REAL, UNIQUE(sucursal, articulo))'''))
    s.commit()

# --- SISTEMA DE LOGIN ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h2 style='text-align: center;'>⚖️ Baja de insumos</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("👤 Usuario:")
                password_input = st.text_input("🔑 Contraseña:", type="password")
                btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
                
                if btn_login:
                    df_check = conn.query("SELECT * FROM usuarios WHERE username = :u AND password = :p", 
                                          params={"u": usuario_input.strip(), "p": password_input}, ttl=0)
                    if not df_check.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = usuario_input.strip()
                        st.session_state.show_toast = "✅ ¡Bienvenid@!"
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

if not verificar_login():
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🏢 Datos de Sesión")
    st.caption(f"👤 Conectado como: **{st.session_state.get('usuario_actual', 'Usuario')}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.divider()
    
    datos_sucursales = {
        "URANO": "522281342454", "COSTA DE ORO": "522292780850", "COSTA VERDE": "522299359597",
        "DÍAZ MIRÓN": "522291302759", "EJÉRCITO MEXICANO": "522299272107", "PLAZA RÍO": "522299864120",
        "PLAYAS DEL CONCHAL": "522291794020", "COYOL": "522299398334", "LA PLACITA": "522299208481",
        "CUAUHTÉMOC": "522291651340", "MARIO MOLINA": "522291780851", "RAFAEL CUERVO": "522291980229",
        "RÍO MEDIO": "522291005852", "DIVERPLAZA": "522293763180", "BOLÍVAR": "522291002947",
        "CIRCUNVALACIÓN": "522299393726", "J.B. LOBOS": "522299201956", "YÁÑEZ": "522293764940",
        "PALACIO DE HIERRO": "522299272100", "CIUDAD INDUSTRIAL": "522299200278", "DONATO CASAS": "522291653833",
        "LAS VEGAS": "522291932980", "PUENTE MORENO": "522296893999", "CONDESA": "522299863464",
        "MURILLO VIDAL": "522286886443", "ARAUCARIAS": "522281177133", "ÁVILA CAMACHO": "522288170989",
        "EMILIANO ZAPATA": "522969628525"
    }
    
    sucursal_in = st.selectbox("📍 Selecciona tu sucursal:", list(datos_sucursales.keys()))
    numero_wa = datos_sucursales[sucursal_in]

# --- FUNCIONES ---
def truncar_dos_decimales(valor):
    if valor is None: return 0.0
    s = f"{float(valor):.10f}"
    entero, decimal = s.split('.')
    return float(f"{entero}.{decimal[:2]}")

def formato_estricto(valor):
    if pd.isna(valor) or valor is None: return "0.00"
    s = f"{float(valor):.10f}" 
    entero, decimal = s.split('.')
    return f"{entero}.{decimal[:2]}"

@st.dialog("✅ Registrado")
def mostrar_popup_exito(id_registro, articulo, resultado_ultimo, sucursal):
    st.markdown(f"### 📦 {articulo}")
    df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
    
    total_real = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
    sumandos = [formato_estricto(val) for val in df_art_combined['resultado_pue']]
    texto_total = f"{' + '.join(sumandos)} = {formato_estricto(total_real)}" if len(sumandos) > 1 else formato_estricto(total_real)
    
    st.metric("TOTAL CALCULADO", texto_total)
    st.divider()
    
    df_stock = conn.query("SELECT stock FROM auditoria_stock WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    saved_stock = float(df_stock.iloc[0]['stock']) if not df_stock.empty else 0.0
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, key=f"modal_stock_{id_registro}")
    with col_st2:
        diferencia = truncar_dos_decimales(total_real - stock_teorico)
        st.metric("DIFERENCIA", value=" ", delta=formato_estricto(diferencia), delta_color="inverse")
        
        with conn.session as s:
            s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, total_real, stock, diferencia) 
                         VALUES (:suc, :art, :tr, :stk, :dif)
                         ON CONFLICT (sucursal, articulo) DO UPDATE 
                         SET total_real = EXCLUDED.total_real, stock = EXCLUDED.stock, diferencia = EXCLUDED.diferencia"""), 
                      {"suc": sucursal, "art": articulo, "tr": total_real, "stk": stock_teorico, "dif": diferencia})
            s.commit()
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continuar", type="primary", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📥 Enviar a Bóveda", type="secondary", use_container_width=True):
            with conn.session as s:
                s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula)
                             SELECT sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula 
                             FROM pesajes_individuales WHERE id = :id"""), {"id": id_registro})
                s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_registro})
                s.commit()
            st.session_state.show_toast = "✅ Trasladado a la Bóveda."
            st.rerun()

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        section.page_width = Cm(21.59)
        section.page_height = Cm(27.94)
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)
        
    cols = 3
    rows = (len(df) + cols - 1) // cols
    if rows == 0: rows = 1
    table = doc.add_table(rows=rows, cols=cols)
    
    for idx, row_data in df.iterrows():
        r = idx // cols
        c_idx = idx % cols
        cell = table.cell(r, c_idx)
        cell.width = Cm(6)
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        texto_tarjeta = (
            f"Producto: {row_data['producto']}\n"
            f"Cant. Ant: {formato_estricto(row_data['cantidad_anterior'])}\n"
            f"Peso Descontado: {formato_estricto(row_data['peso_descontado'])}\n"
            f"Cant. Actual: {formato_estricto(row_data['cantidad_actual'])}"
        )
        p.add_run(texto_tarjeta)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generar_imagen_esquema(df_stock, sucursal):
    fig, ax = plt.subplots(figsize=(10, max(4, len(df_stock) * 0.4 + 2)), dpi=200)
    ax.axis('off')
    
    # Encabezado estilo Champlitte
    plt.text(0.5, 0.95, "Champlitte", fontsize=22, fontweight='bold', color='#581825', ha='center', transform=ax.transAxes)
    plt.text(0.5, 0.91, "PASTELERÍA — INSUMOS", fontsize=11, fontweight='bold', color='#7f8c8d', ha='center', transform=ax.transAxes)
    plt.text(0.5, 0.87, f"SUCURSAL: {sucursal} | {datetime.now(zona_mx).strftime('%d/%m/%Y - %H:%M')}", fontsize=9, color='#95a5a6', ha='center', transform=ax.transAxes)
    
    table_data = []
    for _, row in df_stock.iterrows():
        table_data.append([
            str(row['Producto']),
            formato_estricto(row['Cantidad Anterior']),
            formato_estricto(row['Peso Descontado']),
            formato_estricto(row['Cantidad Actual'])
        ])
    
    columns = ["PRODUCTO", "CANT. ANTERIOR", "PESO DESCONTADO", "CANT. ACTUAL"]
    
    table = ax.table(cellText=table_data, colLabels=columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    
    for key, cell in table.get_celld().items():
        cell.set_edgecolor('#dcdde1')
        if key[0] == 0:
            cell.set_facecolor('#581825')
            cell.set_text_props(color='white', fontweight='bold')
        else:
            cell.set_facecolor('#fdfefe' if key[0] % 2 == 0 else '#f2f4f4')
            cell.set_text_props(color='#2c3e50')
            
    plt.subplots_adjust(top=0.8, bottom=0.1)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf

productos = {
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO BLANCO POR PZA A": 0.000436,
    "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
    "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
    "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
    "HIGIENICO SCOTT ROLLO POR PZA M": 0.500, "TOALLA ROLLO 180M POR PZA M": 1.115, "BOLSA LOCK POR PZA A": 0.018,
    "GRAPAS CJ POR PZA M": 0.164, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
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

# --- 4. INTERFAZ ---
tab_stock, tab_calc, tab_historial, tab_visual = st.tabs(["📦 Stock Real", "🧮 Nueva Entrada", "📋 Reportes y Bóveda", "🖼️ Esquema Visual"])

# --- TAB 0: STOCK REAL EDITABLE Y DINÁMICO ---
with tab_stock:
    st.subheader("📦 Control de Stock Real e Inventario Dinámico")
    st.markdown("Edita directamente la columna **Cantidad Anterior** para calibrar tu base. El sistema restará en automático conforme vayas pesando.")

    df_actual_all = conn.query("SELECT articulo, SUM(resultado_pue) as total_pesado FROM pesajes_individuales WHERE sucursal = :suc GROUP BY articulo", params={"suc": sucursal_in}, ttl=0)
    df_guardados_all = conn.query("SELECT articulo, SUM(resultado_pue) as total_pesado FROM pesajes_guardados WHERE sucursal = :suc GROUP BY articulo", params={"suc": sucursal_in}, ttl=0)
    
    df_total_pesado = pd.concat([df_actual_all, df_guardados_all], ignore_index=True)
    if not df_total_pesado.empty:
        df_total_pesado = df_total_pesado.groupby("articulo", as_index=False)["total_pesado"].sum()

    df_auditoria_base = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)

    lista_todos_articulos = sorted(list(set(list(productos.keys()) + list(df_auditoria_base['articulo'] if not df_auditoria_base.empty else []))))
    df_stock_master = pd.DataFrame({"articulo": lista_todos_articulos})
    
    if not df_auditoria_base.empty:
        df_stock_master = pd.merge(df_stock_master, df_auditoria_base, on="articulo", how="left")
    else:
        df_stock_master["stock"] = 0.0

    if not df_total_pesado.empty:
        df_stock_master = pd.merge(df_stock_master, df_total_pesado, on="articulo", how="left")
        df_stock_master["total_pesado"] = df_stock_master["total_pesado"].fillna(0.0)
    else:
        df_stock_master["total_pesado"] = 0.0

    df_stock_master["stock"] = df_stock_master["stock"].fillna(0.0)
    df_stock_master["cantidad_actual"] = df_stock_master["stock"] - df_stock_master["total_pesado"]

    df_stock_display = df_stock_master[["stock", "total_pesado", "articulo", "cantidad_actual"]].rename(columns={
        "stock": "Cantidad Anterior",
        "total_pesado": "Peso Descontado",
        "articulo": "Producto",
        "cantidad_actual": "Cantidad Actual"
    })

    df_editado = st.data_editor(
        df_stock_display,
        use_container_width=True,
        hide_index=True,
        disabled=["Peso Descontado", "Producto", "Cantidad Actual"],
        key="editor_stock_real"
    )

    if st.button("💾 Guardar Cambios de Stock Inicial", use_container_width=True):
        with conn.session as s:
            for _, row in df_editado.iterrows():
                art = row["Producto"]
                nuevo_stock = row["Cantidad Anterior"]
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, stock, total_real, diferencia) 
                             VALUES (:suc, :art, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET stock = EXCLUDED.stock"""), 
                          {"suc": sucursal_in, "art": art, "stk": nuevo_stock})
            s.commit()
        st.session_state.show_toast = "✅ Stock inicial actualizado correctamente."
        st.rerun()

    st.divider()
    if st.button("🔄 CONVERTIR STOCK ACTUAL EN INVENTARIO REAL PARA MAÑANA", type="primary", use_container_width=True):
        with conn.session as s:
            for _, row in df_stock_master.iterrows():
                art = row["articulo"]
                nueva_base = row["cantidad_actual"]
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, stock, total_real, diferencia) 
                             VALUES (:suc, :art, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET stock = EXCLUDED.stock"""), 
                          {"suc": sucursal_in, "art": art, "stk": nueva_base})
            # Limpiar registros actuales para reiniciar el acumulado de pesaje de mañana
            s.execute(text("DELETE FROM pesajes_individuales WHERE sucursal = :suc"), {"suc": sucursal_in})
            s.commit()
        st.session_state.show_toast = "✅ ¡Inventario convertido con éxito para el siguiente día!"
        st.rerun()

# --- TAB 1: REGISTRO ---
with tab_calc:
    with st.expander("🎤 **Ingreso por Voz**", expanded=False):
        audio_bytes = st.audio_input("Di algo como: 0.620 de capacillo chino.", key="audio_reg")
        if audio_bytes:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                try:
                    recognizer.recognize_google(recognizer.record(source), language="es-MX").upper()
                except:
                    st.error("No se pudo entender el audio.")
    
    opciones = sorted(productos.keys())
    modo_seleccionado = st.selectbox("⚙️ Modo de Registro:", ["Modo Normal", "Artículo NO listado", "PRE-CONTEO MANUAL"], index=0)
    
    nuevo_art = (modo_seleccionado == "Artículo NO listado")
    modo_preconteo = (modo_seleccionado == "PRE-CONTEO MANUAL")
    
    if not nuevo_art:
        art_sel = st.selectbox("Seleccione Artículo:", opciones, placeholder="Elija un producto...")
        pue_final = productos.get(art_sel, 1.0) if art_sel else 1.0
    else:
        art_sel = st.text_input("Nombre del Nuevo Artículo:")
        pue_final = st.number_input("Asignar Peso Unitario:", format="%.4f")

    with st.form(key="form_pesaje", clear_on_submit=True):
        if modo_preconteo:
            cantidad_directa = st.number_input("Cantidad de piezas:", step=1.0)
            peso_bruto, tara_total, formula = 0.0, 0.0, "CONTEO MANUAL"
        else:
            peso_bruto = st.number_input("Peso Bruto (kg):", format="%.3f")
            t_cont = st.checkbox("Contenedor (0.045)")
            t_manual = st.number_input("Tara Manual Extra:", format="%.3f", value=0.0)
        
        btn_save = st.form_submit_button("📥 CONFIRMAR Y GUARDAR")

    if btn_save:
        if modo_preconteo:
            resultado = truncar_dos_decimales(cantidad_directa)
        else:
            tara_total = (0.045 if t_cont else 0) + (t_manual if t_manual else 0)
            resultado = truncar_dos_decimales((peso_bruto - tara_total) / pue_final)
            formula = f"({peso_bruto}PB - {tara_total}T) / {pue_final}PUE"

        fecha_mexico = datetime.now(zona_mx).strftime("%Y-%m-%d %H:%M:%S")
        with conn.session as s:
            result = s.execute(text("""INSERT INTO pesajes_individuales 
                         (sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                         VALUES (:suc, :fh, :art, :pb, :tara, :pue, :rp, :df) RETURNING id"""),
                      {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "pb": peso_bruto if not modo_preconteo else 0, 
                       "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                       "rp": resultado, "df": formula if not modo_preconteo else "DIRECTO"})
            id_recien = result.fetchone()[0]
            s.commit()
            
        mostrar_popup_exito(id_recien, art_sel, resultado, sucursal_in)

# --- TAB 2: REPORTES Y BÓVEDA ---
with tab_historial:
    df_guardados = conn.query("SELECT * FROM pesajes_guardados WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
    if not df_guardados.empty:
        df_stock_base = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
        df_totales = df_guardados.groupby('articulo', as_index=False)['resultado_pue'].sum().rename(columns={'resultado_pue': 'peso_descontado'})
        
        df_impresion = pd.merge(df_guardados[['articulo']], df_stock_base, on='articulo', how='left').fillna(0)
        df_impresion = pd.merge(df_impresion, df_totales, on='articulo', how='left').fillna(0)
        df_impresion['cantidad_actual'] = df_impresion['stock'] - df_impresion['peso_descontado']
        
        df_impresion = df_impresion.rename(columns={
            'articulo': 'producto',
            'stock': 'cantidad_anterior'
        }).drop_duplicates(subset=['producto'])

        word_file = generar_word_tarjetas(df_impresion)
        st.download_button("📄 Descargar Tarjetas en Word", data=word_file, file_name=f"Tarjetas_{sucursal_in}.docx", use_container_width=True)
    else:
        st.info("No hay pre-conteos en la bóveda.")

# --- TAB 3: ESQUEMA VISUAL ---
with tab_visual:
    st.subheader("🖼️ Esquema Visual de Stock (Insumos)")
    st.markdown("Generación automática de imagen con el resumen completo de insumos, cantidad anterior, peso descontado y stock actual.")

    # Calcular datos completos actuales para el reporte visual
    df_actual_all_v = conn.query("SELECT articulo, SUM(resultado_pue) as total_pesado FROM pesajes_individuales WHERE sucursal = :suc GROUP BY articulo", params={"suc": sucursal_in}, ttl=0)
    df_guardados_all_v = conn.query("SELECT articulo, SUM(resultado_pue) as total_pesado FROM pesajes_guardados WHERE sucursal = :suc GROUP BY articulo", params={"suc": sucursal_in}, ttl=0)
    
    df_total_pesado_v = pd.concat([df_actual_all_v, df_guardados_all_v], ignore_index=True)
    if not df_total_pesado_v.empty:
        df_total_pesado_v = df_total_pesado_v.groupby("articulo", as_index=False)["total_pesado"].sum()

    df_auditoria_base_v = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)

    lista_todos_v = sorted(list(set(list(productos.keys()) + list(df_auditoria_base_v['articulo'] if not df_auditoria_base_v.empty else []))))
    df_visual_master = pd.DataFrame({"articulo": lista_todos_v})
    
    if not df_auditoria_base_v.empty:
        df_visual_master = pd.merge(df_visual_master, df_auditoria_base_v, on="articulo", how="left")
    else:
        df_visual_master["stock"] = 0.0

    if not df_total_pesado_v.empty:
        df_visual_master = pd.merge(df_visual_master, df_total_pesado_v, on="articulo", how="left")
        df_visual_master["total_pesado"] = df_visual_master["total_pesado"].fillna(0.0)
    else:
        df_visual_master["total_pesado"] = 0.0

    df_visual_master["stock"] = df_visual_master["stock"].fillna(0.0)
    df_visual_master["cantidad_actual"] = df_visual_master["stock"] - df_visual_master["total_pesado"]

    df_reporte_visual = df_visual_master[["stock", "total_pesado", "articulo", "cantidad_actual"]].rename(columns={
        "stock": "Cantidad Anterior",
        "total_pesado": "Peso Descontado",
        "articulo": "Producto",
        "cantidad_actual": "Cantidad Actual"
    })

    if not df_reporte_visual.empty:
        img_buffer = generar_imagen_esquema(df_reporte_visual, sucursal_in)
        st.image(img_buffer, caption=f"Reporte Visual de Insumos - {sucursal_in}", use_container_width=True)
        
        url_abrir_wa = f"https://wa.me/{numero_wa}"
        st.markdown(f'<a href="{url_abrir_wa}" target="_blank" class="btn-wa">💬 ABRIR WHATSAPP (Para enviar reporte)</a>', unsafe_allow_html=True)
    else:
        st.info("No hay datos suficientes para generar el esquema visual.")
