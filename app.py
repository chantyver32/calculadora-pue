import streamlit as st
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# --- CSS PERSONALIZADO (FONDO CREMA Y BOTONES) ---
st.markdown(
    """
    <style>
    /* Fondo color crema para toda la app */
    .stApp {
        background-color: #FFFDD0;
    }
    
    /* Ocultar elementos de Streamlit Cloud */
    div[data-testid="stStatusWidget"], header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    /* Eliminar flechas de inputs numéricos */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type=number] { -moz-appearance: textfield; }

    /* Estilo botones */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
    }
    div[data-testid="column"] .stButton > button {
        background-color: #6c757d;
        height: 3em;
    }
    
    .block-container { padding-top: 2rem !important; }
    div[data-testid="stMetricValue"] { font-size: 40px; color: #5D4037; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- DICCIONARIO DE PRODUCTOS ---
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

# --- FUNCIONES ---
def limpiar_pantalla():
    st.session_state["peso_input"] = 0.0
    st.session_state["producto_sel"] = ""
    st.session_state["aplicar_tara"] = False
    st.session_state["valor_tara"] = 0.0

# --- INTERFAZ ---
# Mostrar Logo
try:
    img = Image.open("champlitte.jpeg")
    st.image(img, width=250)
except:
    st.title("Champlitte")

st.subheader("Calculadora PUE")

# 1. Selección de producto
opciones = sorted(list(productos.keys()))
opcion = st.selectbox("Selecciona el artículo:", opciones, key="producto_sel")

# 2. Entrada de peso y Tara
col_p1, col_p2 = st.columns(2)

with col_p1:
    peso_kg = st.number_input(
        "Peso Total:", 
        min_value=0.0, 
        format="%.3f", 
        key="peso_input"
    )

with col_p2:
    usa_tara = st.checkbox("¿Descontar Tara?", key="aplicar_tara")
    if usa_tara:
        tara = st.number_input("Peso Tara:", min_value=0.0, format="%.3f", key="valor_tara")
    else:
        tara = 0.0

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
    elif peso_kg <= 0:
        st.warning("⚠️ Ingresa un peso válido.")
    else:
        divisor = productos[opcion]
        
        # Cálculo del peso neto
        peso_neto = peso_kg - tara
        
        if peso_neto < 0:
            st.error("Error: La tara es mayor al peso total.")
        else:
            # Caso especial Tinta Epson
            if opcion == "TINTA EPSON 544 (CMYK)":
                # La lógica original restaba 0.030 adicional
                resultado = (peso_neto - 0.030) / 0.078
                formula_txt = f"({peso_neto:.3f} - 0.030) / 0.078"
            else:
                resultado = peso_neto / divisor
                formula_txt = f"{peso_neto:.3f} / {divisor}"

            st.divider()
            st.metric(label=f"Cantidad Estimada", value=f"{resultado:.2f}")
            st.caption(f"Fórmula aplicada: {formula_txt}")

st.markdown("---")
st.caption("v1.1 - Herramienta Interna Champlitte | Fondo Crema & Sistema de Tara")
