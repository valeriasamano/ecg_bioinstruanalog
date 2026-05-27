import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)  # Permite que tu index.html se comunique con el backend sin bloqueos de origen

# --- SIMULACIÓN DE SEÑALES BIOMÉDICAS (Sustituir con tus lecturas de hardware/Arduino si aplica) ---
def generar_senal_ecg():
    fs = 500  # Frecuencia de muestreo
    tiempo = np.linspace(0, 2, fs)
    # Generación de una señal tipo ECG con ruido aleatorio y complejos QRS simulados
    voltaje = 0.2 * np.sin(2 * np.pi * 1.2 * tiempo)
    for i in range(len(tiempo)):
        if i % 150 == 0:
            voltaje[i] += 1.5  # Simulación de onda R
    voltaje += np.random.normal(0, 0.03, fs)
    return tiempo.tolist(), voltaje.tolist()

@app.route('/api/biomedicos',局 methods=['GET'])
def obtener_datos():
    tiempo, voltaje = generar_senal_ecg()
    bpm_simulado = int(np.random.randint(70, 75))
    temp_simulada = round(float(36.6 + np.random.uniform(-0.2, 0.3)), 1)
    
    return jsonify({
        "tiempo": tiempo[:100],  # Enviamos los primeros 100 puntos para optimizar ancho de banda
        "voltaje": voltaje[:100],
        "bpm": bpm_simulado,
        "temp_actual": temp_simulada
    })

# --- PASARELA DE CORREO (TELEMEDICINA) ---
@app.route('/api/enviar-correo', methods=['POST'])
def enviar_correo():
    datos = request.get_json()
    correo_doctor = datos.get('correo_doctor')
    nombre_paciente = datos.get('nombre_paciente', 'Paciente Anónimo')
    
    if not correo_doctor:
        return jsonify({"status": "error", "message": "Falta el correo del especialista"}), 400

    # Configuración de tus credenciales SMTP (Usa variables de entorno en Render por seguridad)
    # Si usas Gmail, recuerda generar una "Contraseña de Aplicación" en tu cuenta de Google
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    REMITENTE_EMAIL = os.environ.get("EMAIL_USER", "tu.correo@gmail.com") 
    REMITENTE_PASSWORD = os.environ.get("EMAIL_PASS", "tu_contraseña_de_aplicacion")

    # Crear el mensaje estructurado de telemedicina
    msg = MIMEMultipart()
    msg['From'] = REMITENTE_EMAIL
    msg['To'] = correo_doctor
    msg['Subject'] = f"🚨 Alerta Médica: Reporte de Constantes - {nombre_paciente}"

    # Cuerpo en formato HTML limpio para el especialista
    cuerpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
                <h2 style="color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">Healthink. Telemedicine Report</h2>
                <p>Se ha generado un envío de constantes fisiológicas automatizado desde el laboratorio de bioinstrumentación avanzada.</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background: #f8fafc; border: 1px solid #cbd5e1;">Paciente:</td>
                        <td style="padding: 8px; border: 1px solid #cbd5e1;">{nombre_paciente}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; background: #f8fafc; border: 1px solid #cbd5e1;">Estado ECG:</td>
                        <td style="padding: 8px; border: 1px solid #cbd5e1; color: #16a34a; font-weight: bold;">Ritmo Sinusal Estable</td>
                    </tr>
                </table>
                <p style="margin-top: 20px; font-size: 12px; color: #64748b;">Este es un reporte automático de prueba de ingeniería biomédica.</p>
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(cuerpo_html, 'html'))

    try:
        # Conexión segura al servidor SMTP externo
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(REMITENTE_EMAIL, REMITENTE_PASSWORD)
        server.sendmail(REMITENTE_EMAIL, correo_doctor, msg.as_string())
        server.quit()
        
        return jsonify({"status": "success", "message": "Reporte clínico transmitido con éxito."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- DESCARGA DE REPORTE EXCEL/CSV ---
@app.route('/api/descargar', methods=['GET'])
def descargar_reporte():
    tiempo, voltaje = generar_senal_ecg()
    # Empaquetamos los datos en un DataFrame de pandas para la exportación ordenada
    df = pd.DataFrame({
        'Time (s)': tiempo,
        'ECG Voltage (mV)': voltaje
    })
    
    ruta_archivo = "reporte_clinico.xlsx"
    # Exportación usando openpyxl configurado en el requirements.txt
    df.to_excel(ruta_archivo, index=False, sheet_name="ECG Data")
    
    return send_file(ruta_archivo, as_attachment=True, download_name="Reporte_Fisiologico.xlsx")

if __name__ == '__main__':
    # Render asigna el puerto dinámicamente mediante la variable de entorno PORT
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
