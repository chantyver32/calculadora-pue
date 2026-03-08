import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide", page_icon="⚖️")

if "pesajes_detallados" not in st.session_state:
    st.session_state.pesajes_detallados = [] 
if "valores_pesajes" not in st.session_state:
    st.session_state.valores_pesajes = []    
if "articulo_actual" not in st.session_state:
    st.session_state.articulo_actual = ""
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

def finalizar_y_limpiar():
    st.session_state.form_key += 1
    st.session_state.pesajes_detallados = []
    st.session_state.valores_pesajes = []
    st.session_state.articulo_actual = ""

# 2. BASE DE DATOS
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registro_auditoria 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, articulo TEXT, 
              suma_total REAL, valor_restado REAL, diferencia REAL, detalle_operacion TEXT)''')
conn.commit()

# 3. DICCIONARIO DE PRODUCTOS
productos = {
    "": 0, "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO ROJO #72 POR PZA A": 0.000436,
    "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
    "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
    "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
    "HIGIENICO SCOTT ROLLO POR PZA M": 0.500, "TOALLA ROLLO 180M POR PZA M": 1.115, "BOLSA LOCK POR PZA A": 0.018,
    "CAJA DE GRAPAS POR PZA M": 0.176, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
    "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
    "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, "BOLSA CAMISETA LOGO GDE POR KG A": 1.0,
    "BOLSA NATURAL 18 X 25 POR KG A": 1.0, "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0,
    "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0,
    "CLOROLIMP POR L A": 1.0, "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
    "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "JABON LIQUIDO PARA MANOS POR L M": 1.0, "LAVALOZA POR L A": 1.0,
    "PRO GEL POR L B": 1.0, "ROLLO TERMICO P/TPV POR PZA A": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0,
    "ESCURRIDOR POR PZA M": 1.0, "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0,
}

# 4. INTERFAZ DE TABS
tab_calc, tab_db = st.tabs(["📊 Calculadora de Auditoría", "📂 Historial y Reportes WA"])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    st.title("⚖️ PUE Champlitte: Registro de Pesajes")
    
    with st.form(key=f"f_{st.session_state.form_key}", clear_on_submit=True):
        col_art, col_peso = st.columns([2, 1])
        with col_art:
            art_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()))
        with col_peso:
            peso_t = st.number_input("Peso Bruto (kg):", value=None, format="%.3f", placeholder="0.000")
        
        st.markdown("**Descuento de Tara (kg)**")
        c1, c2, c3 = st.columns(3)
        with c1: t_cont = st.checkbox("Contenedor (0.045)")
        with c2: t_bis = st.checkbox("Bisagra (0.160)")
        with c3: t_man = st.number_input("Tara Adicional:", value=0.000, format="%.3f")
        
        btn_add = st.form_submit_button("➕ REGISTRAR PESAJE")

    if btn_add:
        if art_sel != "" and peso_t is not None:
            pue = productos.get(art_sel, 1.0)
            tara_total = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + t_man
            peso_neto = peso_t - tara_total
            
            if "TINTA" in art_sel:
                envase_vacio = 0.030
                resultado = (peso_neto - envase_vacio) / pue
                formula_txt = f"(PN:{peso_neto:.3f}-Env:0.03)/PUE:{pue}"
            else:
                resultado = peso_neto / pue
                formula_txt = f"PN:{peso_neto:.3f}/PUE:{pue}"
            
            st.session_state.valores_pesajes.append(resultado)
            st.session_state.pesajes_detallados.append({
                "N°": len(st.session_state.valores_pesajes),
                "P. Bruto (PB)": f"{peso_t:.3f}kg",
                "Tara (T)": f"{tara_total:.3f}kg",
                "Fórmula": formula_txt,
                "Subtotal": round(resultado, 3)
            })
            st.session_state.articulo_actual = art_sel
        else:
            st.error("⚠️ Ingrese Artículo y Peso Bruto.")

    if st.session_state.valores_pesajes:
        st.divider()
        st.subheader(f"📋 Auditoría Actual: {st.session_state.articulo_actual}")
        st.table(pd.DataFrame(st.session_state.pesajes_detallados))
        
        total_acumulado = sum(st.session_state.valores_pesajes)
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.metric("TOTAL REAL", f"{total_acumulado:.2f}")
        with c_m2: val_teorico = st.number_input("Valor Teórico:", value=None, placeholder="0.00")
        
        if val_teorico is not None:
            diferencia = total_acumulado - val_teorico
            with c_m3: st.metric("DIFERENCIA", f"{diferencia:.2f}", delta=round(diferencia, 2), delta_color="inverse")
            
            if st.button("💾 GUARDAR EN HISTORIAL", use_container_width=True):
                h_act = datetime.now().strftime("%H:%M:%S")
                f_act = datetime.now().strftime("%Y-%m-%d")
                detalles_str = " | ".join([d['Fórmula'] for d in st.session_state.pesajes_detallados])
                
                c.execute('''INSERT INTO registro_auditoria 
                             (fecha, hora, articulo, suma_total, valor_restado, diferencia, detalle_operacion) 
                             VALUES (?,?,?,?,?,?,?)''', 
                          (f_act, h_act, st.session_state.articulo_actual, total_acumulado, val_teorico, diferencia, detalles_str))
                conn.commit()
                st.success("✅ Registro guardado. Ve a la pestaña 'Historial' para enviar el reporte.")
                st.button("🧹 INICIAR NUEVO", on_click=finalizar_y_limpiar)

# --- TAB 2: BASE DE DATOS Y WHATSAPP ---
with tab_db:
    st.header("📂 Historial de Auditorías")
    df_db = pd.read_sql("SELECT * FROM registro_auditoria ORDER BY id DESC", conn)
    
    if not df_db.empty:
        # 1. Selector para elegir cuál registro enviar por WA
        st.subheader("📲 Enviar Reporte a WhatsApp")
        opciones_historial = [f"ID {row['id']} - {row['articulo']} ({row['fecha']})" for index, row in df_db.iterrows()]
        seleccion = st.selectbox("Seleccione el registro para enviar:", opciones_historial)
        
        # Obtener los datos del registro seleccionado
        id_sel = int(seleccion.split(" ")[1])
        reg = df_db[df_db['id'] == id_sel].iloc[0]
        
        # Formato de mensaje profesional
        msg = (f"*AUDITORÍA DE INVENTARIO*\n"
               f"------------------------------\n"
               f"*ID Registro:* {reg['id']}\n"
               f"*Fecha:* {reg['fecha']} {reg['hora']}\n"
               f"*Artículo:* {reg['articulo']}\n"
               f"*Total Real:* {reg['suma_total']:.2f}\n"
               f"*Teórico:* {reg['valor_restado']:.2f}\n"
               f"*Diferencia:* {reg['diferencia']:.2f}\n"
               f"------------------------------\n"
               f"*Desglose:* {reg['detalle_operacion']}")
        
        st.markdown(f"### [📲 ENVIAR REPORTE SELECCIONADO A WA](https://wa.me/522283530069?text={urllib.parse.quote(msg)})")
        
        st.divider()
        st.subheader("📊 Tabla de Registros")
        st.dataframe(df_db, use_container_width=True)
        
        csv = df_db.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DESCARGAR EXCEL (CSV)", data=csv, file_name="historial_pue.csv", mime="text/csv")
        
        if st.checkbox("Zona de Peligro"):
            if st.button("BORRAR TODO EL HISTORIAL"):
                c.execute("DELETE FROM registro_auditoria")
                conn.commit()
                st.rerun()
    else:
        st.info("No hay registros en la base de datos.")
