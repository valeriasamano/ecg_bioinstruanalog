import os
import math
import random
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)  # Evita bloqueos de origen cruzado con tu index.html

# --- GENERACIÓN DE SEÑALES USANDO NUMPY ---
def generar_senal_ecg():
    fs = 500  
    tiempo = np.linspace(0, 2, fs)
    voltaje = 0.2 * np.sin(2 * np.pi * 1.2 * tiempo)
    for i in range(len(tiempo)):
        if i % 150 == 0:
            voltaje[i] += 1.5  # Complejo QRS
    voltaje += np.random.normal(0, 0.03, fs)
    return tiempo.tolist(), voltaje.tolist()

@app.route('/api/biomedicos', methods=['GET'])
def obtener_datos():
    tiempo, voltaje = generar_senal_ecg()
    bpm_simulado = int(np.random.randint(70, 75))
    temp_simulada = round(float(36.6 + np.random.uniform(-0.2, 0.3)), 1)
    
    return jsonify({
        "tiempo": tiempo[:100],  # Primeros 100 puntos optimizados para la gráfica
        "voltaje": voltaje[:100],
        "bpm": bpm_simulado,
        "temp_actual": temp_simulada
    })

# --- PASARELA DE CORREO SMTP ---
@app.route('/api/enviar-correo', methods=['POST'])
def enviar_correo():
    datos = request.get_json() or {}
    correo_doctor = datos.get('correo_doctor')
    nombre_paciente = datos.get('nombre_paciente', 'Paciente Anónimo')
    
    if not correo_doctor:
        return jsonify({"status": "error", "message": "Falta el correo del especialista"}), 400

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    REMITENTE_EMAIL = os.environ.get("EMAIL_USER", "tu.correo@gmail.com") 
    REMITENTE_PASSWORD = os.environ.get("EMAIL_PASS", "tu_contraseña_de_aplicacion")

    msg = MIMEMultipart()
    msg['From'] = REMITENTE_EMAIL
    msg['To'] = correo_doctor
    msg['Subject'] = f"🚨 Telemedicina: Reporte Fisiológico - {nombre_paciente}"

    cuerpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
                <h2 style="color: #0f172a; border-bottom: 2px solid #ef4444; padding-bottom: 8px;">Healthink. Report</h2>
                <p>Monitoreo activo de laboratorio transmitido con éxito.</p>
                <p><b>Paciente:</b> {nombre_paciente}</p>
                <p><b>Estado:</b> Señales estables dentro del rango normotérmico.</p>
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(cuerpo_html, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(REMITENTE_EMAIL, REMITENTE_PASSWORD)
        server.sendmail(REMITENTE_EMAIL, correo_doctor, msg.as_string())
        server.quit()
        return jsonify({"status": "success", "message": "Reporte enviado."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- EXPORTAR REPORTE EXCEL ORIGINAL (.XLSX) ---
@app.route('/api/descargar', methods=['GET'])
def descargar_reporte():
    tiempo, voltaje = generar_senal_ecg()
    df = pd.DataFrame({
        'Time (s)': tiempo,
        'ECG Voltage (mV)': voltaje
    })
    
    ruta_archivo = "reporte_clinico.xlsx"
    df.to_excel(ruta_archivo, index=False, sheet_name="ECG Data")
    
    return send_file(ruta_archivo, as_attachment=True, download_name="Reporte_Fisiologico.xlsx")

if __name__ == '__main__':
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
