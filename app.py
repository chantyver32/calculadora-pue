import streamlit as st
from PIL import Image
import os

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# 2. CSS Avanzado: Fondo crema tenue, texto oscuro y ajustes de UI
st.markdown(
    """
    <style>
    /* Fondo crema muy tenue para legibilidad */
    .stApp {
        background-color: #FFFDF5;
    }
    
    /* Color de texto global para que se vea bien */
    .stApp, p, label, .stMarkdown {
        color: #2D1B08 !important;
    }

    /* Ocultar barra de herramientas de Streamlit Cloud */
    div[data-testid="stStatusWidget"], header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    /* Eliminar flechas en inputs numéricos */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type=number] { -moz-appearance: textfield; }

    /* Estilo botón Calcular (Rojo Champlitte) */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #B22222;
        color: white;
        font-weight: bold;
        border: none;
    }
    
    /* Estilo botón Limpiar (Gris) */
    div[data-testid="column"] .stButton > button {
        background-color: #6c757d;
        color: white;
    }

    /* Ajuste de métricas */
    div[data-testid="stMetricValue"] { 
        font-size: 45px; 
        color: #B22222 !important; 
    }
    
    .block-container { padding-top: 2rem !important; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- CARGAR LOGO ---
# Se intenta cargar la imagen que adjuntaste
try:
    if os.path.exists("champlitte.jpeg"):
        st.image("champlitte.jpeg", width=280)
    else:
        st.title("PASTELERÍA CHAMPLITTE")
except Exception:
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
    st.session_state["peso_input"] = 0.0
    st.session_state["producto_sel"] = ""
    st.session_state["tara_input"] = 0.0
    st.session_state["activar_tara"] = False

# --- INTERFAZ DE USUARIO ---
st.subheader("🧮 Calculadora de Unidades (PUE)")

# 1. Selección de producto
opciones = sorted(list(productos.keys()))
opcion = st.selectbox("Selecciona el artículo:", opciones, key="producto_sel")

# 2. Área de Peso y Tara
col_a, col_b = st.columns(2)

with col_a:
    peso_total = st.number_input(
        "Ingresa el peso total:", 
        min_value=0.0, 
        format="%.3f", 
        key="peso_input"
    )

with col_b:
    usar_tara = st.checkbox("Descontar Tara", key="activar_tara")
    if usar_tara:
        peso_tara = st.number_input("Peso Tara (editable):", min_value=0.0, format="%.3f", key="tara_input")
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
        st.warning("⚠️ Por favor, selecciona el artículo.")
    elif peso_total <= 0:
        st.warning("⚠️ Por favor, ingresa un peso mayor a cero.")
    else:
        pue = productos[opcion]
        
        # Aplicación de la fórmula: (Peso Total - Tara) / PUE
        peso_calculado = peso_total - peso_tara
        
        if peso_calculado < 0:
            st.error("Error: El peso tara no puede ser mayor al peso total.")
        else:
            # Caso especial Tinta Epson heredado del código anterior
            if opcion == "TINTA EPSON 544 (CMYK)":
                resultado = (peso_calculado - 0.030) / 0.078
            else:
                resultado = peso_calculado / pue

            st.divider()
            st.metric(label=f"Resultado para {opcion}", value=f"{resultado:.2f}")
            
            # Nota informativa
            if usar_tara:
                st.caption(f"Cálculo: ({peso_total:.3f} - {peso_tara:.3f}) / {pue}")
            else:
                st.caption(f"Cálculo: {peso_total:.3f} / {pue}")

st.markdown("---")
st.caption("v1.2 - Herramienta Interna Champlitte")
