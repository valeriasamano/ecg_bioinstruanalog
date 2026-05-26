import os
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
    # Datos ECG (Simulados)
    fs = 250  
    tiempo = np.linspace(0, 10, fs * 10)
    ecg = 0.5 * np.sin(2 * np.pi * 1.2 * tiempo)
    for i in range(1, 11):
        ecg += 1.6 * np.exp(-((tiempo - i)**2) / 0.004)
    ruido = np.random.normal(0, 0.03, len(tiempo))
    voltaje = (ecg + ruido).tolist()
    
    # Datos Termómetro (Simulados estables alrededor de 36.7°C con ligeras variaciones)
    temperatura = (36.5 + np.random.normal(0.2, 0.05, len(tiempo))).tolist()
    
    return tiempo.tolist(), voltaje, temperatura

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
    tiempos, voltaje, temperatura = generar_datos_biomedicos()
    return jsonify({
        "tiempo": tiempos, 
        "voltaje": voltaje,
        "temperatura": temperatura,
        "temp_actual": round(temperatura[-1], 1),
        "bpm": 72
    })

@app.route('/api/descargar', methods=['GET'])
def descargar_excel():
    tiempos, voltaje, temperatura = generar_datos_biomedicos()
    df = pd.DataFrame({
        "Tiempo (s)": tiempos, 
        "ECG Voltaje (mV)": voltaje,
        "Temperatura (°C)": temperatura
    })
    filename = "/tmp/reporte_clinico.xlsx" if os.name != 'nt' else "reporte_clinico.xlsx"
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)

@app.route('/api/enviar-correo', methods=['POST'])
def enviar_correo():
    datos = request.json
    correo_doctor = datos.get("correo_doctor", "")
    nombre_paciente = datos.get("nombre_paciente", "Paciente Anónimo")

    if not correo_doctor:
        return jsonify({"status": "error", "message": "Falta el correo."}), 400

    REMITENTE = os.environ.get("EMAIL_REMITENTE", "")
    PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

    tiempos, voltaje, temperatura = generar_datos_biomedicos()
    df = pd.DataFrame({
        "Tiempo (s)": tiempos, 
        "ECG Voltaje (mV)": voltaje,
        "Temperatura (°C)": temperatura
    })
    filepath = "/tmp/reporte_clinico.xlsx" if os.name != 'nt' else "reporte_clinico.xlsx"
    df.to_excel(filepath, index=False)

    msg = MIMEMultipart()
    msg['From'] = REMITENTE
    msg['To'] = correo_doctor
    msg['Subject'] = f"Reporte Clínico Multimodal (ECG + Temp) - {nombre_paciente}"

    cuerpo = f"Adjunto se encuentra el reporte clínico del paciente: {nombre_paciente}.\nSensores incluidos: Electrocardiógrafo analógico y Termómetro digital."
    msg.attach(MIMEText(cuerpo, 'plain'))

    with open(filepath, "rb") as adjunto:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(adjunto.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= Reporte_{nombre_paciente}.xlsx")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(REMITENTE, PASSWORD)
        server.sendmail(REMITENTE, correo_doctor, msg.as_string())
        server.quit()
        return jsonify({"status": "success", "message": "¡Reporte enviado con éxito!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
