import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# ---------------------- CONFIGURACIÓN ----------------------
st.set_page_config(page_title="PUE Champlitte v3.1", page_icon="🍰", layout="centered")

# ---------------------- CSS PERSONALIZADO ----------------------
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3, p, label, .stMarkdown, span { color:#000000 !important; }
    header[data-testid="stHeader"] { visibility:hidden; }
    
    /* Estilo de Inputs */
    input, textarea {
        color:#000000 !important;
        background-color:#f0f2f6 !important;
        border-radius:10px !important;
        border:1px solid #b08d15 !important;
    }
    
    /* Botones */
    div.stButton > button {
        width:100%; border-radius:10px; height:3.5em; 
        background-color:#fff2bd !important; color:#000000 !important; 
        font-weight:bold; border:1px solid #e0d5a6 !important;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color:#ffe585 !important;
        border:1px solid #b08d15 !important;
    }
    
    .confirmacion {
        background:#e8ffe8; border:2px solid #38a169; border-radius:12px; 
        padding:15px; margin-top:10px; font-size:16px; color:#206b2d;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------- LÓGICA DE DATOS ----------------------
DB_FILE = "data_champlitte_v31.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f:
        json.dump(datos, f, indent=4)

datos = cargar_db()
hoy = datetime.now().strftime('%Y-%m-%d')

# ---------------------- PRODUCTOS Y PUE ----------------------
productos = {
    "": 0,
    "BOLSA PAPEL CAFE #5": 0.832,
    "BOLSA PAPEL CAFE #6": 0.870,
    "BOLSA PAPEL CAFE #14": 1.364,
    "BOLSA PAPEL CAFE #20": 1.616,
    "CAJA TUTIS": 0.048,
    "CAPACILLO CHINO": 0.00104,
    "CAPACILLO ROJO #72": 0.000436,
    "CONT BISAGRA": 0.014,
    "CUCHARA DESECHABLE": 0.00165,
    "ETIQUETA 4X4": 0.000328,
    "ETIQUETA 6X6": 0.00057,
    "EMPLAYE GRANDE": 1.174,
    "PAPEL ALUMINIO": 1.342,
    "SERVILLETA PQ/500": 0.001192,
    "COFIA": 0.238,
    "GUANTES POLIURETANO": 0.086,
    "HIGIENICO SCOTT": 0.500,
    "TOALLA ROLLO 180M": 1.115,
    "BOLSA LOCK": 0.018,
    "CAJA DE GRAPAS": 0.176,
    "CINTA EMPAQUE": 0.272,
    "CINTA DELIMITADORA": 0.346,
    "TRASLADO VALORES": 0.0086,
    "ETIQUETA 13X19": 0.050,
    "HOJAS BLANCAS PQ/500": 2.146,
    "TINTA EPSON 544": 0.078
}

# ---------------------- INTERFAZ PRINCIPAL ----------------------
if os.path.exists("champlitte.jpg"):
    st.image("champlitte.jpg", width=150)
else:
    st.title("🍰 CHAMPLITTE")

# Inicializar sesión para limpieza de campos
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

def limpiar_campos():
    st.session_state.reset_key += 1
    st.rerun()

if st.button("🔄 LIMPIAR FORMULARIO"):
    limpiar_campos()

# Selector de Artículo
opcion = st.selectbox(
    "SELECCIONA ARTÍCULO", 
    sorted(productos.keys()), 
    key=f"p_sel_{st.session_state.reset_key}"
)
articulo_actual = opcion if opcion != "" else "MODO LIBRE"

# Gestión de Inventario Inicial Automático
if hoy not in datos["iniciales"]:
    datos["iniciales"][hoy] = {}

if articulo_actual not in datos["iniciales"][hoy]:
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    # Arrastrar saldo de ayer si existe
    ini_ayer = datos.get("iniciales", {}).get(ayer, {}).get(articulo_actual, 0)
    tot_ayer = datos.get("totales", {}).get(ayer, {}).get(articulo_actual, 0)
    datos["iniciales"][hoy][articulo_actual] = max(0.0, float(ini_ayer) - float(tot_ayer))
    guardar_db(datos)

# Ajuste Manual de Inventario
with st.expander("📝 Ajustar Inventario Inicial (Opcional)"):
    st.write(f"Inventario actual registrado: **{datos['iniciales'][hoy][articulo_actual]:.2f}**")
    nuevo_ini = st.number_input("Corregir cantidad inicial:", min_value=0.0, step=1.0)
    if st.button("ACTUALIZAR INICIAL"):
        datos["iniciales"][hoy][articulo_actual] = nuevo_ini
        guardar_db(datos)
        st.success("Inventario inicial actualizado.")
        st.rerun()

st.divider()

# ---------------------- REGISTRO DE PESADA ----------------------
st.subheader(f"⚖️ Registro: {articulo_actual}")
pue = productos.get(opcion, 0.0)

col1, col2 = st.columns(2)
with col1:
    peso_total = st.number_input("Peso en Báscula (kg)", min_value=0.0, format="%.3f", key=f"peso_{st.session_state.reset_key}")
with col2:
    tipo_tara = st.radio("Tipo de tara", ["Sin tara", "Bisagra (45g)", "Contenedor (19g)", "Personalizada"])
    tara_real = 0.0
    if tipo_tara == "Bisagra (45g)": tara_real = 0.045
    elif tipo_tara == "Contenedor (19g)": tara_real = 0.019
    elif tipo_tara == "Personalizada":
        tara_real = st.number_input("Peso tara (kg)", min_value=0.0, format="%.3f")

if opcion == "":
    pue = st.number_input("Introduce PUE manual", min_value=0.0001, format="%.6f")

if st.button("💾 REGISTRAR MOVIMIENTO"):
    if peso_total > 0 and pue > 0:
        # Lógica especial para tintas
        if "TINTA" in opcion: tara_real = 0.030
        
        p_neto = peso_total - tara_real
        if p_neto > 0:
            cant_res = p_neto / pue
            
            # Guardar en historial
            nuevo_registro = {
                "fecha": hoy,
                "hora": datetime.now().strftime("%H:%M"),
                "art": articulo_actual,
                "cant": round(cant_res, 3),
                "op": f"({peso_total:.3f} - {tara_real:.3f}) / {pue}"
            }
            datos["historial"].append(nuevo_registro)
            
            # Actualizar totales del día
            if hoy not in datos["totales"]:
                datos["totales"][hoy] = {}
            datos["totales"][hoy][articulo_actual] = datos["totales"][hoy].get(articulo_actual, 0) + cant_res
            
            guardar_db(datos)
            st.markdown(f"""
                <div class="confirmacion">
                    <b>✅ REGISTRO EXITOSO</b><br>
                    Cantidad calculada: {cant_res:.2f} unidades.
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error("El peso neto no puede ser menor o igual a la tara.")
    else:
        st.warning("Asegúrate de que el peso y el PUE sean mayores a 0.")

# ---------------------- VISUALIZACIÓN DE DATOS ----------------------
tab1, tab2 = st.tabs(["📋 Movimientos de Hoy", "📊 Inventario Actual"])

with tab1:
    df_hist = pd.DataFrame(datos.get("historial", []))
    if not df_hist.empty:
        df_hoy = df_hist[df_hist["fecha"] == hoy].copy()
        if not df_hoy.empty:
            df_hoy = df_hoy[["hora", "art", "cant", "op"]]
            df_hoy.columns = ["Hora", "Artículo", "Cantidad", "Cálculo"]
            st.dataframe(df_hoy, use_container_width=True, hide_index=True)
        else:
            st.info("No hay pesajes registrados hoy.")
    else:
        st.info("El historial está vacío.")

with tab2:
    prod_hoy = set(list(datos["iniciales"].get(hoy, {}).keys()) + list(datos["totales"].get(hoy, {}).keys()))
    resumen = []
    for art in prod_hoy:
        if art == "MODO LIBRE": continue
        ini = datos["iniciales"].get(hoy, {}).get(art, 0)
        consumo = datos["totales"].get(hoy, {}).get(art, 0)
        resumen.append({
            "PRODUCTO": art,
            "INICIAL": round(ini, 2),
            "CONSUMIDO": round(consumo, 2),
            "STOCK FINAL": round(ini - consumo, 2)
        })
    
    if resumen:
        st.table(pd.DataFrame(resumen))
    else:
        st.info("Sin datos de inventario para mostrar.")

# ---------------------- ADMIN ----------------------
with st.expander("⚙️ Peligro: Zona de Administración"):
    confirmar = st.checkbox("Entiendo que esto borrará todos los datos permanentemente.")
    if st.button("🗑 BORRAR TODA LA BASE DE DATOS"):
        if confirmar:
            datos = {"historial": [], "totales": {}, "iniciales": {}}
            guardar_db(datos)
            st.success("Base de datos reiniciada.")
            st.rerun()

st.divider()
st.caption(f"Champlitte v3.1 | {datetime.now().year}")
