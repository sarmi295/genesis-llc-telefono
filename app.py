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

@csrf.exempt
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

@csrf.exempt
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

@csrf.exempt
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

@csrf.exempt
@app.route("/gather_es", methods=["POST"])
def gather_es():
    speech_result = request.form.get('SpeechResult')
    print(f"Cliente (ES) dijo: {speech_result}")
    # ...existing code...
