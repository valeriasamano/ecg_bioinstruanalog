import os
import math
import random
import csv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# --- SIMULACIÓN NATIVA (SIN NUMPY) ---
def generar_senal_ecg_nativa():
    tiempo = []
    voltaje = []
    pasos = 100
    # Simula 2 segundos de señal muestreada
    for i in range(pasos):
        t = i * 0.02
        tiempo.append(round(t, 2))
        
        # Onda senoidal base
        v = 0.3 * math.sin(2 * math.pi * 1.3 * t)
        # Inyección del complejo QRS ficticio cada ciertos pasos
        if i % 35 == 0:
            v += 1.5
        # Ruido térmico simulado de fondo
        v += random.uniform(-0.03, 0.03)
        voltaje.append(round(v, 4))
        
    return tiempo, voltaje

@app.route('/api/biomedicos', methods=['GET'])
def obtener_datos():
    tiempo, voltaje = generar_senal_ecg_nativa()
    bpm_simulado = random.randint(71, 74)
    temp_simulada = round(random.uniform(36.5, 36.9), 1)
    
    return jsonify({
        "tiempo": tiempo,
        "voltaje": voltaje,
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

# --- EXPORTAR REPORTE USANDO EL MÓDULO CSV NATIVO (REEMPLAZA EXCEL) ---
@app.route('/api/descargar', methods=['GET'])
def descargar_reporte():
    tiempo, voltaje = generar_senal_ecg_nativa()
    ruta_archivo = "reporte_clinico.csv"
    
    # Escribir el archivo usando la librería estándar de Python
    with open(ruta_archivo, mode='w', newline='', encoding='utf-8') as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(['Time (s)', 'ECG Voltage (mV)']) # Encabezados
        for t, v in zip(tiempo, voltaje):
            escritor.writerow([t, v])
            
    return send_file(ruta_archivo, as_attachment=True, download_name="Reporte_Fisiologico.csv")

if __name__ == '__main__':
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
