# Importación de bibliotecas necesarias
import streamlit as st  # Importa la biblioteca Streamlit para la creación de aplicaciones web
import os  # Importa la biblioteca os para interactuar con el sistema operativo
import base64  # Importa la biblioteca base64 para manipulación de datos en base64
import requests  # Importa la biblioteca requests para realizar solicitudes HTTP
from google.cloud import vision  # Importa la clase ImageAnnotatorClient desde la biblioteca google.cloud.vision
from googleapiclient.discovery import build  # Importa la función build desde la biblioteca googleapiclient.discovery
from openai import OpenAI  # Importa la clase OpenAI desde la biblioteca openai
from comet import download_model, load_from_checkpoint # Importa la función para descargar y cargar el modelo de COMET
from io import BytesIO
from pydub import AudioSegment
import tempfile
import json
import re

# Establecimiento de variables de entorno y clientes

# Creamos el archivo credentials_google.json si no existe
credentials_dict = {
    "type": st.secrets.type_val,
    "project_id": st.secrets.project_id_val,
    "private_key_id": st.secrets.private_key_id_val,
    "private_key": st.secrets.private_key_val,
    "client_email": st.secrets.client_email_val,
    "client_id": st.secrets.client_id_val,
    "auth_uri": st.secrets.auth_uri_val,
    "token_uri": st.secrets.token_uri_val,
    "auth_provider_x509_cert_url": st.secrets.auth_provider_x509_cert_url_val,
    "client_x509_cert_url": st.secrets.client_x509_cert_url_val,
    "universe_domain": st.secrets.universe_domain_val
}

# Guardar el JSON en un archivo
if not os.path.exists(os.path.join('files', 'credentials_google.json')):
    with open(os.path.join('files', 'credentials_google.json'), 'w') as file:
        json.dump(credentials_dict, file)

# Configuración de la credencial de Google Cloud Vision
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "files/credentials_google.json"

# Creación de cliente para Google Cloud Vision
client = vision.ImageAnnotatorClient()

# Creación de servicio de traducción de Google Cloud
service = build('translate', 'v2', developerKey=st.secrets.google_api)

# Creación de cliente para OpenAI
openai_client = OpenAI(api_key=st.secrets.openai_api)

# Carga el modelo de evaluación COMET
if 'model' not in st.session_state:
    st.session_state.model = load_from_checkpoint(download_model("Unbabel/wmt20-comet-qe-da"))

# Definición de funciones

# Función para realizar OCR y traducción de texto en una imagen utilizando Google Cloud Vision y Google Translate
st.cache_resource(show_spinner = False)
def google_vision_translation(image_path, source_lang, target_lang):
    """
    Esta función realiza OCR (reconocimiento óptico de caracteres) en una imagen y traduce el texto detectado utilizando Google Cloud Vision y Google Translate.

    :param image_path: Ruta de la imagen.
    :param source_lang: Idioma de origen del texto.
    :param target_lang: Idioma de destino para la traducción.
    :return: Texto traducido.
    """
    # Abrimos el archivo y hacemos la petición a la API de Google de Vision (image-to-text)
    with open(image_path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    
    ocr_text = ''

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    ocr_text += word_text

    # Mandamos la petición de traducción del texto extraído a la API de Translations de Google
    outputs = service.translations().list(source=source_lang, target=target_lang, q=[ocr_text]).execute()

    # Devolvemos la traducción, junto al texto original
    return ocr_text, outputs['translations'][0]['translatedText']


# Función para traducir el texto de un archivo de audio utilizando OpenAI
st.cache_resource(show_spinner = False)
def translate_audio_gpt3(file_path, source_lang, target_lang):
    """
    Esta función traduce el texto de un archivo de audio utilizando OpenAI.

    :param file_path: Ruta del archivo de audio.
    :param source_lang: Idioma de origen del texto.
    :param target_lang: Idioma de destino para la traducción.
    :return: Texto traducido.
    """
    # Abrimos el archivo y hacemos la petición a la API de OpenAI de Whisper (speech-to-text)
    with open(file_path, "rb") as audio_file:
        transcript_response = openai_client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            response_format="verbose_json"
        )

    # Mandamos el texto procedente del audio a un Large Language Model (LLM) con un prompt adecuado para la traducción necesaria
    response_translation = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"Translate the following text from {source_lang} to {target_lang}. Answer only with the text translated"},
            {"role": "user", "content": transcript_response.text}
        ]
    )
    
    # Devolvemos el texto traducido, junto al texto original
    return transcript_response.text, response_translation.choices[0].message.content
    

# Función para traducir el texto dentro de una imagen utilizando OpenAI
st.cache_resource(show_spinner = False)
def openai_vision_translation(image_path, source_lang, target_lang):
    """
    Esta función traduce el texto dentro de una imagen utilizando OpenAI.

    :param image_path: Ruta de la imagen.
    :param source_lang: Idioma de origen del texto.
    :param target_lang: Idioma de destino para la traducción.
    :return: Texto traducido.
    """

    # Abrimos el archivo y hacemos la petición al modelo multimodal GPT-4 de OpenAI para extraer y traducir en un solo paso
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
  
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets.openai_api}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": 'Answer with the text you can see on the image in a JSON format all together without spaces: {"text": <text you can read>}'
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Obtenemos el texto de la imagen
    texto = response.json()['choices'][0]['message']['content']

    # Extramos el JSON
    json_data = json.loads(re.search(r'\{.*?\}', texto).group(0))

    # Extrae la clave 'text' del JSON
    texto_original = json_data['text']

    # Mandamos el texto procedente de la imagen a un Large Language Model (LLM) con un prompt adecuado para la traducción necesaria
    response_translation = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"Translate the following text from {source_lang} to {target_lang}. Answer only with the text translated"},
            {"role": "user", "content": texto_original}
        ]
    )

    # Devolvemos el texto traducido, junto al texto original
    return texto_original, response_translation.choices[0].message.content

  

# Definición de la función comet_metric
st.cache_resource(show_spinner = False)
def comet_metric(sentences):
    """
    Esta función calcula una métrica utilizando un modelo específico y las oraciones proporcionadas como entrada.

    :param sentences: Lista de oraciones para calcular la métrica.
    :return: Salida del modelo.
    """
    
    # Llamada al método predict del modelo con las oraciones como entrada.
    model_output = st.session_state.model.predict(sentences, batch_size=8, gpus=0)

    # Devuelve la salida del modelo
    return model_output


st.cache_resource(show_spinner = False)
def transform_audio_mp3(file):

    # Obtener los bytes del archivo de audio
    contenido_bytes = file.read()

    # Crear un objeto AudioSegment a partir de los bytes
    audio_segment = AudioSegment.from_file(BytesIO(contenido_bytes))

    # Crear un archivo temporal con extensión deseada
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".mp3") as temp_file:
        temp_path = temp_file.name

        # Exportar el audio en el nuevo formato
        audio_segment.export(temp_path, format='mp3')

    return temp_path
