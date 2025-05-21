import os
from flask import Flask, request, Response, session, redirect, url_for, render_template_string, send_file, flash, jsonify, make_response
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
import math
import io

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

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if not session.get("admin_user"):
        return redirect(url_for("login"))
    # --- Búsqueda y filtro ---
    search = request.args.get('search', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = 10
    citas = []
    if os.path.exists("citas_clientes.txt"):
        with open("citas_clientes.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    partes = line.strip().split("|")
                    if len(partes) >= 5:
                        cita = {
                            "name": partes[0],
                            "service": partes[1],
                            "date": partes[2],
                            "address": partes[3],
                            "email": partes[4],
                            "message": partes[5] if len(partes) > 5 else ""
                        }
                        if search:
                            if (search in cita["name"].lower() or search in cita["service"].lower() or search in cita["date"].lower() or search in cita["email"].lower() or search in cita["address"].lower() or search in cita["message"].lower()):
                                citas.append(cita)
                        else:
                            citas.append(cita)
    total_citas = len(citas)
    total_pages = max(1, math.ceil(total_citas / per_page))
    citas = citas[(page-1)*per_page:page*per_page]
    mensajes = []
    if os.path.exists("mensajes_clientes.txt"):
        with open("mensajes_clientes.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    mensajes.append(line.strip())
    # --- Notificaciones ---
    notif = request.args.get('notif', '')
    # --- Estadísticas ---
    stats = {}
    months = {}
    services = {}
    for c in citas:
        m = c['date'][:7] if len(c['date']) >= 7 else 'Unknown'
        months[m] = months.get(m, 0) + 1
        s = c['service']
        services[s] = services.get(s, 0) + 1
    stats['months'] = months
    stats['services'] = services
    # Servicios únicos para el filtro
    servicios_unicos = sorted(list(set(c['service'] for c in citas)))
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genesis SA Services LLC Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
    body {
      font-family: Montserrat, Arial, sans-serif;
      background: linear-gradient(135deg, #e0f7fa 0%, #f8fafc 100%);
      margin: 0;
      color: var(--fg, #1a365d);
      transition: background 0.4s;
    }
    :root {
      --bg: #f8fafc;
      --fg: #1a365d;
      --card: #fff;
      --table: #f8fafc;
      --th: #e3eaf2;
      --empty: #b0b8c1;
      --accent1: #1a8cff;
      --accent2: #1ad18c;
      --accent-gradient: linear-gradient(90deg, #1a8cff 0%, #1ad18c 100%);
    }
    body.dark {
      --bg: #1a2332;
      --fg: #f8fafc;
      --card: #232e3c;
      --table: #232e3c;
      --th: #2d3a4a;
      --empty: #6c7a89;
      --accent1: #1ad18c;
      --accent2: #1a8cff;
      --accent-gradient: linear-gradient(90deg, #1ad18c 0%, #1a8cff 100%);
      background: linear-gradient(135deg, #232e3c 0%, #1a2332 100%);
    }
    .container {
      max-width: 1100px;
      margin: 40px auto;
      background: var(--card);
      padding: 36px 32px 32px 32px;
      border-radius: 28px;
      box-shadow: 0 4px 24px rgba(44,83,100,0.13);
      transition: background 0.4s;
    }
    .header {
      display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px;
    }
    .logo-genesis {
      width: 80px; border-radius: 18px; box-shadow: 0 2px 8px rgba(44,83,100,0.10);
    }
    .logout-btn {
      background: var(--accent1);
      color: #fff;
      padding: 11px 26px;
      border: none;
      border-radius: 14px;
      font-weight: 700;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.2s;
      margin-left: 10px;
      box-shadow: 0 2px 8px rgba(26,140,255,0.10);
    }
    .logout-btn:hover {
      background: var(--accent2);
    }
    .dark-toggle {
      background: var(--accent2);
      color: #fff;
      border: none;
      border-radius: 14px;
      padding: 10px 20px;
      margin-left: 18px;
      cursor: pointer;
      font-size: 1em;
      transition: background 0.2s;
      box-shadow: 0 2px 8px rgba(26,209,140,0.10);
    }
    .dark-toggle:hover {
      background: var(--accent1);
    }
    h1 {
      color: var(--fg);
      font-size: 2.3em;
      margin: 0 0 8px 0;
    }
    .summary-cards {
      display: flex; gap: 24px; margin-bottom: 32px;
    }
    .card {
      flex: 1;
      background: var(--accent-gradient);
      border-radius: 22px;
      padding: 28px 20px;
      box-shadow: 0 2px 12px rgba(44,83,100,0.10);
      display: flex; align-items: center; gap: 18px;
      color: #fff;
      transition: background 0.4s;
    }
    body.dark .card {
      background: var(--accent-gradient);
      color: #fff;
    }
    .card i {
      font-size: 2.5em;
      color: #fff;
      filter: drop-shadow(0 2px 6px rgba(26,140,255,0.10));
    }
    .card .info {
      display: flex; flex-direction: column;
    }
    .card .info .label {
      font-size: 1.1em; color: #e0f7fa;
    }
    .card .info .value {
      font-size: 1.7em; font-weight: 700; color: #fff;
    }
    .section {margin-bottom: 38px;}
    .section h2 {color: var(--fg); font-size: 1.3em; margin-bottom: 12px;}
    table {
      width: 100%; border-collapse: collapse; margin-bottom: 18px; background: var(--table); border-radius: 16px; overflow: hidden;
      box-shadow: 0 2px 8px rgba(44,83,100,0.07);
    }
    th, td {padding: 14px 12px; text-align: left;}
    th {
      background: var(--th); color: var(--fg); font-weight: 700;
      border-bottom: 2px solid var(--accent1);
    }
    tr {transition: background 0.15s;}
    tr:hover {background: #e0f7fa;}
    body.dark tr:hover {background: #2d3a4a;}
    td {color: var(--fg);}
    .empty {color: var(--empty); font-style: italic;}
    ul {padding-left: 18px;}
    li {margin-bottom: 7px; color: var(--fg);}
    .notif {
      background: #eafaf1; color: #1a7f37; border: 1px solid #b7e4c7; padding: 12px 22px; border-radius: 12px; margin-bottom: 18px; font-weight: 600;
      box-shadow: 0 2px 8px rgba(26,209,140,0.07);
    }
    .notif.error {background: #fdecea; color: #c0392b; border: 1px solid #f5c6cb;}
    .pagination {display: flex; gap: 8px; margin-bottom: 18px;}
    .pagination button {
      background: var(--accent1); color: #fff; border: none; border-radius: 10px; padding: 8px 18px; cursor: pointer; font-size: 1em;
      transition: background 0.2s;
    }
    .pagination button.active, .pagination button:disabled {
      background: var(--accent2); color: #fff; cursor: not-allowed;
    }
    .edit-btn, .delete-btn {
      background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 7px 14px; margin-right: 4px; cursor: pointer; font-size: 1em;
      transition: background 0.2s;
    }
    .edit-btn:hover {background: var(--accent1);}
    .delete-btn {background: #fdecea; color: #c0392b;}
    .delete-btn:hover {background: #f5c6cb; color: #fff;}
    .add-form {
      background: var(--th); padding: 22px 18px; border-radius: 14px; margin-bottom: 18px;
      box-shadow: 0 2px 8px rgba(44,83,100,0.07);
    }
    .add-form input, .add-form textarea {
      width: 100%; padding: 9px 12px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #b0b8c1;
      font-size: 1em;
    }
    .add-form button {
      background: var(--accent1); color: #fff; border: none; border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 1em;
      transition: background 0.2s;
    }
    .add-form button:hover {background: var(--accent2);}
    .add-form label {font-weight: 600; color: var(--fg);}
    .download-btn {
      background: var(--accent1); color: #fff; border: none; border-radius: 8px; padding: 9px 20px; margin-right: 8px; font-size: 1em; cursor: pointer;
      transition: background 0.2s;
    }
    .download-btn:hover {background: var(--accent2);}
    @media (max-width: 800px) {
      .summary-cards {flex-direction: column; gap: 12px;}
      .container {padding: 18px 4vw;}
      table, th, td {font-size: 0.97em;}
    }
    </style>
    </head>
    <body>
    <div class="container">
      <div class="header">
        <img src="/static/logo_genesis.png" alt="Genesis Logo" class="logo-genesis"/>
        <div>
          <button class="dark-toggle" onclick="toggleDark()"><i class="fas fa-moon"></i> Dark Mode</button>
          <button class="logout-btn" onclick="window.location.href='/logout'"><i class="fas fa-sign-out-alt"></i> Logout</button>
        </div>
      </div>
      <h1>Genesis SA Services LLC</h1>
      <p style="color:#5a6a85; margin-bottom:28px;">Welcome, <b>{{user}}</b>! Here you can manage appointments and voicemails.</p>
      {% if notif %}<div class="notif">{{notif}}</div>{% endif %}
      <div class="summary-cards">
        <div class="card"><i class="fas fa-calendar-check"></i><div class="info"><span class="label">Appointments</span><span class="value">{{total}}</span></div></div>
        <div class="card"><i class="fas fa-voicemail"></i><div class="info"><span class="label">Voicemails</span><span class="value">{{mensajes|length}}</span></div></div>
      </div>
      <div class="section">
        <h2><i class="fas fa-search"></i> Search & Filter</h2>
        <form method="get" style="margin-bottom:18px;display:flex;gap:12px;flex-wrap:wrap;">
          <input name="search" value="{{request.args.get('search','')}}" placeholder="Search by name, service, email..." style="padding:7px 10px;border-radius:6px;border:1px solid #b0b8c1;min-width:180px;">
          <button type="submit" class="download-btn"><i class="fas fa-search"></i> Search</button>
        </form>
        <div style="margin-bottom:10px;">
          <button class="download-btn" onclick="window.location.href='/export_pdf'">Export PDF</button>
          <button class="download-btn" onclick="window.location.href='/export_csv'">Export CSV</button>
        </div>
        {% if citas %}
        <table><tr><th>Name</th><th>Service</th><th>Date</th><th>Address</th><th>Email</th><th>Message</th><th>Actions</th></tr>
        {% for c in citas %}<tr>
          <td>{{c.name}}</td><td>{{c.service}}</td><td>{{c.date}}</td><td>{{c.address}}</td><td>{{c.email}}</td><td>{{c.message}}</td>
          <td>
            <form method="post" action="/edit_appointment" style="display:inline;">
              <input type="hidden" name="old_name" value="{{c.name}}">
              <input type="hidden" name="old_date" value="{{c.date}}">
              <button class="edit-btn" type="submit"><i class="fas fa-edit"></i></button>
            </form>
            <form method="post" action="/delete_appointment" style="display:inline;" onsubmit="return confirm('Delete this appointment?');">
              <input type="hidden" name="name" value="{{c.name}}">
              <input type="hidden" name="date" value="{{c.date}}">
              <button class="delete-btn" type="submit"><i class="fas fa-trash"></i></button>
            </form>
          </td>
        </tr>{% endfor %}
        </table>
        <div class="pagination">
          {% for p in range(1, total_pages+1) %}
            <form method="get" style="display:inline;">
              <input type="hidden" name="search" value="{{request.args.get('search','')}}">
              <button type="submit" name="page" value="{{p}}" {% if p==page %}class="active" disabled{% endif %}>{{p}}</button>
            </form>
          {% endfor %}
        </div>
        {% else %}<div class="empty">No appointments found.</div>{% endif %}
      </div>
      <div class="section">
        <h2><i class="fas fa-voicemail"></i> Voicemail Messages</h2>
        <button class="download-btn" onclick="window.location.href='/download_voicemails'">Download All Voicemails</button>
        {% if mensajes %}
        <ul>{% for m in mensajes %}<li>{{m}}</li>{% endfor %}</ul>
        {% else %}<div class="empty">No voicemail messages found.</div>{% endif %}
      </div>
      <div class="section">
        <h2><i class="fas fa-chart-bar"></i> Statistics</h2>
        <canvas id="statsChart" height="80"></canvas>
      </div>
    </div>
    <script>
    // Dark mode toggle
    function toggleDark() {
      document.body.classList.toggle('dark');
      localStorage.setItem('dark', document.body.classList.contains('dark'));
    }
    if(localStorage.getItem('dark')==='true'){document.body.classList.add('dark');}
    // Chart.js statistics
    fetch('/stats_data').then(r=>r.json()).then(data=>{
      new Chart(document.getElementById('statsChart').getContext('2d'), {
        type: 'bar', data: {labels: data.months, datasets: [{label: 'Appointments per Month', data: data.counts, backgroundColor: '#1a365d'}]},
        options: {plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
      });
    });
    </script>
    </body>
    </html>
    ''', user=session["admin_user"], citas=citas, mensajes=mensajes, total=total_citas, page=page, total_pages=total_pages, servicios_unicos=servicios_unicos, notif=notif)

# --- Agregar cita manualmente ---
@app.route("/add_appointment", methods=["POST"])
def add_appointment():
    if not session.get("admin_user"):
        return redirect(url_for("login"))
    data = [request.form.get(k, "").strip() for k in ["name","service","date","address","email","message"]]
    if not all(data[:5]):
        return redirect(url_for("admin_panel", notif="All fields except message are required!"))
    with open("citas_clientes.txt", "a", encoding="utf-8") as f:
        f.write("|".join(data)+"\n")
    return redirect(url_for("admin_panel", notif="Appointment added!"))

# --- Eliminar cita ---
@app.route("/delete_appointment", methods=["POST"])
def delete_appointment():
    if not session.get("admin_user"):
        return redirect(url_for("login"))
    name = request.form.get("name", "")
    date = request.form.get("date", "")
    new_lines = []
    deleted = False
    with open("citas_clientes.txt", "r", encoding="utf-8") as f:
        for line in f:
            partes = line.strip().split("|")
            if len(partes) >= 3 and partes[0] == name and partes[2] == date:
                deleted = True
                continue
            new_lines.append(line)
    with open("citas_clientes.txt", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return redirect(url_for("admin_panel", notif="Appointment deleted!" if deleted else "Appointment not found!"))

# --- Editar cita (formulario y guardado) ---
@app.route("/edit_appointment", methods=["POST"])
def edit_appointment():
    if not session.get("admin_user"):
        return redirect(url_for("login"))
    old_name = request.form.get("old_name", "")
    old_date = request.form.get("old_date", "")
    # Buscar cita
    cita = None
    with open("citas_clientes.txt", "r", encoding="utf-8") as f:
        for line in f:
            partes = line.strip().split("|")
            if len(partes) >= 3 and partes[0] == old_name and partes[2] == old_date:
                cita = partes
                break
    if not cita:
        return redirect(url_for("admin_panel", notif="Appointment not found!"))
    # Mostrar formulario de edición
    return render_template_string('''
    <html><head><title>Edit Appointment</title></head><body style="font-family:Montserrat;padding:40px;">
    <h2>Edit Appointment</h2>
    <form method="post" action="/save_appointment">
      <input type="hidden" name="old_name" value="{{cita[0]}}">
      <input type="hidden" name="old_date" value="{{cita[2]}}">
      Name: <input name="name" value="{{cita[0]}}" required><br><br>
      Service: <input name="service" value="{{cita[1]}}" required><br><br>
      Date: <input name="date" type="date" value="{{cita[2]}}" required><br><br>
      Address: <input name="address" value="{{cita[3]}}" required><br><br>
      Email: <input name="email" value="{{cita[4]}}" required><br><br>
      Message: <input name="message" value="{{cita[5] if len(cita)>5 else ''}}"><br><br>
      <button type="submit">Save</button>
      <a href="/admin">Cancel</a>
    </form></body></html>
    ''', cita=cita)

@app.route("/save_appointment", methods=["POST"])
def save_appointment():
    if not session.get("admin_user"):
        return redirect(url_for("login"))
    old_name = request.form.get("old_name", "")
    old_date = request.form.get("old_date", "")
    new_data = [request.form.get(k, "").strip() for k in ["name","service","date","address","email","message"]]
    if not all(new_data[:5]):
        return redirect(url_for("admin_panel", notif="All fields except message are required!"))
    new_lines = []
    updated = False
    with open("citas_clientes.txt", "r", encoding="utf-8") as f:
        for line in f:
            partes = line.strip().split("|")
            if len(partes) >= 3 and partes[0] == old_name and partes[2] == old_date:
                new_lines.append("|".join(new_data)+"\n")
                updated = True
            else:
                new_lines.append(line)
    with open("citas_clientes.txt", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return redirect(url_for("admin_panel", notif="Appointment updated!" if updated else "Appointment not found!"))

# --- Exportar citas a CSV ---
@app.route("/export_csv")
def export_csv():
    citas = []
    if os.path.exists("citas_clientes.txt"):
        with open("citas_clientes.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    partes = line.strip().split("|")
                    if len(partes) >= 5:
                        citas.append(partes)
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Name","Service","Date","Address","Email","Message"])
    for c in citas:
        cw.writerow(c[:6])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=appointments.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# --- Descargar mensajes de voz como TXT ---
@app.route("/download_voicemails")
def download_voicemails():
    mensajes = []
    if os.path.exists("mensajes_clientes.txt"):
        with open("mensajes_clientes.txt", "r", encoding="utf-8") as f:
            mensajes = [line.strip() for line in f if line.strip()]
    si = io.StringIO()
    for m in mensajes:
        si.write(m+"\n")
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=voicemails.txt"
    output.headers["Content-type"] = "text/plain"
    return output

# --- Estadísticas para Chart.js ---
@app.route("/stats_data")
def stats_data():
    import calendar
    from collections import Counter
    citas = []
    if os.path.exists("citas_clientes.txt"):
        with open("citas_clientes.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    partes = line.strip().split("|")
                    if len(partes) >= 3:
                        citas.append(partes)
    # Citas por mes
    months = []
    counts = []
    by_month = Counter()
    for c in citas:
        try:
            y,m,_ = c[2].split("-")
            month = f"{calendar.month_abbr[int(m)]} {y}"
            by_month[month] += 1
        except:
            continue
    for k in sorted(by_month, key=lambda x: (int(x.split()[1]), list(calendar.month_abbr).index(x.split()[0]))):
        months.append(k)
        counts.append(by_month[k])
    return jsonify({"months":months, "counts":counts})

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

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/add_test_data")
def add_test_data():
    # Agrega citas de prueba
    with open("citas_clientes.txt", "a", encoding="utf-8") as f:
        f.write("John Doe|Landscaping|2025-06-01|123 Main St|john@example.com|Please call before coming.\n")
        f.write("Jane Smith|Tree Removal|2025-06-03|456 Oak Ave|jane@example.com|Backyard only.\n")
    # Agrega mensajes de voz de prueba
    with open("mensajes_clientes.txt", "a", encoding="utf-8") as f:
        f.write("John Doe: Please call me back about my landscaping appointment.\n")
        f.write("Jane Smith: I need a tree removed urgently.\n")
    return "Test data added! <a href='/admin'>Go to Admin Panel</a>"

@app.route("/export_pdf")
def export_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io
    citas = []
    if os.path.exists("citas_clientes.txt"):
        with open("citas_clientes.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    partes = line.strip().split("|")
                    if len(partes) >= 5:
                        citas.append(partes)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, 750, "Genesis SA Services LLC - Appointments")
    c.setFont("Helvetica", 11)
    y = 720
    for i, cita in enumerate(citas):
        c.drawString(30, y, f"{i+1}. Name: {cita[0]}, Service: {cita[1]}, Date: {cita[2]}, Address: {cita[3]}, Email: {cita[4]}, Message: {cita[5] if len(cita)>5 else ''}")
        y -= 22
        if y < 60:
            c.showPage()
            y = 750
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="appointments.pdf", mimetype="application/pdf")

# --- Agregar datos de ejemplo si es necesario al iniciar la app ---
def auto_add_test_data():
    # Solo agrega si no hay citas ni mensajes
    if not os.path.exists("citas_clientes.txt") or os.path.getsize("citas_clientes.txt") == 0:
        with open("citas_clientes.txt", "a", encoding="utf-8") as f:
            f.write("John Doe|Landscaping|2025-06-01|123 Main St|john@example.com|Please call before coming.\n")
            f.write("Jane Smith|Tree Removal|2025-06-03|456 Oak Ave|jane@example.com|Backyard only.\n")
    if not os.path.exists("mensajes_clientes.txt") or os.path.getsize("mensajes_clientes.txt") == 0:
        with open("mensajes_clientes.txt", "a", encoding="utf-8") as f:
            f.write("John Doe: Please call me back about my landscaping appointment.\n")
            f.write("Jane Smith: I need a tree removed urgently.\n")

# Ejecutar la función al iniciar el script
auto_add_test_data()
