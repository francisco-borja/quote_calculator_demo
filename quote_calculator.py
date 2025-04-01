# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 11:16:59 2024

@author: franc
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import base64
from fpdf import FPDF
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

#Cargar la imagen del logo

# Cargar la imagen del logo
logo_path = "Logo JPG Blanco - Scalesia Lodge.jpg"

logo = Image.open(logo_path)

# Convertir la imagen a base64
with open(logo_path, "rb") as img_file:
    logo_base64 = base64.b64encode(img_file.read()).decode()

# Configuración de la página
st.set_page_config(page_title="Scalesia Lodge Quote Calculator", layout="centered",
                   
    )

# Estilos personalizados con los colores proporcionados y para centrar la imagen
st.markdown(
    f"""
    <style>
    /* Colores */
    .dark-green-bg {{
        background-color: rgba(76, 140, 43, 0.9); /* SCALESIA VERDE OSCURO 90% */
        color: white;
    }}
    .dark-green-bg-light {{
        background-color: rgba(76, 140, 43, 0.4); /* SCALESIA VERDE OSCURO 40% */
    }}
    .light-green-bg {{
        background-color: rgba(76, 140, 43, 0.7); /* SCALESIA VERDE CLARO 70% */
    }}
    .light-green-bg-lighter {{
        background-color: rgba(76, 140, 43, 0.5); /* SCALESIA VERDE CLARO 50% */
    }}
    .celeste-bg {{
        background-color: #64ccc9; /* SCALESIA CELESTE 100% */
    }}
    
    /* Botón de cotización */
    .stButton > button {{
        background-color: rgba(76, 140, 43, 0.7); /* Verde claro para botón */
        color: white;
        border-radius: 5px;
        border: 2px solid #64ccc9; /* Detalle celeste */
    }}
    .stButton > button:hover {{
        background-color: rgba(76, 140, 43, 0.5); /* Verde claro 50% en hover */
        border: 2px solid #4c8c2b; /* Verde oscuro en hover */
    }}

    /* Título en verde oscuro */
    .title {{
        font-size: 2.5em;
        color: rgba(76, 140, 43, 0.9); /* Verde oscuro */
        text-align: center;
        margin-bottom: 20px;
    }}

    /* Contenedor principal */
    .main-container {{
        padding: 10px;
        background-color: rgba(76, 140, 43, 0.4); /* Verde oscuro 40% */
        border-radius: 10px;
        border: 3px solid #64ccc9; /* Detalle celeste */
    }}

    /* Textos y selectores */
    .stTextInput label, .stSelectbox label {{
        color: rgba(76, 140, 43, 0.9); /* Verde oscuro */
        font-weight: bold;
    }}

    /* Bordes de tablas y inputs */
    .stDataFrame, .stMultiselect {{
        border: 2px solid rgba(76, 140, 43, 0.9); /* Bordes en verde oscuro */
    }}

    /* Imagen centrada y tamaño ajustado */
    .logo {{
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 40%; /* Ajusta el tamaño de la imagen, puedes modificar este valor para hacerla más grande o más pequeña */
    }}
    /* Color personalizado para los selectores de servicios */
    [data-baseweb="select"] {{
        background-color: #4c8c2b; /* Verde Scalesia */
        color: white; /* Texto blanco */
    }}
    [data-baseweb="select"]::placeholder {{
        color: white; /* Placeholder blanco */
    }}
    .stSelectbox > div > div {{
        color: white; /* Texto blanco en los selectores */
    
    }}
    
    
    </style>

    <!-- Mostrar el logo centrado -->
    <div>
        <img src="data:image/jpg;base64,{logo_base64}" class="logo">
    </div>
    
    
    """,
    unsafe_allow_html=True
)


# Función para manejar excepciones y conectar a Google Sheets
@st.cache_data(show_spinner=True)
def load_data_from_google_sheets(sheet_url, sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('famous-dialect-433116-n5-ca129ce868dc.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
        data = pd.DataFrame(sheet.get_all_records())
        return data
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame()  # Retornar un DataFrame vacío en caso de error
    
    

## Función genérica para calcular costos con servicios detallados

def calcular_costo(servicio, num_people, df_costos):
    # Filtrar el servicio seleccionado en el DataFrame de costos
    servicios_seleccionados = df_costos[df_costos["Lista Seleccionables"] == servicio]

    # Obtener servicios detallados únicos (para evitar iteraciones duplicadas)
    servicios_detallados_unicos = servicios_seleccionados["Descripción Servicio Detalle (para valor costo)"].unique()

    costo_total = 0  # Inicializar el costo total
    tipo_costo_final = None  # Para almacenar el tipo de costo final
    valor_costo_original_final = 0  # Para almacenar el valor original del costo

    # Iterar sobre los servicios detallados únicos que forman parte del servicio seleccionado
    for detalle_servicio in servicios_detallados_unicos:
        # Filtrar los costos correspondientes a ese servicio detallado
        costos_servicio = df_costos[df_costos["Descripción Servicio Detalle (para valor costo)"] == detalle_servicio]

        if not costos_servicio.empty:
            # Convertir los valores "N/A" o no numéricos a NaN en los límites de personas
            costos_servicio["Límite Mínimo Personas"] = pd.to_numeric(costos_servicio["Límite Mínimo Personas"], errors='coerce')
            costos_servicio["Límite Máximo Personas"] = pd.to_numeric(costos_servicio["Límite Máximo Personas"], errors='coerce')

            # Asegurarnos de que los valores de "Valor Costo" estén en formato flotante
            if "Valor Costo" in costos_servicio.columns:
                costos_servicio["Valor Costo"] = costos_servicio["Valor Costo"].astype(float)

            # Filtrar los rangos que aplican al número de personas (si existen rangos)
            costos_rango = costos_servicio[
                (costos_servicio["Límite Mínimo Personas"] <= num_people) &
                (costos_servicio["Límite Máximo Personas"] >= num_people)
            ]

            if not costos_rango.empty:
                # Si hay un rango adecuado, proceder con el cálculo
                tipo_costo = costos_rango["Costo por persona o Grupo"].iloc[0]
                valor_costo_original = costos_rango["Valor Costo"].iloc[0]

                if tipo_costo == "P/P":
                    # Para P/P, multiplicar por el número de personas
                    costo_final = valor_costo_original * num_people
                elif tipo_costo == "P/G":
                    # Para P/G, tomar el costo directamente
                    costo_final = valor_costo_original

                # Sumar el costo final al total
                costo_total += costo_final
                tipo_costo_final = tipo_costo
                valor_costo_original_final = valor_costo_original

            else:
                # Si no hay rangos, tomar el valor del costo directamente
                tipo_costo = costos_servicio["Costo por persona o Grupo"].iloc[0]
                valor_costo_original = costos_servicio["Valor Costo"].iloc[0]

                if tipo_costo == "P/P":
                    # Para P/P, multiplicar por el número de personas
                    costo_final = valor_costo_original * num_people
                elif tipo_costo == "P/G":
                    # Para P/G, tomar el costo directamente
                    costo_final = valor_costo_original

                # Sumar el costo final al total
                costo_total += costo_final
                tipo_costo_final = tipo_costo
                valor_costo_original_final = valor_costo_original

    # Devolver el costo total, tipo de costo, y el valor original para el servicio seleccionado
    return costo_total, tipo_costo_final, valor_costo_original_final

# Función para generar un PDF con las tablas de cotización


# Función para generar el PDF (modificada para incluir todos los días)
def generar_pdf(day_services_df_list, hotel_cost_df, total_df, num_people, num_nights):
    buffer = BytesIO()  # Crear un buffer en memoria para guardar el PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título del PDF
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Scalesia Lodge Quote Calculator - Quotation")

    y_position = height - 100

    # Iterar sobre los resultados diarios
    c.setFont("Helvetica", 12)
    for i, (day_services_df, day) in enumerate(day_services_df_list):
        c.drawString(100, y_position, f"Day {i+1}: {day.strftime('%A, %d %B %Y')} Services:")
        y_position -= 20

        for idx, row in day_services_df.iterrows():
            c.drawString(100, y_position, f"- {row['Service']} (Cost: ${row['Final Cost']})")
            y_position -= 20

            # Verificar si queda suficiente espacio en la página, si no, añadir una nueva página
            if y_position < 100:
                c.showPage()
                y_position = height - 100

        y_position -= 10  # Espacio adicional entre días

    # Agregar el costo del hotel
    c.drawString(100, y_position, "Isabela Hotel Cost:")
    y_position -= 20
    c.drawString(100, y_position, f"- {hotel_cost_df.iloc[0]['Description']}, cost per person and night: ${hotel_cost_df.iloc[0]['Cost per person']} (Total Cost: ${hotel_cost_df.iloc[0]['Group Cost']})")
    y_position -= 30

    # Agregar el costo total
    c.drawString(100, y_position, "Total Quotation:")
    y_position -= 20
    c.drawString(100, y_position, f"- Group Total: ${total_df.iloc[0]['Group Total Cost']}")
    c.drawString(100, y_position - 20, f"- Cost per Person: ${total_df.iloc[0]['Total Cost per person']}")

    # Finalizar el PDF
    c.showPage()
    c.save()

    # Obtener el contenido del buffer en memoria
    buffer.seek(0)
    return buffer
####Funciones de cálcudo de cada seleccionable######

# Función específica para "Emetebe OW Baltra / Isabela"
def calcular_costo_emetebe(num_people, df_costos):
    servicio = "Emetebe OW Baltra / Isabela"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Emetebe RT Baltra / Isabela"
def calcular_costo_emetebe_rt(num_people, df_costos):
    servicio = "Emetebe RT Baltra / Isabela"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Emetebe RT Baltra / Isabela"
def calcular_costo_charter_emetebe(num_people, df_costos):
    servicio = "Charter Emetebe OW Baltra / Isabela"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Charter Emetebe RT Baltra / Isabela"
def calcular_costo_charter_emetebe_rt(num_people, df_costos):
    servicio = "Charter Emetebe RT Baltra / Isabela"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para "Avianca OW UIO / Baltra"
def calcular_costo_avianca_ow_uio_baltra(num_people, df_costos):
    servicio = "Avianca OW UIO / Baltra"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para "Avianca OW GYE / Baltra"
def calcular_costo_avianca_ow_gye_baltra(num_people, df_costos):
    servicio = "Avianca OW GYE / Baltra"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para "Avianca RT UIO o GYE / Baltra"
def calcular_costo_avianca_rt_uio_gye_baltra(num_people, df_costos):
    servicio = "Avianca RT UIO o GYE / Baltra"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Speedboat OW Pto. Ayora / Pto. Villamil"
def calcular_costo_speedboat_ow(num_people, df_costos):
    servicio = "Charter Speedboat OW Pto. Ayora / Pto. Villamil"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Speedboat RT Pto. Ayora / Pto. Villamil"
def calcular_costo_speedboat_rt(num_people, df_costos):
    servicio = "Charter Speedboat RT  Pto. Ayora / Pto. Villamil"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Water taxi Isabela OW"
def calcular_costo_charter_water_taxi_isabela(num_people, df_costos):
    servicio = "Charter Water taxi Isabela OW"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Charter Water Taxi - Itabaca Channel Small"
def calcular_costo_water_taxi_small(num_people, df_costos):
    servicio = "Charter Water taxi - Itabaca Channel Small"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Water Taxi - Itabaca Channel Big"
def calcular_costo_water_taxi_big(num_people, df_costos):
    servicio = "Charter Water taxi - Itabaca Channel Big"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Ferry Pto Ayora - Pto. Villamil OW"
def calcular_costo_ferry_ow(num_people, df_costos):
    servicio = "Ferry Pto Ayora - Pto. Villamil OW"
    return calcular_costo(servicio, num_people, df_costos)
def calcular_costo_ferry_rt(num_people, df_costos):
    servicio = "Ferry Pto Ayora - Pto. Villamil RT"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Transfer-in Isabela
def calcular_costo_transfer_in_isabela(num_people, df_costos):
    servicio = "Transfer-in Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-in Starting in Santa Cruz
def calcular_costo_transfer_in_santa_cruz(num_people, df_costos):
    servicio = "Transfer-in Starting in Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-out Isabela
def calcular_costo_transfer_out_isabela(num_people, df_costos):
    servicio = "Transfer-out Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-out Santa Cruz
def calcular_costo_transfer_out_santa_cruz(num_people, df_costos):
    servicio = "Transfer-out Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Tintoreras Walk & Snorkel Tour
def calcular_costo_tintoreras_walk_snorkel(num_people, df_costos):
    servicio = "Tintoreras Walk & Snorkel Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Private Tintoreras Walk & Snorkel Tour Charter
def calcular_costo_private_tintoreras_walk_snorkel(num_people, df_costos):
    servicio = "Private Tintoreras Walk & Snorkel Tour Charter"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Private Tintoreras Walk & Snorkel Tour Charter
def calcular_costo_private_tuneles_walk_snorkel(num_people, df_costos):
    servicio = "Private Túneles Walk & Snorkel Tour Charter"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Túneles Walk & Snorkel Tour
def calcular_costo_tuneles_walk_snorkel(num_people, df_costos):
    servicio = "Túneles Walk & Snorkel Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Sierra Negra & Chico Volcanoes
def calcular_costo_sierra_negra_chico_volcanoes(num_people, df_costos):
    servicio = "Sierra Negra & Chico Volcanoes"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Wall of Tears Trekking or biking Tour
def calcular_costo_wall_of_tears(num_people, df_costos):
    servicio = "Wall of Tears Trekking or biking Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Wetlands & Tortoise Breeding Station
def calcular_costo_wetlands_tortoise_breeding_station(num_people, df_costos):
    servicio = "Wetlands & Tortoise Breeding Station"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Sucre's Cave, El Mango Viewpoint & Beach time
def calcular_costo_sucres_cave(num_people, df_costos):
    servicio = "Sucre's Cave, El Mango Viewpoint & Beach time"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Concha de Perla Snorkel Tour + Beach Time
def calcular_costo_concha_de_perla(num_people, df_costos):
    servicio = "Concha de Perla Snorkel Tour + Beach Time"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Kayaking in Tintoreras
def calcular_costo_kayaking_in_tintoreras(num_people, df_costos):
    servicio = "Kayaking in Tintoreras"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Sulfur Mines Tour
def calcular_costo_sulfur_mines(num_people, df_costos):
    servicio = "Sulfur Mines Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Private Cuatro Hermanos Snorkeling & Fishing Tour + Tortuga Island
def calcular_costo_cuatro_hermanos(num_people, df_costos):
    servicio = "Private Cuatro Hermanos Snorkeling & Fishing Tour + Tortuga Island"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Scuba Diving Isabela
def calcular_costo_scuba_diving_isabela(num_people, df_costos):
    servicio = "Scuba Diving Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Surf Isabela-Half Day	
def calcular_costo_surf_isabela_half_day(num_people, df_costos):
    servicio = "Surf Isabela-Half Day"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Surf Isabela-Whole Day
def calcular_costo_surf_isabela_whole_day(num_people, df_costos):
    servicio = "Surf Isabela-Whole Day"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Santa Cruz Highlands Tour
def calcular_costo_santa_cruz_highlands(num_people, df_costos):
    servicio = "Santa Cruz Highlands Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Full-day Yatch Tour
def calcular_costo_full_day_yatch(num_people, df_costos):
    servicio = "Full-day Yacht Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Bahia Divine + Charles Darwin Station
def calcular_costo_bahia_divine(num_people, df_costos):
    servicio = "Bahia Divine + Charles Darwin Station"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Scuba Diving Finch Bay Hotel
def calcular_costo_scuba_diving_finch_bay(num_people, df_costos):
    servicio = "Scuba Diving Finch Bay Hotel"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Scuba Diving Finch Bay Hotel
def calcular_costo_scuba_diving_santa_cruz(num_people, df_costos):
    servicio = "Scuba Diving Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Guide Isabela in English
def calcular_costo_guide_isabela_english(num_people, df_costos):
    servicio = "Guide Isabela in English"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Guide Isabela in German
def calcular_costo_guide_isabela_german(num_people, df_costos):
    servicio = "Guide Isabela in German"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Guide Santa Cruz in English
def calcular_costo_guide_santa_cruz_english(num_people, df_costos):
    servicio = "Guide Santa Cruz in English"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Guide Santa Cruz in German
def calcular_costo_guide_santa_cruz_german(num_people, df_costos):
    servicio = "Guide Santa Cruz in German"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Guide Santa Cruz in German
def calcular_costo_guide_santa_cruz_accomodations(num_people, df_costos):
    servicio = "Guide Santa Cruz accommodations"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Guide Santa Cruz in German
def calcular_costo_guide_santa_cruz_breakfast(num_people, df_costos):
    servicio = "Guide Santa Cruz breakfast"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Guide Santa Cruz in German
def calcular_costo_guide_santa_cruz_lunch(num_people, df_costos):
    servicio = "Guide Santa Cruz lunch"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Guide Santa Cruz in German
def calcular_costo_guide_santa_cruz_dinner(num_people, df_costos):
    servicio = "Guide Santa Cruz dinner"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Guide Transfer in/out (Isabela / Santa Cruz)
def calcular_costo_guide_transfer_in_out(num_people, df_costos):
    servicio = "Guide Transfer in/out (Isabela / Santa Cruz)"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Luggage transport Isabela
def calcular_costo_luggage_transport_isabela(num_people, df_costos):
    servicio = "Luggage transport Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Bilingual airport assistant Santa Cruz
def calcular_costo_bilingual_assistant_santa_cruz(num_people, df_costos):
    servicio = "Bilingual airport assistant Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Luggage transport Santa Cruz
def calcular_costo_luggage_transport_santa_cruz(num_people, df_costos):
    servicio = "Luggage transport Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Lunch Pto. Villamil Isabela
def calcular_costo_lunch_pto_villamil(num_people, df_costos):
    servicio = "Lunch Pto. Villamil Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Dinner Pto. Ayora Santa Cruz
def calcular_costo_dinner_pto_ayora(num_people, df_costos):
    servicio = "Dinner Pto. Ayora Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Lunch Santa Cruz "Narval"
def calcular_costo_lunch_santa_cruz_narval(num_people, df_costos):
    servicio = "Lunch Santa Cruz Narval"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Finch Bay Hotel 4D/3N DBL / TPL Program 2025
def calcular_costo_finch_bay_4d3n_dbl_tpl(num_people, df_costos):
    servicio = "Finch Bay Hotel 4D-3N DBL-TPL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 4D/3N SGL Program 2025
def calcular_costo_finch_bay_4d3n_sgl(num_people, df_costos):
    servicio = "Finch Bay Hotel 4D/3N SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 4D/3N Suite DBL Program 2025
def calcular_costo_finch_bay_4d3n_suite_dbl(num_people, df_costos):
    servicio = "Finch Bay Hotel 4D/3N Suite DBL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 4D/3N Suite SGL Program 2025
def calcular_costo_finch_bay_4d3n_suite_sgl(num_people, df_costos):
    servicio = "Finch Bay Hotel 4D/3N Suite SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 5D/4N DBL / TPL Program 2025
def calcular_costo_finch_bay_5d4n_dbl_tpl(num_people, df_costos):
    servicio = "Finch Bay Hotel 5D/4N DBL / TPL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 5D/4N SGL Program 2025
def calcular_costo_finch_bay_5d4n_sgl(num_people, df_costos):
    servicio = "Finch Bay Hotel 5D/4N SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 5D/4N Suite DBL Program 2025
def calcular_costo_finch_bay_5d4n_suite_dbl(num_people, df_costos):
    servicio = "Finch Bay Hotel 5D/4N Suite DBL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel 5D/4N Suite SGL Program 2025
def calcular_costo_finch_bay_5d4n_suite_sgl(num_people, df_costos):
    servicio = "Finch Bay Hotel 5D/4N Suite SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 4D/3N DBL / TPL Program 2025
def calcular_costo_angermeyer_4d3n_dbl_tpl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 4D/3N DBL / TPL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 4D/3N SGL Program 2025
def calcular_costo_angermeyer_4d3n_sgl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 4D/3N SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 4D/3N Suite DBL Program 2025
def calcular_costo_angermeyer_4d3n_suite_dbl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 4D/3N Suite DBL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 4D/3N Suite SGL Program 2025
def calcular_costo_angermeyer_4d3n_suite_sgl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 4D/3N Suite SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 3D/2N DBL / TPL Program 2025
def calcular_costo_angermeyer_3d2n_dbl_tpl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 3D/2N DBL / TPL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 3D/2N SGL Program 2025
def calcular_costo_angermeyer_3d2n_sgl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 3D/2N SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 3D/2N Suite DBL Program 2025
def calcular_costo_angermeyer_3d2n_suite_dbl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 3D/2N Suite DBL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Waterfront Inn 3D/2N Suite SGL Program 2025
def calcular_costo_angermeyer_3d2n_suite_sgl(num_people, df_costos):
    servicio = "Angermeyer Waterfront Inn 3D/2N Suite SGL Program 2025"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Standard DBL with breakfast
def calcular_costo_angermeyer_standard_dbl_breakfast(num_people, df_costos):
    servicio = "Angermeyer Standard DBL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Angermeyer Standard SGL with breakfast
def calcular_costo_angermeyer_standard_sgl_breakfast(num_people, df_costos):
    servicio = "Angermeyer Standard SGL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Standard DBL with breakfast
def calcular_costo_finch_bay_standard_dbl_breakfast(num_people, df_costos):
    servicio = "Finch Bay Hotel Standard DBL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Standard SGL with breakfast
def calcular_costo_finch_bay_standard_sgl_breakfast(num_people, df_costos):
    servicio = "Finch Bay Hotel Standard SGL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Suite DBL with breakfast
def calcular_costo_finch_bay_suite_dbl_breakfast(num_people, df_costos):
    servicio = "Finch Bay Hotel Suite DBL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Suite SGL with breakfast
def calcular_costo_finch_bay_suite_sgl_breakfast(num_people, df_costos):
    servicio = "Finch Bay Hotel Suite SGL with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Suite Additional adult with breakfast
def calcular_costo_finch_bay_suite_additional_adult(num_people, df_costos):
    servicio = "Finch Bay Hotel Suite Additional adult with breakfast"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Suite Additional adult with breakfast
def calcular_costo_free_time_at_the_beach(num_people, df_costos):
    servicio = "Free Time at the Beach - Isabela"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Finch Bay Hotel Suite Additional adult with breakfast
def calcular_costo_baltra_airport_assistance_continental_flight(num_people, df_costos):
    servicio = "Baltra Airport Assistance | Continental Flight - Inter Island Flight (without transfer assistance)"
    return calcular_costo(servicio, num_people, df_costos)



# Cargar datos desde Google Sheets (se ejecuta solo una vez por sesión)
sheet_url = "https://docs.google.com/spreadsheets/d/1R_1AuEU2x08ugevXYWH9ezgnW1XuTI2fRTnbwcKZINU/edit?gid=0#gid=0"
sheet_name_seleccionables = "Lista de Seleccionables"
sheet_name_costos_persona_grupo = "Costos Por persona y Por Grupo"

lista_seleccionables = load_data_from_google_sheets(sheet_url, sheet_name_seleccionables)
cost_data_persona_grupo = load_data_from_google_sheets(sheet_url, sheet_name_costos_persona_grupo)

# Mostrar el logo en la interfaz

#st.image(logo, use_column_width=False, width=300)  # Ajusta el ancho según tus preferencias
# Título de la aplicación
st.markdown("<div class='title'>Scalesia Lodge Quote Calculator</div>", unsafe_allow_html=True)

# Ingreso de la cantidad de personas
num_people = st.number_input("Number of Pax", min_value=1, value=1)

# Selección de fechas
start_date = st.date_input("Select start date", value=datetime.today())
end_date = st.date_input("Select end date", value=datetime.today() + timedelta(days=1))

# Calcular el número de noches
if start_date and end_date:
    num_nights = (end_date - start_date).days
    if num_nights <= 0:
        st.error("End date must be after start date.")
    else:
        st.write(f"Total Number of nights: {num_nights}")

# Nuevos inputs: Número de noches y costo por noche hotel Isabela
num_nights_isabela = st.number_input("Number of nights at Isabela Hotel", min_value=0, value=0, step=1)
cost_per_night_isabela = st.number_input("Cost per night and person at Isabela Hotel (USD)", min_value=0.0, value=0.0, step=0.01)


# Input: Casilla para incluir o excluir servicios de la Isla Santa Cruz
include_santa_cruz = st.checkbox("Includes Santa Cruz Island")

# Filtrar la lista_seleccionables según el checkbox
if include_santa_cruz:
    filtered_lista_seleccionables = lista_seleccionables
else:
    filtered_lista_seleccionables = lista_seleccionables[lista_seleccionables['Categoría/Isla'] != 'SANTA CRUZ']

# Filtrar por 'Que aparezca como seleccionable (Lista Seleccionable)'
filtered_lista_seleccionables = filtered_lista_seleccionables[filtered_lista_seleccionables['Que aparezca como seleccionable (Lista Seleccionable)'] == "TRUE"]

# Filtrar y organizar los servicios en variables según las categorías
water_transportation = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Water transportation']['Lista Seleccionables'].unique().tolist()
ground_transportation = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Ground transportation']['Lista Seleccionables'].unique().tolist()
tickets_2024 = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Tickets 2024']['Lista Seleccionables'].unique().tolist()
tours = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Tours']['Lista Seleccionables'].unique().tolist()
guide = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Guide']['Lista Seleccionables'].unique().tolist()
airport_assistance = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Airport Assistance']['Lista Seleccionables'].unique().tolist()
meals = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Meals']['Lista Seleccionables'].unique().tolist()
accommodations_santa_cruz = filtered_lista_seleccionables[filtered_lista_seleccionables['Tipo Servicio General'] == 'Accommodations Santa Cruz']['Lista Seleccionables'].unique().tolist()


if start_date and end_date:
    num_nights = (end_date - start_date).days
    if num_nights <= 0:
        st.error("End date must be after start date.")
    else:
               
        st.write("Select costs and services for each day")
        
        # Crear columnas dinámicamente según la cantidad de noches
        columns = st.columns(num_nights)
        
        # Listas para almacenar las selecciones por cada día
        selected_water_transportation = []
        selected_ground_transportation = []
        selected_tickets = []
        selected_tours = []
        selected_guide = []
        selected_airport_assistance = []
        selected_meals = []
        selected_accommodations = []
        
        # Iterar sobre cada día y mostrar los selectores
        for i in range(num_nights+1):
            day = start_date + timedelta(days=i)
            st.write(f"### Day {i+1}: {day.strftime('%A, %d %B %Y')}")
            
            # Selector de water_transportation
            water_transport = st.multiselect(
                f"Water transportation for day {i+1}", 
                water_transportation,
                key=f"water_{i}",
                help="Select water transportation",
            )
            selected_water_transportation.append(water_transport)
            
            # Selector de ground_transportation
            ground_transport = st.multiselect(
                f"Ground transportation for day {i+1}", 
                ground_transportation,
                key=f"ground_{i}",
                help="Select ground transportation",
            )
            selected_ground_transportation.append(ground_transport)
            
            # Selector de tickets_2024
            tickets = st.multiselect(
                f"Tickets for day {i+1}", 
                tickets_2024,
                key=f"tickets_{i}",
                help="Select tickets",
            )
            selected_tickets.append(tickets)
            
            # Selector de tours
            tour = st.multiselect(
                f"Tours for day {i+1}", 
                tours,
                key=f"tour_{i}",
                help="Select tours",
            )
            selected_tours.append(tour)
            
            # Selector de guide
            guide_selected = st.multiselect(
                f"Guide for day {i+1}", 
                guide,
                key=f"guide_{i}",
                help="Select guide",
            )
            selected_guide.append(guide_selected)
            
            # Selector de airport_assistance
            airport = st.multiselect(
                f"Airport assistance for day {i+1}", 
                airport_assistance,
                key=f"airport_{i}",
                help="Select airport assistance",
            )
            selected_airport_assistance.append(airport)
            
            # Selector de meals
            meal = st.multiselect(
                f"Meals for day {i+1}", 
                meals,
                key=f"meals_{i}",
                help="Select meals",
            )
            selected_meals.append(meal)
            
            # Selector de accommodations_santa_cruz
            accommodation = st.multiselect(
                f"Accommodations in Santa Cruz for day {i+1}", 
                accommodations_santa_cruz,
                key=f"accommodation_{i}",
                help="Select accommodations in Santa Cruz",
            )
            selected_accommodations.append(accommodation)
  
 
        # Botón para calcular cotización
        if st.button("Calculate Quote"):
            total_quotation_value = 0  # Valor total por ahora 0
            valid_selection = True  # Variable para verificar si la selección es válida
            servicios_tours_seleccionados_global = []  #Lista global para rastrear servicios seleccionados en diferentes días
            day_services_df_list = []  # Lista para almacenar servicios por cada día
            # Inicializar variables globales para el seguimiento de servicios seleccionados
            excluded_services_selected_global = False  # Para rastrear si se ha seleccionado algún servicio excluido en cualquier día
            other_accommodations_selected_global = False  # Para rastrear si se ha seleccionado otros servicios de 'Accommodations Santa Cruz' en cualquier día
            
            for i in range(num_nights+1):
                day_total = 0
                st.write(f"### Day {i+1}: {start_date + timedelta(days=i):%A, %d %B %Y}")

                # Recopilar todos los servicios seleccionados en una tabla
                day_services = []
                # Listas de servicios para validación
                servicios_emetebe = [
                    "Emetebe OW Baltra / Isabela",
                    "Emetebe RT Baltra / Isabela",
                    "Charter Emetebe OW Baltra / Isabela",
                    "Charter Emetebe RT Baltra / Isabela"
                ]
                servicios_avianca = [
                       "Avianca OW UIO / Baltra",
                       "Avianca OW GYE / Baltra",
                       "Avianca RT UIO o GYE / Baltra"
                   ]
            
                servicios_water_transport = [
                       "Charter Speedboat OW Pto. Ayora / Pto. Villamil",
                       "Charter Speedboat RT  Pto. Ayora / Pto. Villamil",
                       "Ferry Pto Ayora - Pto. Villamil OW",
                       "Ferry Pto Ayora - Pto. Villamil RT"
                   ]      
                excluded_services = [
                    'Angermeyer Standard DBL with breakfast', 
                    'Angermeyer Standard SGL with breakfast', 
                    'Finch Bay Hotel Standard DBL with breakfast', 
                    'Finch Bay Hotel Standard SGL with breakfast', 
                    'Finch Bay Hotel Suite DBL with breakfast', 
                    'Finch Bay Hotel Suite SGL with breakfast', 
                    'Finch Bay Hotel Suite Additional adult with breakfast'
                ]
                servicios_tours_santa_cruz = [
                    "Santa Cruz Highlands Tour",
                    "Full-day Yacht Tour",
                    "Bahia Divine + Charles Darwin Station",
                    "Scuba Diving Finch Bay Hotel",
                    "Scuba Diving Santa Cruz"
                    
                ]
                
                servicios_guide_santa_cruz = [
                    "Guide Santa Cruz in English",
                    "Guide Santa Cruz in German",
                    "Guide Santa Cruz accommodations",
                    "Guide Santa Cruz breakfast",
                    "Guide Santa Cruz lunch",
                    "Guide Santa Cruz dinner",
                    "Guide Transfer in/out (Isabela / Santa Cruz)"
                ]
                # Verificar si se ha seleccionado más de un servicio de la lista "servicios_emetebe" en el mismo día
                selected_emetebe_services = [s for s in selected_tickets[i] if s in servicios_emetebe]
                if len(selected_emetebe_services) > 1:
                    st.error(f"Error: You cannot select more than one Emetebe service on the same day. Day {i+1}")
                    valid_selection = False  # Marcar selección como inválida
               
                # Verificar si se ha seleccionado más de un servicio de Avianca en el mismo día
                
                selected_avianca_services = [s for s in selected_tickets[i] if s in servicios_avianca]
                if len(selected_avianca_services) > 1:
                    st.error(f"Error: You cannot select more than one Avianca service on the same day. Day {i+1}")
                    valid_selection = False  # Marcar selección como inválida

                # Validación para "Avianca OW UIO / Baltra" y "Avianca OW GYE / Baltra" (solo primer o último día)
                if i not in [0, num_nights - 1]:
                    if "Avianca OW UIO / Baltra" in selected_tickets[i] or "Avianca OW GYE / Baltra" in selected_tickets[i]:
                        st.error(f"Error: 'Avianca OW UIO / Baltra' or 'Avianca OW GYE / Baltra' can only be selected on the first or last day. Day {i+1}")
                        valid_selection = False  # Marcar selección como inválida
        
                # Validación para "Avianca RT UIO o GYE / Baltra" (solo primer día)
                if i != 0 and "Avianca RT UIO o GYE / Baltra" in selected_tickets[i]:
                    st.error(f"Error: 'Avianca RT UIO o GYE / Baltra' can only be selected on the first day. Day {i+1}")
                    valid_selection = False  # Marcar selección como inválida
                    
                  # Verificar si se ha seleccionado más de un servicio de la lista "servicios_water_transport" en el mismo día
                selected_water_transport_services = [s for s in selected_water_transportation[i] if s in servicios_water_transport]
                if len(selected_water_transport_services) > 1:
                    st.error(f"Error: You cannot select more than one water transportation service (speedboat or ferry) on the same day. Day {i+1}")
                    valid_selection = False  # Marcar selección como inválida
                
                servicios_tours_seleccionados_dia = []  # Lista para rastrear servicios de Tours seleccionados en este día

        # Validación por día: Verificar si el mismo servicio de Tours se selecciona más de una vez en el mismo día
                if selected_tours[i]:
                    for servicio in selected_tours[i]:
                        # Excluir "Full-day Yatch Tour" de las validaciones
                        if servicio != "Full-day Yacht Tour":
                            # Verificar duplicados en el mismo día
                            if servicio in servicios_tours_seleccionados_dia:
                                st.error(f"Error: The tour service '{servicio}' has been selected more than once on Day {i+1}. Please remove the duplicate.")
                                valid_selection = False
                            servicios_tours_seleccionados_dia.append(servicio)
        
                            # Validación global: Verificar si el servicio de Tours se ha seleccionado en otro día
                            if servicio in servicios_tours_seleccionados_global:
                                st.error(f"Error: The tour service '{servicio}' has already been selected on a previous day. It can only be selected once across all days.")
                                valid_selection = False
                            servicios_tours_seleccionados_global.append(servicio)
                        else:
                            # Permitir múltiples selecciones de "Full-day Yatch Tour" en diferentes días
                            pass
         #Para validación servicios acomodación Sta Cruz no permitir guias ni tours en Santa Cruz, excepto excludde services
                 # Filtrar acomodaciones Santa Cruz excluyendo servicios específicos
                selected_accommodations_santa_cruz = [s for s in selected_accommodations[i]
                        if s not in excluded_services and s in accommodations_santa_cruz
                    ]
                # Verificar si hay tours o guías seleccionados en el mismo día
                selected_tours_santa_cruz = [
                      s for s in selected_tours[i] if s in servicios_tours_santa_cruz
                  ]
                selected_guides_santa_cruz = [
                      s for s in selected_guide[i] if s in servicios_guide_santa_cruz
                  ]
            
                  # Validación en el mismo día
                if selected_accommodations_santa_cruz and (selected_tours_santa_cruz or selected_guides_santa_cruz):
                      st.error(f"Error: You cannot select accommodations in Santa Cruz along with tour or guide services in Santa Cruz on the same day. Day {i+1}")
                      valid_selection = False  
                
                # Si hay un servicio de alojamiento en Santa Cruz (excepto los excluidos)
                if selected_accommodations_santa_cruz:
                     # Validar si hay servicios de guía o tours en Santa Cruz en otro día
                     for j in range(num_nights):
                         if j != i:  # Verificar otros días
                             # Revisar si hay tours o guías seleccionados en días diferentes
                             selected_tours_santa_cruz = [
                                 s for s in selected_tours[j] if s in servicios_tours_santa_cruz
                             ]
                             selected_guides_santa_cruz = [
                                 s for s in selected_guide[j] if s in servicios_guide_santa_cruz
                             ]
                             
                             if selected_tours_santa_cruz or selected_guides_santa_cruz:
                                 st.error(f"Error: Tour or guide services in Santa Cruz cannot be selected on different days when accommodations in Santa Cruz are booked. Day {j+1}")
                                 valid_selection = False    
                 
                                 
                 #Validación de servicios Acomodación Santa de Servicios excluidos (acomodacion sta Cruz) si se escoge cualquier servicio de esa lista que no permita seleccionar otros servicos de Acomodación en Sta Cruz
                  # Recopilar los servicios seleccionados para cada día
                selected_accommodations_santa_cruz = selected_accommodations[i]
                selected_excluded_services = [s for s in selected_accommodations[i] if s in excluded_services]
                  # Verificar si se seleccionaron servicios excluidos en este día
                if selected_excluded_services:
                     excluded_services_selected_global = True
                   # Verificar si se seleccionaron otros servicios de "Accommodations Santa Cruz" en este día
                other_selected_accommodations = [s for s in selected_accommodations[i] if s not in excluded_services and s in accommodations_santa_cruz]
                if other_selected_accommodations:
                      other_accommodations_selected_global = True            
                  # Validación: No permitir la selección de servicios excluidos junto con otros servicios de 'Accommodations Santa Cruz' en cualquier día
                if excluded_services_selected_global and other_accommodations_selected_global:
                      st.error(f"Error: You cannot select services from 'Accommodations Santa Cruz' and excluded services on different or the same days. Day {i+1}")
                      valid_selection = False
                      break  # Detener el ciclo si se encuentra una selección inválida
                               
              # Verificar si hay servicios de 'Accommodations Santa Cruz' (exceptuando los excluidos) y si ya se seleccionaron servicios excluidos en otros días
                if other_selected_accommodations and excluded_services_selected_global:
                      st.error(f"Error: You cannot select services from 'Accommodations Santa Cruz' after selecting an excluded service. Day {i+1}")
                      valid_selection = False
                      break  # Detener el ciclo si se encuentra una selección inválida
              
                  # Verificar si hay servicios excluidos seleccionados y si ya se seleccionaron otros servicios de 'Accommodations Santa Cruz' en otros días
                if selected_excluded_services and other_accommodations_selected_global:
                      st.error(f"Error: You cannot select excluded services from 'Accommodations Santa Cruz' after selecting other services from 'Accommodations Santa Cruz'. Day {i+1}")
                      valid_selection = False
                      break  # Detener el ciclo si se encuentra una selección inválida
                 
                    # Si valid_selection es False, detenemos el proceso
                if not valid_selection:
                    break
            
               # Si la selección es válida, proceder con el cálculo
               
                if valid_selection:
                    if selected_water_transportation[i]:
                        for servicio in selected_water_transportation[i]:
                            if servicio == "Charter Speedboat OW Pto. Ayora / Pto. Villamil":
                                costo, tipo_costo, valor_original = calcular_costo_speedboat_ow(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Speedboat RT  Pto. Ayora / Pto. Villamil":
                                costo, tipo_costo, valor_original = calcular_costo_speedboat_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Water taxi - Itabaca Channel Small":
                                costo, tipo_costo, valor_original = calcular_costo_water_taxi_small(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Water taxi - Itabaca Channel Big":
                                costo, tipo_costo, valor_original = calcular_costo_water_taxi_big(num_people, cost_data_persona_grupo)
                            elif servicio == "Ferry Pto Ayora - Pto. Villamil OW":
                                costo, tipo_costo, valor_original = calcular_costo_ferry_ow(num_people, cost_data_persona_grupo)
                            elif servicio == "Ferry Pto Ayora - Pto. Villamil RT":
                                costo, tipo_costo, valor_original = calcular_costo_ferry_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Water taxi Isabela OW":
                                costo, tipo_costo, valor_original = calcular_costo_charter_water_taxi_isabela(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0  # Valor por defecto si no se aplica el cálculo
                                
                            day_services.append({
                                "Type": "Water Transportation",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                               # "Original Cost (before calculation)": valor_original,
                                "Final Cost": costo
                            })
                
                    if selected_ground_transportation[i]:
                        for servicio in selected_ground_transportation[i]:
                            if servicio == "Transfer-in Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_in_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Transfer-in Starting in Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_in_santa_cruz(num_people, cost_data_persona_grupo)
                            elif servicio == "Transfer-out Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_out_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Transfer-out Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_out_santa_cruz(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                
                            day_services.append({
                                "Type": "Ground Transportation",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                               # "Original Cost (before calculation)": valor_original,
                                "Final Cost": costo
                            })
                
                    if selected_tickets[i]:
                        for servicio in selected_tickets[i]:
                            if servicio == "Emetebe OW Baltra / Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_emetebe(num_people, cost_data_persona_grupo)
                            elif servicio == "Emetebe RT Baltra / Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_emetebe_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Emetebe OW Baltra / Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_charter_emetebe(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Emetebe RT Baltra / Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_charter_emetebe_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Avianca OW UIO / Baltra":
                                costo, tipo_costo, valor_original = calcular_costo_avianca_ow_uio_baltra(num_people, cost_data_persona_grupo)
                            elif servicio == "Avianca OW GYE / Baltra":
                                costo, tipo_costo, valor_original = calcular_costo_avianca_ow_gye_baltra(num_people, cost_data_persona_grupo)
                            elif servicio == "Avianca RT UIO o GYE / Baltra":
                                costo, tipo_costo, valor_original = calcular_costo_avianca_rt_uio_gye_baltra(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                
                            day_services.append({
                                "Type": "Tickets",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                                #"Original Cost (before calculation)": valor_original,
                                "Final Cost": costo
                            })
                
                    if selected_tours[i]:
                        for servicio in selected_tours[i]:
                            if servicio == "Tintoreras Walk & Snorkel Tour":
                                costo, tipo_costo, valor_original = calcular_costo_tintoreras_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Private Tintoreras Walk & Snorkel Tour Charter":
                                costo, tipo_costo, valor_original = calcular_costo_private_tintoreras_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Private Túneles Walk & Snorkel Tour Charter":
                                costo, tipo_costo, valor_original = calcular_costo_private_tuneles_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Túneles Walk & Snorkel Tour":
                                costo, tipo_costo, valor_original = calcular_costo_tuneles_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Sierra Negra & Chico Volcanoes":
                                costo, tipo_costo, valor_original = calcular_costo_sierra_negra_chico_volcanoes(num_people, cost_data_persona_grupo)
                            elif servicio == "Wall of Tears Trekking or biking Tour":
                                costo, tipo_costo, valor_original = calcular_costo_wall_of_tears(num_people, cost_data_persona_grupo)
                            elif servicio == "Wetlands & Tortoise Breeding Station":
                                costo, tipo_costo, valor_original = calcular_costo_wetlands_tortoise_breeding_station(num_people, cost_data_persona_grupo)
                            elif servicio == "Sucre's Cave, El Mango Viewpoint & Beach time":
                                costo, tipo_costo, valor_original = calcular_costo_sucres_cave(num_people, cost_data_persona_grupo)
                            elif servicio == "Concha de Perla Snorkel Tour + Beach Time":
                                costo, tipo_costo, valor_original = calcular_costo_concha_de_perla(num_people, cost_data_persona_grupo)
                            elif servicio == "Kayaking in Tintoreras":
                                costo, tipo_costo, valor_original = calcular_costo_kayaking_in_tintoreras(num_people, cost_data_persona_grupo)
                            elif servicio == "Sulfur Mines Tour":
                                costo, tipo_costo, valor_original = calcular_costo_sulfur_mines(num_people, cost_data_persona_grupo)
                            elif servicio == "Private Cuatro Hermanos Snorkeling & Fishing Tour + Tortuga Island":
                                costo, tipo_costo, valor_original = calcular_costo_cuatro_hermanos(num_people, cost_data_persona_grupo)
                            elif servicio == "Scuba Diving Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_scuba_diving_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Surf Isabela-Half Day":
                                costo, tipo_costo, valor_original = calcular_costo_surf_isabela_half_day(num_people, cost_data_persona_grupo)
                            elif servicio == "Surf Isabela-Whole Day":
                                 costo, tipo_costo, valor_original = calcular_costo_surf_isabela_whole_day(num_people, cost_data_persona_grupo)    
                            elif servicio == "Santa Cruz Highlands Tour":
                                costo, tipo_costo, valor_original = calcular_costo_santa_cruz_highlands(num_people, cost_data_persona_grupo)
                            elif servicio == "Full-day Yacht Tour":
                                costo, tipo_costo, valor_original = calcular_costo_full_day_yatch(num_people, cost_data_persona_grupo)
                            elif servicio == "Bahia Divine + Charles Darwin Station":
                                costo, tipo_costo, valor_original = calcular_costo_bahia_divine(num_people, cost_data_persona_grupo)
                            elif servicio == "Scuba Diving Finch Bay Hotel":
                                costo, tipo_costo, valor_original = calcular_costo_scuba_diving_finch_bay(num_people, cost_data_persona_grupo)
                            elif servicio == "Scuba Diving Santa Cruz":
                                 costo, tipo_costo, valor_original = calcular_costo_scuba_diving_santa_cruz(num_people, cost_data_persona_grupo)   
                            elif servicio == "Free Time at the Beach - Isabela":
                                 costo, tipo_costo, valor_original = calcular_costo_free_time_at_the_beach(num_people, cost_data_persona_grupo)   

                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                
                            day_services.append({
                                "Type": "Tours",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                               # "Original Cost (before calculation)": valor_original,
                                "Final Cost": costo
                            })
                
                                       # Cálculo para Guide
                    if selected_guide[i]:
                        for servicio in selected_guide[i]:
                            if servicio == "Guide Isabela in English":
                                costo, tipo_costo, valor_original = calcular_costo_guide_isabela_english(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Isabela in German":
                                costo, tipo_costo, valor_original = calcular_costo_guide_isabela_german(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz in English":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_english(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz in German":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_german(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz accommodations":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_accomodations(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz lunch":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_lunch(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide Santa Cruz dinner":
                                costo, tipo_costo, valor_original = calcular_costo_guide_santa_cruz_dinner(num_people, cost_data_persona_grupo)
                            
                            
                            elif servicio == "Guide Transfer in/out (Isabela / Santa Cruz)":
                                costo, tipo_costo, valor_original = calcular_costo_guide_transfer_in_out(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                    
                            day_services.append({
                                "Type": "Guide",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                                #"Original Cost (before calculation)": valor_original,
                                "Final Cost": costo
                            })
                    
                    # Cálculo para Airport Assistance
                    if selected_airport_assistance[i]:
                        for servicio in selected_airport_assistance[i]:
                            if servicio == "Luggage transport Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_luggage_transport_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Bilingual airport assistant Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_bilingual_assistant_santa_cruz(num_people, cost_data_persona_grupo)
                            elif servicio == "Luggage transport Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_luggage_transport_santa_cruz(num_people, cost_data_persona_grupo)
                            elif servicio == "Baltra Airport Assistance | Continental Flight - Inter Island Flight (without transfer assistance)":
                                costo, tipo_costo, valor_original = calcular_costo_baltra_airport_assistance_continental_flight(num_people, cost_data_persona_grupo)
                            
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                    
                            day_services.append({
                                "Type": "Airport Assistance",
                                "Service": servicio,
                               "Cost Type": tipo_costo,
                               #"Original Cost (before calculation)": valor_original,
                               "Final Cost": costo
                            })
                    
                    # Cálculo para Meals
                    if selected_meals[i]:
                        for servicio in selected_meals[i]:
                            if servicio == "Lunch Pto. Villamil Isabela":
                                costo, tipo_costo, valor_original = calcular_costo_lunch_pto_villamil(num_people, cost_data_persona_grupo)
                            elif servicio == "Dinner Pto. Ayora Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_dinner_pto_ayora(num_people, cost_data_persona_grupo)
                            elif servicio == "Lunch Santa Cruz Narval":
                                costo, tipo_costo, valor_original = calcular_costo_lunch_santa_cruz_narval(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                    
                            day_services.append({
                                "Type": "Meals",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                                
                                "Final Cost": costo
                            })
                    
                    # Cálculo para Accommodations Santa Cruz
                    if selected_accommodations[i]:
                        for servicio in selected_accommodations[i]:
                            if servicio == "Finch Bay Hotel 4D-3N DBL-TPL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_4d3n_dbl_tpl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 4D/3N SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_4d3n_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 4D/3N Suite DBL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_4d3n_suite_dbl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 4D/3N Suite SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_4d3n_suite_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 5D/4N DBL / TPL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_5d4n_dbl_tpl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 5D/4N SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_5d4n_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 5D/4N Suite DBL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_5d4n_suite_dbl(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel 5D/4N Suite SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_5d4n_suite_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 4D/3N DBL / TPL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_4d3n_dbl_tpl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 4D/3N SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_4d3n_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 4D/3N Suite DBL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_4d3n_suite_dbl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 4D/3N Suite SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_4d3n_suite_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 3D/2N DBL / TPL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_3d2n_dbl_tpl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 3D/2N SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_3d2n_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 3D/2N Suite DBL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_3d2n_suite_dbl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Waterfront Inn 3D/2N Suite SGL Program 2025":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_3d2n_suite_sgl(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Standard DBL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_standard_dbl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Angermeyer Standard SGL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_angermeyer_standard_sgl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel Standard DBL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_standard_dbl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel Standard SGL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_standard_sgl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel Suite DBL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_suite_dbl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel Suite SGL with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_suite_sgl_breakfast(num_people, cost_data_persona_grupo)
                            elif servicio == "Finch Bay Hotel Suite Additional adult with breakfast":
                                costo, tipo_costo, valor_original = calcular_costo_finch_bay_suite_additional_adult(num_people, cost_data_persona_grupo)
                            else:
                                costo = 0
                                tipo_costo = "N/A"
                                valor_original = 0
                    
                            day_services.append({
                                "Type": "Accommodations in Santa Cruz",
                                "Service": servicio,
                                "Cost Type": tipo_costo,
                               
                                "Final Cost": costo
                                
                            })

                
    

                    # Convertir a DataFrame para mostrar en la tabla
                    day_services_df = pd.DataFrame(day_services)
          
                    if not day_services_df.empty:
                      st.write("**Services selected for the day:**")
                      st.table(day_services_df)
                      day_total += day_services_df["Final Cost"].sum()

                   # Guardar la tabla del día en la lista para el PDF
                    day_services_df_list.append((day_services_df, day))  # Guardamos el DataFrame y la fecha
                    
                    # Tabla con el total del día
                    st.write("**Total for the day:**")
                    total_day_df = pd.DataFrame({
                        "Description": ["Total for the day"],
                        "Group Cost": [day_total],
                        "Cost per person": [day_total / num_people]
                    })
                    st.table(total_day_df)
            
                    total_quotation_value += day_total

            if valid_selection:
                # Calcular el costo del hotel Isabela
              total_cost_isabela = num_nights_isabela * cost_per_night_isabela* num_people
              # Mostrar el resultado en una nueva tabla
              st.write("### Cost of Isabela Hotel Nights")
              st.table(pd.DataFrame({"Description": [f"{num_nights_isabela} night(s), {num_people} pax"], 
                                     "Group Cost": [total_cost_isabela], "Cost per person":[total_cost_isabela/num_people]}))
              # Sumar el costo del hotel Isabela al valor total de la cotización
              total_quotation_value += total_cost_isabela
                # Tabla con el total final de la cotización
                
              st.write("### Total Quotation Value:")
              total_df = pd.DataFrame({"Description": ["Total Quotation Value"], "Group Total Cost": [total_quotation_value],
                                       "Total Cost per person": [total_quotation_value/num_people]})
              st.table(total_df)
              
             # Guardar los datos del hotel y el total para incluir en el PDF
                
              hotel_cost_df = pd.DataFrame({
                    "Description": [f"{num_nights_isabela} night(s), {num_people} pax"],
                    "Group Cost": [total_cost_isabela],
                    "Cost per person": [cost_per_night_isabela]
                })

               
                        
              pdf_buffer = generar_pdf(day_services_df_list, hotel_cost_df, total_df, num_people, num_nights)
                
# Mostrar el botón para descargar el PDF solo si el PDF ya fue generado
              st.download_button(
                label="Download Quotation PDF",
                data=pdf_buffer,
                file_name="quotation.pdf",
                mime="application/pdf"
            )