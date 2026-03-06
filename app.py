import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v2.8", page_icon="🍰", layout="centered")

# 2. CSS MEJORADO (Eliminación de bordes de enfoque y optimización de inputs)
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    
    h1, h2, h3, p, label, .stMarkdown, span {
        color: #000000 !important;
    }

    header[data-testid="stHeader"] { visibility: hidden; }

    /* CAMPOS DE ENTRADA */
    input {
        color: #FFFFFF !important; 
        background-color: #444444 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: 2px solid #b08d15 !important;
    }
    
    /* BOTONES ESTILO CHAMPLITTE */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #fce895 !important;
        border: 1px solid #b08d15 !important;
    }

    .resumen-caja {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #f0e6bc;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        margin: 20px 0px;
    }
    
    .metric-total { font-size: 26px; font-weight: 900; color: #b08d15; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- LÓGICA DE DATOS ---
DB_FILE = "data_champlitte_v28.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"historial": [], "totales": {}, "iniciales": {}}
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f: json.dump(datos, f, indent=4)

# --- LOGO ---
if os.path.exists("champlitte.jpg"):
    st.image("champlitte.jpg", width=120)
else:
    st.title("🍰 CHAMPLITTE")

productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870,
    "BOLSA PAPEL CAFE #14": 1.364, "BOLSA PAPEL CAFE #20": 1.616,
    "CAJA TUTIS": 0.048, "CAPACILLO CHINO": 0.00104,
    "CAPACILLO ROJO #72": 0.000436, "CONT BISAGRA": 0.014,
    "CUCHARA DESECHABLE": 0.00165, "ETIQUETA 4X4": 0.000328,
    "ETIQUETA 6X6": 0.00057, "EMPLAYE GRANDE": 1.174,
    "PAPEL ALUMINIO": 1.342, "SERVILLETA PQ/500": 0.001192,
    "COFIA": 0.238, "GUANTES POLIURETANO": 0.086,
    "HIGIENICO SCOTT": 0.500, "TOALLA ROLLO 180M": 1.115,
    "BOLSA LOCK": 0.018, "CAJA DE GRAPAS": 0.176,
    "CINTA EMPAQUE": 0.272, "CINTA DELIMITADORA": 0.346,
    "TRASLADO VALORES": 0.0086, "ETIQUETA 13X19": 0.050,
    "HOJAS BLANCAS PQ/500": 2.146, "TINTA EPSON 544": 0.078
}

# --- INTERFAZ PRINCIPAL ---
datos = cargar_db()
hoy = datetime.now().strftime('%Y-%m-%d')

# Botón Limpiar Selección (ubicado arriba para flujo rápido)
if st.button("🔄 LIMPIAR / BUSCAR OTRO"):
    st.session_state.p_sel = ""
    st.rerun()

opcion = st.selectbox("SELECCIONA ARTÍCULO:", sorted(list(productos.keys())), key="p_sel")

if opcion != "":
    # Lógica de inventario inicial
    if hoy not in datos["iniciales"]: datos["iniciales"][hoy] = {}
    if opcion not in datos["iniciales"][hoy]:
        ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        ini_ayer = datos.get("iniciales", {}).get(ayer, {}).get(opcion, 0.0)
        tot_ayer = datos.get("totales", {}).get(ayer, {}).get(opcion, 0.0)
        datos["iniciales"][hoy][opcion] = max(0.0, ini_ayer - tot_ayer)
        guardar_db(datos)

    val_ini = datos["iniciales"][hoy][opcion]
    
    with st.expander("📝 Ajustar Inventario Inicial"):
        nuevo_ini = st.number_input("Cantidad actual:", value=float(val_ini))
        if st.button("GUARDAR INICIAL"):
            datos["iniciales"][hoy][opcion] = nuevo_ini
            guardar_db(datos)
            st.rerun()

    st.write(f"### ⚖️ Registro: {opcion}")
    pue = productos[opcion]
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        # value=0.0 hace que sea más fácil borrar o sobreescribir
        peso_total = st.number_input("Peso Báscula:", value=0.0, format="%.3f")
    with col_p2:
        t_cont = st.checkbox("Contenedor")
        t_bisag = st.checkbox("Bisagra")

    if st.button("REGISTRAR PESADA"):
        if peso_total > 0:
            tara_calc = (0.045 if t_cont else 0) + (0.016 if t_bisag else 0)
            p_neto = peso_total - (0.030 if "TINTA" in opcion else tara_calc)
            
            if p_neto > 0:
                cant_res = p_neto / pue
                datos["historial"].append({
                    "fecha": hoy, "art": opcion, "cant": round(cant_res, 2)
                })
                if hoy not in datos["totales"]: datos["totales"][hoy] = {}
                datos["totales"][hoy][opcion] = datos["totales"][hoy].get(opcion, 0.0) + cant_res
                guardar_db(datos)
                st.success(f"Añadido: {cant_res:.2f}")
                st.rerun()

# --- TABLA DE OPERACIONES REALIZADAS ---
st.divider()
st.subheader("📊 Operaciones del Día")

df_hist = pd.DataFrame(datos.get("historial", []))
if not df_hist.empty:
    df_hoy = df_hist[df_hist["fecha"] == hoy].copy()
    if not df_hoy.empty:
        # Agrupar por producto para mostrar la tabla resumen solicitada
        resumen_dia = []
        for art in df_hoy["art"].unique():
            p_ini = datos["iniciales"].get(hoy, {}).get(art, 0.0)
            p_hoy = datos["totales"].get(hoy, {}).get(art, 0.0)
            resumen_dia.append({
                "PRODUCTO": art,
                "PESO INICIAL": round(p_ini, 2),
                "CONSUMO HOY": round(p_hoy, 2),
                "DIFERENCIA (SALDO)": round(p_ini - p_hoy, 2)
            })
        
        st.table(pd.DataFrame(resumen_dia))
    else:
        st.info("Sin movimientos hoy.")
else:
    st.info("Historial vacío.")

if st.button("🗑️ REINICIAR TODO EL DÍA"):
    datos["totales"][hoy] = {}
    datos["historial"] = [h for h in datos["historial"] if h["fecha"] != hoy]
    guardar_db(datos)
    st.rerun()

# --- SECCIÓN DE CONSULTA DE INVENTARIO ACTUALIZADO ---
st.divider()
st.subheader("🔍 Resumen de Inventario: Ayer vs Hoy")

# Calculamos fechas
ayer_obj = datetime.now() - timedelta(days=1)
ayer = ayer_obj.strftime('%Y-%m-%d')

# Obtenemos la lista de productos que tienen algún registro hoy o ayer
productos_activos = set(
    list(datos.get("iniciales", {}).get(hoy, {}).keys()) + 
    list(datos.get("totales", {}).get(hoy, {}).keys())
)

if productos_activos:
    tabla_final = []
    for art in productos_activos:
        # 1. Cantidad que tenía (Inventario inicial de hoy)
        cant_inicial_hoy = datos.get("iniciales", {}).get(hoy, {}).get(art, 0.0)
        
        # 2. Lo que pesé hoy (Consumo registrado)
        lo_que_pese = datos.get("totales", {}).get(hoy, {}).get(art, 0.0)
        
        # 3. Lo que tengo ahora (Saldo)
        saldo_ahora = cant_inicial_hoy - lo_que_pese
        
        tabla_final.append({
            "PRODUCTO": art,
            "CANT. INICIAL (TENÍA)": round(cant_inicial_hoy, 2),
            "PESAJE HOY (CONSUMO)": round(lo_que_pese, 2),
            "SALDO (TENGO AHORA)": round(saldo_ahora, 2),
            "FECHA": hoy
        })
    
    # Crear DataFrame
    df_resumen = pd.DataFrame(tabla_final)
    
    # Aplicar un poco de color para que sea fácil de leer
    def resaltar_saldo(val):
        color = 'red' if val < 0 else 'black'
        return f'color: {color}; font-weight: bold'

    # Mostrar la tabla con estilo
    st.dataframe(
        df_resumen.style.map(resaltar_saldo, subset=['SALDO (TENGO AHORA)']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No se han registrado movimientos ni inventarios para el día de hoy.")

st.caption("v2.8 | Champlitte - Control de Insumos")  SOLO QUIERO QUE CONFIRME EN UN RECUADRO VERDE DESPUES DEL REGISTRO DEL PESADO
