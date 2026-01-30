import streamlit as st

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🧮", layout="centered")

# 2. CSS Avanzado: Elimina flechas, ajusta botones y métricas
st.markdown("""
    <style>
    /* Eliminar flechas en Chrome, Safari, Edge, Opera */
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    /* Eliminar flechas en Firefox */
    input[type=number] {
        -moz-appearance: textfield;
    }
    .main { padding-top: 1rem; }
    /* Estilo botón Calcular (Rojo) */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border: none;
    }
    /* Estilo botón Limpiar (Gris) */
    div[data-testid="column"] .stButton > button {
        background-color: #6c757d;
        height: 3em;
    }
    div[data-testid="stMetricValue"] { font-size: 40px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Diccionario de productos
productos = {

    -----------
    # --- ABARROTES ---
    "AGUA CIEL 20 LT": 1.0,
    "AZÚCAR REFINADA KG": 1.0,
    # --- EMPAQUES Y DESECHABLES ---
    "BOLSA CAMISETA LOGO CH KG": 1.0,
    "BOLSA CAMISETA LOGO GDE KG": 1.0,
    "BOLSA NATURAL 18 X 25 KG": 1.0,
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
    "PAPEL ENVOLTURA CHAMPLITTE KG": 1.0,
    "PAPEL ALUMINIO PZA": 1.342,
    "ROLLO POLIPUNTEADO 25 X 35 KG": 1.0,
    "SERVILLETA PQ/500 HJ": 0.001192,
    # --- LIMPIEZA Y QUÍMICOS ---
    "BOLSA 90 X 120 KG": 1.0,
    "BOLSA 60 X 90 KG": 1.0,
    "CLOROLIMP LT": 1.0,
    "COFIA PQ/100 PZS": 0.238,
    "FIBRA PREGON PZA (P/Baño)": 1.0,
    "FIBRA PZ (Scotch Brite)": 1.0,
    "FIBRA AZUL PZA (P/Lavar charolas)": 1.0,
    "GUANTES TRANSP POLIURETANO PQ/100": 0.086,
    "HIGIENICO SCOTT ROLLO": 0.500,
    "JABON LIQUIDO PARA MANOS LT": 1.0,
    "LAVALOZA LT": 1.0,
    "PRO GEL LT": 1.0,
    "TOALLA ROLLO 180M PZA": 1.115,
    # --- PAPELERÍA ---
    "BOLSA LOCK PZA": 0.018,
    "CAJA DE GRAPAS": 0.176,
    "CINTA TRANSP EMPAQUE PZA": 0.272,
    "CINTA DELIMITADORA PZA": 0.346,
    "COMPROBANTE TRASLADO VALORES": 0.0086,
    "ETIQUETA BLANCA ADH 13 X 19 PQ": 0.050,
    "HOJAS BLANCAS PAQ/500": 2.146,
    "ROLLO TERMICO P/ TPV": 1.0,
    "TINTA EPSON 544 (CMYK)": 0.078,
    # --- JARCERÍA ---
    "CUBETA PZA": 1.0,
    "ESCOBA PZA": 1.0,
    "ESCURRIDOR PZA": 1.0,
    "RECOGEDOR PZA": 1.0,
    "MECHUDO PZA": 1.0
}

# Función para resetear la app
def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["producto_sel"] = sorted(list(productos.keys()))[0]

# Títulos
st.title("🧮 Calculadora PUE")
st.write("Pastelería Champlitte 2026")

# 1. Selección de producto
opciones = sorted(list(productos.keys()))
opcion = st.selectbox("Selecciona el artículo:", opciones, key="producto_sel")

# 2. Entrada de peso
peso_kg = st.number_input(
    "Ingresa el peso total:", 
    min_value=0.0, 
    format="%.3f", 
    value=None, 
    placeholder="0.000",
    key="peso_input"
)

# 3. Botones (Calculo y Limpieza)
col1, col2 = st.columns([3, 1])

with col1:
    calcular = st.button("CALCULAR")
with col2:
    st.button("LIMPIAR", on_click=limpiar_pantalla)

# 4. Lógica de cálculo
if calcular:
    if peso_kg is not None:
        divisor = productos[opcion]
        
        if opcion == "TINTA EPSON 544 (CMYK)":
            peso_ajustado = peso_kg - 0.030
            if peso_ajustado < 0:
                st.error("Peso menor al envase (0.030).")
                resultado = None
            else:
                resultado = peso_ajustado / 0.078
        elif divisor > 0:
            resultado = peso_kg / divisor
        else:
            st.error("Error en el divisor.")
            resultado = None

        if resultado is not None:
            st.divider()
            st.metric(label=f"Cantidad para {opcion}", value=f"{resultado:.2f}")
            
            if opcion == "TINTA EPSON 544 (CMYK)":
                st.caption("Fórmula: (Peso - 0.030) / 0.078")
            else:
                st.caption(f"PUE utilizado: {divisor}")
    else:
        st.warning("Por favor, ingresa un peso.")

st.markdown("---")
st.caption("v1.1 - Herramienta Interna Champlitte")
