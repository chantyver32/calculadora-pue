import streamlit as st

# Configuración de página para móviles
st.set_page_config(page_title="PUE Champlitte", page_icon="🧮", layout="centered")

# Estilo CSS para mejorar la visibilidad en celular
st.markdown("""
    <style>
    .main { padding-top: 1rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #FF4B4B; color: white; }
    div[data-testid="stMetricValue"] { font-size: 40px; }
    </style>
    """, unsafe_allow_html=True)

# Diccionario completo de productos y sus divisores (PUE)
productos = {
 
    "BOLSA LOCK PZA": 0.018,
    "BOLSA PAPEL CAFÉ #5 PQ/100": 0.832,
    "BOLSA PAPEL CAFÉ #6 PQ/100": 0.870,
    "BOLSA PAPEL CAFÉ #14 PQ/100": 1.364,
    "BOLSA PAPEL CAFÉ #20 PQ/100": 1.616,   
    "CAJA DE GRAPAS": 0.176,
    "CAPACILLO CHINO PZA": 0.00104,
    "CAPACILLO ROJO #72 PQ": 0.000436,
    "CINTA TRANSP EMPAQUE PZA": 0.272,
    "COFIA PQ/100 PZS": 0.238,
    "CONT BISAG P/ 5-6 TUTIS PZ": 0.014,
    "CUCHARA MED DESCH PZ": 0.00165,
    "EMPLAYE GRANDE ROLLO": 1.174,
    "ETIQUETA BLANCA ADH 13 X 19 PQ": 0.050,
    "HOJAS BLANCAS PAQ/500": 2.146,
    "PAPEL ALUMINIO PZA": 1.342,
    "SERVILLETA PQ/500 HJ": 0.001192,
    "TINTA EPSON 544 (CMYK)": 0.078,
    "TOALLA ROLLO 180M PZA": 1.115,
    "HIGIENICO SCOTT ROLLO": 0.500
}

st.title("🧮 Calculadora PUE")
st.write("Pastelería Champlitte 2026")

# 1. Selección de producto con buscador
opciones = sorted(list(productos.keys()))
opcion = st.selectbox("Selecciona el artículo:", opciones)

# 2. Entrada de datos (Formato 0.000 y sin valor predeterminado para facilitar escritura)
peso_kg = st.number_input(
    "Ingresa el peso total:", 
    min_value=0.0, 
    step=0.001, 
    format="%.3f", 
    value=None,  # Esto hace que el campo aparezca vacío al inicio
    placeholder="0.000" # Muestra esto como guía
)

# 3. Botón de cálculo
if st.button("CALCULAR"):
    divisor = productos[opcion]
    
    # Lógica especial para la Tinta Epson
    if opcion == "TINTA EPSON 544 (CMYK)":
        peso_ajustado = peso_kg - 0.030
        if peso_ajustado < 0:
            st.error("El peso es menor a 0.030 (peso del envase).")
            resultado = 0
        else:
            resultado = peso_ajustado / 0.078
    
    # Lógica normal para los demás productos
    elif divisor > 0:
        resultado = peso_kg / divisor
    else:
        st.error("Error en el divisor.")
        resultado = None

    # Mostrar el resultado si el cálculo fue exitoso
    if resultado is not None:
        st.divider()
        st.metric(label=f"{opcion}", value=f"{resultado:.2f}")
        
        # Pie de página dinámico
        if opcion == "TINTA EPSON 544 (CMYK)":
            st.caption("Fórmula: (Peso - 0.030) / 0.078")
        else:
            st.caption(f"PUE utilizado: {divisor}")

st.markdown("---")
st.caption("v1.0 - Herramienta interna basada en la Tabla Corporativa de Pesos Unitarios.")
