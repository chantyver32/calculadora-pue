import streamlit as st
from PIL import Image
import os

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# 2. CSS: Fondo Blanco, Botones con efecto rebote y letras negras
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

    /* Estilo de los Botones */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
        transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    /* Efecto Rebote al hacer clic (Active) */
    div.stButton > button:active {
        transform: scale(0.92);
    }
    
    /* Efecto al pasar el mouse */
    div.stButton > button:hover {
        border: 1px solid #000000 !important;
        background-color: #ffe88a !important;
    }

    /* Métrica en Negro */
    div[data-testid="stMetricValue"] { 
        font-size: 45px; 
        color: #000000 !important; 
    }

    /* Eliminar flechas de inputs */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type=number] { -moz-appearance: textfield; }
    
    .block-container { padding-top: 1.5rem !important; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- LOGO CHAMPLITTE ---
nombre_imagen = "champlitte.jpg"
ruta_actual = os.path.dirname(__file__)
ruta_imagen = os.path.join(ruta_actual, nombre_imagen)

try:
    if os.path.exists(ruta_imagen):
        img = Image.open(ruta_imagen)
    else:
        img = Image.open(nombre_imagen)
    st.image(img, width=120)
except:
    st.write("### PASTELERÍA CHAMPLITTE")

# 3. Diccionario de productos
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

def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["tara_input"] = None
    st.session_state["activar_tara"] = False
    st.session_state["producto_sel"] = ""

# --- INTERFAZ ---
st.write("## Calculadora de PUE")

opcion = st.selectbox("Artículo:", sorted(list(productos.keys())), key="producto_sel")

col_a, col_b = st.columns(2)
with col_a:
    # Agregado step=0.0001 para permitir alta precisión decimal
    peso_total = st.number_input("Peso Total:", min_value=0.0, format="%.4f", step=0.0001, value=None, placeholder="0.0000", key="peso_input")

with col_b:
    usar_tara = st.checkbox("Descontar Tara", key="activar_tara")
    if usar_tara:
        # Agregado step=0.0001 para permitir alta precisión decimal en la tara
        peso_tara = st.number_input("Peso Tara:", min_value=0.0, format="%.4f", step=0.0001, value=None, placeholder="0.0000", key="tara_input")
    else:
        peso_tara = 0.0

st.write("") 

col1, col2 = st.columns([3, 1])
with col1:
    calcular = st.button("CALCULAR")
with col2:
    st.button("LIMPIAR", on_click=limpiar_pantalla)

if calcular:
    if opcion == "":
        st.warning("⚠️ Selecciona un artículo.")
    elif peso_total is None:
        st.warning("⚠️ Ingresa el peso total.")
    else:
        pue = productos[opcion]
        tara_final = peso_tara if peso_tara is not None else 0.0
        peso_neto = peso_total - tara_final
        
        if peso_neto < 0:
            st.error("Error: La tara es mayor al peso total.")
        else:
            if opcion == "TINTA EPSON 544 (CMYK)":
                resultado = (peso_neto - 0.030) / 0.078
            else:
                resultado = peso_neto / pue

            st.divider()
            st.metric(label=f"Cantidad para {opcion}", value=f"{resultado:.2f}")
            
            # Mostrar la fórmula con 4 decimales para mayor claridad
            txt_formula = f"({peso_total:.4f} - {tara_final:.4f}) / {pue}" if usar_tara else f"{peso_total:.4f} / {pue}"
            st.caption(f"Fórmula: {txt_formula}")

st.markdown("---")
st.caption("v1.0 - Champlitte")
