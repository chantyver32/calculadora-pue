import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
import urllib.parse
import pytz
import io
import time
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

# 1. CONFIGURACIÓN Y ESTADO

# ------------------ CONFIGURACIÓN GENERAL ------------------
# st.set_page_config DEBE ser siempre el primer comando de Streamlit
st.set_page_config(page_title="Insumos", page_icon="⚖️", layout="wide")

with st.spinner('Iniciando sistema Champlitte... 🥐'):
    zona_mx = pytz.timezone('America/Mexico_City')
    fecha_hoy_mx = datetime.now(zona_mx).date()

# Estilos CSS
st.markdown("""
    <style>
    /* Ajuste equilibrado del espacio superior para no tapar las pestañas */
    .block-container { padding-top: 3rem; padding-bottom: 1rem; }
    
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
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    
    /* Tamaño del total azul */
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    
    /* Tamaño gigante para la diferencia (verde/roja) y su flecha */
    div[data-testid="stMetricDelta"] { font-size: 30px !important; font-weight: bold !important; }
    div[data-testid="stMetricDelta"] svg { width: 35px !important; height: 35px !important; }

    /* ESTILO OSCURO PARA LISTAS DESPLEGABLES (FONDO NEGRO) */
    
    /* 1. Fondo del menú desplegable (opciones) */
    div[data-baseweb="popover"] > div {
        background-color: #1a1a1c !important; /* Fondo oscuro suavizado (tipo panel) */
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.8) !important;
    }
    div[data-baseweb="popover"] ul {
        background-color: transparent !important; 
    }
    div[data-baseweb="popover"] li {
        background-color: transparent !important;
        color: #FFFFFF !important;
        font-size: 14px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #2d2d30 !important; /* Efecto hover sutil */
    }
    
    /* --> NUEVO: Sombreado de la opción PREVIAMENTE SELECCIONADA <-- */
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #3a3b3e !important; /* Color gris resaltado tipo 94389.jpg */
        font-weight: bold !important;
    }

    /* 2. Caja principal del Selectbox (antes de abrir) */
    div[data-baseweb="select"] > div {
        background-color: #1a1a1c !important; 
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    /* 3. Efecto Focus */
    div[data-baseweb="select"] > div:focus-within {
        border-color: #ff4b4b !important; 
        box-shadow: 0 0 0 1px #ff4b4b !important;
    }

    /* 4. Color del texto seleccionado y el ícono de la flecha */
    div[data-baseweb="select"] div {
        color: #FFFFFF !important;
    }
    div[data-baseweb="select"] svg {
        fill: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN A LA BASE DE DATOS SUPABASE (POSTGRESQL)
conn = st.connection("supabase", type="sql")

# Inicialización de tablas en Supabase
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

# ------------------ SISTEMA DE USUARIOS EN SUPABASE ------------------
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h2 style='text-align: center;'>⚖️ Baja de insumos</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray;'>Control de Acceso</h4>", unsafe_allow_html=True)
        
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
                        # NUEVO: Mensaje de bienvenida y pausa breve
                        st.success(f"✅ ¡Bienvenido, {usuario_input.strip()}!")
                        time.sleep(1.2) # Pausa para que el usuario alcance a leerlo
                        
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = usuario_input.strip()
                        st.rerun()
                    else:
                        # NUEVO: Mensaje de error más claro
                        st.error("❌ Usuario o contraseña no válidos. Por favor, intenta de nuevo.")
        return False
    return True

if not verificar_login():
    st.stop()
# ---------------------------------------------------------------------

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🏢 Datos de Sesión")
    
    st.caption(f"👤 Conectado como: **{st.session_state.get('usuario_actual', 'Usuario')}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        if "usuario_actual" in st.session_state:
            del st.session_state["usuario_actual"]
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
    elabora_in = st.session_state.get('usuario_actual', 'USUARIO').upper()
    numero_wa = datos_sucursales[sucursal_in]
    st.caption(f"📱WhatsApp: **{numero_wa}**")

    st.divider()
    st.markdown("### 💾 Respaldo de Base de Datos")
    st.info(f"Restaura pre-conteos (bóveda) específicamente para {sucursal_in}.")
    
    with st.form("form_restaurar_boveda"):
        uploaded_csv = st.file_uploader("⬆️ Subir Respaldo CSV", type=["csv"])
        btn_restaurar = st.form_submit_button("🔄 Restaurar Preconteos", use_container_width=True)
        
        if btn_restaurar:
            if uploaded_csv is not None:
                try:
                    df_upload = pd.read_csv(uploaded_csv)
                    if 'id' in df_upload.columns:
                        df_upload = df_upload.drop(columns=['id'])
                    
                    df_upload['sucursal'] = sucursal_in 
                    df_upload.to_sql("pesajes_guardados", con=conn.engine, if_exists="append", index=False)
                    st.success("✅ Respaldo restaurado con éxito")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al restaurar: {e}")
            else:
                st.warning("⚠️ Primero selecciona un archivo CSV.")

    st.divider()
    if st.session_state.get('usuario_actual') == 'admin':
        with st.expander("🚨 Zona de Peligro (Formatear Nube)", expanded=False):
            st.warning("⚠️ ESTE BOTÓN BORRA TODA LA BASE DE DATOS.")
            confirmar_borrado = st.checkbox("Confirmar el formateo total")
            if st.button("⚠️ ELIMINAR TODO.", use_container_width=True):
                if not confirmar_borrado:
                    st.error("Debes confirmar primero")
                else:
                    with conn.session as s:
                        s.execute(text("DROP TABLE IF EXISTS pesajes_individuales, pesajes_guardados, auditoria_stock CASCADE"))
                        s.commit()
                    st.success("✅ Base de datos eliminada")
                    time.sleep(2)
                    st.rerun()

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

# --- FUNCIÓN DEL POP-UP ACTUALIZADA (AHORA CON AUDITORÍA) ---
@st.dialog("✅ Registrado")
def mostrar_popup_exito(id_registro, articulo, resultado_ultimo, sucursal):
    st.markdown(f"### 📦 {articulo}")
    
    # Consultar todos los pesajes (sesión + bóveda) para este artículo
    df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
    
    total_real = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
    
    # Crear string de la sumatoria (Ej. 40.00 + 13.78 = 53.78)
    sumandos = [formato_estricto(val) for val in df_art_combined['resultado_pue']]
    if len(sumandos) > 1:
        texto_total = f"{' + '.join(sumandos)} = {formato_estricto(total_real)}"
    else:
        texto_total = formato_estricto(total_real)
    
    st.metric("TOTAL CALCULADO (Sesión + Bóveda)", texto_total)
    
    st.divider()
    
    # Manejo de Stock y Diferencia dentro del Pop-up
    df_stock = conn.query("SELECT stock FROM auditoria_stock WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    saved_stock = float(df_stock.iloc[0]['stock']) if not df_stock.empty else None
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, placeholder="Ingresa y presiona Enter", key=f"modal_stock_{id_registro}")
        
    with col_st2:
        if stock_teorico is not None:
            diferencia = truncar_dos_decimales(total_real - stock_teorico)
            st.metric("DIFERENCIA", value=" ", delta=formato_estricto(diferencia), delta_color="inverse")
            
            # Guardado automático de la auditoría en BD
            with conn.session as s:
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, total_real, stock, diferencia) 
                             VALUES (:suc, :art, :tr, :stk, :dif)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET total_real = EXCLUDED.total_real, 
                                 stock = EXCLUDED.stock, 
                                 diferencia = EXCLUDED.diferencia"""), 
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
            st.success("Trasladado a la Bóveda.")
            time.sleep(0.8)
            st.rerun()
# -------------------------------------------------------------------

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        # Configurar Tamaño Carta (8.5 x 11 pulgadas = 21.59 x 27.94 cm)
        section.page_width = Cm(21.59)
        section.page_height = Cm(27.94)
        
        # Margen general de 1.5 cm
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)
        
    # Columnas: Con margen de 1.5cm, quedan 18.59cm utilizables.
    # Tarjetas de 6 cm -> Caben perfectamente 3 columnas (18 cm).
    cols = 3
    rows = (len(df) + cols - 1) // cols
    if rows == 0: rows = 1
    
    table = doc.add_table(rows=rows, cols=cols)
    
    # ---------------------------------------------------------
    # Inyectar XML para crear bordes punteados en toda la tabla
    # ---------------------------------------------------------
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    
    # Aplicamos estilo 'dashed' (línea punteada para recortar) a todos los bordes
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border_el = OxmlElement(f'w:{edge}')
        border_el.set(qn('w:val'), 'dashed')  
        border_el.set(qn('w:sz'), '4')        # Grosor de la línea
        border_el.set(qn('w:space'), '0')
        border_el.set(qn('w:color'), '000000') # Negro
        tblBorders.append(border_el)
    tblPr.append(tblBorders)
    # ---------------------------------------------------------
    
    for idx, row_data in df.iterrows():
        r = idx // cols
        c_idx = idx % cols
        cell = table.cell(r, c_idx)
        
        # Dimensiones de la celda (tarjeta): 6 cm de ancho x 4 cm de alto
        cell.width = Cm(6)
        table.rows[r].height = Cm(4)
        table.rows[r].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        
        # Centrado Vertical del contenido de la celda
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcVAlign = OxmlElement('w:vAlign')
        tcVAlign.set(qn('w:val'), 'center')
        tcPr.append(tcVAlign)
        
        articulo = str(row_data['articulo'])
        resultado_str = formato_estricto(row_data['resultado_pue'])
        
        # Quitamos ".00" si el producto es una pieza (PZA, PZAS)
        if "PZA" in articulo.upper():
            if resultado_str.endswith(".00"):
                resultado_str = resultado_str[:-3]
        
        # Textos internos
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        run1 = p.add_run(f"{articulo}\n")
        run1.font.size = Pt(8)
        run1.bold = True
        
        # Insertamos el número directamente, sin la palabra "Total: "
        run2 = p.add_run(f"\n{resultado_str}")
        run2.font.size = Pt(12)
        run2.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 3. DICCIONARIO DE PRODUCTOS
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

# 4. INTERFAZ
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada & Auditoría", "📋 Reportes y Bóveda"])

# --- TAB 1: REGISTRO Y AUDITORÍA UNIFICADA ---
with tab_calc:
    with st.expander("🎤 **Ingreso por Voz** (Click para desplegar)", expanded=False):
        audio_bytes = st.audio_input("Di algo como: 0.620 de capacillo chino en contenedor.", key="audio_reg")
        
        texto_reconocido = ""
        texto_filtro = ""
        
        if audio_bytes:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                audio_data = recognizer.record(source)
                try:
                    texto_reconocido = recognizer.recognize_google(audio_data, language="es-MX")
                    st.success(f"**Escuchado:** {texto_reconocido}")
                    
                    js_tts = f"""
                    <script>
                        const utterance = new SpeechSynthesisUtterance("{texto_reconocido}");
                        utterance.lang = 'es-MX';
                        utterance.rate = 1.0;
                        window.speechSynthesis.speak(utterance);
                    </script>
                    """
                    components.html(js_tts, height=0)
                    
                except sr.UnknownValueError:
                    st.error("No se pudo entender el audio.")
                except sr.RequestError:
                    st.error("Error en el servicio de reconocimiento de voz.")
            
            texto_filtro = texto_reconocido.upper() if texto_reconocido else ""
    
    idx_sugerido = None
    peso_sugerido = None
    pue_sugerido = None
    t_cont_sugerido = False
    nombre_limpio_sugerido = ""
    
    opciones = sorted(productos.keys())
    
    if texto_filtro:
        if "CONTENEDOR" in texto_filtro: t_cont_sugerido = True
        
        match_pue = re.search(r'(?:PESO UNITARIO|UNITARIO|PUE|ESTÁNDAR|ESTANDAR)[^\d]*(\d+(?:[.,]\d+)?)', texto_filtro)
        if match_pue:
            pue_sugerido = float(match_pue.group(1).replace(',', '.'))
            
        numeros_str = re.findall(r'\d+(?:[.,]\d+)?', texto_filtro)
        numeros_floats = [float(n.replace(',', '.')) for n in numeros_str]
        
        if numeros_floats:
            if pue_sugerido in numeros_floats:
                numeros_floats.remove(pue_sugerido) 
            if numeros_floats:
                peso_sugerido = numeros_floats[0] 
                
        palabras_basura = [r'\d+(?:[.,]\d+)?', 'PESO UNITARIO', 'PUE', 'PESO', 'UNITARIO', 'ESTÁNDAR', 'ESTANDAR', 'KILOS', 'KG', 'GRAMOS', 'CON', 'SIN', 'Y', 'DE', 'EL', 'LA', 'CONTENEDOR', 'BISAGRA', 'LLEVA', 'ASIGNAR']
        texto_limpio = texto_filtro
        for p in palabras_basura:
            texto_limpio = re.sub(r'\b' + p + r'\b', '', texto_limpio)
        nombre_limpio_sugerido = ' '.join(texto_limpio.split()) 
        
        palabras_clave = nombre_limpio_sugerido.split()
        if palabras_clave:
            max_coincidencias = 0
            for i, prod in enumerate(opciones):
                coincidencias = sum(1 for palabra in palabras_clave if palabra in prod.upper())
                if coincidencias > max_coincidencias:
                    max_coincidencias = coincidencias
                    idx_sugerido = i

    modo_seleccionado = st.selectbox(
        "⚙️ Seleccione el Modo de Registro:",
        ["Modo Normal", "Artículo NO listado", "PRE-CONTEO MANUAL (Piezas directas)"],
        index=0
    )
    
    nuevo_art = (modo_seleccionado == "Artículo NO listado")
    modo_preconteo = (modo_seleccionado == "PRE-CONTEO MANUAL (Piezas directas)")
    
    if not nuevo_art:
        art_sel = st.selectbox("Seleccione Artículo (Aplica para registro y desglose):", opciones, index=idx_sugerido, placeholder="Elija un producto...")
        pue_final = productos.get(art_sel, 1.0) if art_sel else 1.0
    else:
        c_n1, c_n2 = st.columns([2,1])
        with c_n1:
            art_sel = st.text_input("Nombre del Nuevo Artículo:", value=nombre_limpio_sugerido if nombre_limpio_sugerido else None, placeholder="Ej. CAJA PERSONALIZADA")
        with c_n2:
            pue_final = st.number_input("Asignar Peso Unitario:", value=pue_sugerido, format="%.4f", placeholder="0.0000")

    with st.form(key="form_pesaje", clear_on_submit=True):
        
        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=peso_sugerido, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total, formula = 0.0, 0.0, "CONTEO MANUAL DIRECTO"
        else:
            peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=peso_sugerido, format="%.3f", placeholder="0.000")
            with st.expander("🛠️ Configuración de Taras", expanded=True):
                c1, c2 = st.columns(2)
                with c1: t_cont = st.checkbox("Contenedor (0.045)", value=t_cont_sugerido)
                with c2: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f", placeholder="0.000")
        
        btn_save = st.form_submit_button("📥 CONFIRMAR Y GUARDAR REGISTRO")

    if btn_save:
        articulo_valido = art_sel is not None and art_sel.strip() != ""
        pue_valido = pue_final is not None
        
        if modo_preconteo:
            datos_listos = articulo_valido and cantidad_directa is not None
            resultado = truncar_dos_decimales(cantidad_directa) if datos_listos else 0
        else:
            datos_listos = articulo_valido and peso_bruto is not None and pue_valido
            if datos_listos:
                tm = t_manual if t_manual is not None else 0.0
                tara_total = (0.045 if t_cont else 0) + tm
                peso_neto = peso_bruto - tara_total
                is_tinta = "TINTA" in str(art_sel).upper()
                offset = 0.030 if is_tinta else 0.0
                resultado_calc = (peso_neto - offset) / pue_final
                resultado = truncar_dos_decimales(resultado_calc) 
                formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"

        if datos_listos:
            zona_mexico = pytz.timezone('America/Mexico_City')
            fecha_mexico = datetime.now(zona_mexico).strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                with conn.session as s:
                    result = s.execute(text("""INSERT INTO pesajes_individuales 
                                 (sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                                 VALUES (:suc, :fh, :art, :pb, :tara, :pue, :rp, :df) RETURNING id"""),
                              {"suc": sucursal_in, "fh": fecha_mexico, "art": art_sel, "pb": peso_bruto if not modo_preconteo else 0, 
                               "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, 
                               "rp": resultado, "df": formula})
                    id_recien_creado = result.fetchone()[0]
                    s.commit()
                    
                # POP-UP CON SUMATORIA Y AUDITORÍA
                mostrar_popup_exito(id_recien_creado, art_sel, resultado, sucursal_in)
            except Exception as e:
                st.error(f"Error al guardar en base de datos: {e}")
        else:
            st.error("❌ Error: Revisa que el Nombre, el Peso Unitario y el Peso de Báscula estén correctos.")

    # -------------------------------------------------------------
    # MOSTRAR SOLO 2 COLUMNAS EN EL HISTORIAL (Operación, Cantidad)
    # -------------------------------------------------------------
    if art_sel:
        st.divider()
        st.markdown(f"📋 **Historial de {art_sel}**")
        
        df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        
        if not df_guardados_art.empty:
            df_guardados_art['detalle_formula'] = "[GUARDADO] " + df_guardados_art['detalle_formula'].astype(str)
            
        df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
        
        if not df_art_combined.empty:
            # Aquí seleccionamos solo las 2 columnas requeridas y las renombramos
            st.dataframe(df_art_combined[['detalle_formula', 'resultado_pue']].rename(columns={
                'detalle_formula': 'Operación',
                'resultado_pue': 'Cantidad'
            }), hide_index=True, use_container_width=True)
        else:
            st.info(f"No hay pesajes registrados para este artículo.")

# --- TAB 2: EXPORTACIÓN Y BÓVEDA ---
with tab_historial:
    df_actual = conn.query("SELECT * FROM pesajes_individuales WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
    df_guardados = conn.query("SELECT * FROM pesajes_guardados WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
    
    df_guardados_rep = df_guardados.copy()
    if not df_guardados_rep.empty:
        df_guardados_rep['detalle_formula'] = "[GUARDADO] " + df_guardados_rep['detalle_formula'].astype(str)
    df_combined = pd.concat([df_actual, df_guardados_rep], ignore_index=True)

    if not df_combined.empty:
        st.subheader("📄 Tarjetas Recortables (Word)")
        if not df_guardados.empty:
            df_impresion = df_guardados[['articulo', 'resultado_pue']].copy()
            word_file = generar_word_tarjetas(df_impresion)
            st.download_button(
                label="📄 Descargar Tarjetas en Word (Pre-conteos)",
                data=word_file,
                file_name=f"Tarjetas_Preconteos_{sucursal_in.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:
            st.info("No hay pre-conteos guardados en la bóveda para generar tarjetas.")
            
        url_abrir_wa = f"https://wa.me/{numero_wa}"
        st.markdown(f'<a href="{url_abrir_wa}" target="_blank" class="btn-wa">💬 ABRIR WHATSAPP (Para enviar archivos)</a>', unsafe_allow_html=True)
        
        st.divider()
        
        with st.expander("🗑️ Administración de Registros Individuales (Sesión Actual)", expanded=False):
            st.markdown("#### Selecciona el renglón de la izquierda y presiona el ícono de papelera 🗑️ para borrar.")
            columnas_bloqueadas = df_actual.columns.tolist() 
            edited_df = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=columnas_bloqueadas, key="editor_db")
            
            if st.button("💾 Guardar Cambios en Tabla", use_container_width=True):
                original_ids = set(df_actual['id'])
                current_ids = set(edited_df['id'])
                ids_to_delete = original_ids - current_ids
                
                if ids_to_delete:
                    with conn.session as s:
                        for del_id in ids_to_delete:
                            s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": int(del_id)})
                        s.commit()
                    st.success(f"Se eliminaron {len(ids_to_delete)} registros correctamente.")
                    st.rerun()
                else:
                    st.info("No detecté ninguna fila eliminada para guardar.")

        with st.expander("🛡️ Trasladar a Bóveda (Preconteos Permanentes)", expanded=False):
            st.markdown("Mueve registros de la sesión actual a la bóveda segura.")
            opciones_proteger = df_actual.apply(lambda x: f"ID {x['id']} | {x['articulo']} | {x['resultado_pue']} u.", axis=1).tolist()
            seleccionados_para_proteger = st.multiselect("Selecciona los registros a mover a la bóveda:", opciones_proteger)
            
            if st.button("📥 Mover seleccionados a la Bóveda"):
                if seleccionados_para_proteger:
                    with conn.session as s:
                        for sel in seleccionados_para_proteger:
                            id_val = int(sel.split(" | ")[0].replace("ID ", ""))
                            s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula)
                                         SELECT sucursal, fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula 
                                         FROM pesajes_individuales WHERE id = :id"""), {"id": id_val})
                            s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_val})
                        s.commit()
                    st.success(f"Se han trasladado {len(seleccionados_para_proteger)} registros a la Bóveda de Supabase.")
                    st.rerun()
                else:
                    st.warning("Selecciona al menos un registro de la lista.")
            
            st.divider()
            st.markdown("#### 🗃️ Pre-conteos Guardados Actualmente")
            if not df_guardados.empty:
                edited_guardados = st.data_editor(df_guardados, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_guardados.columns.tolist(), key="editor_db_guardados")
                if st.button("💾 Eliminar filas borradas de la Bóveda", use_container_width=True):
                    original_ids_g = set(df_guardados['id'])
                    current_ids_g = set(edited_guardados['id'])
                    ids_to_delete_g = original_ids_g - current_ids_g
                    
                    if ids_to_delete_g:
                        with conn.session as s:
                            for del_id in ids_to_delete_g:
                                s.execute(text("DELETE FROM pesajes_guardados WHERE id = :id"), {"id": int(del_id)})
                            s.commit()
                        st.success(f"Se eliminaron {len(ids_to_delete_g)} registros guardados.")
                        st.rerun()
            else:
                st.info("No hay pre-conteos guardados en la bóveda para esta sucursal en este momento.")
    else:
        st.info(f"No hay pesajes registrados para {sucursal_in}.")

# --- AUTO-FOCO CON JAVASCRIPT ---
components.html(
    """
    <script>
    const num_inputs = window.parent.document.querySelectorAll('input[type="number"]');
    num_inputs.forEach(input => {
        input.setAttribute('enterkeyhint', 'done');
    });

    setTimeout(() => {
        const mainContent = window.parent.document.querySelector('.main');
        if (mainContent) {
            const selectores = mainContent.querySelectorAll('input[aria-autocomplete="list"], input[role="combobox"]');
            if(selectores.length > 0){
                selectores[0].focus();
            }
        }
    }, 600); 
    </script>
    """,
    height=0
)
