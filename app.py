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

# 3. DICCIONARIO DE PRODUCTOS COMPLETO
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

# 4. INTERFAZ DE TABS
tab_calc, tab_db = st.tabs(["📊 Calculadora de Auditoría", "📂 Historial y Reportes WA"])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    st.title("⚖️ PUE Champlitte: Control de Pesajes")
    
    with st.form(key=f"f_{st.session_state.form_key}", clear_on_submit=True):
        col_art, col_peso = st.columns([2, 1])
        with col_art:
            art_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()))
        with col_peso:
            peso_t = st.number_input("Peso Bruto Registrado (kg):", value=None, format="%.3f", placeholder="0.000")
        
        st.markdown("**Configuración de Tara (kg)**")
        c1, c2, c3 = st.columns(3)
        with c1: t_cont = st.checkbox("Contenedor (0.045)")
        with c2: t_bis = st.checkbox("Bisagra (0.160)")
        with c3: 
            # Ajuste: value=None y placeholder hace que el campo inicie vacío
            t_man = st.number_input("Tara Adicional:", value=None, format="%.3f", placeholder="0.000")
        
        btn_add = st.form_submit_button("➕ AGREGAR AL DESGLOSE")

    if btn_add:
        if art_sel != "" and peso_t is not None:
            pue = productos.get(art_sel, 1.0)
            # Manejo de tara manual si es None
            t_man_val = t_man if t_man is not None else 0.0
            tara_total = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + t_man_val
            peso_neto = peso_t - tara_total
            
            if "TINTA" in art_sel:
                envase = 0.030
                resultado = (peso_neto - envase) / pue
                formula_txt = f"(PN:{peso_neto:.3f}-Env:0.03)/PUE:{pue}"
            else:
                resultado = peso_neto / pue
                formula_txt = f"PN:{peso_neto:.3f}/PUE:{pue}"
            
            st.session_state.valores_pesajes.append(resultado)
            st.session_state.pesajes_detallados.append({
                "N°": len(st.session_state.valores_pesajes),
                "P. Bruto (PB)": f"{peso_t:.3f} kg",
                "Tara (T)": f"{tara_total:.3f} kg",
                "Fórmula": formula_txt,
                "Subtotal": round(resultado, 3)
            })
            st.session_state.articulo_actual = art_sel
        else:
            st.error("⚠️ Datos incompletos. Seleccione artículo y peso.")

    if st.session_state.valores_pesajes:
        st.divider()
        st.subheader(f"📋 Revisión: {st.session_state.articulo_actual}")
        st.table(pd.DataFrame(st.session_state.pesajes_detallados))
        
        total_s = sum(st.session_state.valores_pesajes)
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.metric("TOTAL CALCULADO", f"{total_s:.2f}")
        with c_m2:
            val_teorico = st.number_input("Valor Teórico (Stock):", value=None, placeholder="Escriba valor...")
        
        if val_teorico is not None:
            dif = total_s - val_teorico
            with c_m3:
                st.metric("DIFERENCIA", f"{dif:.2f}", delta=round(dif, 2), delta_color="inverse")
            
            if st.button("💾 GUARDAR REGISTRO EN HISTORIAL", use_container_width=True):
                f_act = datetime.now().strftime("%Y-%m-%d")
                h_act = datetime.now().strftime("%H:%M:%S")
                detalles_str = " | ".join([d['Fórmula'] for d in st.session_state.pesajes_detallados])
                
                c.execute('''INSERT INTO registro_auditoria 
                             (fecha, hora, articulo, suma_total, valor_restado, diferencia, detalle_operacion) 
                             VALUES (?,?,?,?,?,?,?)''', 
                          (f_act, h_act, st.session_state.articulo_actual, total_s, val_teorico, dif, detalles_str))
                conn.commit()
                st.success("✅ Guardado correctamente. Pasa a la pestaña 'Historial' para enviar.")
                st.button("🧹 NUEVO REGISTRO", on_click=finalizar_y_limpiar)

# --- TAB 2: HISTORIAL Y WHATSAPP ---
with tab_db:
    st.header("📂 Historial de Auditorías")
    df_db = pd.read_sql("SELECT * FROM registro_auditoria ORDER BY id DESC", conn)
    
    if not df_db.empty:
        st.subheader("📲 Generar Reporte para WhatsApp")
        opciones = [f"ID {row['id']} - {row['articulo']} ({row['fecha']})" for _, row in df_db.iterrows()]
        seleccion = st.selectbox("Seleccione el registro a enviar:", opciones)
        
        id_sel = int(seleccion.split(" ")[1])
        reg = df_db[df_db['id'] == id_sel].iloc[0]
        
        msg = (f"*REPORTE DE AUDITORÍA PUE*\n"
               f"--------------------------------\n"
               f"*ID:* {reg['id']}\n"
               f"*Fecha:* {reg['fecha']} {reg['hora']}\n"
               f"*Artículo:* {reg['articulo']}\n"
               f"*Suma Real:* {reg['suma_total']:.2f}\n"
               f"*Teórico:* {reg['valor_restado']:.2f}\n"
               f"*Diferencia:* {reg['diferencia']:.2f}\n"
               f"--------------------------------\n"
               f"*Desglose:* {reg['detalle_operacion']}")
        
        url_wa = f"https://wa.me/522283530069?text={urllib.parse.quote(msg)}"

        st.markdown(f"""
            <style>
            .btn-wa {{
                background-color: #25D366;
                color: white !important;
                padding: 15px 30px;
                text-align: center;
                text-decoration: none;
                display: block;
                font-size: 20px;
                font-weight: bold;
                border-radius: 10px;
                margin: 10px 0px;
                transition: 0.3s;
                border: none;
            }}
            .btn-wa:hover {{
                background-color: #128C7E;
                color: white !important;
                text-decoration: none;
            }}
            </style>
            <a href="{url_wa}" target="_blank" class="btn-wa">
                🟢 ENVIAR POR WHATSAPP
            </a>
        """, unsafe_allow_html=True)
        
        st.divider()
        st.dataframe(df_db, use_container_width=True)
        
        col_ex, col_del = st.columns(2)
        with col_ex:
            csv = df_db.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Excel (CSV)", data=csv, file_name="auditoria_pue.csv", mime="text/csv")
        with col_del:
            if st.checkbox("Habilitar Borrado"):
                if st.button("🗑️ BORRAR TODO EL HISTORIAL"):
                    c.execute("DELETE FROM registro_auditoria")
                    conn.commit()
                    st.rerun()
    else:
        st.info("No hay registros guardados todavía.")
