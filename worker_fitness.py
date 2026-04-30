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
        
        prompt = """Extrae las métricas de esta imagen de fitness y devuelve SOLO un JSON:
        { "duracionMinutos": int, "distanciaKm": float, "frecuenciaCardiacaMedia": int, 
          "nombreEjercicio": "string", "ejerciciosRealizados": [] }"""
        
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
        Analiza este audio de entrenamiento y devuelve ESTRICTAMENTE un objeto JSON.
        No incluyas texto explicativo, solo el JSON.
        Formato:
        {
          "duracionMinutos": int,
          "rpeSesion": int,
          "notas": "string",
          "ejerciciosRealizados": [
            {
              "nombreEjercicio": "string",
              "seriesRealizadas": int,
              "repeticionesStr": "string",
              "pesosStr": "string"
            }
          ]
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)

# --- RUTA 3: HEALTH CHECK (Para pruebas) ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Agente Fitness activo"}), 200

# --- INICIO DEL SERVIDOR (SIEMPRE AL FINAL) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)