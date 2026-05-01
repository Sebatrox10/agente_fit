from flask import Flask, request, jsonify
import google.generativeai as genai
import json
from PIL import Image
import io
import os
import re
import sys

app = Flask(__name__)

# Configuración de Gemini
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("⚠️ ¡ALERTA! La GEMINI_API_KEY no está configurada.", file=sys.stderr, flush=True)
genai.configure(api_key=API_KEY)

# --- RUTA 1: PROCESAR IMAGEN ---
@app.route('/api/ia/fitness/leer-imagen', methods=['POST'])
def leer_imagen_fitness():
    print("📸 [VISION] Recibiendo imagen...")
    if 'imagen' not in request.files:
        return jsonify({"error": "Falta el campo 'imagen'"}), 400
    
    try:
        archivo = request.files['imagen']
        imagen = Image.open(io.BytesIO(archivo.read()))
        modelo = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = """
        Analiza esta captura de pantalla de running y devuelve ESTRICTAMENTE un JSON.
        Estructura:
        {
        "datosEstructurados": {
            "duracionMinutos": int,
            "rpeSesion": int, 
            "ejerciciosRealizados": [
            {
                "nombreEjercicio": "Running",
                "distanciaKm": float,
                "frecuenciaCardiacaMedia": int,
                "tiempoSegundos": int,
                "seriesRealizadas": 1,
                "repeticiones": [],
                "pesos": []
            }
            ]
        },
        "mensajeCoach": "string" // Analiza tu ritmo y pulso, y dame un feedback corto sobre tu rendimiento aeróbico.
        }
        """
        
        respuesta = modelo.generate_content([prompt, imagen])
        return jsonify(json.loads(respuesta.text.replace("```json", "").replace("```", "").strip()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RUTA 2: PROCESAR AUDIO ---
def extraer_json_puro(texto):
    try:
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except:
        return None

@app.route('/api/ia/fitness/leer-audio', methods=['POST'])
def leer_audio_fitness():
    print("🎙️ --- INICIO DE PETICIÓN DE AUDIO ---", flush=True)
    
    try:
        if 'audio' not in request.files:
            print(f"❌ Error: El campo 'audio' no está en request.files. Claves recibidas: {list(request.files.keys())}", flush=True)
            return jsonify({"error": "Falta el campo 'audio'"}), 400
            
        archivo = request.files['audio']
        print(f"📦 Archivo recibido: {archivo.filename} ({archivo.content_type})", flush=True)
        
        audio_bytes = archivo.read()
        print(f"📏 Tamaño del audio: {len(audio_bytes)} bytes", flush=True)

        # Usar gemini-2.5-flash para procesar el audio directo
        modelo = genai.GenerativeModel('gemini-2.5-flash')
        
        # Telegram envía .oga (que es ogg/opus)
        audio_blob = { "mime_type": "audio/ogg", "data": audio_bytes }

        prompt = """
        Eres un analista y coach deportivo de élite. Analiza este audio de entrenamiento y devuelve ESTRICTAMENTE un objeto JSON.
        Formatos:
        {
        "datosEstructurados": {
            "duracionMinutos": int,
            "rpeSesion": int,
            "notas": "string",
            "ejerciciosRealizados": [
                {
                "nombreEjercicio": "string", // IMPORTANTE: Estandariza el nombre (ej. Si dice 'pecho inclinado' usa 'Press Inclinado con Mancuernas')
                "seriesRealizadas": int,
                "repeticiones": [int],
                "pesos": [float]
                }
            ]
        },
        "mensajeCoach": "string" // Crea un mensaje motivador y analítico de 2 líneas para Telegram resumiendo la sesión, felicitando por los logros o advirtiendo sobre el RPE.
        }
        """
        # ... (puedes dejar el prompt corto para probar) ...

        print("🧠 Llamando a Gemini...", flush=True)
        respuesta = modelo.generate_content([prompt, audio_blob])
        print(f"🤖 Respuesta de Gemini: {respuesta.text}", flush=True)
        
        datos = extraer_json_puro(respuesta.text)
        if datos:
            return jsonify(datos)
        
        return jsonify({"error": "No se pudo extraer JSON", "raw": respuesta.text}), 500

    except Exception as e:
        print(f"💥 ERROR CRÍTICO EN PYTHON: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr) # Esto imprimirá el error exacto y la línea donde falló
        return jsonify({"error": str(e)}), 500

# --- RUTA 3: HEALTH CHECK (Para pruebas) ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Agente Fitness activo"}), 200


@app.route('/api/ia/fitness/planificar', methods=['POST'])
def planificar_rutina():
    print("🗓️ [PLANNER] Generando planificación semanal...")
    datos = request.get_json()
    
    if not datos:
        return jsonify({"error": "No se recibieron datos"}), 400

    biometria_y_metas = datos.get('contextoEstrategico', '')
    horarios_usuario = datos.get('horarios', '')

    try:
        modelo = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Eres TroxiFit, un planificador de entrenamiento de élite. 
        Tu objetivo es crear una rutina SEMANAL basada ESTRICTAMENTE en la disponibilidad de tiempo del usuario y alineada con sus metas.

        CONTEXTO DEL USUARIO (Biometría y Metas):
        {biometria_y_metas}

        DISPONIBILIDAD Y HORARIOS PARA ESTA SEMANA:
        {horarios_usuario}

        REGLAS:
        1. Distribuye el volumen de entrenamiento inteligentemente según los días y tiempos que el usuario indicó.
        2. Si la meta es fuerza (ej. Sentadilla), asegúrate de incluir ejercicios accesorios.
        3. Si la meta es cardio, programa las distancias o tiempos según la duración permitida.
        4. DEVUELVE ÚNICAMENTE UN JSON válido.

        ESTRUCTURA DEL JSON (Debe coincidir con las entidades de Java):
        {{
          "rutinas": [
            {{
              "nombre": "string", // Ej: "Semana 1 - Lunes - Fuerza Piernas"
              "descripcion": "string", // Ej: "Enfoque en hipertrofia y acercamiento a meta de 100kg en sentadilla. Duración: 1h30m"
              "tipo": "string", // SOLO PUEDE SER: "FUERZA", "CARDIO", o "HÍBRIDO"
              "ejercicios": [
                {{
                  "nombreEjercicio": "string",
                  "series": int,
                  "repeticionesBase": int,
                  "pesoSugerido": float, // Calcula un peso sugerido basado en la meta
                  "descansoSegundos": int,
                  "orden": int // 1, 2, 3...
                }}
              ]
            }}
          ],
          "mensajeCoach": "string" // Un mensaje motivador corto confirmando cómo organizaste su semana basándote en sus horarios.
        }}
        """
        
        print("🧠 Pensando la periodización...")
        respuesta = modelo.generate_content(prompt)
        
        json_limpio = extraer_json_puro(respuesta.text)
        if json_limpio:
            return jsonify(json_limpio)
            
        return jsonify({"error": "No se pudo extraer JSON estructurado", "raw": respuesta.text}), 500

    except Exception as e:
        print(f"💥 ERROR EN PLANIFICADOR: {str(e)}", file=sys.stderr, flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)