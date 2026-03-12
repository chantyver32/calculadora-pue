import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz
import io

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
conn.commit()

# --- FUNCIONES DE FORMATEO ESTRICTO ---
def truncar_dos_decimales(valor):
    if valor is None: return 0.0
    return int(valor * 100) / 100.0

def formato_estricto(valor):
    """Convierte a texto y corta en 2 decimales SIN redondear absolutamente nada."""
    if pd.isna(valor) or valor is None: return "0.00"
    s = f"{float(valor):.10f}" 
    entero, decimal = s.split('.')
    return f"{entero}.{decimal[:2]}"

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

# 4. INTERFAZ
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada", "📋 Auditoría y Reportes"])

# --- TAB 1: REGISTRO ---
with tab_calc:
    st.title("⚖️ Registro de Pesaje")
    
    col_mode1, col_mode2 = st.columns(2)
    with col_mode1:
        nuevo_art = st.toggle("Modo: Artículo NO listado", value=False)
    with col_mode2:
        modo_preconteo = st.toggle("Modo: PRE-CONTEO MANUAL (Piezas directas)", value=False)
    
    with st.form(key="form_pesaje", clear_on_submit=True):
        if not nuevo_art:
            art_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()), index=None, placeholder="Elija un producto...")
            pue_final = productos.get(art_sel, 1.0)
        else:
            c_n1, c_n2 = st.columns([2,1])
            with c_n1:
                art_sel = st.text_input("Nombre del Nuevo Artículo:", value=None, placeholder="Ej. CAJA PERSONALIZADA")
            with c_n2:
                pue_final = st.number_input("Asignar PUE:", value=None, format="%.4f", placeholder="0.0000")

        st.divider()

        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas (Conteo manual):", value=None, step=1.0, placeholder="Ej. 50")
            peso_bruto, tara_total, formula = 0.0, 0.0, "CONTEO MANUAL DIRECTO"
        else:
            peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=None, format="%.3f", placeholder="0.000")
            with st.expander("🛠️ Configuración de Taras", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1: t_cont = st.checkbox("Contenedor (0.016)")
                with c2: t_bis = st.checkbox("Bisagra (0.045)")
                with c3: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f", placeholder="0.000")
        
        btn_save = st.form_submit_button("📥 GUARDAR REGISTRO")

    if btn_save:
        articulo_valido = art_sel is not None
        pue_valido = pue_final is not None
        
        if modo_preconteo:
            datos_listos = articulo_valido and cantidad_directa is not None
            resultado = truncar_dos_decimales(cantidad_directa) if datos_listos else 0
        else:
            datos_listos = articulo_valido and peso_bruto is not None and pue_valido
            if datos_listos:
                tm = t_manual if t_manual is not None else 0.0
                tara_total = (0.016 if t_cont else 0) + (0.045 if t_bis else 0) + tm
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
            st.error("❌ Error: Faltan datos críticos para el registro.")

# --- TAB 2: AUDITORÍA ---
with tab_historial:
    st.title("📋 Consolidación de Auditoría")
    df = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    
    if not df.empty:
        # 1. SECCIÓN DE RESULTADOS VISUALES (ARRIBA)
        art_filtro = st.selectbox("Seleccione el Artículo a Consultar:", sorted(df['articulo'].unique()), index=None, placeholder="Seleccione para ver desglose...")
        
        msg_reporte = "" 
        stock_teorico = None
        
        if art_filtro:
            df_art = df[df['articulo'] == art_filtro]
            total_real = truncar_dos_decimales(df_art['resultado_pue'].sum())
            
            st.subheader(f"Resultados de: {art_filtro}")
            st.table(df_art[['fecha_hora', 'peso_bruto', 'tara', 'pue', 'detalle_formula', 'resultado_pue']].rename(columns={
                'fecha_hora': 'Fecha/Hora', 'peso_bruto': 'P. Bruto', 'tara': 'Tara Total', 'pue': 'PUE Usado', 'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad/Resultado'
            }))
            
            st.divider()
            c_res1, c_res2, c_res3 = st.columns(3)
            with c_res1:
                st.metric("TOTAL (PESAJE + PRECONTEO)", formato_estricto(total_real))
            with c_res2:
                stock_teorico = st.number_input("Valor en Sistema (Stock):", value=None, placeholder="Ingrese stock...")
            
            if stock_teorico is not None:
                diferencia = truncar_dos_decimales(total_real - stock_teorico)
                with c_res3:
                    st.metric("DIFERENCIA", formato_estricto(diferencia), delta=round(diferencia, 2), delta_color="inverse")
                
                desglose_txt = "\n".join([f"• {f} = {formato_estricto(r)}" for f, r in zip(df_art['detalle_formula'], df_art['resultado_pue'])])
                msg_reporte = (f"*REPORTE DE AUDITORÍA PUE*\n"
                               f"------------------------------\n"
                               f"*Producto:* {art_filtro}\n"
                               f"*Total Acumulado:* {formato_estricto(total_real)}\n"
                               f"*Stock Sistema:* {formato_estricto(stock_teorico)}\n"
                               f"*Diferencia:* {formato_estricto(diferencia)}\n"
                               f"------------------------------\n"
                               f"*OPERACIONES Y PRECONTEOS:*\n{desglose_txt}")

        st.divider()
        
        # 2. SECCIÓN DE CSV FÍSICO Y EXCEL ESTRUCTURADO (EN MEDIO)
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            st.subheader("🖨️ Archivo CSV (Solo para Tarjetas)")
            df_impresion = df[['articulo', 'resultado_pue']].copy()
            df_impresion['resultado_pue'] = df_impresion['resultado_pue'].apply(formato_estricto)
            csv_data = df_impresion.to_csv(index=False)
            mensaje_csv = "📊 *CSV Generado para Impresión*\n\n" + csv_data
            
            st.download_button(
                label="⬇️ Descargar CSV para Tarjetas",
                data=csv_data,
                file_name="tarjetas_impresion_pue.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with col_export2:
            st.subheader("📊 Reporte Excel Oficial")
            sucursal_in = st.text_input("Sucursal:", value="COSTA VERDE")
            elabora_in = st.text_input("Elabora / Vendedor:", value="PEDRO GARCÍA")
            
            # Preparar Excel en memoria
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_empty = pd.DataFrame()
                df_empty.to_excel(writer, sheet_name='Baja de insumos', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Baja de insumos']
                
                # Formatos de celdas
                format_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#8B0000', 'font_color': 'white', 'font_size': 12, 'border': 1})
                format_subtitle = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11, 'border': 1})
                format_label = workbook.add_format({'bold': True, 'border': 1})
                format_data = workbook.add_format({'border': 1})
                format_header = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#f2f2f2'})
                format_center = workbook.add_format({'align': 'center', 'border': 1})
                
                # Encabezados
                worksheet.merge_range('A1:D1', 'PASTELERÍA CHAMPLITTE, S.A. DE C.V.', format_title)
                worksheet.merge_range('A2:D2', 'BAJA DE INSUMOS', format_subtitle)
                
                fecha_hoy = datetime.now(pytz.timezone('America/Mexico_City')).strftime("%d/%m/%Y")
                worksheet.write('A3', 'SUCURSAL', format_label)
                worksheet.merge_range('B3:D3', sucursal_in, format_data)
                
                worksheet.write('A4', 'FECHA', format_label)
                worksheet.merge_range('B4:D4', fecha_hoy, format_data)
                
                worksheet.write('A5', 'ELABORA', format_label)
                worksheet.merge_range('B5:D5', elabora_in, format_data)
                
                # Cambio en el nombre de la columna
                headers_excel = ['DESCRIPCIÓN', 'CANTIDAD', 'CÁLCULOS REALIZADOS', 'VENDEDOR']
                for col_num, data in enumerate(headers_excel):
                    worksheet.write(5, col_num, data, format_header)
                    
                # Llenar datos desglosados (ahora integrando detalle_formula)
                row = 6
                for index, row_data in df.iterrows():
                    worksheet.write(row, 0, row_data['articulo'], format_data)
                    worksheet.write(row, 1, float(formato_estricto(row_data['resultado_pue'])), format_center)
                    worksheet.write(row, 2, row_data['detalle_formula'], format_center) 
                    worksheet.write(row, 3, elabora_in, format_data)
                    row += 1
                    
                # Ajustar columnas
                worksheet.set_column('A:A', 35)
                worksheet.set_column('B:B', 15)
                worksheet.set_column('C:C', 45) # Se hizo más ancha para que quepa bien la fórmula
                worksheet.set_column('D:D', 20)

            output.seek(0)
            
            st.download_button(
                label="⬇️ Descargar Excel Formato Oficial",
                data=output,
                file_name="Reporte_Baja_Insumos_Champlitte.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.divider()
        
        # 3. SECCIÓN DE WHATSAPP (HASTA ABAJO)
        st.subheader("📞 Configuración y Envíos a WhatsApp")
        numero_wa = st.text_input("Número destino (Incluir código de país, ej. 52 para México):", value="522283530069")
        
        col_wa1, col_wa2 = st.columns(2)
        with col_wa1:
            if art_filtro and stock_teorico is not None:
                url_wa = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(msg_reporte)}"
                st.markdown(f'<a href="{url_wa}" target="_blank" class="btn-wa">📲 ENVIAR REPORTE DE ESTE ARTÍCULO</a>', unsafe_allow_html=True)
            else:
                st.info("📌 Selecciona un artículo e ingresa el stock arriba para habilitar el reporte de auditoría.")
                
        with col_wa2:
            url_wa_csv = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(mensaje_csv)}"
            st.markdown(f'<a href="{url_wa_csv}" target="_blank" class="btn-wa" style="margin: 0px;">📲 ENVIAR CSV COMPLETO</a>', unsafe_allow_html=True)
            
        st.divider()
        
        # 4. ADMINISTRACIÓN DE BASE DE DATOS
        with st.expander("🗑️ Administración de Base de Datos"):
            st.dataframe(df, use_container_width=True)
            
            st.markdown("#### Eliminar Registro Individual")
            c_del1, c_del2 = st.columns([1, 2])
            with c_del1:
                id_a_eliminar = st.number_input("Ingresa el ID a eliminar:", min_value=1, step=1)
            with c_del2:
                st.write("") 
                st.write("")
                if st.button("ELIMINAR ESTE ID"):
                    c.execute("DELETE FROM pesajes_individuales WHERE id = ?", (id_a_eliminar,))
                    conn.commit()
                    st.success(f"ID {id_a_eliminar} eliminado.")
                    st.rerun()
            
            st.divider()
            
            if st.button("LIMPIAR TODA LA BASE DE DATOS"):
                c.execute("DELETE FROM pesajes_individuales")
                conn.commit()
                st.rerun()
    else:
        st.info("No hay pesajes registrados aún.")
