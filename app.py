# Instalamos las librerias necesarias
#pip install -r requirements.txt

# Importación de bibliotecas necesarias
import streamlit as st  # Importa la biblioteca Streamlit para la creación de aplicaciones web
import os  # Importa la biblioteca os para interactuar con el sistema operativo
import json  # Importa la biblioteca json para manipulación de datos JSON
import re # Importa el modulo de regex
from streamlit_option_menu import option_menu  # Importa la función option_menu desde la biblioteca streamlit_option_menu
#from functions import google_vision_translation, translate_audio_gpt3, openai_vision_translation, comet_metric, transform_audio_mp3 # Importamos de functions.py las funciones creadas para traducir
import tempfile # Módulo que permite crear archivos temporales

# Configuración de la aplicación web
st.set_page_config(page_title="Traducción automatizada", layout='wide')

# Carga de los resultados desde un archivo JSON si no están en la sesión actual
if 'results' not in st.session_state:
    st.session_state.results = json.load(open('files/results.json', 'r'))

# Inicializamos una variable para almacenar las traducciones
if 'traduccion_resultados' not in st.session_state:
    st.session_state.traduccion_resultados = []
    
# Inicializamos una variable para almacenar el orden de subida
if 'file_uploader_key' not in st.session_state:
    st.session_state.file_uploader_key = 0

# Creación de un menú desplegable en la barra lateral para seleccionar entre "Imágenes" y "Audios"
with st.sidebar:
    selected = option_menu("Menú", ["Imágenes", "Audios"], 
        icons=['card-image', 'soundwave'], menu_icon="cast", default_index=0)

if selected == 'Traducir':

    st.write("# 📂 Sube el archivo a traducir")

    files = st.file_uploader("Selecciona los archivos", accept_multiple_files=True, key=st.session_state["file_uploader_key"])

    if len(files) > 0:
        for uploaded_file in files:
            # Obtener la extensión del archivo
            file_name = uploaded_file.name
            extension = file_name.split('.')[-1].lower()

            # Definir listas de extensiones para imágenes y audios
            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
            audio_extensions = ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a']

            # Verificar si el archivo es una imagen
            if extension in image_extensions:
                tipo_archivo = 'imagen'
            # Verificar si el archivo es un audio
            elif extension in audio_extensions:
                tipo_archivo = 'audio'
            else:
                tipo_archivo = None
        
        if tipo_archivo is not None:
            # Crear un archivo temporal para guardar el archivo subido
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as temp_file:
                # Copiar el contenido del archivo subido al archivo temporal
                temp_file.write(uploaded_file.getvalue())
                # Guardar la ruta del archivo temporal para uso posterior
                file_path = temp_file.name

            st.markdown(':blue[Escribe los idiomas en código ISO 639 de 2 dígitos]')

            col1, col2 = st.columns(2)

            with col1:
                source_lang = st.text_input('Idioma inicial')
            with col2:
                target_lang = st.text_input('Idioma final')

            if st.button("Traducir", type = "primary", key = "traducir"):
                st.session_state.file_uploader_key += 1

                with st.spinner('Traduciendo...⏳'):

                    if tipo_archivo == 'imagen':
                        # Traducimos la imagen en Google
                        texto_original_google, texto_traducido_google = google_vision_translation(file_path, source_lang, target_lang)
                        # Calculamos la puntuación COMET de la traducción obtenida
                        puntuacion_google = comet_metric([{"src": texto_original_google, "mt": texto_traducido_google}])

                        # Traducimos la imagen en OpenAI
                        texto_original_openai, texto_traducido_openai = openai_vision_translation(file_path, source_lang, target_lang)
                        # Calculamos la puntuación COMET de la traducción obtenida
                        puntuacion_openai= comet_metric([{"src": texto_original_openai, "mt": texto_traducido_openai}])
  
                        # Guardamos el resultado
                        st.session_state.traduccion_resultados.append({"type": "imagen", "path": file_path, "texto_original_google": texto_original_google, "texto_traducido_google": texto_traducido_google, "puntuacion_google": puntuacion_google[0][0], "texto_original_openai": texto_original_openai, "texto_traducido_openai": texto_traducido_openai, "puntuacion_openai": puntuacion_openai[0][0]})
                        
                    if tipo_archivo == 'audio':

                        # Transformamos el audio a mp3
                        file_path = transform_audio_mp3(uploaded_file)
                        # Traducimos el audio en OpenAI
                        texto_original_openai, texto_traducido_openai = translate_audio_gpt3(file_path, source_lang, target_lang)
                        # Calculamos la puntuación COMET de la traducción obtenida
                        puntuacion_openai= comet_metric([{"src": texto_original_openai, "mt": texto_traducido_openai}])
                        # Guardamos el resultado
                        st.session_state.traduccion_resultados.append({"type": "audio", "path": file_path,"texto_original": texto_original_openai, "texto_traducido": texto_traducido_openai, "puntuacion": puntuacion_openai[0][0]})


    if len(st.session_state.traduccion_resultados) > 0:

        for i, resultado in enumerate(st.session_state.traduccion_resultados):

            st.write(f"### Resultado {i+1}")

            if resultado['type'] == 'imagen':
                # Mostramos el archivo
                with st.expander('Ver Imagen'):
                    st.image(resultado['path'])

                # Mostramos las traducciones por separado
                google, openai = st.tabs(['Google', 'OpenAI'])
                
                with google:
                    st.markdown(f"**:blue[Texto Original:]** {resultado['texto_original_google']}")
                    st.markdown(f"**:blue[Traducción de Google:]** {resultado['texto_traducido_google']}")
                    st.markdown(f"**:blue[Puntuación COMET:]** {resultado['puntuacion_google']}")

                with openai:
                    st.markdown(f"**:blue[Texto Original:]** {resultado['texto_original_openai']}")
                    st.markdown(f"**:blue[Traducción de OpenAI:]** {resultado['texto_traducido_openai']}")
                    st.markdown(f"**:blue[Puntuación COMET:]** {resultado['puntuacion_openai']}")

            elif resultado['type'] == 'audio':
                # Mostramos el archivo
                with st.expander('Ver Audio'):
                    st.audio(resultado['path'])
                
                st.markdown(f"**:blue[Texto Original:]** {resultado['texto_original']}")
                st.markdown(f"**:blue[Traducción de OpenAI:]** {resultado['texto_traducido']}")
                st.markdown(f"**:blue[Puntuación COMET:]** {resultado['puntuacion']}")

            st.write('---')

# Si se selecciona "Imágenes", se mostrarán las imágenes y las traducciones disponibles
if selected == "Imágenes":

    ejemplos = []

    for i in range(11):
        ejemplos.append(f'Imagen {i+1}')

    option = st.selectbox('Selecciona una imagen', ejemplos)

    # Listado de archivos de imágenes en el directorio 'files/images'
    file_list = os.listdir('files/images')

    # Extramos con regex el indice del ejemplo seleccionado
    index = int(re.search(r'\b\d+\b', option).group()) - 1

    # Titular de la imagen
    st.write(f'## {option}')

    # Mostramos la imagen traducida
    with st.expander('Ver Imagen'):
        st.image(f'files/images/{file_list[index]}')

    # Mostramos las traducciones por separado
    google, openai = st.tabs(['Google', 'OpenAI'])
    
    with google:
        st.markdown(f"**:blue[Texto Original:]** {st.session_state.results['images']['google'][file_list[index]]['texto_original']}")
        st.markdown(f"**:blue[Traducción de Google:]** {st.session_state.results['images']['google'][file_list[index]]['texto_traducido']}")
        st.markdown(f"**:blue[Puntuación COMET:]** {st.session_state.results['images']['google'][file_list[index]]['puntuacion']}")

    with openai:
        st.markdown(f"**:blue[Texto Original:]** {st.session_state.results['images']['openai'][file_list[index]]['texto_original']}")
        st.markdown(f"**:blue[Traducción de OpenAI:]** {st.session_state.results['images']['openai'][file_list[index]]['texto_traducido']}")
        st.markdown(f"**:blue[Puntuación COMET:]** {st.session_state.results['images']['openai'][file_list[index]]['puntuacion']}")

                    
# Si se selecciona "Audios", se mostrarán los audios y las traducciones disponibles
if selected == "Audios":

    ejemplos = []

    for i in range(3):
        ejemplos.append(f'Audio {i+1}')

    option = st.selectbox('Selecciona un audio', ejemplos)

    # Listado de archivos de audios en el directorio 'files/images'
    file_list = os.listdir('files/audios')

    # Extramos con regex el indice del ejemplo seleccionado
    index = int(re.search(r'\b\d+\b', option).group()) - 1

    # Titular del audio
    st.write(f'## {option}')

    # Mostramos la imagen traducida
    with st.expander('Reproducir audio'):
        st.audio(f'files/audios/{file_list[index]}')

    st.markdown(f"**:blue[Texto Original:]** {st.session_state.results['audios']['openai'][file_list[index]]['texto_original']}")
    st.markdown(f"**:blue[Traducción de OpenAI:]** {st.session_state.results['audios']['openai'][file_list[index]]['texto_traducido']}")
    st.markdown(f"**:blue[Puntuación COMET:]** {st.session_state.results['audios']['openai'][file_list[index]]['puntuacion']}")

