import os
from flask import Flask, request, Response, session, redirect, url_for, render_template_string, send_file
from twilio.twiml.voice_response import VoiceResponse
import openai
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import bcrypt
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import csv
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Cambia esto en producción
csrf = CSRFProtect(app)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Advertencia sobre HTTPS en producción
# if not app.debug and not os.getenv('RENDER', '').lower() == 'true':
#     @app.before_request
#     def enforce_https():
#         if not request.is_secure:
#             return '<b>Warning:</b> This admin panel should be accessed over HTTPS for security.', 403

PROMPT = (
    "Hello, thanks for calling Genesis SA Services LLC. What's your name?\n"
    "What service do you need? (For example: Landscaping, Tree Remival, Fence Installation ...)\n"
    "What is the ideal date for the appointment?\n"
    "And what is your direction or city?\n"
    "Thank you, we will contact you soon to confirm the appointment."
)

GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def check_admin_login(username, password):
    try:
        with open("admins.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    user, hashed = line.strip().split(":", 1)
                    if user == username and bcrypt.checkpw(password.encode(), hashed.encode()):
                        return True
    except Exception as e:
        print(f"[SECURITY] Error leyendo admins.txt: {e}")
    return False

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if check_admin_login(username, password):
            session["admin_user"] = username
            return redirect(url_for("admin_panel"))
        else:
            error = "Invalid credentials. Please try again."
    return render_template_string('''
    <html><head><title>Admin Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
    <style>body{font-family:Montserrat;background:#f8fafc;display:flex;align-items:center;justify-content:center;height:100vh;}
    .login-box{background:#fff;padding:32px 28px;border-radius:14px;box-shadow:0 2px 12px rgba(44,83,100,0.13);max-width:340px;width:100%;}
    h2{color:#1a365d;margin-bottom:18px;}
    input{width:100%;padding:9px 12px;margin-bottom:14px;border-radius:7px;border:1px solid #b0b8c1;}
    button{width:100%;background:#1a365d;color:#fff;padding:10px 0;border:none;border-radius:7px;font-weight:700;font-size:1.1em;}
    .error{color:#c0392b;margin-bottom:10px;}
    .logo-genesis{display:block;margin:0 auto 18px auto;width:90px;border-radius:10px;box-shadow:0 2px 8px rgba(44,83,100,0.10);}
    </style></head><body>
    <form class="login-box" method="post">
        <img src="/static/logo_genesis.png" alt="Genesis Logo" class="logo-genesis"/>
        <h2>Admin Login</h2>
        {% if error %}<div class="error">{{error}}</div>{% endif %}
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}"/>
        <input name="username" placeholder="Username" required autofocus>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form></body></html>
    ''', error=error, csrf_token=generate_csrf())

@app.route("/logout")
def logout():
    session.pop("admin_user", None)
    return redirect(url_for("home"))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/voice", methods=["POST"])
def voice():
    resp = VoiceResponse()
    gather = resp.gather(
        input='speech',
        action='/gather_name',
        method='POST',
        timeout=7,
        speechTimeout='auto',
        voice='alice',
        language='en-US'
    )
    gather.say(
        "Hello and welcome to Genesis SA Services LLC! We are honored to receive your call today. At Genesis, your satisfaction and peace of mind are our priority. May I have your name, please?",
        voice='alice', language='en-US')
    resp.say(
        "We could not hear your response. If you need help, please call us again or visit genesissaservices.com. Thank you for trusting Genesis SA Services LLC! Goodbye.",
        voice='alice', language='en-US')
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_language", methods=["POST"])
def gather_language():
    speech_result = request.form.get('SpeechResult', '').lower()
    print(f"[LOG] Selección de idioma o agente: {speech_result}")
    resp = VoiceResponse()
    if 'español' in speech_result or 'spanish' in speech_result:
        resp.redirect('/voice_es')
    elif 'agent' in speech_result or 'agente' in speech_result:
        resp.say("Transferring you to a human agent. Please wait.", voice='alice', language='en-US')
        # Aquí puedes poner el número real de un agente humano
        resp.dial('+1XXXXXXXXXX')
        resp.hangup()
    else:
        resp.redirect('/voice')
    return Response(str(resp), mimetype='text/xml')

@app.route("/voice_es", methods=["POST"])
def voice_es():
    print("[LOG] Endpoint /voice_es fue llamado")
    resp = VoiceResponse()
    gather = resp.gather(
        input='speech',
        action='/gather_es',
        method='POST',
        timeout=7,
        speechTimeout='auto',
        voice='alice',
        language='es-ES'
    )
    gather.say(
        "¡Hola y bienvenido a Genesis SA Services LLC! Nos sentimos honrados de recibir su llamada hoy. En Genesis, su satisfacción y tranquilidad son nuestra prioridad. ¿Me puede decir su nombre, por favor?",
        voice='alice', language='es-ES')
    resp.say(
        "No pudimos escuchar su respuesta. Si necesita ayuda, por favor llámenos de nuevo o visite genesissaservices.com. ¡Gracias por confiar en Genesis SA Services LLC! Adiós.",
        voice='alice', language='es-ES')
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_es", methods=["POST"])
def gather_es():
    speech_result = request.form.get('SpeechResult')
    print(f"Cliente (ES) dijo: {speech_result}")
    ia_response = "Gracias por su mensaje. Nos pondremos en contacto pronto."
    if speech_result:
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente telefónico profesional y amable para una empresa de servicios a domicilio. Responde de forma útil, concisa y educada. Si el usuario solicita un servicio, confirma la solicitud y pide más detalles si es necesario."},
                    {"role": "user", "content": speech_result}
                ]
            )
            ia_response = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error con OpenAI: {e}")
    resp = VoiceResponse()
    resp.say(ia_response, voice='alice', language='es-ES')
    resp.gather(
        input='speech',
        action='/gather_es',
        method='POST',
        timeout=5,
        speechTimeout='auto',
        language='es-ES'
    )
    resp.say("Gracias por llamar. ¡Adiós!", voice='alice', language='es-ES')
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

@app.route("/ia_conversation", methods=["POST"])
def ia_conversation():
    speech_result = request.form.get('SpeechResult')
    print(f"Cliente dijo: {speech_result}")
    ia_response = "Thank you for your message. We will contact you soon."
    error_ia = False
    if speech_result:
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional, friendly phone assistant for a home services company. Answer in a helpful, concise, and polite way. If the user requests a service, confirm the request and ask for more details if needed. Always keep the conversation going until the user says goodbye or hangs up."},
                    {"role": "user", "content": speech_result}
                ]
            )
            ia_response = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error con OpenAI: {e}")
            ia_response = "Sorry, there was an error with our AI service. Please try again later or leave a message after the beep."
            error_ia = True
    resp = VoiceResponse()
    resp.say(ia_response, voice='alice', language='en-US')
    if not error_ia:
        resp.gather(
            input='speech',
            action='/ia_conversation',
            method='POST',
            timeout=7,
            speechTimeout='auto'
        )
        resp.say("Thank you for calling. Goodbye!", voice='alice', language='en-US')
        resp.hangup()
    else:
        resp.record(
            action="/recording",
            method="POST",
            maxLength=120,
            playBeep=True,
            timeout=15,
            transcribe=True,
            transcribeCallback="/transcription"
        )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_name", methods=["POST"])
def gather_name():
    name = request.form.get('SpeechResult')
    print(f"Nombre del cliente: {name}")
    resp = VoiceResponse()
    if name:
        # Guardar nombre en archivo temporal
        with open("cita_temp.txt", "w", encoding="utf-8") as f:
            f.write(f"{name}")
        resp.say(f"Nice to meet you, {name}! What service do you need? For example: Landscaping, Tree Removal, or Fence Installation.", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_service',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    else:
        resp.say("Sorry, I didn't catch your name. May I have your name, please?", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_name',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_service", methods=["POST"])
def gather_service():
    service = request.form.get('SpeechResult')
    print(f"Servicio solicitado: {service}")
    # Leer nombre del archivo temporal
    try:
        with open("cita_temp.txt", "r", encoding="utf-8") as f:
            nombre = f.read().strip()
    except Exception:
        nombre = None
    resp = VoiceResponse()
    if service:
        # Guardar nombre y servicio en archivo temporal
        with open("cita_temp.txt", "w", encoding="utf-8") as f:
            f.write(f"{nombre}|:|{service}")
        resp.say(f"Great! When would you like to schedule your {service}? Please say the ideal date.", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_date',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    else:
        resp.say("Sorry, I didn't catch the service you need. Could you please repeat it?", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_service',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_date", methods=["POST"])
def gather_date():
    date = request.form.get('SpeechResult')
    print(f"Fecha ideal: {date}")
    # Leer nombre y servicio del archivo temporal
    try:
        with open("cita_temp.txt", "r", encoding="utf-8") as f:
            datos = f.read().split("|:|")
            if len(datos) == 2:
                nombre, servicio = datos
            else:
                nombre = servicio = None
    except Exception:
        nombre = servicio = None
    resp = VoiceResponse()
    if date:
        # Guardar nombre, servicio y fecha en archivo temporal
        with open("cita_temp.txt", "w", encoding="utf-8") as f:
            f.write(f"{nombre}|:|{servicio}|:|{date}")
        resp.say(f"Thank you! Finally, could you tell me your address or city?", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_address',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    else:
        resp.say("Sorry, I didn't catch the date. Could you please repeat it?", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_date',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_address", methods=["POST"])
def gather_address():
    address = request.form.get('SpeechResult')
    print(f"Dirección o ciudad: {address}")
    nombre = request.args.get('nombre')
    servicio = request.args.get('servicio')
    fecha = request.args.get('fecha')
    # Recuperar datos previos del archivo temporal si existen
    try:
        with open("cita_temp.txt", "r", encoding="utf-8") as f:
            datos = f.read().split("|:|")
            if len(datos) == 3:
                nombre, servicio, fecha = datos
    except Exception:
        pass
    resp = VoiceResponse()
    if address:
        # Guardar todos los datos en archivo temporal
        with open("cita_temp.txt", "w", encoding="utf-8") as f:
            f.write(f"{nombre}|:|{servicio}|:|{fecha}|:|{address}")
        resp.say(
            "Thank you very much for providing your information. If you would like to receive a confirmation by email, please say your email address now. If not, just stay silent.",
            voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_email',
            method='POST',
            timeout=7,
            speechTimeout='auto'
        )
    else:
        resp.say("Sorry, I didn't catch your address. Could you please repeat it?", voice='alice', language='en-US')
        resp.gather(
            input='speech',
            action='/gather_address',
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather_email", methods=["POST"])
def gather_email():
    email = request.form.get('SpeechResult')
    print(f"Email del cliente: {email}")
    resp = VoiceResponse()
    # Guardar el email en la sesión o pasarlo a la grabación
    resp.say(
        "Thank you! If you would like to leave an additional message, special request, or any extra details, please do so after the beep. You will have up to two minutes. When you finish, simply hang up or wait for the call to end. We truly appreciate your trust in Genesis SA Services LLC and look forward to serving you!",
        voice='alice', language='en-US')
    resp.record(
        action=f"/recording?client_email={email}",
        method="POST",
        maxLength=120,
        playBeep=True,
        timeout=15,
        transcribe=True,
        transcribeCallback="/transcription"
    )
    return Response(str(resp), mimetype='text/xml')

@app.route("/gather", methods=["POST"])
def gather():
    speech_result = request.form.get('SpeechResult')
    print(f"Cliente dijo: {speech_result}")
    ia_response = "Thank you for your message. We will contact you soon."
    if speech_result:
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional and friendly phone assistant for a home services company. Answer in a helpful, concise, and polite way. If the user requests a service, confirm the request and ask for more details if needed."},
                    {"role": "user", "content": speech_result}
                ]
            )
            ia_response = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error con OpenAI: {e}")
    resp = VoiceResponse()
    resp.say(ia_response, voice='alice', language='en-US')
    # Permite seguir conversando
    resp.gather(
        input='speech',
        action='/gather',
        method='POST',
        timeout=5,
        speechTimeout='auto'
    )
    resp.say("Thank you for calling. Goodbye!", voice='alice', language='en-US')
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

def guardar_mensaje_archivo(caller, recording_url, transcription_text):
    import os
    import datetime
    try:
        path = os.path.abspath("mensajes_clientes.txt")
        print(f"[VOICEMAIL] Guardando mensaje en: {path}")
        print(f"[VOICEMAIL] Existe antes de escribir? {os.path.exists(path)}")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"Fecha: {str(datetime.datetime.now())}\n")
                f.write(f"De: {caller}\n")
                f.write(f"Grabación: {recording_url}\n")
                f.write(f"Transcripción: {transcription_text}\n")
                f.write("-"*40 + "\n")
            print(f"[VOICEMAIL] Mensaje guardado correctamente.")
        except PermissionError as pe:
            print(f"[VOICEMAIL ERROR] Permiso denegado al escribir en {path}: {pe}")
        except Exception as e:
            print(f"[VOICEMAIL ERROR] Error al escribir en archivo: {e}")
        print(f"[VOICEMAIL] Existe después de escribir? {os.path.exists(path)} Tamaño: {os.path.getsize(path) if os.path.exists(path) else 'N/A'} bytes")
    except Exception as e:
        print(f"[VOICEMAIL ERROR] No se pudo guardar el mensaje: {e}")
        import traceback
        print(traceback.format_exc())

# Endpoint de depuración para admins: muestra estado y contenido de mensajes_clientes.txt
@app.route('/debug_voicemail_file')
@admin_required
def debug_voicemail_file():
    import os, datetime
    path = os.path.abspath('mensajes_clientes.txt')
    exists = os.path.exists(path)
    info = ''
    content = ''
    if exists:
        stat = os.stat(path)
        info = f"<b>File path:</b> {path}<br>"
        info += f"<b>Exists:</b> Yes<br>"
        info += f"<b>Size:</b> {stat.st_size} bytes<br>"
        info += f"<b>Last modified:</b> {datetime.datetime.fromtimestamp(stat.st_mtime)}<br>"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                preview = lines[:10] + (["...\n"] if len(lines)>20 else []) + lines[-10:] if len(lines)>20 else lines
                content = '<pre style="background:#f4f6fa;padding:12px;border-radius:8px;max-height:400px;overflow:auto;">' + ''.join(preview) + '</pre>'
        except Exception as e:
            content = f"<b>Error reading file:</b> {e}"
    else:
        info = f"<b>File path:</b> {path}<br><b>Exists:</b> No<br>"
        content = "<i>No voicemail file found.</i>"
    return f"""
    <html><head><title>Debug Voicemail File</title></head><body style='font-family:Montserrat,sans-serif;background:#f8fafc;color:#23272f;'>
    <div style='max-width:700px;margin:40px auto;background:#fff;padding:28px 18px;border-radius:14px;box-shadow:0 2px 12px rgba(44,83,100,0.13);'>
    <h2 style='color:#1a365d;'>Voicemail File Debug</h2>
    {info}
    <h3>File Content Preview:</h3>
    {content}
    <a href='/admin' style='display:inline-block;margin-top:18px;background:#1a365d;color:#fff;padding:9px 22px;border-radius:8px;text-decoration:none;font-weight:700;'>Back to Admin Panel</a>
    </div></body></html>
    """

def enviar_email(caller, recording_url, transcription_text, client_email=None):
    remitente = "sagenesis94@gmail.com"
    destinatario = "sarmientosarmi5@gmail.com"  # Cambia aquí si quieres otro correo
    asunto = "📞 Nuevo mensaje de voz de un cliente - Genesis SA Services LLC"
    cuerpo = f"""
    Hola equipo de Genesis SA Services LLC,

    Han recibido un nuevo mensaje de voz de un cliente potencial o actual.

    Detalles del mensaje:
    ──────────────────────────────
    • Teléfono del cliente: {caller}
    • Fecha y hora: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    • Enlace a la grabación de voz: {recording_url}.mp3
    • Transcripción automática:
    {transcription_text if transcription_text else 'No disponible.'}
    ──────────────────────────────

    Por favor, atienda este mensaje lo antes posible para brindar una excelente experiencia al cliente.

    ¡Gracias por confiar en Genesis SA Services LLC!
    """
    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain"))
    try:
        print("[EMAIL] Intentando enviar email...")
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.set_debuglevel(1)
        server.starttls()
        server.login(remitente, GMAIL_PASSWORD)
        result = server.sendmail(remitente, destinatario, msg.as_string())
        print(f"[EMAIL] Resultado sendmail: {result}")
        server.quit()
        print("Email enviado correctamente.")
        # Si el cliente dejó su email, envía confirmación
        if client_email:
            enviar_confirmacion_cliente(client_email)
    except Exception as e:
        print(f"Error enviando email: {e}")
        import traceback
        traceback.print_exc()
        print("[EMAIL] Verifica tu contraseña de aplicación de Gmail, acceso a internet, y revisa si Gmail bloqueó el acceso.")

# Nueva función para enviar confirmación al cliente

def enviar_confirmacion_cliente(client_email):
    remitente = "sagenesis94@gmail.com"
    asunto = "Gracias por contactarnos - Genesis SA Services LLC"
    cuerpo = """
    Hola,

    Gracias por contactarnos. Hemos recibido su mensaje y nos pondremos en contacto con usted lo antes posible para confirmar su cita o responder a su solicitud.

    ¡Gracias por confiar en Genesis SA Services LLC!
    """
    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = client_email
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain"))
    try:
        print(f"[EMAIL] Enviando confirmación a cliente: {client_email}")
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(remitente, GMAIL_PASSWORD)
        server.sendmail(remitente, client_email, msg.as_string())
        server.quit()
        print("Confirmación enviada al cliente.")
    except Exception as e:
        print(f"Error enviando confirmación al cliente: {e}")

# BASE PARA ALERTAS SMS AUTOMÁTICAS AL ADMINISTRADOR
# Puedes activar esto si tienes saldo en Twilio y configuras las credenciales
from twilio.rest import Client as TwilioClient

def enviar_sms_admin(mensaje):
    try:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
        admin_number = os.getenv('ADMIN_PHONE_NUMBER')  # Tu número personal
        if not all([account_sid, auth_token, twilio_number, admin_number]):
            print('[SMS] Faltan variables de entorno para SMS')
            return
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(
            body=mensaje,
            from_=twilio_number,
            to=admin_number
        )
        print(f'[SMS] Notificación enviada: {mensaje}')
    except Exception as e:
        print(f'[SMS] Error enviando SMS: {e}')

# Llama a esta función en /recording para notificar cada nueva cita o mensaje
# Ejemplo de uso:
# enviar_sms_admin(f'Nuevo mensaje de voz de {caller}. Revisa tu email o panel.')

# Guardar cita automáticamente al finalizar el flujo guiado en inglés
@app.route("/recording", methods=["POST"])
def recording():
    recording_url = request.form.get("RecordingUrl")
    caller = request.form.get("From")
    transcription_text = request.form.get("TranscriptionText")
    client_email = request.args.get("client_email")
    # Extraer datos de la cita del archivo temporal si existen
    try:
        with open("cita_temp.txt", "r", encoding="utf-8") as f:
            datos = f.read().split("|:|")
            if len(datos) == 4:
                nombre, servicio, fecha, direccion = datos
            else:
                nombre = servicio = fecha = direccion = None
    except Exception:
        nombre = servicio = fecha = direccion = None
    # Guardar cita si hay datos suficientes
    if nombre and servicio and fecha and direccion:
        guardar_cita(nombre, servicio, fecha, direccion, client_email)
        # Notificación SMS automática al admin
        enviar_sms_admin(f'Nueva cita/mensaje de voz de {nombre} ({caller}). Revisa tu email o panel.')
    print(f"Nuevo mensaje de voz de {caller}: {recording_url}")
    print(f"Transcripción recibida: {transcription_text}")
    print(f"Email recogido: {client_email}")
    guardar_mensaje_archivo(caller, recording_url, transcription_text)
    enviar_email(caller, recording_url, transcription_text, client_email)
    ia_response = (
        "Thank you for leaving your message. Our team at Genesis SA Services LLC truly appreciates your trust. "
        "We will review your request and contact you as soon as possible to provide the best service. "
        "Have a wonderful day!"
    )
    if transcription_text:
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional and friendly phone assistant for a home services company. Answer in a helpful, concise, and polite way. If the user requests a service, confirm the request and say that someone will contact them soon."},
                    {"role": "user", "content": transcription_text}
                ]
            )
            ia_response = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error con OpenAI: {e}")
    resp = VoiceResponse()
    resp.say(ia_response, voice='alice', language='en-US')
    resp.hangup()
    # Limpia el archivo temporal
    try:
        os.remove("cita_temp.txt")
    except Exception:
        pass
    return Response(str(resp), mimetype='text/xml')

@app.route("/transcription", methods=["POST"])
def transcription():
    transcription_text = request.form.get("TranscriptionText")
    print(f"Transcripción recibida: {transcription_text}")
    return ("", 204)

# Estructura para guardar datos de cita y base para integración con Google Calendar

def guardar_cita(nombre, servicio, fecha, direccion, email):
    cita = {
        'nombre': nombre,
        'servicio': servicio,
        'fecha': fecha,
        'direccion': direccion,
        'email': email,
        'timestamp': str(datetime.datetime.now())
    }
    with open("citas_clientes.txt", "a", encoding="utf-8") as f:
        f.write(str(cita) + "\n")
    print(f"[CITA] Guardada: {cita}")
    # Aquí puedes llamar a la función de integración con Google Calendar
    # crear_evento_google_calendar(cita)

# Base para integración futura con Google Calendar

def crear_evento_google_calendar(cita):
    # Aquí iría la lógica para crear un evento en Google Calendar usando la API
    # Por ejemplo, usando google-api-python-client
    print(f"[GOOGLE CALENDAR] Evento a crear: {cita}")
    # TODO: Implementar integración real
    pass

# Panel web de administración básico para ver citas
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_panel():
    try:
        from flask import request
        citas = []
        try:
            with open('citas_clientes.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        cita = eval(line.strip())
                        citas.append(cita)
                    except Exception:
                        continue
        except FileNotFoundError:
            citas = []
        # Filtrado de citas en Python antes de renderizar
        search = request.args.get('search','').lower()
        service = request.args.get('service','')
        date = request.args.get('date','')
        filtered_citas = []
        for c in citas:
            if search and not (search in str(c['nombre']).lower() or search in str(c['email']).lower() or search in str(c['direccion']).lower()):
                continue
            if service and c['servicio'] != service:
                continue
            if date and date not in str(c['fecha']):
                continue
            filtered_citas.append(c)
        citas = filtered_citas
        # Paginación
        page = int(request.args.get('page', 1))
        per_page = 10
        total = len(citas)
        total_pages = (total + per_page - 1) // per_page
        citas_pag = citas[(page-1)*per_page:page*per_page]
        if request.args.get('export') == '1':
            from io import StringIO, BytesIO
            si = StringIO()
            cw = csv.writer(si)
            cw.writerow(["Name", "Service", "Date", "Address", "Email", "Registered"])
            for cita in citas:
                cw.writerow([cita['nombre'], cita['servicio'], cita['fecha'], cita['direccion'], cita['email'], cita['timestamp']])
            output = BytesIO()
            output.write(si.getvalue().encode('utf-8'))
            output.seek(0)
            return send_file(output, as_attachment=True, download_name="genesis_appointments.csv", mimetype='text/csv')
        # Exportar PDF
        if request.args.get('export_pdf') == '1':
            from io import BytesIO
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            elements = []
            styles = getSampleStyleSheet()
            title = Paragraph("Citas - Genesis SA Services LLC", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 18))
            data = [["Nombre", "Servicio", "Fecha", "Dirección", "Email", "Registrado"]]
            for cita in citas:
                data.append([
                    cita['nombre'], cita['servicio'], cita['fecha'], cita['direccion'], cita['email'], cita['timestamp']
                ])
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a365d')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(table)
            doc.build(elements)
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name="genesis_appointments.pdf", mimetype='application/pdf')
        # Inicializar html vacío para evitar errores de referencia
        html = ''
        # Si se solicita enviar recordatorios desde el panel
        reminder_message = ''
        if request.args.get('send_reminders') == '1':
            enviados = enviar_recordatorios_citas()
            reminder_message = f'<div style="background:#eaf0f6;padding:12px 0;color:#1a365d;font-weight:600;">{enviados} reminder(s) sent for tomorrow\'s appointments.</div>'
        # Mostrar mensajes de voz si se solicita la pestaña 'voicemails'
        show_voicemails = request.args.get('tab') == 'voicemails'
        voicemails = []
        if show_voicemails:
            try:
                with open('mensajes_clientes.txt', 'r', encoding='utf-8') as f:
                    mensaje = {}
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('Fecha:'):
                            mensaje['fecha'] = line.replace('Fecha:','').strip()
                        elif line.startswith('De:'):
                            mensaje['telefono'] = line.replace('De:','').strip()
                        elif line.startswith('Grabación:'):
                            mensaje['grabacion'] = line.replace('Grabación:','').strip()
                        elif line.startswith('Transcripción:'):
                            mensaje['transcripcion'] = line.replace('Transcripción:','').strip()
                        elif line.startswith('----------------------------------------'):
                            if mensaje and any(mensaje.values()):
                                voicemails.append(mensaje)
                            mensaje = {}
                    # Si el archivo termina sin separador, agregar el último mensaje si tiene datos
                    if mensaje and any(mensaje.values()):
                        voicemails.append(mensaje)
            except Exception as e:
                import traceback
                print(f"[VOICEMAIL ERROR] {e}\n{traceback.format_exc()}")
                voicemails = []
            html = reminder_message + '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Admin Panel - Genesis SA Services LLC</title>
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
                <style>
                    body {
                        font-family: 'Montserrat', Arial, sans-serif;
                        background: #f4f6fa;
                        color: #23272f;
                        margin: 0;
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: flex-start;
                    }
                    .panel-container {
                        background: #fff;
                        border-radius: 16px;
                        box-shadow: 0 4px 16px 0 rgba(44, 62, 80, 0.10);
                        padding: 32px 18px 24px 18px;
                        max-width: 900px;
                        width: 98vw;
                        margin: 40px 0 32px 0;
                        text-align: center;
                        border: 1px solid #e0e4ea;
                    }
                    h2 {
                        color: #1a365d;
                        margin-bottom: 10px;
                        font-size: 2em;
                        font-weight: 700;
                        letter-spacing: 0.5px;
                    }
                    .export-btn {
                        display: inline-block;
                        background: #1a365d;
                        color: #fff;
                        padding: 9px 22px;
                        border: none;
                        border-radius: 8px;
                        font-size: 1em;
                        font-weight: 700;
                        text-decoration: none;
                        margin: 14px 0 14px 0;
                        transition: background 0.18s, box-shadow 0.18s;
                        box-shadow: 0 2px 8px rgba(44,83,100,0.08);
                        cursor: pointer;
                        letter-spacing: 0.2px;
                    }
                    .export-btn:hover {
                        background: #274472;
                    }
                    .export-btn.gray {
                        background: #e6eaf3;
                        color: #1a365d;
                    }
                    .export-btn.gray:hover {
                        background: #d1d8e6;
                        color: #23272f;
                    }
                    .export-btn.green {
                        background: #2ecc71;
                        color: #fff;
                    }
                    .export-btn.green:hover {
                        background: #27ae60;
                    }
                    .table-responsive {
                        overflow-x: auto;
                        margin-top: 14px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 0 auto;
                        background: #fff;
                        border-radius: 10px;
                        box-shadow: 0 1px 4px rgba(44,83,100,0.06);
                        overflow: hidden;
                    }
                    th, td {
                        padding: 10px 8px;
                        text-align: left;
                    }
                    th {
                        background: #1a365d;
                        color: #fff;
                        font-weight: 700;
                        font-size: 1em;
                        border-bottom: 2px solid #e0e4ea;
                    }
                    tr:nth-child(even) {
                        background: #f4f6fa;
                    }
                    tr:nth-child(odd) {
                        background: #fff;
                    }
                    tr:hover {
                        background: #eaf0f6 !important;
                        transition: background 0.15s;
                    }
                    @media (max-width: 700px) {
                        .panel-container {
                            padding: 12px 2vw 12px 2vw;
                            max-width: 99vw;
                        }
                        table, th, td {
                            font-size: 0.97em;
                        }
                        .logo-genesis {
                            width: 70px !important;
                        }
                    }
                    .filter-bar {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 10px;
                        justify-content: center;
                        margin-bottom: 14px;
                    }
                    .filter-bar input, .filter-bar select {
                        padding: 6px 10px;
                        border-radius: 6px;
                        border: 1px solid #b0b8c1;
                        font-family: 'Montserrat', Arial, sans-serif;
                        font-size: 1em;
                        background: #fff;
                        color: #23272f;
                    }
                    .filter-bar label {
                        font-weight: 600;
                        color: #1a365d;
                        margin-right: 4px;
                    }
                    .pagination {
                        display: flex;
                        justify-content: center;
                        margin: 14px 0 0 0;
                        gap: 5px;
                    }
                    .pagination a, .pagination span {
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 6px;
                        background: #e6eaf3;
                        color: #1a365d;
                        font-weight: 700;
                        text-decoration: none;
                        margin: 0 2px;
                        border: 1px solid #b0b8c1;
                        transition: background 0.18s, color 0.18s;
                    }
                    .pagination a:hover {
                        background: #1a365d;
                        color: #fff;
                    }
                    .pagination .active {
                        background: #2ecc71;
                        color: #fff;
                        pointer-events: none;
                    }
                    .action-btn {
                        padding: 6px 12px;
                        border-radius: 6px;
                        border: none;
                        font-family: 'Montserrat', Arial, sans-serif;
                        font-size: 1em;
                        font-weight: 700;
                        margin: 0 2px;
                        cursor: pointer;
                        transition: background 0.18s;
                    }
                    .delete-btn {
                        background: #e74c3c;
                        color: #fff;
                    }
                    .delete-btn:hover {
                        background: #c0392b;
                    }
                    .edit-btn {
                        background: #2ecc71;
                        color: #fff;
                    }
                    .edit-btn:hover {
                        background: #27ae60;
                    }
                </style>
                <script>
                function confirmDelete(idx) {
                    if(confirm('Are you sure you want to delete this appointment?')) {
                        window.location.href = '?delete=' + idx + '&page={{page}}&search={{request.args.get('search','')}}&service={{request.args.get('service','')}}&date={{request.args.get('date','')}}';
                    }
                }
                </script>
            </head>
            <body>
                <div class="panel-container">
                    <img src="/static/logo_genesis.png" alt="Genesis Logo" class="logo-genesis" style="width:90px;margin-bottom:14px;box-shadow:0 2px 8px rgba(44,83,100,0.10);border-radius:10px;">
                    <h2>{% if show_voicemails %}Voicemails{% else %}Appointments Panel{% endif %} - Genesis SA Services LLC</h2>
                    <div class="filter-bar">
                        {% if show_voicemails %}
                        <a href="/admin?tab=appointments" class="export-btn gray">Appointments</a>
                        <a href="/admin?tab=voicemails" class="export-btn">Voicemails</a>
                        {% else %}
                        <form method="get" style="display:inline-block;">
                            <label>Search: <input type="text" name="search" value="{{request.args.get('search','')}}"></label>
                            <label>Service: <input type="text" name="service" value="{{request.args.get('service','')}}"></label>
                            <label>Date: <input type="date" name="date" value="{{request.args.get('date','')}}"></label>
                            <button type="submit" class="export-btn green">Filter</button>
                            <a href="/admin" class="export-btn gray">Clear</a>
                        </form>
                        <a href="?export=1" class="export-btn">Export CSV</a>
                        <a href="?export_pdf=1" class="export-btn gray">Export PDF</a>
                        <a href="?send_reminders=1" class="export-btn green">Send Reminders</a>
                        <a href="?tab=voicemails" class="export-btn gray">Voicemails</a>
                        <a href="?tab=appointments" class="export-btn">Appointments</a>
                        {% endif %}
                    </div>
                    <div class="table-responsive">
                        <table>
                            {% if show_voicemails %}
                            <tr><th>Date</th><th>Phone</th><th>Recording</th><th>Transcription</th></tr>
                            {% if voicemails|length == 0 %}
                            <tr><td colspan="4" style="text-align:center;color:#888;font-style:italic;">No voicemails registered.</td></tr>
                            {% else %}
                            {% for v in voicemails %}
                            <tr>
                                <td>{{v.get('fecha','')}}</td>
                                <td>{{v.get('telefono','')}}</td>
                                <td>{% if v.get('grabacion') %}<a href="{{v['grabacion']}}.mp3" target="_blank">Listen</a>{% else %}-{% endif %}</td>
                                <td style="max-width:320px;white-space:pre-wrap;">{{v.get('transcripcion','')}}</td>
                            </tr>
                            {% endfor %}
                            {% endif %}
                            {% endif %}
                            {% if not show_voicemails %}
                            <tr><th>Name</th><th>Service</th><th>Date</th><th>Address</th><th>Email</th><th>Registered</th><th>Actions</th></tr>
                            {% for c in citas_pag %}
                            <tr>
                                <td>{{c['nombre']}}</td>
                                <td>{{c['servicio']}}</td>
                                <td>{{c['fecha']}}</td>
                                <td>{{c['direccion']}}</td>
                                <td>{{c['email']}}</td>
                                <td>{{c['timestamp']}}</td>
                                <td>
                                    <a href="?edit={{loop.index0}}" class="action-btn edit-btn">Edit</a>
                                    <button onclick="confirmDelete({{loop.index0}})" class="action-btn delete-btn">Delete</button>
                                </td>
                            </tr>
                            {% endfor %}
                            {% endif %}
                        </table>
                    </div>
                    <div class="pagination">
                        {% for p in range(1, total_pages+1) %}
                            {% if p == page %}
                                <span class="active">{{p}}</span>
                            {% else %}
                                <a href="?page={{p}}&search={{request.args.get('search','')}}&service={{request.args.get('service','')}}&date={{request.args.get('date','')}}">{{p}}</a>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
            </body>
            </html>
            '''
        else:
            # Asignar el HTML principal del panel de citas cuando no es voicemails
            html = reminder_message + '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Appointments Panel - Genesis SA Services LLC</title>
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
                <style>
                body {
                    font-family: 'Montserrat', Arial, sans-serif;
                    background: linear-gradient(135deg, #eaf0f6 0%, #f8fafc 100%);
                    color: #23272f;
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-start;
                }
                .panel-container {
                    background: #fff;
                    border-radius: 18px;
                    box-shadow: 0 6px 32px 0 rgba(44, 62, 80, 0.13);
                    padding: 38px 24px 28px 24px;
                    max-width: 1100px;
                    width: 98vw;
                    margin: 48px 0 36px 0;
                    text-align: center;
                    border: 1px solid #e0e4ea;
                    position: relative;
                }
                h2 {
                    color: #1a365d;
                    margin-bottom: 18px;
                    font-size: 2.3em;
                    font-weight: 800;
                    letter-spacing: 0.5px;
                }
                .logo-genesis {
                    display: block;
                    margin: 0 auto 18px auto;
                    width: 110px;
                    border-radius: 14px;
                    box-shadow: 0 2px 8px rgba(44,83,100,0.10);
                }
                .export-btn {
                    display: inline-block;
                    background: #1a365d;
                    color: #fff;
                    padding: 11px 28px;
                    border: none;
                    border-radius: 10px;
                    font-size: 1.08em;
                    font-weight: 700;
                    text-decoration: none;
                    margin: 14px 0 14px 0;
                    transition: background 0.18s, box-shadow 0.18s;
                    box-shadow: 0 2px 8px rgba(44,83,100,0.08);
                    cursor: pointer;
                    letter-spacing: 0.2px;
                }
                .export-btn:hover {
                    background: #274472;
                }
                .export-btn.gray {
                    background: #e6eaf3;
                    color: #1a365d;
                }
                .export-btn.gray:hover {
                    background: #d1d8e6;
                    color: #23272f;
                }
                .export-btn.green {
                    background: #2ecc71;
                    color: #fff;
                }
                .export-btn.green:hover {
                    background: #27ae60;
                }
                .table-responsive {
                    overflow-x: auto;
                    margin-top: 18px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 0 auto;
                    background: #fff;
                    border-radius: 12px;
                    box-shadow: 0 1px 8px rgba(44,83,100,0.09);
                    overflow: hidden;
                }
                th, td {
                    padding: 13px 10px;
                    text-align: left;
                }
                th {
                    background: linear-gradient(90deg, #1a365d 80%, #274472 100%);
                    color: #fff;
                    font-weight: 800;
                    font-size: 1.08em;
                    border-bottom: 2px solid #e0e4ea;
                }
                tr:nth-child(even) {
                    background: #f4f6fa;
                }
                tr:nth-child(odd) {
                    background: #fff;
                }
                tr:hover {
                    background: #eaf0f6 !important;
                    transition: background 0.15s;
                }
                @media (max-width: 900px) {
                    .panel-container {
                        padding: 14px 2vw 14px 2vw;
                        max-width: 99vw;
                    }
                    table, th, td {
                        font-size: 0.98em;
                    }
                    .logo-genesis {
                        width: 70px !important;
                    }
                }
                .filter-bar {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    justify-content: center;
                    margin-bottom: 18px;
                }
                .filter-bar input, .filter-bar select {
                    padding: 8px 12px;
                    border-radius: 7px;
                    border: 1px solid #b0b8c1;
                    font-family: 'Montserrat', Arial, sans-serif;
                    font-size: 1em;
                    background: #fff;
                    color: #23272f;
                }
                .filter-bar label {
                    font-weight: 700;
                    color: #1a365d;
                    margin-right: 4px;
                }
                .pagination {
                    display: flex;
                    justify-content: center;
                    margin: 18px 0 0 0;
                    gap: 7px;
                }
                .pagination a, .pagination span {
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 8px;
                    background: #e6eaf3;
                    color: #1a365d;
                    font-weight: 800;
                    text-decoration: none;
                    margin: 0 2px;
                    border: 1px solid #b0b8c1;
                    transition: background 0.18s, color 0.18s;
                }
                .pagination a:hover {
                    background: #1a365d;
                    color: #fff;
                }
                .pagination .active {
                    background: #2ecc71;
                    color: #fff;
                    pointer-events: none;
                }
                .action-btn {
                    padding: 8px 16px;
                    border-radius: 8px;
                    border: none;
                    font-family: 'Montserrat', Arial, sans-serif;
                    font-size: 1em;
                    font-weight: 700;
                    margin: 0 2px;
                    cursor: pointer;
                    transition: background 0.18s;
                }
                .delete-btn {
                    background: #e74c3c;
                    color: #fff;
                }
                .delete-btn:hover {
                    background: #c0392b;
                }
                .edit-btn {
                    background: #2ecc71;
                    color: #fff;
                }
                .edit-btn:hover {
                    background: #27ae60;
                }
                /* NUEVO: Tarjeta resumen arriba */
                .summary-cards {
                    display: flex;
                    gap: 24px;
                    justify-content: center;
                    margin-bottom: 24px;
                    flex-wrap: wrap;
                }
                .summary-card {
                    background: linear-gradient(120deg, #1a365d 80%, #2ecc71 100%);
                    color: #fff;
                    border-radius: 14px;
                    box-shadow: 0 2px 12px rgba(44,83,100,0.13);
                    padding: 22px 36px;
                    min-width: 180px;
                    font-size: 1.25em;
                    font-weight: 700;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .summary-card .big {
                    font-size: 2.1em;
                    font-weight: 900;
                    margin-bottom: 6px;
                }
                </style>
                <script>
                function confirmDelete(idx) {
                    if(confirm('Are you sure you want to delete this appointment?')) {
                        window.location.href = '?delete=' + idx + '&page={{page}}&search={{request.args.get('search','')}}&service={{request.args.get('service','')}}&date={{request.args.get('date','')}}';
                    }
                }
                </script>
            </head>
            <body>
                <div class="panel-container">
                    <img src="/static/logo_genesis.png" alt="Genesis Logo" class="logo-genesis">
                    <h2>Appointments Panel - Genesis SA Services LLC</h2>
                    <div class="summary-cards">
                        <div class="summary-card">
                            <span class="big">{{ total }}</span>
                            Total Appointments
                        </div>
                        <div class="summary-card" style="background:linear-gradient(120deg,#2ecc71 80%,#1a365d 100%);">
                            <span class="big">{{ citas_pag|length }}</span>
                            On this page
                        </div>
                    </div>
                    <div class="filter-bar">
                        <form method="get" style="display:inline-block;">
                            <label>Search: <input type="text" name="search" value="{{request.args.get('search','')}}"></label>
                            <label>Service: <input type="text" name="service" value="{{request.args.get('service','')}}"></label>
                            <label>Date: <input type="date" name="date" value="{{request.args.get('date','')}}"></label>
                            <button type="submit" class="export-btn green">Filter</button>
                            <a href="/admin" class="export-btn gray">Clear</a>
                        </form>
                        <a href="?export=1" class="export-btn">Export CSV</a>
                        <a href="?export_pdf=1" class="export-btn gray">Export PDF</a>
                        <a href="?send_reminders=1" class="export-btn green">Send Reminders</a>
                        <a href="?tab=voicemails" class="export-btn gray">Voicemails</a>
                        <a href="?tab=appointments" class="export-btn">Appointments</a>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <tr><th>Name</th><th>Service</th><th>Date</th><th>Address</th><th>Email</th><th>Registered</th><th>Actions</th></tr>
                            {% for c in citas_pag %}
                            <tr>
                                <td>{{c['nombre']}}</td>
                                <td>{{c['servicio']}}</td>
                                <td>{{c['fecha']}}</td>
                                <td>{{c['direccion']}}</td>
                                <td>{{c['email']}}</td>
                                <td>{{c['timestamp']}}</td>
                                <td>
                                    <a href="?edit={{loop.index0}}" class="action-btn edit-btn">Edit</a>
                                    <button onclick="confirmDelete({{loop.index0}})" class="action-btn delete-btn">Delete</button>
                                </td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                    <div class="pagination">
                        {% for p in range(1, total_pages+1) %}
                            {% if p == page %}
                                <span class="active">{{p}}</span>
                            {% else %}
                                <a href="?page={{p}}&search={{request.args.get('search','')}}&service={{request.args.get('service','')}}&date={{request.args.get('date','')}}">{{p}}</a>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
            </body>
            </html>
            '''
    except Exception as e:
        import traceback
        error_msg = f"<h2 style='color:#c0392b'>Internal Server Error</h2><pre>{traceback.format_exc()}</pre>"
        print(traceback.format_exc())
        return error_msg, 500

    # AUDITORÍA DE ACCIONES ADMINISTRATIVAS
    def registrar_auditoria(usuario, accion, detalles):
        with open('admin_audit.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now().isoformat()} | {usuario} | {accion} | {detalles}\n")

    # Procesar eliminación si corresponde
    delete_idx = request.args.get('delete')
    if delete_idx is not None and delete_idx.isdigit():
        delete_idx = int(delete_idx)
        if 0 <= delete_idx < len(citas):
            cita_eliminada = citas[delete_idx]
            del citas[delete_idx]
            # Guardar el archivo actualizado
            with open('citas_clientes.txt', 'w', encoding='utf-8') as f:
                for c in citas:
                    c.pop('__idx__', None)
                    f.write(str(c) + "\n")
            # Registrar auditoría
            registrar_auditoria(session.get('admin_user','?'), 'delete', f"Cita: {cita_eliminada}")
            # Redirigir para evitar re-envío
            from flask import redirect, url_for
            args = request.args.to_dict()
            args.pop('delete', None)
            url = url_for('admin_panel', **args)
            return redirect(url)
    # Procesar edición si corresponde
    edit_idx = request.args.get('edit')
    if edit_idx is not None and edit_idx.isdigit():
        edit_idx = int(edit_idx)
        if 0 <= edit_idx < len(citas):
            cita_edit = citas[edit_idx]
            # Si se envió el formulario de edición (POST)
            if request.method == 'POST':
                form = request.form
                old_cita = cita_edit.copy()
                cita_edit['nombre'] = form.get('nombre', cita_edit['nombre'])
                cita_edit['servicio'] = form.get('servicio', cita_edit['servicio'])
                cita_edit['fecha'] = form.get('fecha', cita_edit['fecha'])
                cita_edit['direccion'] = form.get('direccion', cita_edit['direccion'])
                cita_edit['email'] = form.get('email', cita_edit['email'])
                # Guardar el archivo actualizado
                with open('citas_clientes.txt', 'w', encoding='utf-8') as f:
                    for c in citas:
                        c.pop('__idx__', None)
                        f.write(str(c) + "\n")
                # Registrar auditoría
                registrar_auditoria(session.get('admin_user','?'), 'edit', f"Antes: {old_cita} | Después: {cita_edit}")
                # Redirigir para evitar re-envío
                from flask import redirect, url_for
                args = request.args.to_dict()
                args.pop('edit', None)
                url = url_for('admin_panel', **args)
                return redirect(url)
        # Mostrar formulario de edición
        edit_form = f'''
        <form method="post" style="background:#f8fafc;padding:22px 18px;border-radius:12px;max-width:420px;margin:30px auto 0 auto;box-shadow:0 2px 8px rgba(44,83,100,0.10);">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}"/>
            <h3 style="color:#1a365d;margin-bottom:12px;">Edit Appointment</h3>
            <label>Name:<br><input name="nombre" value="{cita_edit['nombre']}" style="width:100%;padding:7px 10px;margin-bottom:10px;border-radius:6px;border:1px solid #b0b8c1;"></label><br>
            <label>Service:<br><input name="servicio" value="{cita_edit['servicio']}" style="width:100%;padding:7px 10px;margin-bottom:10px;border-radius:6px;border:1px solid #b0b8c1;"></label><br>
            <label>Date:<br><input name="fecha" value="{cita_edit['fecha']}" style="width:100%;padding:7px 10px;margin-bottom:10px;border-radius:6px;border:1px solid #b0b8c1;"></label><br>
            <label>Address:<br><input name="direccion" value="{cita_edit['direccion']}" style="width:100%;padding:7px 10px;margin-bottom:10px;border-radius:6px;border:1px solid #b0b8c1;"></label><br>
            <label>Email:<br><input name="email" value="{cita_edit['email']}" style="width:100%;padding:7px 10px;margin-bottom:10px;border-radius:6px;border:1px solid #b0b8c1;"></label><br>
            <button type="submit" class="export-btn" style="width:100%;margin-top:10px;">Save Changes</button>
            <a href="?tab=appointments" class="export-btn" style="width:100%;margin-top:10px;background:#b0b8c1;">Cancel</a>
        </form>
        '''
        return render_template_string(html + edit_form, citas_pag=citas_pag, page=page, total_pages=total_pages, request=request, csrf_token=generate_csrf())
    return render_template_string(html, citas_pag=citas_pag, page=page, total_pages=total_pages, request=request, show_voicemails=show_voicemails, csrf_token=generate_csrf())

# Manejo personalizado de errores 404
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return '''
    <h2>Página no encontrada / Page Not Found</h2>
    <p>La ruta que intentaste acceder no existe en el sistema de Genesis SA Services LLC.</p>
    <p>The page you are looking for does not exist in the Genesis SA Services LLC system.</p>
    <a href="/admin">Ir al panel de administración</a>
    ''', 404

@app.route("/")
def index():
    return redirect(url_for('admin_panel'))

def home():
    return '''
    <html><head><title>Genesis SA Services LLC</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
    <style>
    body {font-family:Montserrat,Arial,sans-serif;background:#f4f6fa;color:#23272f;margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;}
    .welcome-box {background:#fff;padding:38px 28px 32px 28px;border-radius:16px;box-shadow:0 4px 16px 0 rgba(44,62,80,0.10);max-width:420px;width:98vw;text-align:center;border:1px solid #e0e4ea;}
    h1 {color:#1a365d;margin-bottom:10px;font-size:2.1em;font-weight:700;letter-spacing:0.5px;}
    .logo-genesis{display:block;margin:0 auto 18px auto;width:110px;border-radius:12px;box-shadow:0 2px 8px rgba(44,83,100,0.10);}
    .admin-btn{display:inline-block;background:#1a365d;color:#fff;padding:13px 36px;border:none;border-radius:9px;font-size:1.1em;font-weight:700;text-decoration:none;margin:18px 0 0 0;transition:background 0.18s,box-shadow 0.18s;box-shadow:0 2px 8px rgba(44,83,100,0.08);cursor:pointer;letter-spacing:0.2px;}
    .admin-btn:hover{background:#274472;}
    </style></head><body>
    <div class="welcome-box">
        <img src="/static/logo_genesis.png" alt="Genesis Logo" class="logo-genesis"/>
        <h1>Genesis SA Services LLC</h1>
        <p style="font-size:1.13em;margin-bottom:18px;">Bienvenido al sistema de gestión de citas y mensajes.<br>Por favor, accede al panel de administración para ver o gestionar las citas y mensajes de voz.</p>
        <a href="/admin" class="admin-btn">Ir al panel de administración</a>
    </div>
    </body></html>
    '''

def enviar_recordatorios_citas():
    import os
    import datetime
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    enviados = 0
    try:
        with open('citas_clientes.txt', 'r', encoding='utf-8') as f:
            citas = []
            for line in f:
                try:
                    citas.append(eval(line.strip()))
                except Exception as e:
                    print(f"[REMINDER ERROR] Línea corrupta ignorada: {e}")
    except Exception as e:
        print(f"[REMINDER ERROR] No se pudo leer citas_clientes.txt: {e}")
        return 0
    hoy = datetime.datetime.now()
    maniana = hoy + datetime.timedelta(days=1)
    global GMAIL_PASSWORD
    for cita in citas:
        try:
            fecha_cita = cita.get('fecha', '')
            if len(fecha_cita) >= 10:
                fecha_cita_dt = datetime.datetime.strptime(fecha_cita[:10], '%Y-%m-%d')
            else:
                continue
            if fecha_cita_dt.date() == maniana.date() and cita.get('email'):
                remitente = "sagenesis94@gmail.com"
                destinatario = cita['email']
                asunto = "Appointment Reminder - Genesis SA Services LLC"
                cuerpo = f"""
                Hello {cita.get('nombre','')},\n\nThis is a friendly reminder of your appointment for {cita.get('servicio','')} scheduled on {cita.get('fecha','')} at {cita.get('direccion','')}.\n\nIf you need to reschedule, please contact us.\n\nThank you for choosing Genesis SA Services LLC!\n"""
                msg = MIMEMultipart()
                msg["From"] = remitente
                msg["To"] = destinatario
                msg["Subject"] = asunto
                msg.attach(MIMEText(cuerpo, "plain"))
                try:
                    if not GMAIL_PASSWORD:
                        print("[REMINDER EMAIL ERROR] GMAIL_PASSWORD no está configurado.")
                        continue
                    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
                    server.starttls()
                    server.login(remitente, GMAIL_PASSWORD)
                    server.sendmail(remitente, destinatario, msg.as_string())
                    server.quit()
                    enviados += 1
                except Exception as e:
                    print(f"[REMINDER EMAIL ERROR] {e}")
                # SMS opcional
                if os.getenv('TWILIO_ACCOUNT_SID') and cita.get('telefono'):
                    try:
                        from twilio.rest import Client as TwilioClient
                        client = TwilioClient(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
                        client.messages.create(
                            body=f"Genesis SA Services LLC: Reminder of your appointment for {cita.get('servicio','')} on {cita.get('fecha','')} at {cita.get('direccion','')}",
                            from_=os.getenv('TWILIO_PHONE_NUMBER'),
                            to=cita['telefono']
                        )
                    except Exception as e:
                        print(f"[REMINDER SMS ERROR] {e}")
        except Exception as e:
            print(f"[REMINDER ERROR] {e}")
    return enviados

@app.route('/admin/send_reminders_cron', methods=['POST', 'GET'])
def send_reminders_cron():
    token = request.args.get('token') or request.headers.get('X-Admin-Token')
    ADMIN_CRON_TOKEN = os.getenv('ADMIN_CRON_TOKEN', 'changeme')
    if token != ADMIN_CRON_TOKEN:
        return 'Unauthorized', 401
    enviados = enviar_recordatorios_citas()
    return f"{enviados} reminders sent for tomorrow's appointments."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
