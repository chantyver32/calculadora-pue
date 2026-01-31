import streamlit as st
from PIL import Image
import os

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# 2. CSS Avanzado: Fondo, Colores y Estética
st.markdown(
    """
    <style>
    /* Fondo crema extremadamente tenue */
    .stApp {
        background-color: #FFFEFA;
    }
    
    /* Forzar color de texto negro para legibilidad */
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
        font-weight: 500;
    }

    /* Ocultar elementos de Streamlit Cloud */
    header[data-testid="stHeader"], footer {
        visibility: hidden;
        height: 0;
    }

    /* Eliminar flechas en inputs numéricos */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type=number] { -moz-appearance: textfield; }

    /* Estilo botón Calcular */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #B22222;
        color: white !important;
        font-weight: bold;
        border: none;
    }
    
    /* Estilo botón Limpiar */
    div[data-testid="column"] .stButton > button {
        background-color: #6c757d;
        color: white !important;
    }

    /* Ajuste de métricas */
    div[data-testid="stMetricValue"] { 
        font-size: 45px; 
        color: #B22222 !important; 
    }
    
    .block-container { padding-top: 1rem !important; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- LOGO CHAMPLITTE ---
try:
    if os.path.exists("champlitte.jpeg"):
        st.image("champlitte.jpeg", width=250)
    else:
        st.title("PASTELERÍA CHAMPLITTE")
except:
    st.title("PASTELERÍA CHAMPLITTE")

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

# Función para resetear
def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["tara_input"] = None
    st.session_state["activar_tara"] = False
    st.session_state["producto_sel"] = ""

# --- INTERFAZ ---
st.subheader("Calculadora de Unidades")

# 1. Selección de producto
opcion = st.selectbox("Selecciona el artículo:", sorted(list(productos.keys())), key="producto_sel")

# 2. Entrada de Pesos
col_a, col_b = st.columns(2)

with col_a:
    peso_total = st.number_input(
        "Peso Total:", 
        min_value=0.0, 
        format="%.3f", 
        value=None, 
        placeholder="0.000",
        key="peso_input"
    )

with col_b:
    usar_tara = st.checkbox("Descontar Tara", key="activar_tara")
    if usar_tara:
        peso_tara = st.number_input(
            "Peso Tara:", 
            min_value=0.0, 
            format="%.3f", 
            value=None, 
            placeholder="0.000",
            key="tara_input"
        )
    else:
        peso_tara = 0.0

# 3. Botones
col1, col2 = st.columns([3, 1])
with col1:
    calcular = st.button("CALCULAR")
with col2:
    st.button("LIMPIAR", on_click=limpiar_pantalla)

# 4. Lógica de cálculo
if calcular:
    if opcion == "":
        st.warning("⚠️ Selecciona un artículo.")
    elif peso_total is None:
        st.warning("⚠️ Ingresa el peso total.")
    else:
        pue = productos[opcion]
        # Si la tara es None (vacia), se trata como 0
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
            
            # Detalle del cálculo
            txt_tara = f" - {tara_final:.3f}" if usar_tara else ""
            st.caption(f"Fórmula: ({peso_total:.3f}{txt_tara}) / {pue}")

st.markdown("---")
st.caption("v1.3 - Champlitte Internal Tool")
