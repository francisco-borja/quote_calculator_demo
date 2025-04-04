# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 11:16:59 2024

@author: franc
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import gspread
from google.oauth2 import service_account
from PIL import Image
import base64
from fpdf import FPDF
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

#Cargar la imagen del logo

# Cargar la imagen del logo
logo_path = "Logo Francisco Borja.jpg"

logo = Image.open(logo_path)

# Convertir la imagen a base64
with open(logo_path, "rb") as img_file:
    logo_base64 = base64.b64encode(img_file.read()).decode()

# Configuración de la página
st.set_page_config(page_title="Touristic Services Quote Calculator", layout="centered",
                   
    )

st.markdown(
    f"""
    <style>
    /* Colores */
    .dark-green-bg {{
        background-color: rgba(43, 76, 140, 0.9); /* Azul oscuro 90% */
        color: white;
    }}
    .dark-green-bg-light {{
        background-color: rgba(43, 76, 140, 0.4); /* Azul oscuro 40% */
    }}
    .light-green-bg {{
        background-color: rgba(43, 76, 140, 0.7); /* Azul oscuro 70% */
    }}
    .light-green-bg-lighter {{
        background-color: rgba(43, 76, 140, 0.5); /* Azul oscuro 50% */
    }}
    .celeste-bg {{
        background-color: #64a6cc; /* Azul claro 100% */
    }}
    
    /* Botón de cotización */
    .stButton > button {{
        background-color: rgba(43, 76, 140, 0.7); /* Azul claro para botón */
        color: white;
        border-radius: 5px;
        border: 2px solid #64a6cc; /* Detalle azul claro */
    }}
    .stButton > button:hover {{
        background-color: rgba(43, 76, 140, 0.5); /* Azul claro 50% en hover */
        border: 2px solid #2b4c8c; /* Azul oscuro en hover */
    }}

    /* Título en azul oscuro */
    .title {{
        font-size: 2.5em;
        color: rgba(43, 76, 140, 0.9); /* Azul oscuro */
        text-align: center;
        margin-bottom: 20px;
    }}

    /* Contenedor principal */
    .main-container {{
        padding: 10px;
        background-color: rgba(43, 76, 140, 0.4); /* Azul oscuro 40% */
        border-radius: 10px;
        border: 3px solid #64a6cc; /* Detalle azul claro */
    }}

    /* Textos y selectores */
    .stTextInput label, .stSelectbox label {{
        color: rgba(43, 76, 140, 0.9); /* Azul oscuro */
        font-weight: bold;
    }}

    /* Bordes de tablas y inputs */
    .stDataFrame, .stMultiselect {{
        border: 2px solid rgba(43, 76, 140, 0.9); /* Bordes en azul oscuro */
    }}

    /* Imagen centrada y tamaño ajustado */
    .logo {{
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 40%; /* Ajusta el tamaño de la imagen */
    }}

    /* Color personalizado para los selectores de servicios */
    [data-baseweb="select"] {{
        background-color: #2b4c8c; /* Azul fuerte */
        color: white;
    }}
    [data-baseweb="select"]::placeholder {{
        color: white;
    }}
    .stSelectbox > div > div {{
        color: white;
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
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        ).with_scopes(scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
        data = pd.DataFrame(sheet.get_all_records())
        return data
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame()

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
def generar_pdf(day_services_df_list, total_df, num_people, num_nights):
    buffer = BytesIO()  # Crear un buffer en memoria para guardar el PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título del PDF
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Demo Quote Calculator - Quotation")

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
   # c.drawString(100, y_position, "Hotel Cost:")
    #y_position -= 20
    #c.drawString(100, y_position, f"- {hotel_cost_df.iloc[0]['Description']}, cost per person and night: ${hotel_cost_df.iloc[0]['Cost per person']} (Total Cost: ${hotel_cost_df.iloc[0]['Group Cost']})")
    #y_position -= 30

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

# Función específica para calcular el costo de "Boat 1 One Way. Location 1 - Location 2"
def calcular_costo_boat1_ow(num_people, df_costos):
    servicio = "Boat 1 One Way. Location 1 - Location 2"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Speedboat RT Pto. Ayora / Pto. Villamil"
def calcular_costo_boat1_rt(num_people, df_costos):
    servicio = "Boat 1 Round Trip. Location 1 - Location 2"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Mini Boat Location 2"
def calcular_costo_mini_boat_location2(num_people, df_costos):
    servicio = "Mini Boat Location 2"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Charter Water Taxi - Itabaca Channel Small"
def calcular_costo_water_taxi_small(num_people, df_costos):
    servicio = "Charter Water taxi - Itabaca Channel Small"
    return calcular_costo(servicio, num_people, df_costos)

# Función específica para calcular el costo de "Charter Water Taxi - Itabaca Channel Big"
def calcular_costo_water_taxi_big(num_people, df_costos):
    servicio = "Charter Water taxi - Itabaca Channel Big"
    return calcular_costo(servicio, num_people, df_costos)
# Función específica para calcular el costo de "Ferry Location 1 - Location 2 One Way"
def calcular_costo_ferry_ow(num_people, df_costos):
    servicio = "Ferry Location 1 - Location 2 One Way"
    return calcular_costo(servicio, num_people, df_costos)
def calcular_costo_ferry_rt(num_people, df_costos):
    servicio = "Ferry Location 1 - Location 2 Round Trip"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Transfer-in Hotel
def calcular_costo_transfer_in_isabela(num_people, df_costos):
    servicio = "Transfer-in Hotel"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-in Starting in Santa Cruz
def calcular_costo_transfer_in_santa_cruz(num_people, df_costos):
    servicio = "Transfer-in Starting in Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-out Hotel
def calcular_costo_transfer_out_isabela(num_people, df_costos):
    servicio = "Transfer-out Hotel"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Transfer-out Santa Cruz
def calcular_costo_transfer_out_santa_cruz(num_people, df_costos):
    servicio = "Transfer-out Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Walking Tour
def calcular_costo_tintoreras_walk_snorkel(num_people, df_costos):
    servicio = "Walking Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Walking Tour- Private
def calcular_costo_private_tintoreras_walk_snorkel(num_people, df_costos):
    servicio = "Walking Tour- Private"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Walking Tour- Private
def calcular_costo_private_tuneles_walk_snorkel(num_people, df_costos):
    servicio = "Walking Tour Second Location-Private"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Walking Tour Second Location
def calcular_costo_tuneles_walk_snorkel(num_people, df_costos):
    servicio = "Walking Tour Second Location"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Trekking
def calcular_costo_sierra_negra_chico_volcanoes(num_people, df_costos):
    servicio = "Trekking"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Trekking and Biking Tour
def calcular_costo_wall_of_tears(num_people, df_costos):
    servicio = "Trekking and Biking Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Animal Viewing Tour
def calcular_costo_wetlands_tortoise_breeding_station(num_people, df_costos):
    servicio = "Animal Viewing Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Caves and Swimming Spot 1
def calcular_costo_sucres_cave(num_people, df_costos):
    servicio = "Caves and Swimming Spot 1"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Caves and Swimming Spot 2
def calcular_costo_concha_de_perla(num_people, df_costos):
    servicio = "Caves and Swimming Spot 2"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Kayaking
def calcular_costo_kayaking_in_tintoreras(num_people, df_costos):
    servicio = "Kayaking"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Springs Walk and Swimming Tour
def calcular_costo_sulfur_mines(num_people, df_costos):
    servicio = "Springs Walk and Swimming Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Diving Tour - Private
def calcular_costo_cuatro_hermanos(num_people, df_costos):
    servicio = "Diving Tour - Private"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Fishing Tour
def calcular_costo_scuba_diving_isabela(num_people, df_costos):
    servicio = "Fishing Tour"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Boat trip - Half day	
def calcular_costo_surf_isabela_half_day(num_people, df_costos):
    servicio = "Boat trip - Half day"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Boat trip - Whole day
def calcular_costo_surf_isabela_whole_day(num_people, df_costos):
    servicio = "Boat trip - Whole day"
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
# Función para Guide - English
def calcular_costo_guide_isabela_english(num_people, df_costos):
    servicio = "Guide - English"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Guide - German
def calcular_costo_guide_isabela_german(num_people, df_costos):
    servicio = "Guide - German"
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
# Función para Luggage Transport
def calcular_costo_luggage_transport_isabela(num_people, df_costos):
    servicio = "Luggage Transport"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Bilingual airport assistant Santa Cruz
def calcular_costo_bilingual_assistant_santa_cruz(num_people, df_costos):
    servicio = "Bilingual airport assistant Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)

# Función para Luggage transport Santa Cruz
def calcular_costo_luggage_transport_santa_cruz(num_people, df_costos):
    servicio = "Luggage transport Santa Cruz"
    return calcular_costo(servicio, num_people, df_costos)
# Función para Lunch
def calcular_costo_lunch_pto_villamil(num_people, df_costos):
    servicio = "Lunch"
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
    servicio = "River tour"
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
st.markdown("<div class='title'>Touristic Services Quote Calculator</div>", unsafe_allow_html=True)

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
#num_nights_isabela = st.number_input("Number of nights at Hotel", min_value=0, value=0, step=1)
#cost_per_night_isabela = st.number_input("Cost per night and person at Hotel (USD)", min_value=0.0, value=0.0, step=0.01)


# Input: Casilla para incluir o excluir servicios de la Isla Santa Cruz
#include_santa_cruz = st.checkbox("Includes Santa Cruz Island")

# Filtrar la lista_seleccionables según el checkbox
#if include_santa_cruz:
 #   filtered_lista_seleccionables = lista_seleccionables
#else:
   # filtered_lista_seleccionables = lista_seleccionables[lista_seleccionables['Categoría/Isla'] != 'SANTA CRUZ']= lista_seleccionables[lista_seleccionables['Categoría/Isla'] != 'SANTA CRUZ']

filtered_lista_seleccionables=lista_seleccionables[lista_seleccionables['Categoría/Isla'] != 'SANTA CRUZ']= lista_seleccionables[lista_seleccionables['Categoría/Isla'] != 'SANTA CRUZ']
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
        #selected_tickets = []
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
            
            
            #selected_tickets.append(tickets)
            
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
                       "Boat 1 One Way. Location 1 - Location 2",
                       "Boat 1 Round Trip. Location 1 - Location 2",
                       "Ferry Location 1 - Location 2 One Way",
                       "Ferry Location 1 - Location 2 Round Trip"
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
       
                               
            
              
                
                 
                    # Si valid_selection es False, detenemos el proceso
                if not valid_selection:
                    break
            
               # Si la selección es válida, proceder con el cálculo
               
                if valid_selection:
                    if selected_water_transportation[i]:
                        for servicio in selected_water_transportation[i]:
                            if servicio == "Boat 1 One Way. Location 1 - Location 2":
                                costo, tipo_costo, valor_original = calcular_costo_boat1_ow(num_people, cost_data_persona_grupo)
                            elif servicio == "Boat 1 Round Trip. Location 1 - Location 2":
                                costo, tipo_costo, valor_original = calcular_costo_boat1_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Water taxi - Itabaca Channel Small":
                                costo, tipo_costo, valor_original = calcular_costo_water_taxi_small(num_people, cost_data_persona_grupo)
                            elif servicio == "Charter Water taxi - Itabaca Channel Big":
                                costo, tipo_costo, valor_original = calcular_costo_water_taxi_big(num_people, cost_data_persona_grupo)
                            elif servicio == "Ferry Location 1 - Location 2 One Way":
                                costo, tipo_costo, valor_original = calcular_costo_ferry_ow(num_people, cost_data_persona_grupo)
                            elif servicio == "Ferry Location 1 - Location 2 Round Trip":
                                costo, tipo_costo, valor_original = calcular_costo_ferry_rt(num_people, cost_data_persona_grupo)
                            elif servicio == "Mini Boat Location 2":
                                costo, tipo_costo, valor_original = calcular_costo_mini_boat_location2(num_people, cost_data_persona_grupo)
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
                            if servicio == "Transfer-in Hotel":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_in_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Transfer-in Starting in Santa Cruz":
                                costo, tipo_costo, valor_original = calcular_costo_transfer_in_santa_cruz(num_people, cost_data_persona_grupo)
                            elif servicio == "Transfer-out Hotel":
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
                           
                    if selected_tours[i]:
                        for servicio in selected_tours[i]:
                            if servicio == "Walking Tour":
                                costo, tipo_costo, valor_original = calcular_costo_tintoreras_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Walking Tour- Private":
                                costo, tipo_costo, valor_original = calcular_costo_private_tintoreras_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Walking Tour Second Location-Private":
                                costo, tipo_costo, valor_original = calcular_costo_private_tuneles_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Walking Tour Second Location":
                                costo, tipo_costo, valor_original = calcular_costo_tuneles_walk_snorkel(num_people, cost_data_persona_grupo)
                            elif servicio == "Trekking":
                                costo, tipo_costo, valor_original = calcular_costo_sierra_negra_chico_volcanoes(num_people, cost_data_persona_grupo)
                            elif servicio == "Trekking and Biking Tour":
                                costo, tipo_costo, valor_original = calcular_costo_wall_of_tears(num_people, cost_data_persona_grupo)
                            elif servicio == "Animal Viewing Tour":
                                costo, tipo_costo, valor_original = calcular_costo_wetlands_tortoise_breeding_station(num_people, cost_data_persona_grupo)
                            elif servicio == "Caves and Swimming Spot 1":
                                costo, tipo_costo, valor_original = calcular_costo_sucres_cave(num_people, cost_data_persona_grupo)
                            elif servicio == "Caves and Swimming Spot 2":
                                costo, tipo_costo, valor_original = calcular_costo_concha_de_perla(num_people, cost_data_persona_grupo)
                            elif servicio == "Kayaking":
                                costo, tipo_costo, valor_original = calcular_costo_kayaking_in_tintoreras(num_people, cost_data_persona_grupo)
                            elif servicio == "Springs Walk and Swimming Tour":
                                costo, tipo_costo, valor_original = calcular_costo_sulfur_mines(num_people, cost_data_persona_grupo)
                            elif servicio == "Diving Tour - Private":
                                costo, tipo_costo, valor_original = calcular_costo_cuatro_hermanos(num_people, cost_data_persona_grupo)
                            elif servicio == "Fishing Tour":
                                costo, tipo_costo, valor_original = calcular_costo_scuba_diving_isabela(num_people, cost_data_persona_grupo)
                            elif servicio == "Boat trip - Half day":
                                costo, tipo_costo, valor_original = calcular_costo_surf_isabela_half_day(num_people, cost_data_persona_grupo)
                            elif servicio == "Boat trip - Whole day":
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
                            elif servicio == "River tour":
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
                            if servicio == "Guide - English":
                                costo, tipo_costo, valor_original = calcular_costo_guide_isabela_english(num_people, cost_data_persona_grupo)
                            elif servicio == "Guide - German":
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
                            if servicio == "Luggage Transport":
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
                            if servicio == "Lunch":
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
            #  total_cost_isabela = num_nights_isabela * cost_per_night_isabela* num_people
              # Mostrar el resultado en una nueva tabla
              st.write("### Cost of Hotel Nights")
             # st.table(pd.DataFrame({"Description": [f"{num_nights_isabela} night(s), {num_people} pax"], 
              #                       "Group Cost": [total_cost_isabela], "Cost per person":[total_cost_isabela/num_people]}))
              # Sumar el costo del hotel Isabela al valor total de la cotización
              total_quotation_value #+= total_cost_isabela
                # Tabla con el total final de la cotización
                
              st.write("### Total Quotation Value:")
              total_df = pd.DataFrame({"Description": ["Total Quotation Value"], "Group Total Cost": [total_quotation_value],
                                       "Total Cost per person": [total_quotation_value/num_people]})
              st.table(total_df)
              
             # Guardar los datos del hotel y el total para incluir en el PDF
                
          #    hotel_cost_df = pd.DataFrame({
           #         "Description": [f"{num_nights_isabela} night(s), {num_people} pax"],
            #        "Group Cost": [total_cost_isabela],
             #       "Cost per person": [cost_per_night_isabela]
              #  })

               
                        
              pdf_buffer = generar_pdf(day_services_df_list, total_df, num_people, num_nights)
                
# Mostrar el botón para descargar el PDF solo si el PDF ya fue generado
              st.download_button(
                label="Download Quotation PDF",
                data=pdf_buffer,
                file_name="quotation.pdf",
                mime="application/pdf"
            )