import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz
import io
import time
import speech_recognition as sr
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
import re  
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide", page_icon="⚖️")

# Estilos CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .btn-wa {
        background-color: #25D366;
        color: white !important;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none !important;
        display: block;
        font-size: 14px;
        font-weight: bold;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    </style>
""", unsafe_allow_html=True)

# 2. BASE DE DATOS
conn = sqlite3.connect("pue_champlitte_v4.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, articulo TEXT, 
             peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS pesajes_guardados 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, articulo TEXT, 
             peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS auditoria_stock 
             (articulo TEXT PRIMARY KEY, total_real REAL, stock REAL, diferencia REAL)''')
conn.commit()

# --- BARRA LATERAL (SIDEBAR) ESTILO IMAGEN ---
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    opciones_wa = [
        "522283530069",
        "522281111111", 
        "522280000000"  
    ]
    numero_wa = st.selectbox("📱 Número WhatsApp", opciones_wa)
    
    st.divider()
    st.markdown("### 💾 Respaldo de Base de Datos")
    st.info("Guarda o restaura tus preconteos (bóveda) mediante un archivo CSV para mantenerlos fijos y no perderlos.")
    
    # Importar Bóveda
    with st.form("form_restaurar_boveda"):
        uploaded_csv = st.file_uploader("⬆️ Subir Respaldo CSV", type=["csv"])
        btn_restaurar = st.form_submit_button("🔄 Restaurar Preconteos", use_container_width=True)
        
        if btn_restaurar:
            if uploaded_csv is not None:
                try:
                    df_upload = pd.read_csv(uploaded_csv)
                    # Eliminamos el ID si existe para que no choque con la base de datos
                    if 'id' in df_upload.columns:
                        df_upload = df_upload.drop(columns=['id'])
                    
                    df_upload.to_sql("pesajes_guardados", conn, if_exists="append", index=False)
                    st.success("✅ Respaldo restaurado con éxito")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al restaurar: {e}")
            else:
                st.warning("⚠️ Primero selecciona un archivo CSV.")

    st.divider()
    with st.expander("🚨 Zona de Peligro", expanded=False):
        confirmar_borrado = st.checkbox("Confirmar que deseo borrar todo")
        if st.button("⚠️ EJECUTAR RESET TOTAL", use_container_width=True):
            if not confirmar_borrado:
                st.error("Debes confirmar primero")
            else:
                c.execute("DELETE FROM pesajes_individuales")
                c.execute("DELETE FROM auditoria_stock")  
                conn.commit()
                st.success("✅ Base de datos limpiada por completo")
                time.sleep(1.5)
                st.rerun()

# --- FUNCIONES ---
def truncar_dos_decimales(valor):
    if valor is None: return 0.0
    return int(valor * 100) / 100.0

def formato_estricto(valor):
    if pd.isna(valor) or valor is None: return "0.00"
    s = f"{float(valor):.10f}" 
    entero, decimal = s.split('.')
    return f"{entero}.{decimal[:2]}"

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(1)
        section.bottom_margin = Cm(1)
        section.left_margin = Cm(1)
        section.right_margin = Cm(1)
        
    cols = 4
    rows = (len(df) + cols - 1) // cols
    if rows == 0: rows = 1
    
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Table Grid'
    
    for idx, row_data in df.iterrows():
        r = idx // cols
        c_idx = idx % cols
        cell = table.cell(r, c_idx)
        
        cell.width = Cm(5)
        table.rows[r].height = Cm(2)
        table.rows[r].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        
        articulo = str(row_data['articulo'])
        resultado = formato_estricto(row_data['resultado_pue'])
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p.add_run(f"\n{articulo}\n")
        run1.font.size = Pt(8)
        run1.bold = True
        
        run2 = p.add_run(f"\nTotal: {resultado}")
        run2.font.size = Pt(12)
        run2.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 3. DICCIONARIO DE PRODUCTOS
productos = {
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
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

# VARIABLES FIJAS
sucursal_in = "COSTA VERDE"
elabora_in = "PEDRO GARCÍA"

# 4. INTERFAZ
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada & Auditoría", "📋 Reportes y Bóveda"])

# --- TAB 1: REGISTRO Y AUDITORÍA UNIFICADA ---
with tab_calc:
    st.title("⚖️ Registro y Control de Stock")
    
    texto_reconocido = ""
    
    # MODIFICACIÓN: Desplegable para el ingreso por voz (cerrado por defecto)
    with st.expander("🎤 **Ingreso por Voz** (Click para desplegar)", expanded=False):
        st.info("Dicta algo como: 0.620 kg de capacillo chino en contenedor.")
        audio_bytes = st.audio_input("Grabar voz para registro", key="audio_reg")
        
        if audio_bytes:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                audio_data = recognizer.record(source)
                try:
                    texto_reconocido = recognizer.recognize_google(audio_data, language="es-MX")
                    st.success(f"**Escuchado:** {texto_reconocido}")
                    
                    js_tts = f"""
                    <script>
                        const utterance = new SpeechSynthesisUtterance("{texto_reconocido}");
                        utterance.lang = 'es-MX';
                        utterance.rate = 1.0;
                        window.speechSynthesis.speak(utterance);
                    </script>
                    """
                    components.html(js_tts, height=0)
                    
                except sr.UnknownValueError:
                    st.error("No se pudo entender el audio.")
                except sr.RequestError:
                    st.error("Error en el servicio de reconocimiento de voz.")

    texto_filtro = texto_reconocido.upper() if texto_reconocido else ""
    
    idx_sugerido = None
    peso_sugerido = None
    pue_sugerido = None
    t_cont_sugerido = False
    nombre_limpio_sugerido = ""
    
    opciones = sorted(productos.keys())
    
    if texto_filtro:
        if "CONTENEDOR" in texto_filtro: t_cont_sugerido = True
        
        match_pue = re.search(r'(?:PESO UNITARIO|UNITARIO|PUE|ESTÁNDAR|ESTANDAR)[^\d]*(\d+(?:[.,]\d+)?)', texto_filtro)
        if match_pue:
            pue_sugerido = float(match_pue.group(1).replace(',', '.'))
            
        numeros_str = re.findall(r'\d+(?:[.,]\d+)?', texto_filtro)
        numeros_floats = [float(n.replace(',', '.')) for n in numeros_str]
        
        if numeros_floats:
            if pue_sugerido in numeros_floats:
                numeros_floats.remove(pue_sugerido) 
            if numeros_floats:
                peso_sugerido = numeros_floats[0] 
                
        palabras_basura = [r'\d+(?:[.,]\d+)?', 'PESO UNITARIO', 'PUE', 'PESO', 'UNITARIO', 'ESTÁNDAR', 'ESTANDAR', 'KILOS', 'KG', 'GRAMOS', 'CON', 'SIN', 'Y', 'DE', 'EL', 'LA', 'CONTENEDOR', 'BISAGRA', 'LLEVA', 'ASIGNAR']
        texto_limpio = texto_filtro
        for p in palabras_basura:
            texto_limpio = re.sub(r'\b' + p + r'\b', '', texto_limpio)
        nombre_limpio_sugerido = ' '.join(texto_limpio.split()) 
        
        palabras_clave = nombre_limpio_sugerido.split()
        if palabras_clave:
            max_coincidencias = 0
            for i, prod in enumerate(opciones):
                coincidencias = sum(1 for palabra in palabras_clave if palabra in prod.upper())
                if coincidencias > max_coincidencias:
                    max_coincidencias = coincidencias
                    idx_sugerido = i

    # SELECCIÓN PRINCIPAL (FUERA DEL FORMULARIO PARA FUNCIONAR COMO BUSCADOR GENERAL)
    col_mode1, col_mode2 = st.columns(2)
    with col_mode1:
        nuevo_art = st.toggle("Modo: Artículo NO listado", value=False)
    with col_mode2:
        modo_preconteo = st.toggle("Modo: PRE-CONTEO MANUAL (Piezas directas)", value=False)
    
    if not nuevo_art:
        art_sel = st.selectbox("Seleccione Artículo (Aplica para registro y desglose):", opciones, index=idx_sugerido, placeholder="Elija un producto...")
        pue_final = productos.get(art_sel, 1.0) if art_sel else 1.0
    else:
        c_n1, c_n2 = st.columns([2,1])
        with c_n1:
            art_sel = st.text_input("Nombre del Nuevo Artículo:", value=nombre_limpio_sugerido if nombre_limpio_sugerido else None, placeholder="Ej. CAJA PERSONALIZADA")
        with c_n2:
            pue_final = st.number_input("Asignar Peso Unitario:", value=pue_sugerido, format="%.4f", placeholder="0.0000")

    # FORMULARIO DE INGRESO
    with st.form(key="form_pesaje", clear_on_submit=True):
        st.markdown(f"**Registrando cantidad para:** {art_sel if art_sel else 'Ninguno seleccionado'}")
        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=peso_sugerido, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total, formula = 0.0, 0.0, "CONTEO MANUAL DIRECTO"
        else:
            peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=peso_sugerido, format="%.3f", placeholder="0.000")
            with st.expander("🛠️ Configuración de Taras", expanded=True):
                c1, c2 = st.columns(2)
                with c1: t_cont = st.checkbox("Contenedor (0.045)", value=t_cont_sugerido)
                with c2: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f", placeholder="0.000")
        
        btn_save = st.form_submit_button("📥 CONFIRMAR Y GUARDAR REGISTRO")

    if btn_save:
        articulo_valido = art_sel is not None and art_sel.strip() != ""
        pue_valido = pue_final is not None
        
        if modo_preconteo:
            datos_listos = articulo_valido and cantidad_directa is not None
            resultado = truncar_dos_decimales(cantidad_directa) if datos_listos else 0
        else:
            datos_listos = articulo_valido and peso_bruto is not None and pue_valido
            if datos_listos:
                tm = t_manual if t_manual is not None else 0.0
                tara_total = (0.045 if t_cont else 0) + tm
                peso_neto = peso_bruto - tara_total
                is_tinta = "TINTA" in str(art_sel).upper()
                offset = 0.030 if is_tinta else 0.0
                resultado_calc = (peso_neto - offset) / pue_final
                resultado = truncar_dos_decimales(resultado_calc) 
                formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"

        if datos_listos:
            zona_mexico = pytz.timezone('America/Mexico_City')
            fecha_mexico = datetime.now(zona_mexico).strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("""INSERT INTO pesajes_individuales 
                         (fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                         VALUES (?,?,?,?,?,?,?)""",
                      (fecha_mexico, art_sel, peso_bruto if not modo_preconteo else 0, 
                       tara_total if not modo_preconteo else 0, pue_final if not modo_preconteo else 0, 
                       resultado, formula))
            conn.commit()
            st.balloons()
            st.success(f"✅ Registrado con éxito: {formato_estricto(resultado)} de {art_sel}")
        else:
            st.error("❌ Error: Revisa que el Nombre, el Peso Unitario y el Peso de Báscula estén correctos.")

    # --- SECCIÓN INTEGRADA DE AUDITORÍA Y STOCK ---
    if art_sel:
        st.divider()
        st.subheader(f"📊 Desglose y Stock de: {art_sel}")
        
        df_actual_art = pd.read_sql("SELECT * FROM pesajes_individuales WHERE articulo=?", conn, params=(art_sel,))
        df_guardados_art = pd.read_sql("SELECT * FROM pesajes_guardados WHERE articulo=?", conn, params=(art_sel,))
        
        if not df_guardados_art.empty:
            df_guardados_art['detalle_formula'] = "[GUARDADO] " + df_guardados_art['detalle_formula'].astype(str)
            
        df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
        
        if not df_art_combined.empty:
            st.table(df_art_combined[['fecha_hora', 'peso_bruto', 'tara', 'pue', 'detalle_formula', 'resultado_pue']].rename(columns={
                'fecha_hora': 'Fecha/Hora', 'peso_bruto': 'P. Bruto', 'tara': 'Tara Total', 'pue': 'PUE Usado', 'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad/Resultado'
            }))
            
            total_real = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
            
            # Buscar si ya hay un stock guardado
            c.execute("SELECT stock FROM auditoria_stock WHERE articulo=?", (art_sel,))
            row_stock = c.fetchone()
            saved_stock = row_stock[0] if row_stock else None
            
            col_st1, col_st2, col_st3 = st.columns(3)
            with col_st1:
                st.metric("TOTAL CALCULADO (Sesión + Bóveda)", formato_estricto(total_real))
            
            with col_st2:
                stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, placeholder="Ingresa y presiona Enter")
                
            if stock_teorico is not None:
                diferencia = truncar_dos_decimales(total_real - stock_teorico)
                c.execute("""INSERT OR REPLACE INTO auditoria_stock (articulo, total_real, stock, diferencia) 
                             VALUES (?, ?, ?, ?)""", (art_sel, total_real, stock_teorico, diferencia))
                conn.commit()
                
                with col_st3:
                    st.metric("DIFERENCIA", formato_estricto(diferencia), delta=round(diferencia, 2), delta_color="inverse")
                    
                # Botón de WhatsApp individual aquí mismo
                desglose_txt = "\n".join([f"• {f} = *{formato_estricto(r)}*" for f, r in zip(df_art_combined['detalle_formula'], df_art_combined['resultado_pue'])])
                msg_reporte = (f"*REPORTE DE AUDITORÍA INDIVIDUAL*\n"
                               f"------------------------------\n"
                               f"*Producto:* {art_sel}\n"
                               f"*Total Físico Acumulado:* *{formato_estricto(total_real)}*\n"
                               f"*Stock Sistema:* *{formato_estricto(stock_teorico)}*\n"
                               f"*Diferencia:* *{formato_estricto(diferencia)}*\n"
                               f"------------------------------\n"
                               f"*OPERACIONES Y PRECONTEOS:*\n{desglose_txt}")
                
                url_wa = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(msg_reporte)}"
                st.markdown(f'<a href="{url_wa}" target="_blank" class="btn-wa">📲 ENVIAR REPORTE {art_sel}</a>', unsafe_allow_html=True)
        else:
            st.info("No hay pesajes ni preconteos registrados para este artículo aún.")

# --- TAB 2: EXPORTACIÓN Y BÓVEDA ---
with tab_historial:
    st.title("🖨️ Exportación y Base de Datos")
    
    df_actual = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    df_guardados = pd.read_sql("SELECT * FROM pesajes_guardados", conn)
    df_guardados_rep = df_guardados.copy()
    if not df_guardados_rep.empty:
        df_guardados_rep['detalle_formula'] = "[GUARDADO] " + df_guardados_rep['detalle_formula'].astype(str)
    df_combined = pd.concat([df_actual, df_guardados_rep], ignore_index=True)

    if not df_combined.empty:
        st.subheader("1. Generar Reporte Total (WhatsApp)")
        df_auditoria = pd.read_sql("SELECT * FROM auditoria_stock", conn)
        
        reporte_wa_texto = f"📊 *BAJA DE INSUMOS*\n"
        reporte_wa_texto += f"🏢 *Sucursal:* {sucursal_in}\n"
        reporte_wa_texto += f"👤 *Vendedor:* {elabora_in}\n"
        reporte_wa_texto += f"📅 *Fecha:* {datetime.now(pytz.timezone('America/Mexico_City')).strftime('%d/%m/%Y %H:%M')}\n\n"
        reporte_wa_texto += "📦 *RESUMEN DE DIFERENCIAS:*\n"
        
        if not df_auditoria.empty:
            for index, row_aud in df_auditoria.iterrows():
                art_actual = row_aud['articulo']
                df_art_desglose = df_combined[df_combined['articulo'] == art_actual]
                sumandos = [formato_estricto(val) for val in df_art_desglose['resultado_pue']]
                
                if len(sumandos) > 1:
                    desglose_str = f"{' + '.join(sumandos)} = {formato_estricto(row_aud['total_real'])}"
                else:
                    desglose_str = formato_estricto(row_aud['total_real'])

                reporte_wa_texto += f"▪️ *{art_actual}*\n"
                reporte_wa_texto += f"   Total Físico: {desglose_str}\n"
                reporte_wa_texto += f"   Stock Sistema: {formato_estricto(row_aud['stock'])}\n"
                reporte_wa_texto += f"   Diferencia: *{formato_estricto(row_aud['diferencia'])}*\n\n"
        else:
            reporte_wa_texto += "No se han calculado stocks en esta sesión.\n"
            
        url_wa_reporte = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(reporte_wa_texto)}"
        st.markdown(f'<a href="{url_wa_reporte}" target="_blank" class="btn-wa">📲 ENVIAR REPORTE TOTAL A WHATSAPP</a>', unsafe_allow_html=True)
        
        st.divider()

        st.subheader("2. Reporte Excel Oficial")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_empty = pd.DataFrame()
            df_empty.to_excel(writer, sheet_name='Baja de insumos', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Baja de insumos']
            
            format_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#8B0000', 'font_color': 'white', 'font_size': 12, 'border': 1})
            format_subtitle = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11, 'border': 1})
            format_label = workbook.add_format({'bold': True, 'border': 1})
            format_data = workbook.add_format({'border': 1})
            format_header = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#f2f2f2'})
            format_center = workbook.add_format({'align': 'center', 'border': 1})
            
            worksheet.merge_range('A1:D1', 'PASTELERÍA CHAMPLITTE, S.A. DE C.V.', format_title)
            worksheet.merge_range('A2:D2', 'BAJA DE INSUMOS', format_subtitle)
            
            fecha_hoy = datetime.now(pytz.timezone('America/Mexico_City')).strftime("%d/%m/%Y")
            worksheet.write('A3', 'SUCURSAL', format_label)
            worksheet.merge_range('B3:D3', sucursal_in, format_data)
            worksheet.write('A4', 'FECHA', format_label)
            worksheet.merge_range('B4:D4', fecha_hoy, format_data)
            worksheet.write('A5', 'ELABORA', format_label)
            worksheet.merge_range('B5:D5', elabora_in, format_data)
            
            headers_excel = ['DESCRIPCIÓN', 'CANTIDAD', 'CÁLCULOS REALIZADOS', 'VENDEDOR']
            for col_num, data in enumerate(headers_excel):
                worksheet.write(5, col_num, data, format_header)
                
            row = 6
            for index, row_data in df_combined.iterrows():
                worksheet.write(row, 0, row_data['articulo'], format_data)
                worksheet.write(row, 1, float(formato_estricto(row_data['resultado_pue'])), format_center)
                worksheet.write(row, 2, row_data['detalle_formula'], format_center) 
                worksheet.write(row, 3, elabora_in, format_center) 
                row += 1
                
            worksheet.set_column('A:A', 35)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 45)
            worksheet.set_column('D:D', 20)

        output.seek(0)
        
        st.download_button(
            label="⬇️ Descargar Excel Formato Oficial",
            data=output,
            file_name="Reporte_Baja_Insumos_Champlitte.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.caption("ℹ️ *Nota: WhatsApp no permite adjuntar archivos Excel mediante enlaces automáticos. Por favor, descarga el archivo y adjúntalo manualmente en tu chat.*")

        st.divider()
        st.subheader("3. Tarjetas Recortables (Word)")
        if not df_guardados.empty:
            df_impresion = df_guardados[['articulo', 'resultado_pue']].copy()
            word_file = generar_word_tarjetas(df_impresion)
            st.download_button(
                label="📄 Descargar Tarjetas en Word (Pre-conteos)",
                data=word_file,
                file_name="Tarjetas_Recortables_Preconteos.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:
            st.info("No hay pre-conteos guardados en la bóveda para generar tarjetas.")
        
        st.divider()
        
        with st.expander("🗑️ Administración de Registros Individuales (Sesión Actual)", expanded=False):
            st.markdown("#### Selecciona el renglón de la izquierda y presiona el ícono de papelera 🗑️ para borrar.")
            columnas_bloqueadas = df_actual.columns.tolist() 
            edited_df = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=columnas_bloqueadas, key="editor_db")
            
            if st.button("💾 Guardar Cambios en Tabla", use_container_width=True):
                original_ids = set(df_actual['id'])
                current_ids = set(edited_df['id'])
                ids_to_delete = original_ids - current_ids
                
                if ids_to_delete:
                    for del_id in ids_to_delete:
                        c.execute("DELETE FROM pesajes_individuales WHERE id = ?", (del_id,))
                    conn.commit()
                    st.success(f"Se eliminaron {len(ids_to_delete)} registros correctamente.")
                    st.rerun()
                else:
                    st.info("No detecté ninguna fila eliminada para guardar.")

        with st.expander("🛡️ Trasladar a Bóveda (Preconteos Permanentes)", expanded=False):
            st.markdown("Mueve registros de la sesión actual a la bóveda segura.")
            opciones_proteger = df_actual.apply(lambda x: f"ID {x['id']} | {x['articulo']} | {x['resultado_pue']} u.", axis=1).tolist()
            seleccionados_para_proteger = st.multiselect("Selecciona los registros a mover a la bóveda:", opciones_proteger)
            
            if st.button("📥 Mover seleccionados a la Bóveda"):
                if seleccionados_para_proteger:
                    for sel in seleccionados_para_proteger:
                        id_val = sel.split(" | ")[0].replace("ID ", "")
                        c.execute("""INSERT INTO pesajes_guardados (fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula)
                                     SELECT fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula 
                                     FROM pesajes_individuales WHERE id = ?""", (id_val,))
                        c.execute("DELETE FROM pesajes_individuales WHERE id = ?", (id_val,))
                    conn.commit()
                    st.success(f"Se han trasladado {len(seleccionados_para_proteger)} registros.")
                    st.rerun()
                else:
                    st.warning("Selecciona al menos un registro de la lista.")
            
            st.divider()
            st.markdown("#### 🗃️ Pre-conteos Guardados Actualmente")
            if not df_guardados.empty:
                edited_guardados = st.data_editor(df_guardados, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_guardados.columns.tolist(), key="editor_db_guardados")
                if st.button("💾 Eliminar filas borradas de la Bóveda", use_container_width=True):
                    original_ids_g = set(df_guardados['id'])
                    current_ids_g = set(edited_guardados['id'])
                    ids_to_delete_g = original_ids_g - current_ids_g
                    if ids_to_delete_g:
                        for del_id in ids_to_delete_g:
                            c.execute("DELETE FROM pesajes_guardados WHERE id = ?", (del_id,))
                        conn.commit()
                        st.success(f"Se eliminaron {len(ids_to_delete_g)} registros guardados.")
                        st.rerun()
            else:
                st.info("No hay pre-conteos guardados en la bóveda en este momento.")
    else:
        st.info("No hay pesajes registrados.")

# --- AJUSTE DE TECLADO MÓVIL ---
components.html(
    """
    <script>
    const inputs = window.parent.document.querySelectorAll('input[type="number"]');
    inputs.forEach(input => {
        input.setAttribute('enterkeyhint', 'done');
    });
    </script>
    """,
    height=0
)
