import streamlit as st
from PIL import Image
import os

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# 2. CSS: Fondo Blanco, Botones Amarillos con Rebote, Línea Negra y Texto
st.markdown(
    """
    <style>
    /* Fondo Blanco Puro */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Forzar texto en negro */
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }

    /* Ocultar elementos de Streamlit */
    header[data-testid="stHeader"], footer {
        visibility: hidden !important;
        height: 0;
    }

    /* Estilo de los Botones (Amarillo #fff2bd) */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
        transition: transform 0.1s ease-in-out;
    }

    /* Efecto Rebote al tocar */
    div.stButton > button:active {
        transform: scale(0.90);
    }
    
    div.stButton > button:hover {
        border: 1px solid #000000 !important;
    }

    /* Métrica en Negro */
    div[data-testid="stMetricValue"] { 
        font-size: 50px; 
        color: #000000 !important;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        text-align: center;
    }

    /* Línea divisoria negra personalizada */
    .black-line {
        border: 0;
        height: 2px;
        background: #000000;
        margin-bottom: 25px;
        margin-top: 10px;
    }

    /* Inputs numéricos sin flechas */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type=number] { -moz-appearance: textfield; }
    
    .block-container { padding-top: 1rem !important; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- INICIALIZACIÓN DE ESTADOS ---
if 'resultado' not in st.session_state:
    st.session_state.resultado = None
if 'detalle' not in st.session_state:
    st.session_state.detalle = ""

# --- LOGO CHAMPLITTE ---
nombre_imagen = "champlitte.jpg"
ruta_imagen = os.path.join(os.path.dirname(__file__), nombre_imagen)

col_logo_center, _ = st.columns([1, 2])
with col_logo_center:
    try:
        img = Image.open(ruta_imagen if os.path.exists(ruta_imagen) else nombre_imagen)
        st.image(img, width=110)
    except:
        st.write("### CHAMPLITTE")

# --- 4. ÁREA DE RESULTADO (ARRIBA) ---
if st.session_state.resultado is not None:
    st.metric(label="CANTIDAD CALCULADA", value=st.session_state.resultado)
    if st.session_state.detalle:
        st.caption(st.session_state.detalle)
else:
    st.write("###") # Espacio cuando no hay resultado

# LÍNEA DIVISORIA NEGRA
st.markdown('<div class="black-line"></div>', unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA ---
def calcular_pue():
    if st.session_state.producto_sel == "":
        st.warning("⚠️ Selecciona un artículo.")
        return
    
    peso_t = st.session_state.peso_input
    if peso_t is None or peso_t <= 0:
        st.warning("⚠️ Ingresa un peso válido.")
        return

    pue = productos[st.session_state.producto_sel]
    tara_f = st.session_state.tara_input if (st.session_state.activar_tara and st.session_state.tara_input is not None) else 0.0
    
    peso_neto = peso_t - tara_f
    
    if peso_neto < 0:
        st.error("La tara es mayor al peso.")
    else:
        # Caso Tinta Epson
        if st.session_state.producto_sel == "TINTA EPSON 544 (CMYK)":
            res = (peso_neto - 0.030) / 0.078
        else:
            res = peso_neto / pue
        
        st.session_state.resultado = f"{res:.2f}"
        txt_tara = f" - {tara_f:.3f}" if st.session_state.activar_tara else ""
        st.session_state.detalle = f"Fórmula: ({peso_t:.3f}{txt_tara}) / {pue}"

def limpiar():
    st.session_state.peso_input = None
    st.session_state.tara_input = None
    st.session_state.activar_tara = False
    st.session_state.producto_sel = ""
    st.session_state.resultado = None
    st.session_state.detalle = ""

# --- 3. DICCIONARIO DE PRODUCTOS ---
productos = {
    "": 0,
    "BOLSA PAPEL CAFÉ #5 PQ/100": 0.832,
    "BOLSA PAPEL CAFÉ #6 PQ/100": 0.870,
    "BOLSA PAPEL CAFÉ #14 PQ/100": 1.364,
    "BOLSA PAPEL CAFÉ #20 PQ/100": 1.616,
    "CAJA TUTIS": 0.048,
    "CAPACILLO CHINO PZA": 0.00104,
    "CAPACILLO ROJO #72 PQ": 0.000436,
    "CONT BISAG P/ 5-6 TUTIS PZ": 0.014,
    "CUCHARA MED DESCH PZ": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4": 0.000328,
    "ETIQUETA CHAMPLITTE MEDIANA 6 X 6": 0.00057,
    "EMPLAYE GRANDE ROLLO": 1.174,
    "PAPEL ALUMINIO PZA": 1.342,
    "SERVILLETA PQ/500 HJ": 0.001192,
    "COFIA PQ/100 PZS": 0.238,
    "GUANTES TRANSP POLIURETANO PQ/100": 0.086,
    "HIGIENICO SCOTT ROLLO": 0.500,
    "TOALLA ROLLO 180M PZA": 1.115,
    "BOLSA LOCK PZA": 0.018,
    "CAJA DE GRAPAS": 0.176,
    "CINTA TRANSP EMPAQUE PZA": 0.272,
    "CINTA DELIMITADORA PZA": 0.346,
    "COMPROBANTE TRASLADO VALORES": 0.0086,
    "ETIQUETA BLANCA ADH 13 X 19 PQ": 0.050,
    "HOJAS BLANCAS PAQ/500": 2.146,
    "TINTA EPSON 544 (CMYK)": 0.078,
}

# --- CAPTURA DE DATOS ---
opcion = st.selectbox("Selecciona artículo:", sorted(list(productos.keys())), key="producto_sel")

col_p1, col_p2 = st.columns(2)
with col_p1:
    st.number_input("Peso Total:", min_value=0.0, format="%.3f", value=None, placeholder="0.000", key="peso_input")

with col_p2:
    st.checkbox("Descontar Tara", key="activar_tara")
    if st.session_state.activar_tara:
        st.number_input("Peso Tara:", min_value=0.0, format="%.3f", value=None, placeholder="0.000", key="tara_input")

st.write("###")

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    st.button("CALCULAR", on_click=calcular_pue)
with col_btn2:
    st.button("LIMPIAR", on_click=limpiar)

st.markdown("---")
st.caption("v1.8 - Champlitte Internal Tool")
