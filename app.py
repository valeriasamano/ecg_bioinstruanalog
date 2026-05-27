import os
import random
import math
from flask import Flask, jsonify, send_file, request, render_template_string
from flask_cors import CORS
import pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
CORS(app)

def generar_datos_biomedicos():
    # Usamos numpy para generar los pasos de tiempo exactos de la serie analógica
    puntos = 300
    tiempo = np.round(np.arange(puntos) * 0.02, 2).tolist()
    voltaje = []
    temperatura = []
    
    for i in range(puntos):
        t = tiempo[i]
        # Simulación de onda ECG base
        v = 0.5 * math.sin(2 * math.pi * 1.2 * t)
        if i % 50 == 0: v += 1.5  # Complejo QRS (Onda R)
        if (i - 2) % 50 == 0: v -= 0.3 # Onda S
        v += random.normalvariate(0, 0.03) # Ruido de fondo
        voltaje.append(round(v, 3))
        
        # Simulación de Temperatura estable
        temp = 36.5 + random.normalvariate(0.2, 0.05)
        temperatura.append(round(temp, 1))
        
    return tiempo, voltaje, temperatura

@app.route('/', methods=['GET'])
def home():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            contenido_html = f.read()
        return render_template_string(contenido_html)
    except Exception as e:
        return f"Error al cargar la interfaz visual: {str(e)}", 500

@app.route('/api/biomedicos', methods=['GET'])
def obtener_datos():
    tiempo, voltaje, temperatura = generar_datos_biomedicos()
    return jsonify({
        "tiempo": tiempo, 
        "voltaje": voltaje,
        "temperatura": temperatura,
        "temp_actual": temperatura[-1],
        "bpm": 72
    })

@app.route('/api/descargar', methods=['GET'])
def descargar_reporte():
    tiempo, voltaje, temperatura = generar_datos_biomedicos()
    filename = "/tmp/reporte_clinico.csv" if os.name != 'nt' else "reporte_clinico.csv"
    
    # Generación estructurada con DataFrame de Pandas
    df = pd.DataFrame({
        "Tiempo (s)": tiempo,
        "ECG Voltaje (mV)": voltaje,
        "Temperatura (C)": temperatura
    })
    df.to_csv(filename, index=False, encoding='utf-8')
            
    return send_file(filename, as_attachment=True, download_name="reporte_clinico.csv")

@app.route('/api/enviar-correo', methods=['POST'])
def enviar_correo():
    datos = request.json or {}
    correo_doctor = datos.get("correo_doctor", "")
    nombre_paciente = datos.get("nombre_paciente", "Valeria Sámano")

    if not correo_doctor:
        return jsonify({"status": "error", "message": "Falta el correo."}), 400

    REMITENTE = os.environ.get("EMAIL_REMITENTE", "")
    PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

    tiempo, voltaje, temperatura = generar_datos_biomedicos()
    filepath = "/tmp/reporte_clinico.csv" if os.name != 'nt' else "reporte_clinico.csv"
    
    df = pd.DataFrame({
        "Tiempo (s)": tiempo,
        "ECG Voltaje (mV)": voltaje,
        "Temperatura (C)": temperatura
    })
    df.to_csv(filepath, index=False, encoding='utf-8')

    msg = MIMEMultipart()
    msg['From'] = REMITENTE
    msg['To'] = correo_doctor
    msg['Subject'] = f"Reporte Clínico (ECG + Temp) - {nombre_paciente}"

    cuerpo = f"Adjunto reporte clínico del paciente: {nombre_paciente}.\nSensores: Electrocardiógrafo analógico y Termómetro digital."
    msg.attach(MIMEText(cuerpo, 'plain'))

    with open(filepath, "rb") as adjunto:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(adjunto.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= Reporte_{nombre_paciente}.csv")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(REMITENTE, PASSWORD)
        server.sendmail(REMITENTE, correo_doctor, msg.as_string())
        server.quit()
        return jsonify({"status": "success", "message": "¡Reporte enviado!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
