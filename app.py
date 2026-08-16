import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
import pytz
import urllib.parse
import io
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re  
import os
import streamlit.components.v1 as components

# ------------------ 1. CONFIGURACIÓN GENERAL ------------------
st.set_page_config(page_title="Insumos Champlitte", page_icon="⚖️", layout="wide")

with st.spinner('Iniciando sistema Champlitte... 🥐'):
    zona_mx = pytz.timezone('America/Mexico_City')
    fecha_hoy_mx = datetime.now(zona_mx).date()

st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 1rem; }
    .main { background-color: #f5f7f9; }
    
    .stButton > button, 
    .stFormSubmitButton > button { 
        width: 100%; border-radius: 8px; font-weight: bold; 
        transition: none !important; -webkit-transition: none !important;
    }
    .stButton > button:focus, .stButton > button:active,
    .stFormSubmitButton > button:focus, .stFormSubmitButton > button:active {
        box-shadow: none !important; outline: none !important; transform: none !important;
    }

    [data-testid="stElementContainer"], [data-testid="stForm"] {
        transition: none !important; animation: none !important;
    }

    /* CENTRADO DEL MENSAJE DE CONFIRMACIÓN (TOAST) */
    div[data-testid="stToastContainer"] {
        top: 2rem !important; 
        bottom: auto !important; 
        left: 50% !important; 
        right: auto !important; 
        transform: translateX(-50%) !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    ul[role="listbox"] li[aria-selected="true"] {
        background-color: transparent !important; font-weight: bold !important;
    }

    div[data-baseweb="popover"] > div {
        background-color: #1a1a1c !important; border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.8) !important;
    }
    div[data-baseweb="popover"] ul { background-color: transparent !important; }
    div[data-baseweb="popover"] li {
        background-color: transparent !important; color: #FFFFFF !important; font-size: 14px !important; padding: 10px 0 !important;
    }
    div[data-baseweb="popover"] li:hover { background-color: #2d2d30 !important; }
    div[data-baseweb="popover"] li[aria-selected="true"] { background-color: #3a3b3e !important; font-weight: bold !important; }

    div[data-baseweb="select"] > div {
        background-color: #1a1a1c !important; border-radius: 8px !important; border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    div[data-baseweb="select"] > div:focus-within { border-color: #ff4b4b !important; box-shadow: 0 0 0 1px #ff4b4b !important; }
    div[data-baseweb="select"] div, div[data-baseweb="select"] svg { color: #FFFFFF !important; fill: #FFFFFF !important; }

    .btn-wa {
        background-color: #25D366; color: white !important; padding: 10px 20px;
        text-align: center; text-decoration: none !important; display: block;
        font-size: 14px; font-weight: bold; border-radius: 8px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    div[data-testid="stMetricDelta"] { font-size: 30px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

if "show_toast" in st.session_state:
    st.toast(st.session_state.show_toast)
    del st.session_state.show_toast

# ------------------ 2. CONEXIÓN A SUPABASE ------------------
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
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, categoria TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS pesajes_guardados 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, categoria TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS auditoria_stock 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, articulo TEXT, categoria TEXT, 
                 total_real REAL, stock REAL, diferencia REAL, UNIQUE(sucursal, articulo))'''))
    
    s.execute(text('''CREATE TABLE IF NOT EXISTS usuarios 
                 (id SERIAL PRIMARY KEY, username TEXT, password TEXT)'''))
                 
    s.execute(text('''CREATE TABLE IF NOT EXISTS catalogo_productos 
                 (id SERIAL PRIMARY KEY, categoria TEXT, articulo TEXT, pue REAL, UNIQUE(categoria, articulo))'''))

    s.execute(text('ALTER TABLE pesajes_individuales ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE auditoria_stock ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS aplicado_en_corte BOOLEAN DEFAULT TRUE;'))
    s.execute(text('ALTER TABLE catalogo_productos ADD COLUMN IF NOT EXISTS ubicacion_conteo TEXT DEFAULT \'Combinado\';'))

    s.commit()

# ------------------ DICCIONARIO BASE ------------------
dicc_inicial = {
    "Insumos Venta": {
        "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
        "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
        "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO BLANCO POR PZA A": 0.000436,
        "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
        "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
        "BOLSA LOCK POR PZA A": 0.018,
        "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, 
        "BOLSA CAMISETA LOGO GDE POR KG A": 1.0, "BOLSA NATURAL 18 X 25 POR KG A": 1.0, 
        "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0, "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, 
        "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0
    },
    "Limpieza Venta": {
        "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
        "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
        "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0, 
        "ESCURRIDOR POR PZA M": 1.0, "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0
    },
    "Papelería Venta": {
        "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
        "GRAPAS CJ POR PZA M": 0.164, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
        "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
        "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, 
        "ROLLO TERMICO P/TPV POR PZA A": 1.0
    }
}

# AJUSTE 1: Aplicando Caché (ttl="1h") al catálogo global
df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h")
if df_cat_global.empty:
    with conn.session as s:
        for cat, prods in dicc_inicial.items():
            for art, pue in prods.items():
                s.execute(text("INSERT INTO catalogo_productos (categoria, articulo, pue, ubicacion_conteo) VALUES (:c, :a, :p, 'Combinado') ON CONFLICT DO NOTHING"), 
                          {"c": cat, "a": art, "p": pue})
        s.commit()
    st.cache_data.clear() # Limpia caché al insertar iniciales
    df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h")

productos_por_categoria = {}
for _, row in df_cat_global.iterrows():
    c = row['categoria']
    if c not in productos_por_categoria:
        productos_por_categoria[c] = {}
    productos_por_categoria[c][row['articulo']] = row['pue']

for c in ["Papelería Venta", "Limpieza Venta", "Insumos Venta"]:
    if c not in productos_por_categoria:
        productos_por_categoria[c] = {}

# ------------------ SISTEMA DE LOGIN ------------------
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h2 style='text-align: center;'>⚖️ Baja de insumos</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray; margin-bottom: 2rem;'>Control de Acceso</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("👤 Usuario:")
                password_input = st.text_input("🔑 Contraseña:", type="password")
                st.write("")
                btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
                
                if btn_login:
                    # AJUSTE 2: Aplicando Caché al login (ttl="10m")
                    df_check = conn.query("SELECT * FROM usuarios WHERE username = :u AND password = :p", 
                                          params={"u": usuario_input.strip(), "p": password_input}, ttl="10m")
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

# ------------------ BARRA LATERAL ------------------
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
    st.caption(f"📱WhatsApp: **{numero_wa}**")

    st.divider()
    st.markdown("### 💾 Respaldo de Base de Datos")
    
    with st.form("form_restaurar_boveda"):
        uploaded_csv = st.file_uploader("⬆️ Subir Respaldo CSV", type=["csv"])
        btn_restaurar = st.form_submit_button("🔄 Restaurar Preconteos", use_container_width=True)
        if btn_restaurar:
            if uploaded_csv is not None:
                try:
                    df_upload = pd.read_csv(uploaded_csv)
                    if 'id' in df_upload.columns: df_upload = df_upload.drop(columns=['id'])
                    df_upload['sucursal'] = sucursal_in 
                    df_upload.to_sql("pesajes_guardados", con=conn.engine, if_exists="append", index=False)
                    st.session_state.show_toast = "✅ Respaldo restaurado con éxito"
                    st.rerun()
                except Exception as e: st.error(f"Error al restaurar: {e}")
            else: st.warning("⚠️ Primero selecciona un archivo CSV.")

    st.divider()
    if st.session_state.get('usuario_actual') == 'admin':
        with st.expander("🚨 Zona de Peligro (Formatear Nube)", expanded=False):
            confirmar_borrado = st.checkbox("Confirmar el formateo total")
            if st.button("⚠️ ELIMINAR TODO.", use_container_width=True):
                if not confirmar_borrado: st.error("Debes confirmar primero")
                else:
                    with conn.session as s:
                        s.execute(text("DROP TABLE IF EXISTS pesajes_individuales, pesajes_guardados, auditoria_stock CASCADE"))
                        s.commit()
                    st.session_state.show_toast = "✅ Base de datos eliminada"
                    st.rerun()

# ------------------ FUNCIONES AUXILIARES ------------------
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
def mostrar_popup_exito(id_registro, articulo, resultado_ultimo, sucursal, categoria):
    st.markdown(f"### 📦 {articulo}")
    df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
    
    total_real = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
    sumandos = [formato_estricto(val) for val in df_art_combined['resultado_pue']]
    texto_total = f"{' + '.join(sumandos)} = {formato_estricto(total_real)}" if len(sumandos) > 1 else formato_estricto(total_real)
    
    st.metric("TOTAL CALCULADO (Sesión + Bóveda)", texto_total)
    st.divider()
    
    df_stock = conn.query("SELECT stock FROM auditoria_stock WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    saved_stock = float(df_stock.iloc[0]['stock']) if not df_stock.empty else None
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, placeholder="Ingresa y presiona Enter", key=f"modal_stock_{id_registro}")
        
    with col_st2:
        if stock_teorico is not None:
            diferencia = truncar_dos_decimales(total_real - stock_teorico)
            st.metric("DIFERENCIA", value=" ", delta=formato_estricto(diferencia), delta_color="inverse")
            with conn.session as s:
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, total_real, stock, diferencia) 
                             VALUES (:suc, :art, :cat, :tr, :stk, :dif)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET total_real = EXCLUDED.total_real, stock = EXCLUDED.stock, diferencia = EXCLUDED.diferencia, categoria = EXCLUDED.categoria"""), 
                          {"suc": sucursal, "art": articulo, "cat": categoria, "tr": total_real, "stk": stock_teorico, "dif": diferencia})
                s.commit()
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continuar", type="primary", use_container_width=True): st.rerun() 
    with col2:
        if st.button("📥 Enviar a Bóveda", type="secondary", use_container_width=True):
            with conn.session as s:
                s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula, aplicado_en_corte)
                             SELECT sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula, FALSE 
                             FROM pesajes_individuales WHERE id = :id"""), {"id": id_registro})
                s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_registro})
                s.commit()
            st.session_state.show_toast = "✅ Trasladado a la Bóveda."
            st.rerun()

# AJUSTE 3: Agregando la nueva función Global de Actualización de Stock
@st.dialog("⏭️ Confirmar Avance")
def dialog_confirmar_transicion(orden_categorias, orden_ubicaciones, sucursal):
    idx_cat = st.session_state.cat_idx
    idx_ubi = st.session_state.ubi_idx
    
    next_cat_idx = idx_cat
    next_ubi_idx = idx_ubi
    is_complete = False

    if idx_cat < len(orden_categorias) - 1:
        next_cat_idx = idx_cat + 1
    else:
        next_cat_idx = 0
        if idx_ubi < len(orden_ubicaciones) - 1:
            next_ubi_idx = idx_ubi + 1
        else:
            is_complete = True

    if is_complete:
        st.success("🎉 ¡Has completado todas las categorías en todas las ubicaciones!")
        
        # NUEVO BOTÓN: Actualiza todo el stock dinámicamente
        if st.button("✅ ACTUALIZAR STOCK REAL (Todas las categorías)", type="primary", use_container_width=True):
            with conn.session as s:
                for cat in orden_categorias:
                    q_pesajes = text('''
                        SELECT articulo, SUM(resultado_pue) as total_pesado 
                        FROM (
                            SELECT articulo, resultado_pue FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat
                            UNION ALL
                            SELECT articulo, resultado_pue FROM pesajes_guardados WHERE sucursal = :suc AND categoria = :cat AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)
                        ) as combinados GROUP BY articulo
                    ''')
                    res_pesajes = s.execute(q_pesajes, {"suc": sucursal, "cat": cat}).mappings().all()
                    
                    q_stock = text("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc AND categoria = :cat")
                    res_stock = s.execute(q_stock, {"suc": sucursal, "cat": cat}).mappings().all()
                    dict_stock = {row['articulo']: row['stock'] for row in res_stock}
                    
                    for p in res_pesajes:
                        art = p['articulo']
                        tot_pesado = float(p['total_pesado'] or 0)
                        stock_ant = float(dict_stock.get(art, 0))
                        nuevo_stock = stock_ant - tot_pesado
                        
                        s.execute(text("""
                            INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) 
                            VALUES (:suc, :art, :cat, :stk, 0, 0)
                            ON CONFLICT (sucursal, articulo) DO UPDATE 
                            SET stock = EXCLUDED.stock
                        """), {"suc": sucursal, "art": art, "cat": cat, "stk": nuevo_stock})
                        
                    s.execute(text("DELETE FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal, "cat": cat})
                    s.execute(text("UPDATE pesajes_guardados SET aplicado_en_corte = TRUE WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal, "cat": cat})
                s.commit()
            
            st.session_state.show_toast = "✅ Stock de todas las categorías actualizado para mañana."
            st.session_state.pending_transition = False
            st.session_state.cat_idx = 0
            st.session_state.ubi_idx = 0
            st.session_state.auto_index = 0
            st.cache_data.clear()
            st.rerun()

        if st.button("Finalizar y reiniciar recorrido (Sin actualizar)", use_container_width=True):
            st.session_state.pending_transition = False
            st.session_state.cat_idx = 0
            st.session_state.ubi_idx = 0
            st.session_state.auto_index = 0
            st.rerun()
    else:
        st.write(f"Terminaste con todos los productos de **{orden_categorias[idx_cat]}**.")
        st.info(f"¿Deseas pasar a **{orden_categorias[next_cat_idx]}** en **{orden_ubicaciones[next_ubi_idx]}**?")
        
        if st.button("✅ Sí, avanzar", type="primary", use_container_width=True):
            st.session_state.cat_idx = next_cat_idx
            st.session_state.ubi_idx = next_ubi_idx
            st.session_state.auto_index = 0
            st.session_state.pending_transition = False
            st.rerun()

        if st.button("❌ No, quedarme aquí", use_container_width=True):
            st.session_state.pending_transition = False
            st.rerun()

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21.59), Cm(27.94)
        section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Cm(1.5)
        
    cols = 3
    rows = (len(df) + cols - 1) // cols or 1
    table = doc.add_table(rows=rows, cols=cols)
    
    tblBorders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border_el = OxmlElement(f'w:{edge}')
        border_el.set(qn('w:val'), 'dashed'); border_el.set(qn('w:sz'), '4'); border_el.set(qn('w:space'), '0'); border_el.set(qn('w:color'), '000000')
        tblBorders.append(border_el)
    table._tbl.tblPr.append(tblBorders)
    
    for idx, row_data in df.iterrows():
        r = idx // cols
        c_idx = idx % cols
        cell = table.cell(r, c_idx)
        cell.width = Cm(6)
        table.rows[r].height = Cm(4)
        table.rows[r].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        
        tcVAlign = OxmlElement('w:vAlign')
        tcVAlign.set(qn('w:val'), 'center')
        cell._tc.get_or_add_tcPr().append(tcVAlign)
        
        articulo, resultado_str = str(row_data['articulo']), formato_estricto(row_data['resultado_pue'])
        if "PZA" in articulo.upper() and resultado_str.endswith(".00"): resultado_str = resultado_str[:-3]
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p.add_run(f"{articulo}\n")
        run1.font.size, run1.bold = Pt(8), True
        run2 = p.add_run(f"\n{resultado_str}")
        run2.font.size, run2.bold = Pt(12), True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ------------------ 4. INTERFAZ PRINCIPAL ------------------
tab_calc, tab_stock, tab_historial = st.tabs(["🧮 Pesaje", "📦 Stock Real", "📋 Reportes"])

# --- TAB 1: REGISTRO Y AUDITORÍA UNIFICADA (AHORA PESAJE) ---
with tab_calc:
    orden_categorias = ["Papelería Venta", "Limpieza Venta", "Insumos Venta"]
    orden_ubicaciones = ["Bodega", "Piso de Venta"]
    
    if "cat_idx" not in st.session_state: st.session_state.cat_idx = 0
    if "ubi_idx" not in st.session_state: st.session_state.ubi_idx = 0
    if "auto_index" not in st.session_state: st.session_state.auto_index = 0
    if "pending_transition" not in st.session_state: st.session_state.pending_transition = False

    if st.session_state.pending_transition:
        dialog_confirmar_transicion(orden_categorias, orden_ubicaciones, sucursal_in)

    with st.expander("⚙️ Ajustes", expanded=False):
        new_cat = st.selectbox("📂 Seleccione Categoría:", orden_categorias, index=st.session_state.cat_idx)
        new_ubi = st.radio("📍 Ubicación del pesaje:", orden_ubicaciones, index=st.session_state.ubi_idx, horizontal=True)
        modo_seleccionado = st.selectbox("⚙️ Seleccione el Modo:", ["Modo Normal", "Artículo NO listado", "PRE-CONTEO MANUAL (Piezas directas)"], index=0)

        if new_cat != orden_categorias[st.session_state.cat_idx]:
            st.session_state.cat_idx = orden_categorias.index(new_cat)
            st.session_state.auto_index = 0
            st.rerun()
        if new_ubi != orden_ubicaciones[st.session_state.ubi_idx]:
            st.session_state.ubi_idx = orden_ubicaciones.index(new_ubi)
            st.session_state.auto_index = 0
            st.rerun()

    categoria_actual = orden_categorias[st.session_state.cat_idx]
    ubicacion_actual = orden_ubicaciones[st.session_state.ubi_idx]
    
    # Aplicando caché aquí también
    df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h") 
    df_cat_filtrado = df_cat_global[df_cat_global['categoria'] == categoria_actual]
    
    opciones = []
    for _, row in df_cat_filtrado.iterrows():
        ubi_item = row.get('ubicacion_conteo', 'Combinado')
        if pd.isna(ubi_item) or ubi_item == "":
            ubi_item = "Combinado"
        if ubi_item == "Combinado" or ubi_item.lower() == ubicacion_actual.lower():
            opciones.append(row['articulo'])
            
    opciones = sorted(list(set(opciones)))
    
    def avanzar_flujo():
        if len(opciones) > 0 and st.session_state.auto_index < len(opciones) - 1:
            st.session_state.auto_index += 1
        else:
            st.session_state.pending_transition = True

    nuevo_art = (modo_seleccionado == "Artículo NO listado")
    modo_preconteo = (modo_seleccionado == "PRE-CONTEO MANUAL (Piezas directas)")
    
    if not nuevo_art:
        current_index = st.session_state.auto_index
        if current_index >= len(opciones) and len(opciones) > 0: current_index = 0 
        
        art_sel = st.selectbox("📦 Seleccione Artículo:", opciones, index=current_index if len(opciones) > 0 else None, placeholder="Elija un producto...")
        
        # Recuperamos el PUE desde el dataframe filtrado
        df_match = df_cat_filtrado[df_cat_filtrado['articulo'] == art_sel]
        pue_final = float(df_match['pue'].values[0]) if art_sel and not df_match.empty else 1.0
    else:
        c_n1, c_n2 = st.columns([2,1])
        with c_n1: art_sel = st.text_input("Nombre del Nuevo Artículo:", value=None, placeholder="Ej. CAJA PERSONALIZADA")
        with c_n2: pue_final = st.number_input("Asignar Peso Unitario:", value=None, format="%.4f", placeholder="0.0000")

    with st.form(key="form_pesaje", clear_on_submit=True):
        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=None, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total = 0.0, 0.0
            formula = f"[{ubicacion_actual.upper()}] CONTEO MANUAL DIRECTO"
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                peso_bruto = st.number_input("⚖️ Peso Bruto (kg):", value=None, format="%.3f", placeholder="0.000")
            with col2:
                st.write("") 
                t_cont = st.checkbox("📦 Tara Contenedor (0.045)", value=False)
                with st.popover("➕ Tara Manual"):
                    t_manual = st.number_input("⚖️ Peso de tara extra:", value=None, format="%.3f", placeholder="0.000")
        
        st.divider()
        
        col_izq, col_centro, col_der = st.columns([1, 2, 1])
        with col_centro:
            btn_save = st.form_submit_button("📥 GUARDAR Y SIGUIENTE", type="primary", use_container_width=True)
            btn_skip = st.form_submit_button("⏭️ OMITIR", use_container_width=True)

    if btn_skip:
        if not nuevo_art:
            avanzar_flujo()
        st.rerun()

    if btn_save:
        articulo_valido = art_sel is not None and art_sel.strip() != ""
        if modo_preconteo:
            datos_listos = articulo_valido and cantidad_directa is not None
            resultado = truncar_dos_decimales(cantidad_directa) if datos_listos else 0
        else:
            datos_listos = articulo_valido and peso_bruto is not None and pue_final is not None
            if datos_listos:
                tara_total = (0.045 if t_cont else 0) + (t_manual if t_manual is not None else 0.0)
                is_tinta = "TINTA" in str(art_sel).upper(); offset = 0.030 if is_tinta else 0.0
                resultado = truncar_dos_decimales(((peso_bruto - tara_total) - offset) / pue_final)
                formula = f"[{ubicacion_actual.upper()}] ({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"

        if datos_listos:
            fecha_mexico = datetime.now(zona_mx).strftime("%Y-%m-%d %H:%M:%S")
            try:
                with conn.session as s:
                    q_bov = text("SELECT COALESCE(SUM(resultado_pue), 0) FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)")
                    total_boveda = float(s.execute(q_bov, {"art": art_sel, "suc": sucursal_in}).scalar() or 0.0)
                    
                    if total_boveda > 0 and (resultado < total_boveda or resultado == 0):
                        s.execute(text("DELETE FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)"), {"art": art_sel, "suc": sucursal_in})
                        s.execute(text("DELETE FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc"), {"art": art_sel, "suc": sucursal_in})
                        
                        if resultado > 0:
                            s.execute(text("""INSERT INTO pesajes_guardados 
                                         (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula, aplicado_en_corte) 
                                         VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df, FALSE)"""),
                                      {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "cat": categoria_actual, "pb": peso_bruto if not modo_preconteo else 0, 
                                       "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                                       "rp": resultado, "df": "[AUTO-AJUSTE BÓVEDA] " + formula})
                        s.commit()
                        
                        if not nuevo_art:
                            avanzar_flujo()
                            
                        st.session_state.show_toast = f"✅ Bóveda auto-ajustada (Se detectó menos cantidad: de {total_boveda} a {resultado})"
                        st.rerun() 
                    
                    else:
                        res = s.execute(text("""INSERT INTO pesajes_individuales 
                                     (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                                     VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df) RETURNING id"""),
                                  {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "cat": categoria_actual, "pb": peso_bruto if not modo_preconteo else 0, 
                                   "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                                   "rp": resultado, "df": formula})
                        id_recien = res.fetchone()[0]
                        s.commit()
                        
                        if not nuevo_art:
                            avanzar_flujo()
                            
                        mostrar_popup_exito(id_recien, art_sel, resultado, sucursal_in, categoria_actual)
            except Exception as e: st.error(f"Error al guardar: {e}")
        else: st.error("❌ Error: Revisa los datos ingresados.")

    if art_sel:
        st.divider()
        with st.expander(f"📋 Ver detalle e historial de: {art_sel}", expanded=False):
            df_a = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
            df_g = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
            if not df_g.empty: df_g['detalle_formula'] = "[GUARDADO] " + df_g['detalle_formula'].astype(str)
            df_comb = pd.concat([df_a, df_g], ignore_index=True)
            if not df_comb.empty:
                st.dataframe(df_comb[['detalle_formula', 'resultado_pue']].rename(columns={'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad'}), hide_index=True, use_container_width=True)
            else: st.info("No hay pesajes registrados para este artículo.")


# --- TAB 2: STOCK REAL POR CATEGORÍAS (AHORA STOCK REAL) ---
with tab_stock:
    st.subheader("📦 Control de Stock Real e Inventario Dinámico")
    
    categoria_activa_stock = st.selectbox("📂 Seleccione la Categoría de Inventario:", list(productos_por_categoria.keys()), key="cat_stock")
    productos_dict_stock = productos_por_categoria.get(categoria_activa_stock, {})
    
    st.markdown("Edita directamente la columna **Cantidad Anterior** para calibrar tu base. El sistema restará en automático sumando la sesión normal y la Bóveda.")

    query_unificada = """
        SELECT articulo, resultado_pue 
        FROM (
            SELECT articulo, resultado_pue FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat
            UNION ALL
            SELECT articulo, resultado_pue FROM pesajes_guardados WHERE sucursal = :suc AND categoria = :cat AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)
        ) as combinados
    """
    df_raw = conn.query(query_unificada, params={"suc": sucursal_in, "cat": categoria_activa_stock}, ttl=0)
    
    pesajes_data = []
    if not df_raw.empty:
        for art, group in df_raw.groupby('articulo'):
            valores = group['resultado_pue'].tolist()
            total = truncar_dos_decimales(sum(valores))
            str_vals = [formato_estricto(v) for v in valores]
            desglose = f"{' + '.join(str_vals)} = {formato_estricto(total)}" if len(valores) > 1 else formato_estricto(total)
            pesajes_data.append({"articulo": art, "total_pesado": total, "desglose_pesada": desglose})
            
    df_total_pesado = pd.DataFrame(pesajes_data) if pesajes_data else pd.DataFrame(columns=["articulo", "total_pesado", "desglose_pesada"])

    df_auditoria_base = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc AND categoria = :cat", params={"suc": sucursal_in, "cat": categoria_activa_stock}, ttl=0)

    lista_dict = list(productos_dict_stock.keys())
    lista_audit = df_auditoria_base['articulo'].tolist() if not df_auditoria_base.empty else []
    lista_pesados = df_total_pesado['articulo'].tolist() if not df_total_pesado.empty else []
    lista_todos_articulos = sorted(list(set(lista_dict + lista_audit + lista_pesados)))
    
    df_stock_master = pd.DataFrame({"articulo": lista_todos_articulos})
    
    if not df_auditoria_base.empty:
        df_stock_master = pd.merge(df_stock_master, df_auditoria_base, on="articulo", how="left")
    else:
        df_stock_master["stock"] = 0.0

    if not df_total_pesado.empty:
        df_stock_master = pd.merge(df_stock_master, df_total_pesado, on="articulo", how="left")
        df_stock_master["total_pesado"] = df_stock_master["total_pesado"].fillna(0.0)
        df_stock_master["desglose_pesada"] = df_stock_master["desglose_pesada"].fillna("0.00")
    else:
        df_stock_master["total_pesado"] = 0.0
        df_stock_master["desglose_pesada"] = "0.00"

    df_stock_master["stock"] = df_stock_master["stock"].fillna(0.0)
    df_stock_master["cantidad_actual"] = df_stock_master["stock"] - df_stock_master["total_pesado"]

    df_stock_display = df_stock_master[[
        "stock", "articulo", "desglose_pesada", "total_pesado", "cantidad_actual"
    ]].rename(columns={
        "stock": "Cantidad Anterior",
        "articulo": "Producto",
        "desglose_pesada": "Cantidad Pesada",
        "total_pesado": "Cantidad a Restar",
        "cantidad_actual": "Stock Actualizado"
    })

    with st.expander("📦 Tabla de Stock Real", expanded=False):
        df_editado = st.data_editor(
            df_stock_display,
            use_container_width=True,
            hide_index=True,
            disabled=["Producto", "Cantidad Pesada", "Cantidad a Restar", "Stock Actualizado"],
            key=f"editor_stock_real_{categoria_activa_stock}"
        )

        if st.button(f"💾 Guardar Cambios de Stock Inicial ({categoria_activa_stock})", use_container_width=True):
            with conn.session as s:
                for _, row in df_editado.iterrows():
                    art = row["Producto"]
                    nuevo_stock = row["Cantidad Anterior"]
                    s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) 
                                 VALUES (:suc, :art, :cat, :stk, 0, 0)
                                 ON CONFLICT (sucursal, articulo) DO UPDATE 
                                 SET stock = EXCLUDED.stock"""), 
                              {"suc": sucursal_in, "art": art, "cat": categoria_activa_stock, "stk": nuevo_stock})
                s.commit()
            st.session_state.show_toast = "✅ Stock inicial actualizado correctamente."
            st.rerun()

    st.divider()
    if st.button(f"🔄 CONVERTIR STOCK DE {categoria_activa_stock.upper()} PARA MAÑANA", type="primary", use_container_width=True):
        with conn.session as s:
            articulos_con_pesaje = df_stock_master[df_stock_master["total_pesado"] > 0]
            for _, row in articulos_con_pesaje.iterrows():
                art = row["articulo"]
                nueva_base = row["cantidad_actual"]
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) 
                             VALUES (:suc, :art, :cat, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET stock = EXCLUDED.stock"""), 
                          {"suc": sucursal_in, "art": art, "cat": categoria_activa_stock, "stk": nueva_base})
            
            s.execute(text("DELETE FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal_in, "cat": categoria_activa_stock})
            s.execute(text("UPDATE pesajes_guardados SET aplicado_en_corte = TRUE WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal_in, "cat": categoria_activa_stock})
            s.commit()
            
        st.session_state.show_toast = f"✅ ¡Inventario convertido para mañana ({categoria_activa_stock})!"
        st.rerun()

    # --- ADMINISTRADOR DE CATÁLOGO DINÁMICO ---
    st.divider()
    with st.expander(f"📝 Administrar Catálogo: {categoria_activa_stock}", expanded=False):
        st.markdown("Agrega nuevos productos, modifica nombres o cambia el PUE. Al guardar, se aplicará en toda la aplicación.")
        
        # Aplicando caché aquí también
        df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h")
        df_cat_edit = df_cat_global[df_cat_global['categoria'] == categoria_activa_stock][['articulo', 'pue', 'ubicacion_conteo']].copy()
        
        if 'ubicacion_conteo' not in df_cat_edit.columns: 
            df_cat_edit['ubicacion_conteo'] = "Combinado"
        df_cat_edit['ubicacion_conteo'] = df_cat_edit['ubicacion_conteo'].fillna("Combinado")
        
        edited_catalogo = st.data_editor(
            df_cat_edit,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_cat_{categoria_activa_stock}",
            column_config={
                "articulo": st.column_config.TextColumn("Nombre del Producto", required=True),
                "pue": st.column_config.NumberColumn("Peso Unitario Estándar (PUE)", required=True, format="%.4f"),
                "ubicacion_conteo": st.column_config.SelectboxColumn(
                    "Aplica en",
                    help="¿Dónde se cuenta este insumo?",
                    options=["Bodega", "Piso de Venta", "Combinado"],
                    required=True,
                    default="Combinado"
                )
            }
        )
        
        if st.button(f"💾 Guardar Catálogo y Actualizar Pestañas", type="secondary", use_container_width=True):
            with conn.session as s:
                s.execute(text("DELETE FROM catalogo_productos WHERE categoria = :cat"), {"cat": categoria_activa_stock})
                
                for _, row in edited_catalogo.iterrows():
                    art_val = str(row['articulo']).strip()
                    if art_val and not pd.isna(row['pue']):
                        pue_val = float(row['pue'])
                        ubi_val = str(row['ubicacion_conteo']) if pd.notna(row['ubicacion_conteo']) else "Combinado"
                        
                        s.execute(text("INSERT INTO catalogo_productos (categoria, articulo, pue, ubicacion_conteo) VALUES (:c, :a, :p, :u) ON CONFLICT DO NOTHING"), 
                                  {"c": categoria_activa_stock, "a": art_val, "p": pue_val, "u": ubi_val})
                s.commit()
            st.cache_data.clear() # AJUSTE 4: Limpiamos caché para refrescar catálogo
            st.session_state.show_toast = "✅ Catálogo guardado. La aplicación se ha actualizado."
            st.rerun()

# --- TAB 3: EXPORTACIÓN Y BÓVEDA (AHORA REPORTES) ---
with tab_historial:
    cat_filtro = st.selectbox("📂 Filtrar vistas por Categoría:", ["Todas"] + list(productos_por_categoria.keys()))
    
    if cat_filtro == "Todas":
        df_actual = conn.query("SELECT * FROM pesajes_individuales WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
        df_guardados = conn.query("SELECT * FROM pesajes_guardados WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
    else:
        df_actual = conn.query("SELECT * FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat", params={"suc": sucursal_in, "cat": cat_filtro}, ttl=0)
        df_guardados = conn.query("SELECT * FROM pesajes_guardados WHERE sucursal = :suc AND categoria = :cat", params={"suc": sucursal_in, "cat": cat_filtro}, ttl=0)

    df_guardados_rep = df_guardados.copy()
    if not df_guardados_rep.empty: df_guardados_rep['detalle_formula'] = "[GUARDADO] " + df_guardados_rep['detalle_formula'].astype(str)
    df_combined = pd.concat([df_actual, df_guardados_rep], ignore_index=True)

    if not df_combined.empty:
        st.subheader("📄 Tarjetas Recortables (Word)")
        if not df_guardados.empty:
            st.download_button("📄 Descargar Tarjetas en Word (Pre-conteos)", data=generar_word_tarjetas(df_guardados[['articulo', 'resultado_pue']].copy()), file_name=f"Tarjetas_Preconteos_{sucursal_in.replace(' ', '_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        else: st.info("No hay pre-conteos guardados en la bóveda para generar tarjetas.")
            
        st.markdown(f'<a href="https://wa.me/{numero_wa}" target="_blank" class="btn-wa">💬 ABRIR WHATSAPP (Para enviar archivos)</a>', unsafe_allow_html=True)
        st.divider()
        
        with st.expander("🗑️ Administración de Registros Individuales (Sesión Actual)", expanded=False):
            st.markdown("#### Selecciona el renglón de la izquierda y presiona el ícono de papelera 🗑️ para borrar.")
            edited_df = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_actual.columns.tolist(), key="editor_db")
            if st.button("💾 Guardar Cambios en Tabla", use_container_width=True):
                ids_to_delete = set(df_actual['id']) - set(edited_df['id'])
                if ids_to_delete:
                    with conn.session as s:
                        for del_id in ids_to_delete: s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": int(del_id)})
                        s.commit()
                    st.session_state.show_toast = f"✅ Se eliminaron {len(ids_to_delete)} registros correctamente."
                    st.rerun()
                else: st.info("No detecté ninguna fila eliminada para guardar.")

        with st.expander("🛡️ Trasladar a Bóveda (Preconteos Permanentes)", expanded=False):
            st.markdown("Mueve registros de la sesión actual a la bóveda segura.")
            opciones_proteger = df_actual.apply(lambda x: f"ID {x['id']} | {x['articulo']} | {x['resultado_pue']} u.", axis=1).tolist()
            sel = st.multiselect("Selecciona los registros a mover a la bóveda:", opciones_proteger)
            if st.button("📥 Mover seleccionados a la Bóveda") and sel:
                with conn.session as s:
                    for item in sel:
                        id_val = int(item.split(" | ")[0].replace("ID ", ""))
                        s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula)
                                     SELECT sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula 
                                     FROM pesajes_individuales WHERE id = :id"""), {"id": id_val})
                        s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_val})
                    s.commit()
                st.session_state.show_toast = f"✅ Se han trasladado {len(sel)} registros a la Bóveda."
                st.rerun()
            
            st.divider()
            st.markdown("#### 🗃️ Pre-conteos Guardados Actualmente")
            if not df_guardados.empty:
                edited_guardados = st.data_editor(df_guardados, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_guardados.columns.tolist(), key="editor_db_guardados")
                if st.button("💾 Eliminar filas borradas de la Bóveda", use_container_width=True):
                    ids_to_delete_g = set(df_guardados['id']) - set(edited_guardados['id'])
                    if ids_to_delete_g:
                        with conn.session as s:
                            for del_id in ids_to_delete_g: s.execute(text("DELETE FROM pesajes_guardados WHERE id = :id"), {"id": int(del_id)})
                            s.commit()
                        st.session_state.show_toast = f"✅ Se eliminaron {len(ids_to_delete_g)} registros guardados."
                        st.rerun()
            else: st.info("No hay pre-conteos guardados en la bóveda.")
    else: st.info(f"No hay pesajes registrados para {sucursal_in} en esta categoría.")

components.html("""
    <script>
    const num_inputs = window.parent.document.querySelectorAll('input[type="number"]');
    num_inputs.forEach(input => input.setAttribute('enterkeyhint', 'done'));
    setTimeout(() => {
        const selectores = window.parent.document.querySelectorAll('input[aria-autocomplete="list"], input[role="combobox"]');
        if(selectores.length > 0) selectores[0].focus();
    }, 600); 
    </script>
""", height=0)
