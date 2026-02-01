import streamlit as st
from PIL import Image
import os

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# 2. CSS: Fondo Blanco, Botones con efecto rebote y letras negras
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    header[data-testid="stHeader"], footer {
        visibility: hidden !important;
        height: 0;
    }
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
    div.stButton > button:active { transform: scale(0.92); }
    div.stButton > button:hover {
        border: 1px solid #000000 !important;
        background-color: #ffe88a !important;
    }
    div[data-testid="stMetricValue"] { 
        font-size: 45px; 
        color: #000000 !important; 
    }
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
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,
    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,
    "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048,
    "CAPACILLO CHINO POR PZA B": 0.00104,
    "CAPACILLO ROJO #72 POR PZA A": 0.000436,
    "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014,
    "CUCHARA MED DESCH POR PZA A": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328,
    "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
    "EMPLAYE GRANDE ROLLO POR PZA T": 1.174,
    "PAPEL ALUMINIO POR PZA T": 1.342,
    "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
    "COFIA POR PQ/100 PZAS A": 0.238,
    "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
    "HIGIENICO SCOTT ROLLO POR PZA M": 0.500,
    "TOALLA ROLLO 180M POR PZA M": 1.115,
    "BOLSA LOCK POR PZA A": 0.018,
    "CAJA DE GRAPAS POR PZA M": 0.176,
    "CINTA TRANSP EMPAQUE POR PZA M": 0.272,
    "CINTA DELIMITADORA POR PZA B": 0.346,
    "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086,
    "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
    "HOJAS BLANCAS PQ/500 POR PZA A": 2.146,
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,
    # --- PRODUCTOS CON PUE 1.0 ---
    "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0,
    "BOLSA CAMISETA LOGO CH POR KG A": 1.0,
    "BOLSA CAMISETA LOGO GDE POR KG A": 1.0,
    "BOLSA NATURAL 18 X 25 POR KG A": 1.0,
    "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0,
    "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0,
    "BOLSA 90 X 120 POR KG A": 1.0,
    "BOLSA 60 X 90 POR KG M": 1.0,
    "CLOROLIMP POR L A": 1.0,
    "FIBRA PREGON P/BAÑO POR PZA M": 1.0,
    "FIBRA SCOTCH BRITE POR PZA A": 1.0,
    "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0,
    "JABON LIQUIDO PARA MANOS POR L M": 1.0,
    "LAVALOZA POR L A": 1.0,
    "PRO GEL POR L B": 1.0,
    "ROLLO TERMICO P/TPV POR PZA A": 1.0,
    "CUBETA POR PZA M": 1.0,
    "ESCOBA POR PZA A": 1.0,
    "ESCURRIDOR POR PZA M": 1.0,
    "RECOGEDOR POR PZA M": 1.0,
    "MECHUDO POR PZA A": 1.0,
}

def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["tara_input"] = None
    st.session_state["activar_tara"] = False
    st.session_state["producto_sel"] = ""

# --- INTERFAZ ---
st.write("## Calculadora de PUE")

opciones_lista = sorted(list(productos.keys()))
opcion = st.selectbox("Artículo:", opciones_lista, key="producto_sel")

col_a, col_b = st.columns(2)
with col_a:
    peso_total = st.number_input("Peso Total:", min_value=0.0, format="%.3f", step=0.001, value=None, placeholder="0.000", key="peso_input")

with col_b:
    usar_tara = st.checkbox("Descontar Tara", key="activar_tara")
    if usar_tara:
        peso_tara = st.number_input("Peso Tara:", min_value=0.0, format="%.4f", step=0.0001, value=None, placeholder="0.0000", key="tara_input")
    else:
        peso_tara = 0.0

st.write("") 

col1, col2 = st.columns([3, 1])
with col1:
    btn_calcular = st.button("CALCULAR")
with col2:
    st.button("LIMPIAR", on_click=limpiar_pantalla)

# --- LÓGICA DE CÁLCULO UNIFICADA ---
if btn_calcular:
    if opcion == "":
        st.warning(" ⚠️ Selecciona el artículo.")
    elif peso_total is None:
        st.warning(" ⚠️ Ingresa el peso total.")
    else:
        pue = productos[opcion]
        tara_final = peso_tara if peso_tara is not None else 0.0
        peso_neto = peso_total - tara_final
        
        if peso_neto < 0:
            st.error(" 📢 La tara es mayor al peso total.")
        else:
            # Alerta cuadro rojo si PUE es 1.0
            if pue == 1.0:
                st.error(" 📢 El artículo se cuenta por pieza, kilo o litro.")
            
            resultado = None
            
            # Lógica especial Tinta
            if opcion == "TINTA EPSON 544 (CMYK) POR PZA A":
                peso_ajustado = peso_neto - 0.030
                if peso_ajustado < 0:
                    st.error("📢 El peso neto es menor al envase de la tinta (0.030).")
                else:
                    resultado = peso_ajustado / 0.078
            # Lógica para productos normales
            else:
                if pue > 0:
                    resultado = peso_ajustado / pue
                else:
                    st.warning("⚠️ El artículo seleccionado no tiene un divisor válido.")

            # Mostrar resultado final
            if resultado is not None:
                st.divider()
                st.metric(label=f"Cantidad para {opcion}", value=f"{resultado:.2f}")
                
                # Fórmula informativa
                txt_formula = f"({peso_total:.3f} - {tara_final:.4f}) / {pue}" if usar_tara else f"{peso_total:.3f} / {pue}"
                st.caption(f"Fórmula utilizada: {txt_formula}")
                st.caption(f"PUE utilizado: {pue}")

st.markdown("---")
st.caption("v1.0 - Champlitte 2026")
