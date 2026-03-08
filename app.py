import streamlit as st
from PIL import Image
import os
from datetime import datetime

# ------------------ CONFIGURACIÓN DE PÁGINA ------------------
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# ------------------ CSS ------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: #000000 !important; }
    header[data-testid="stHeader"], footer { visibility: hidden !important; height: 0; }
    div.stButton > button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #fff2bd !important; color: #000000 !important; font-weight: bold; border: 1px solid #e0d5a6 !important; transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);}
    div.stButton > button:active { transform: scale(0.92); }
    div.stButton > button:hover { border: 1px solid #000000 !important; background-color: #ffe88a !important; }
    div[data-testid="stMetricValue"] { font-size: 45px; color: #000000 !important; }
    .block-container { padding-top: 1.5rem !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------ LOGO ------------------
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

# ------------------ PRODUCTOS ------------------
productos = {
    "": 0,
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,
    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,
    "CAJA TUTIS POR PZA A": 0.048,
    "CAPACILLO CHINO POR PZA B": 0.00104,
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,
    "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0,
    # ... (agregar todos los productos de tu lista)
}

# ------------------ FUNCIONES ------------------
def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["tara_input"] = None
    st.session_state["activar_tara"] = False
    st.session_state["tara_contenedor"] = False
    st.session_state["tara_bisagra"] = False
    st.session_state["producto_sel"] = ""
    st.session_state["pue_libre_val"] = 0.0
    st.session_state["resultado_calc"] = None
    st.session_state["hora_calc"] = None

# ------------------ INTERFAZ ------------------
st.write("## Calculadora de PUE")

# Checkbox para alternar modo libre
modo_libre = st.checkbox("📝 Modo Libre (Artículo no registrado)")

if not modo_libre:
    opciones_lista = sorted(list(productos.keys()))
    opcion = st.selectbox("Artículo:", opciones_lista, key="producto_sel")
    pue_final = productos.get(opcion, 0)
    es_tinta = (opcion == "TINTA EPSON 544 (CMYK) POR PZA A")
else:
    pue_final = st.number_input(
        "PUE Libre (Divisor):",
        min_value=0.0, format="%.6f", step=0.001,
        key="pue_libre_val",
        help="Ingresa el factor de división manualmente"
    )
    opcion = "Manual"
    es_tinta = False

# ------------------ INPUT PESO ------------------
col_a, col_b = st.columns(2)
with col_a:
    peso_total = st.number_input(
        "Peso Total:",
        min_value=0.0, format="%.3f", step=0.001,
        value=None, placeholder="0.000", key="peso_input"
    )
with col_b:
    if not es_tinta:
        st.write("**Opciones de Tara:**")
        t_cont = st.checkbox("Contenedor (.045)", key="tara_contenedor")
        t_bisag = st.checkbox("Bisagra (0.16)", key="tara_bisagra")
        usar_tara_manual = st.checkbox("Tara Manual", key="activar_tara")
        peso_tara_manual = 0.0
        if usar_tara_manual:
            peso_tara_manual = st.number_input(
                "Peso Tara:",
                min_value=0.0, format="%.4f", step=0.0001,
                value=None, placeholder="0.0000", key="tara_input"
            )
    else:
        peso_tara_manual = 0.0
        t_cont = False
        t_bisag = False

st.write("")
col1, col2 = st.columns([3,1])
with col1: btn_calcular = st.button("CALCULAR")
with col2: st.button("LIMPIAR", on_click=limpiar_pantalla)

# ------------------ LÓGICA DE CÁLCULO ------------------
if btn_calcular:
    if not modo_libre and opcion == "":
        st.warning(" ⚠️ Selecciona un artículo de la lista.")
    elif modo_libre and pue_final <= 0:
        st.warning(" ⚠️ Ingresa un valor de PUE Libre mayor a cero.")
    elif peso_total is None:
        st.warning(" ⚠️ Ingresa el peso total.")
    else:
        tara_fija = 0.0
        if not es_tinta:
            if t_cont: tara_fija += 0.045
            if t_bisag: tara_fija += 0.16
        tara_manual_val = peso_tara_manual if (not es_tinta and peso_tara_manual is not None) else 0.0
        tara_total_final = tara_fija + tara_manual_val
        peso_neto = peso_total - tara_total_final
        resultado = None

        if peso_neto < 0:
            st.error(" 📢 La tara es mayor al peso total.")
        else:
            if es_tinta:
                peso_ajustado = peso_total - 0.030
                if peso_ajustado < 0:
                    st.error("📢 Peso insuficiente para descontar envase de tinta.")
                else:
                    resultado = peso_ajustado / 0.078
                    txt_formula = f"({peso_total:.3f} - 0.030) / 0.078"
            else:
                if pue_final > 0:
                    resultado = peso_neto / pue_final
                    txt_formula = f"({peso_total:.3f} - {tara_total_final:.4f}) / {pue_final}"
                else:
                    st.error("⚠️ El PUE debe ser mayor a 0.")

        if resultado is not None:
            hora_calc = datetime.now().strftime("%H:%M:%S")
            st.session_state["resultado_calc"] = resultado
            st.session_state["hora_calc"] = hora_calc

            st.divider()
            st.metric(label=f"Cantidad Resultante (Hora {hora_calc})", value=f"{resultado:.2f}")
            st.caption(f"Fórmula: {txt_formula}")
            if tara_total_final > 0:
                st.caption(f"Descuento total de tara: {tara_total_final:.4f}")

st.markdown("---")
st.caption("v1.5 - Champlitte 2026 - Calculadora mejorada")
