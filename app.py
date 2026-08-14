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

    div[data-testid="stToastContainer"] {
        top: 2rem !important; bottom: auto !important; right: 2rem !important;
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

    # Parchar bases de datos existentes con la columna de categoría
    s.execute(text('ALTER TABLE pesajes_individuales ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE auditoria_stock ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS aplicado_en_corte BOOLEAN DEFAULT TRUE;'))

    s.commit()

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

# ------------------ DICCIONARIO CATEGORIZADO ------------------
productos_por_categoria = {
    "Insumos Venta": {
        "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
        "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
        "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO BLANCO POR PZA A": 0.000436,
        "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
        "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
        "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
        "HIGIENICO SCOTT ROLLO POR PZA M": 0.500, "TOALLA ROLLO 180M POR PZA M": 1.115, "BOLSA LOCK POR PZA A": 0.018,
        "AGUA CIEL 20 POR LT A": 1.0, "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, 
        "BOLSA CAMISETA LOGO GDE POR KG A": 1.0, "BOLSA NATURAL 18 X 25 POR KG A": 1.0, 
        "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0, "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, 
        "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0
    },
    "Limpieza Venta": {
        "CLOROLIMP POR L A": 1.0, "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
        "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "JABON LIQUIDO PARA MANOS POR L M": 1.0, "LAVALOZA POR L A": 1.0,
        "PRO GEL POR L B": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0, "ESCURRIDOR POR PZA M": 1.0, 
        "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0
    },
    "Papelería Venta": {
        "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
        "GRAPAS CJ POR PZA M": 0.164, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
        "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
        "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, 
        "ROLLO TERMICO P/TPV POR PZA A": 1.0
    }
}

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
tab_stock, tab_calc, tab_historial = st.tabs(["📦 Stock Real", "🧮 Nueva Entrada & Auditoría", "📋 Reportes y Bóveda"])

# --- TAB 0: STOCK REAL POR CATEGORÍAS ---
with tab_stock:
    st.subheader("📦 Control de Stock Real e Inventario Dinámico")
    
    categoria_activa = st.selectbox("📂 Seleccione la Categoría de Inventario:", list(productos_por_categoria.keys()))
    productos_dict = productos_por_categoria[categoria_activa]
    
    st.markdown("Edita directamente la columna **Cantidad Anterior** para calibrar tu base. El sistema restará en automático sumando la sesión normal y la Bóveda.")

    # Filtramos todo por la categoría activa
    query_unificada = """
        SELECT articulo, resultado_pue 
        FROM (
            SELECT articulo, resultado_pue FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat
            UNION ALL
            SELECT articulo, resultado_pue FROM pesajes_guardados WHERE sucursal = :suc AND categoria = :cat AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)
        ) as combinados
    """
    df_raw = conn.query(query_unificada, params={"suc": sucursal_in, "cat": categoria_activa}, ttl=0)
    
    pesajes_data = []
    if not df_raw.empty:
        for art, group in df_raw.groupby('articulo'):
            valores = group['resultado_pue'].tolist()
            total = truncar_dos_decimales(sum(valores))
            str_vals = [formato_estricto(v) for v in valores]
            desglose = f"{' + '.join(str_vals)} = {formato_estricto(total)}" if len(valores) > 1 else formato_estricto(total)
            pesajes_data.append({"articulo": art, "total_pesado": total, "desglose_pesada": desglose})
            
    df_total_pesado = pd.DataFrame(pesajes_data) if pesajes_data else pd.DataFrame(columns=["articulo", "total_pesado", "desglose_pesada"])

    df_auditoria_base = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc AND categoria = :cat", params={"suc": sucursal_in, "cat": categoria_activa}, ttl=0)

    lista_dict = list(productos_dict.keys())
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

    df_editado = st.data_editor(
        df_stock_display,
        use_container_width=True,
        hide_index=True,
        disabled=["Producto", "Cantidad Pesada", "Cantidad a Restar", "Stock Actualizado"],
        key=f"editor_stock_real_{categoria_activa}"
    )

    if st.button(f"💾 Guardar Cambios de Stock Inicial ({categoria_activa})", use_container_width=True):
        with conn.session as s:
            for _, row in df_editado.iterrows():
                art = row["Producto"]
                nuevo_stock = row["Cantidad Anterior"]
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) 
                             VALUES (:suc, :art, :cat, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET stock = EXCLUDED.stock"""), 
                          {"suc": sucursal_in, "art": art, "cat": categoria_activa, "stk": nuevo_stock})
            s.commit()
        st.session_state.show_toast = "✅ Stock inicial actualizado correctamente."
        st.rerun()

    st.divider()
    if st.button(f"🔄 CONVERTIR STOCK DE {categoria_activa.upper()} PARA MAÑANA", type="primary", use_container_width=True):
        with conn.session as s:
            articulos_con_pesaje = df_stock_master[df_stock_master["total_pesado"] > 0]
            for _, row in articulos_con_pesaje.iterrows():
                art = row["articulo"]
                nueva_base = row["cantidad_actual"]
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) 
                             VALUES (:suc, :art, :cat, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET stock = EXCLUDED.stock"""), 
                          {"suc": sucursal_in, "art": art, "cat": categoria_activa, "stk": nueva_base})
            
            s.execute(text("DELETE FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal_in, "cat": categoria_activa})
            s.execute(text("UPDATE pesajes_guardados SET aplicado_en_corte = TRUE WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal_in, "cat": categoria_activa})
            s.commit()
            
        st.session_state.show_toast = f"✅ ¡Inventario convertido para mañana ({categoria_activa})!"
        st.rerun()

# --- TAB 1: REGISTRO Y AUDITORÍA UNIFICADA ---
with tab_calc:
    cat_reg = st.selectbox("📂 Seleccione Categoría de Registro:", list(productos_por_categoria.keys()), key="cat_reg")
    productos_dict_reg = productos_por_categoria[cat_reg]
    
    # --- Estado para avance automático e ubicación ---
    if "auto_index" not in st.session_state:
        st.session_state.auto_index = 0
    if "ubicacion_pesaje" not in st.session_state:
        st.session_state.ubicacion_pesaje = "Bodega"
        
    st.session_state.ubicacion_pesaje = st.radio(
        "📍 Ubicación del pesaje:", 
        ["Bodega", "Piso de Venta"], 
        horizontal=True, 
        index=["Bodega", "Piso de Venta"].index(st.session_state.ubicacion_pesaje)
    )
    
    with st.expander("🎤 **Ingreso por Voz** (Click para desplegar)", expanded=False):
        audio_bytes = st.audio_input("Di algo como: 0.620 de capacillo chino en contenedor.", key="audio_reg")
        texto_reconocido, texto_filtro = "", ""
        if audio_bytes:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                audio_data = recognizer.record(source)
                try:
                    texto_reconocido = recognizer.recognize_google(audio_data, language="es-MX")
                    st.toast(f"🎤 Escuchado: {texto_reconocido}")
                    components.html(f"""<script>
                        const utterance = new SpeechSynthesisUtterance("{texto_reconocido}");
                        utterance.lang = 'es-MX'; utterance.rate = 1.0;
                        window.speechSynthesis.speak(utterance);
                    </script>""", height=0)
                except sr.UnknownValueError: st.error("No se pudo entender el audio.")
                except sr.RequestError: st.error("Error en el servicio de reconocimiento de voz.")
            texto_filtro = texto_reconocido.upper() if texto_reconocido else ""
    
    idx_sugerido, peso_sugerido, pue_sugerido, t_cont_sugerido, nombre_limpio_sugerido = None, None, None, False, ""
    opciones = sorted(productos_dict_reg.keys())
    
    if texto_filtro:
        if "CONTENEDOR" in texto_filtro: t_cont_sugerido = True
        match_pue = re.search(r'(?:PESO UNITARIO|UNITARIO|PUE|ESTÁNDAR|ESTANDAR)[^\d]*(\d+(?:[.,]\d+)?)', texto_filtro)
        if match_pue: pue_sugerido = float(match_pue.group(1).replace(',', '.'))
        numeros_floats = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', texto_filtro)]
        if numeros_floats:
            if pue_sugerido in numeros_floats: numeros_floats.remove(pue_sugerido) 
            if numeros_floats: peso_sugerido = numeros_floats[0] 
        texto_limpio = texto_filtro
        for p in [r'\d+(?:[.,]\d+)?', 'PESO UNITARIO', 'PUE', 'PESO', 'UNITARIO', 'ESTÁNDAR', 'ESTANDAR', 'KILOS', 'KG', 'GRAMOS', 'CON', 'SIN', 'Y', 'DE', 'EL', 'LA', 'CONTENEDOR', 'BISAGRA', 'LLEVA', 'ASIGNAR']:
            texto_limpio = re.sub(r'\b' + p + r'\b', '', texto_limpio)
        nombre_limpio_sugerido = ' '.join(texto_limpio.split()) 
        if nombre_limpio_sugerido.split():
            max_coincidencias = 0
            for i, prod in enumerate(opciones):
                coincidencias = sum(1 for palabra in nombre_limpio_sugerido.split() if palabra in prod.upper())
                if coincidencias > max_coincidencias: max_coincidencias, idx_sugerido = coincidencias, i

    modo_seleccionado = st.selectbox("⚙️ Seleccione el Modo de Registro:", ["Modo Normal", "Artículo NO listado", "PRE-CONTEO MANUAL (Piezas directas)"], index=0)
    nuevo_art, modo_preconteo = (modo_seleccionado == "Artículo NO listado"), (modo_seleccionado == "PRE-CONTEO MANUAL (Piezas directas)")
    
    if not nuevo_art:
        # Lógica de auto-avance
        current_index = idx_sugerido if idx_sugerido is not None else st.session_state.auto_index
        if current_index >= len(opciones): current_index = 0 
        
        art_sel = st.selectbox("Seleccione Artículo (Aplica para registro y desglose):", opciones, index=current_index, placeholder="Elija un producto...")
        pue_final = productos_dict_reg.get(art_sel, 1.0) if art_sel else 1.0
    else:
        c_n1, c_n2 = st.columns([2,1])
        with c_n1: art_sel = st.text_input("Nombre del Nuevo Artículo:", value=nombre_limpio_sugerido if nombre_limpio_sugerido else None, placeholder="Ej. CAJA PERSONALIZADA")
        with c_n2: pue_final = st.number_input("Asignar Peso Unitario:", value=pue_sugerido, format="%.4f", placeholder="0.0000")

    # --- Interfaz aplanada para taras rápidas ---
    with st.form(key="form_pesaje", clear_on_submit=True):
        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=peso_sugerido, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total = 0.0, 0.0
            formula = f"[{st.session_state.ubicacion_pesaje.upper()}] CONTEO MANUAL DIRECTO"
        else:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                peso_bruto = st.number_input("⚖️ Peso Bruto (kg):", value=peso_sugerido, format="%.3f", placeholder="0.000")
            with col2:
                t_cont = st.checkbox("📦 Tara Contenedor (0.045)", value=t_cont_sugerido)
            with col3:
                t_manual = st.number_input("⚖️ Tara Manual:", value=None, format="%.3f", placeholder="0.000")
        
        st.divider()
        btn_save = st.form_submit_button("📥 GUARDAR Y SIGUIENTE PRODUCTO")

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
                formula = f"[{st.session_state.ubicacion_pesaje.upper()}] ({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"

        if datos_listos:
            fecha_mexico = datetime.now(zona_mx).strftime("%Y-%m-%d %H:%M:%S")
            try:
                with conn.session as s:
                    # LÓGICA DE ACTUALIZACIÓN AUTOMÁTICA DE BÓVEDA
                    q_bov = text("SELECT COALESCE(SUM(resultado_pue), 0) FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)")
                    total_boveda = float(s.execute(q_bov, {"art": art_sel, "suc": sucursal_in}).scalar() or 0.0)
                    
                    if total_boveda > 0 and (resultado < total_boveda or resultado == 0):
                        s.execute(text("DELETE FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)"), {"art": art_sel, "suc": sucursal_in})
                        s.execute(text("DELETE FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc"), {"art": art_sel, "suc": sucursal_in})
                        
                        if resultado > 0:
                            s.execute(text("""INSERT INTO pesajes_guardados 
                                         (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula, aplicado_en_corte) 
                                         VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df, FALSE)"""),
                                      {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "cat": cat_reg, "pb": peso_bruto if not modo_preconteo else 0, 
                                       "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                                       "rp": resultado, "df": "[AUTO-AJUSTE BÓVEDA] " + formula})
                        s.commit()
                        
                        # Avance Automático
                        if not nuevo_art:
                            if st.session_state.auto_index < len(opciones) - 1: st.session_state.auto_index += 1
                            else: st.session_state.auto_index = 0
                            
                        st.session_state.show_toast = f"✅ Bóveda auto-ajustada (Se detectó menos cantidad: de {total_boveda} a {resultado})"
                        st.rerun() 
                    
                    else:
                        res = s.execute(text("""INSERT INTO pesajes_individuales 
                                     (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                                     VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df) RETURNING id"""),
                                  {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "cat": cat_reg, "pb": peso_bruto if not modo_preconteo else 0, 
                                   "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                                   "rp": resultado, "df": formula})
                        id_recien = res.fetchone()[0]
                        s.commit()
                        
                        # Avance Automático
                        if not nuevo_art:
                            if st.session_state.auto_index < len(opciones) - 1: st.session_state.auto_index += 1
                            else: st.session_state.auto_index = 0
                            
                        mostrar_popup_exito(id_recien, art_sel, resultado, sucursal_in, cat_reg)
            except Exception as e: st.error(f"Error al guardar: {e}")
        else: st.error("❌ Error: Revisa los datos ingresados.")

    if art_sel:
        st.divider()
        st.markdown(f"📋 **Historial de {art_sel}**")
        df_a = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        df_g = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        if not df_g.empty: df_g['detalle_formula'] = "[GUARDADO] " + df_g['detalle_formula'].astype(str)
        df_comb = pd.concat([df_a, df_g], ignore_index=True)
        if not df_comb.empty:
            st.dataframe(df_comb[['detalle_formula', 'resultado_pue']].rename(columns={'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad'}), hide_index=True, use_container_width=True)
        else: st.info("No hay pesajes registrados para este artículo.")

# --- TAB 2: EXPORTACIÓN Y BÓVEDA ---
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

# --- AUTO-FOCO CON JAVASCRIPT ---
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
