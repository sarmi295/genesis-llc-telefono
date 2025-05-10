import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT = (
    "Hello, thanks for calling Genesis SA Services LLC. What's your name?\n"
    "What service do you need? (For example: Landscaping, Tree Remival, Fence Installation ...)\n"
    "What is the ideal date for the appointment?\n"
    "And what is your direction or city?\n"
    "Thank you, we will contact you soon to confirm the appointment."
)

@app.route("/voice", methods=["POST"])
def voice():
    print("[LOG] Endpoint /voice fue llamado")
    resp = VoiceResponse()
    gather = resp.gather(
        input='speech',
        action='/gather',
        method='POST',
        timeout=7,
        speechTimeout='auto',
        voice='alice',
        language='en-US'
    )
    gather.say(
        "Hello and welcome to Genesis SA Services LLC! We are honored to have you call us today. "
        "At Genesis, your satisfaction and peace of mind are our top priorities. "
        "Please let us know how we can help you: whether you need landscaping, tree removal, fence installation, or any other home service, our team is ready to assist you with professionalism and care. "
        "How can we serve you today?",
        voice='alice', language='en-US')
    # Si no hay respuesta, fallback
    resp.say(
        "We apologize for not hearing your response. If you need assistance, please call us again or visit our website at genesissaservices.com. "
        "Thank you for considering Genesis SA Services LLC. We look forward to serving you soon. Goodbye!",
        voice='alice', language='en-US')
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
    resp = VoiceResponse()
    if service:
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
    resp = VoiceResponse()
    if date:
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
    resp = VoiceResponse()
    if address:
        resp.say(
            "Thank you very much for providing your information. "
            "If you would like to leave an additional message, special request, or any extra details, please do so after the beep. "
            "You will have up to two minutes. When you finish, simply hang up or wait for the call to end. "
            "We truly appreciate your trust in Genesis SA Services LLC and look forward to serving you!",
            voice='alice', language='en-US')
        resp.record(
            action="/recording",
            method="POST",
            maxLength=120,  # Hasta 2 minutos
            playBeep=True,
            timeout=15,     # Espera hasta 15 segundos de silencio
            transcribe=True,
            transcribeCallback="/transcription"
        )
        # No agregues resp.hangup() aquí, <Record> cuelga automáticamente si el usuario cuelga o termina el tiempo
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
    with open("mensajes_clientes.txt", "a", encoding="utf-8") as f:
        f.write(f"Fecha: {str(datetime.datetime.now())}\n")
        f.write(f"De: {caller}\n")
        f.write(f"Grabación: {recording_url}\n")
        f.write(f"Transcripción: {transcription_text}\n")
        f.write("-"*40 + "\n")

def enviar_email(caller, recording_url, transcription_text):
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
        server.set_debuglevel(1)  # Activa debug SMTP para ver todo el proceso
        server.starttls()
        server.login(remitente, "dhgd lhve zvgz fxkv")
        result = server.sendmail(remitente, destinatario, msg.as_string())
        print(f"[EMAIL] Resultado sendmail: {result}")
        server.quit()
        print("Email enviado correctamente.")
    except Exception as e:
        print(f"Error enviando email: {e}")
        import traceback
        traceback.print_exc()
        # Mensaje claro para el usuario en consola
        print("[EMAIL] Verifica tu contraseña de aplicación de Gmail, acceso a internet, y revisa si Gmail bloqueó el acceso.")

@app.route("/recording", methods=["POST"])
def recording():
    recording_url = request.form.get("RecordingUrl")
    caller = request.form.get("From")
    transcription_text = request.form.get("TranscriptionText")
    print(f"Nuevo mensaje de voz de {caller}: {recording_url}")
    print(f"Transcripción recibida: {transcription_text}")

    # Guardar en archivo
    guardar_mensaje_archivo(caller, recording_url, transcription_text)
    # Enviar por email
    enviar_email(caller, recording_url, transcription_text)

    # Respuesta automática mejorada con IA
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
    return Response(str(resp), mimetype='text/xml')

@app.route("/transcription", methods=["POST"])
def transcription():
    transcription_text = request.form.get("TranscriptionText")
    print(f"Transcripción recibida: {transcription_text}")
    return ("", 204)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
