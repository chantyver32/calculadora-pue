import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz
import io
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

# NUEVA TABLA PARA GUARDAR EL RESUMEN DE STOCK Y DIFERENCIAS
c.execute('''CREATE TABLE IF NOT EXISTS auditoria_stock 
             (articulo TEXT PRIMARY KEY, total_real REAL, stock REAL, diferencia REAL)''')
conn.commit()

# --- BARRA LATERAL (SIDEBAR) ESTILO IMAGEN ---
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    # Lista de números de WhatsApp para el desplegable (Puedes agregar más aquí)
    opciones_wa = [
        "522283530069",
        "522280000000",  # Cambia esto por otro número si lo necesitas
        "522281111111"
    ]
    numero_wa = st.selectbox("📱 Número WhatsApp", opciones_wa)
    
    with st.expander("🚨 Zona de Peligro", expanded=True):
        confirmar_borrado = st.checkbox("Confirmar que deseo borrar todo")
        
        # El botón solo se habilita si el checkbox está marcado
        if st.button("⚠️ EJECUTAR RESET TOTAL", disabled=not confirmar_borrado, type="secondary"):
            c.execute("DELETE FROM pesajes_individuales")
            c.execute("DELETE FROM auditoria_stock")  
            conn.commit()
            st.success("Base de datos reseteada.")
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
        c = idx % cols
        cell = table.cell(r, c)
        
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
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada", "📋 Auditoría y Reportes"])

# --- TAB 1: REGISTRO ---
with tab_calc:
    st.title("⚖️ Registro de Pesaje")
    
    st.info("🎤 **Ingreso por Voz:** Dicta algo como 0.620 kg de capacillo chino en contenedor.")
    audio_bytes = st.audio_input("Grabar voz para registro", key="audio_reg")
    texto_reconocido = ""
    
    if audio_bytes:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_bytes) as source:
            audio_data = recognizer.record(source)
            try:
                texto_reconocido = recognizer.recognize_google(audio_data, language="es-MX")
                st.success(f"**Escuchado:** {texto_reconocido}")
            except sr.UnknownValueError:
                st.error("No se pudo entender el audio.")
            except sr.RequestError:
                st.error("Error en el servicio de reconocimiento de voz.")

    texto_filtro = texto_reconocido.upper() if texto_reconocido else ""
    
    idx_sugerido = None
    peso_sugerido = None
    pue_sugerido = None
    t_cont_sugerido = False
    t_bis_sugerido = False
    nombre_limpio_sugerido = ""
    
    opciones = sorted(productos.keys())
    
    if texto_filtro:
        if "CONTENEDOR" in texto_filtro: t_cont_sugerido = True
        if "BISAGRA" in texto_filtro: t_bis_sugerido = True
        
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

    col_mode1, col_mode2 = st.columns(2)
    with col_mode1:
        nuevo_art = st.toggle("Modo: Artículo NO listado", value=False)
    with col_mode2:
        modo_preconteo = st.toggle("Modo: PRE-CONTEO MANUAL (Piezas directas)", value=False)
    
    with st.form(key="form_pesaje", clear_on_submit=True):
        if not nuevo_art:
            art_sel = st.selectbox("Seleccione Artículo:", opciones, index=idx_sugerido, placeholder="Elija un producto...")
            pue_final = productos.get(art_sel, 1.0) if art_sel else 1.0
        else:
            c_n1, c_n2 = st.columns([2,1])
            with c_n1:
                art_sel = st.text_input("Nombre del Nuevo Artículo:", value=nombre_limpio_sugerido if nombre_limpio_sugerido else None, placeholder="Ej. CAJA PERSONALIZADA")
            with c_n2:
                pue_final = st.number_input("Asignar Peso Unitario:", value=pue_sugerido, format="%.4f", placeholder="0.0000")

        st.divider()

        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=peso_sugerido, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total, formula = 0.0, 0.0, "CONTEO MANUAL DIRECTO"
        else:
            peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=peso_sugerido, format="%.3f", placeholder="0.000")
            with st.expander("🛠️ Configuración de Taras", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1: t_cont = st.checkbox("Contenedor (0.045)", value=t_cont_sugerido)
                with c2: t_bis = st.checkbox("Bisagra (0.016)", value=t_bis_sugerido)
                with c3: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f", placeholder="0.000")
        
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
                tara_total = (0.045 if t_cont else 0) + (0.016 if t_bis else 0) + tm
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

# --- TAB 2: AUDITORÍA ---
with tab_historial:
    st.title("📋 Consolidación de Auditoría")
    
    # Cargar datos de ambas tablas
    df_actual = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    df_guardados = pd.read_sql("SELECT * FROM pesajes_guardados", conn)
    
    # Etiquetar los registros guardados para diferenciarlos en los reportes combinados
    if not df_guardados.empty:
        df_guardados_rep = df_guardados.copy()
        df_guardados_rep['detalle_formula'] = "[GUARDADO] " + df_guardados_rep['detalle_formula'].astype(str)
    else:
        df_guardados_rep = pd.DataFrame(columns=df_actual.columns)
        
    # Combinar ambas tablas para la vista unificada de auditoría y exportaciones
    df_combined = pd.concat([df_actual, df_guardados_rep], ignore_index=True)
    
    if not df_combined.empty:
        st.info("🎤 **Buscar Artículo por Voz:** Dicta el nombre del producto que quieres auditar.")
        audio_filtro_bytes = st.audio_input("Grabar voz para buscar", key="audio_filtro")
        texto_busqueda = ""
        idx_filtro_sugerido = None
        opciones_filtro = sorted(df_combined['articulo'].unique())
        
        if audio_filtro_bytes:
            recognizer_filtro = sr.Recognizer()
            with sr.AudioFile(audio_filtro_bytes) as source_filtro:
                audio_data_filtro = recognizer_filtro.record(source_filtro)
                try:
                    texto_busqueda = recognizer_filtro.recognize_google(audio_data_filtro, language="es-MX").upper()
                    st.success(f"**Buscando:** {texto_busqueda}")
                except sr.UnknownValueError:
                    st.error("No se pudo entender el audio de búsqueda.")
                except sr.RequestError:
                    st.error("Error en el servicio de reconocimiento de voz.")
                    
        if texto_busqueda:
            palabras_clave_busqueda = texto_busqueda.split()
            max_coincidencias_busqueda = 0
            for i, prod in enumerate(opciones_filtro):
                coincidencias = sum(1 for palabra in palabras_clave_busqueda if palabra in prod.upper())
                if coincidencias > max_coincidencias_busqueda:
                    max_coincidencias_busqueda = coincidencias
                    idx_filtro_sugerido = i

        art_filtro = st.selectbox("Seleccione el Artículo a Consultar:", opciones_filtro, index=idx_filtro_sugerido, placeholder="Seleccione para ver desglose...")
        
        msg_reporte = "" 
        
        if art_filtro:
            # Filtramos sobre df_combined para sumar tanto los nuevos como los guardados
            df_art = df_combined[df_combined['articulo'] == art_filtro]
            total_real = truncar_dos_decimales(df_art['resultado_pue'].sum())
            
            st.subheader(f"Resultados de: {art_filtro}")
            st.table(df_art[['fecha_hora', 'peso_bruto', 'tara', 'pue', 'detalle_formula', 'resultado_pue']].rename(columns={
                'fecha_hora': 'Fecha/Hora', 'peso_bruto': 'P. Bruto', 'tara': 'Tara Total', 'pue': 'PUE Usado', 'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad/Resultado'
            }))
            
            st.divider()
            c_res1, c_res2, c_res3 = st.columns(3)
            with c_res1:
                st.metric("TOTAL (SESIÓN + BÓVEDA)", formato_estricto(total_real))
            
            # Buscar si ya hay un stock guardado para este artículo
            c.execute("SELECT stock FROM auditoria_stock WHERE articulo=?", (art_filtro,))
            row_stock = c.fetchone()
            saved_stock = row_stock[0] if row_stock else None
            
            with c_res2:
                stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, placeholder="Ingrese stock y presione Enter")
            
            if stock_teorico is not None:
                diferencia = truncar_dos_decimales(total_real - stock_teorico)
                
                # GUARDADO AUTOMÁTICO EN LA BASE DE DATOS AL PRESIONAR ENTER
                c.execute("""INSERT OR REPLACE INTO auditoria_stock (articulo, total_real, stock, diferencia) 
                             VALUES (?, ?, ?, ?)""", (art_filtro, total_real, stock_teorico, diferencia))
                conn.commit()
                
                with c_res3:
                    st.metric("DIFERENCIA", formato_estricto(diferencia), delta=round(diferencia, 2), delta_color="inverse")
                
                desglose_txt = "\n".join([f"• {f} = *{formato_estricto(r)}*" for f, r in zip(df_art['detalle_formula'], df_art['resultado_pue'])])
                msg_reporte = (f"*REPORTE DE AUDITORÍA INDIVIDUAL*\n"
                               f"------------------------------\n"
                               f"*Producto:* {art_filtro}\n"
                               f"*Total Físico Acumulado:* *{formato_estricto(total_real)}*\n"
                               f"*Stock Sistema:* *{formato_estricto(stock_teorico)}*\n"
                               f"*Diferencia:* *{formato_estricto(diferencia)}*\n"
                               f"------------------------------\n"
                               f"*OPERACIONES Y PRECONTEOS:*\n{desglose_txt}")

        st.divider()

        st.subheader("🖨️ Exportación de Archivos")
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            st.markdown("**1. Tarjetas para Recorte**")
            
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
            
        with col_export2:
            st.markdown("**2. Reporte Excel Oficial**")
            
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

        with col_export3:
            st.markdown("**3. Generar Reporte Total (WhatsApp)**")
            
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
                
            st.info("El Reporte Total está listo con las sumatorias. Envía desde los botones de abajo.")

        st.divider()
        
        st.subheader("📞 Envíos a WhatsApp")
        col_wa1, col_wa2 = st.columns(2)
        with col_wa1:
            if art_filtro and msg_reporte:
                url_wa = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(msg_reporte)}"
                st.markdown(f'<a href="{url_wa}" target="_blank" class="btn-wa">📲 ENVIAR REPORTE INDIVIDUAL</a>', unsafe_allow_html=True)
            else:
                st.info("📌 Selecciona un artículo para enviar su reporte individual.")
                
        with col_wa2:
            url_wa_reporte = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(reporte_wa_texto)}"
            st.markdown(f'<a href="{url_wa_reporte}" target="_blank" class="btn-wa" style="margin: 0px;">📲 ENVIAR REPORTE TOTAL (LISTA DIFERENCIAS)</a>', unsafe_allow_html=True)
            
        st.divider()
        
        with st.expander("🗑️ Administración de Base de Datos - Eliminar Registros", expanded=True):
            st.markdown("#### Selecciona el renglón de la izquierda y presiona el ícono de papelera 🗑️ para borrar.")
            
            columnas_bloqueadas = df_actual.columns.tolist() 
            edited_df = st.data_editor(
                df_actual,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                disabled=columnas_bloqueadas, 
                key="editor_db"
            )
            
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

        # --- SECCIÓN DE DATOS PROTEGIDOS ---
        st.divider()
        with st.expander("🛡️ Guardar Aparte (Registros Protegidos)", expanded=False):
            st.markdown("Selecciona registros de la sesión actual para trasladarlos a la bóveda segura. **Estos funcionarán como pre-conteos y se sumarán automáticamente a tus nuevos pesajes.**")
            
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
                    st.success(f"Se han trasladado {len(seleccionados_para_proteger)} registros a la bóveda de pre-conteos de forma segura.")
                    st.rerun()
                else:
                    st.warning("Selecciona al menos un registro de la lista.")
                    
            st.divider()
            st.markdown("#### 🗃️ Pre-conteos Guardados Actualmente")
            
            if not df_guardados.empty:
                edited_guardados = st.data_editor(
                    df_guardados,
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True,
                    disabled=df_guardados.columns.tolist(),
                    key="editor_db_guardados"
                )
                
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
        st.info("No hay pesajes ni pre-conteos registrados aún.")

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
