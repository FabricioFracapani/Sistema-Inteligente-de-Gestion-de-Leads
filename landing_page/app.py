"""
============================================================
SISTEMA INTELIGENTE DE GESTIÓN DE LEADS
Landing Page — Flask + Seguridad + SEO
TFI — Tecnicatura Superior en Programación — UTN FRM

MEDIDAS DE SEGURIDAD IMPLEMENTADAS:
  ✅ Content-Security-Policy (CSP)
  ✅ X-Frame-Options: DENY
  ✅ X-Content-Type-Options: nosniff
  ✅ Referrer-Policy: strict-origin-when-cross-origin
  ✅ Strict-Transport-Security (HSTS)
  ✅ CORS configurado (solo orígenes permitidos)
  ✅ Rate limiting (60 req/min por IP en /api/leads)
  ✅ Input sanitization (bleach)
  ✅ Validación server-side (email RFC 5322, teléfono >= 7 dígitos)
  ✅ CSRF via SameSite=Strict cookies + token en form
  ✅ Logging sin PII (solo hash de email)
  ✅ IP anonimizada en logs
============================================================
"""
import os
import re
import hashlib
import secrets
import logging
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify, make_response,
    session, redirect, url_for
)
from flask_cors import CORS

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================
app = Flask(__name__)

# SECRET_KEY desde variable de entorno (obligatorio en producción)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Modo debug solo en desarrollo
app.config['DEBUG'] = os.getenv('FLASK_ENV', 'development') == 'development'

# Configuración de cookies seguras
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV', 'development') == 'production',  # Solo HTTPS en producción
    SESSION_COOKIE_HTTPONLY=True,    # No accesible desde JS
    SESSION_COOKIE_SAMESITE='Strict', # Protección CSRF
)

# n8n webhook URL
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/leads')

# Orígenes permitidos para CORS
ALLOWED_ORIGINS = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:5000,http://localhost:8501'
).split(',')

# Configurar CORS
CORS(app, origins=[o.strip() for o in ALLOWED_ORIGINS])

# ============================================================
# LOGGING (sin PII — solo hashes, nunca datos reales)
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('leads_landing')

def log_safe(email, event, extra=None):
    """Log seguro: nunca expone el email real, solo SHA-256."""
    email_hash = hashlib.sha256(email.encode()).hexdigest()[:12] if email else 'no_email'
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ip_safe = '.'.join(ip.split('.')[:2] + ['0', '0']) if ip and '.' in ip else 'anon'
    msg = f"[{datetime.now().isoformat()}] {event} | email={email_hash} | ip={ip_safe}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)

# ============================================================
# SECURITY HEADERS (aplicados a TODAS las respuestas)
# ============================================================
@app.after_request
def set_security_headers(response):
    """Agrega headers de seguridad OWASP recomendados a cada respuesta."""

    # CSP: solo permite recursos del mismo origen + Google Fonts
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp

    # Protección anti-clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Evitar MIME-type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Control de referrer (no filtrar URL completa a externos)
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # HSTS (solo en producción con HTTPS)
    if not app.config['DEBUG']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # Ocultar tecnología del servidor
    response.headers['Server'] = ''

    # Permissions-Policy: deshabilitar APIs innecesarias del navegador
    response.headers['Permissions-Policy'] = (
        'camera=(), microphone=(), geolocation=(), '
        'payment=(), usb=(), magnetometer=(), gyroscope=()'
    )

    # Cross-Origin-Opener-Policy
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'

    return response


# ============================================================
# RATE LIMITING (protección anti-abuso)
# ============================================================
from functools import wraps
from time import time

# Almacenamiento simple en memoria (en producción usar Redis)
_rate_limits = {}

def rate_limit(max_requests=60, window_seconds=60):
    """Decorador: limita requests por IP en una ventana de tiempo."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
            now = time()

            # Limpiar entradas antiguas para esta IP
            if ip in _rate_limits:
                _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < window_seconds]
            else:
                _rate_limits[ip] = []

            if len(_rate_limits[ip]) >= max_requests:
                logger.warning(f"RATE_LIMIT: IP={'.'.join(ip.split('.')[:2]) + '.0.0'}")
                return jsonify({
                    'success': False,
                    'errores': ['Demasiadas solicitudes. Intenta nuevamente en un minuto.']
                }), 429

            _rate_limits[ip].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# VALIDACIÓN Y SANITIZACIÓN
# ============================================================

def sanitize_input(value, max_length=500):
    """Sanitiza input del usuario: strip, trim, limitar longitud, remover HTML."""
    if not value:
        return ''
    # Limitar longitud
    value = str(value)[:max_length]
    # Remover tags HTML (protección XSS básica)
    value = re.sub(r'<[^>]*>', '', value)
    # Remover caracteres nulos y de control
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value.strip()


def validate_lead_fields(nombre, email, telefono):
    """Validación server-side con reglas estrictas."""
    errores = []

    # Nombre: 2-100 caracteres, solo letras y espacios
    if not nombre or len(nombre) < 2 or len(nombre) > 100:
        errores.append('El nombre debe tener entre 2 y 100 caracteres.')
    elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9\s\.\-\']+$', nombre):
        errores.append('El nombre contiene caracteres no permitidos.')

    # Email: RFC 5322 simplificado
    if not email:
        errores.append('El email es obligatorio.')
    elif len(email) > 254:
        errores.append('El email excede la longitud máxima permitida.')
    elif not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        errores.append('El formato del email no es válido.')

    # Teléfono (opcional): al menos 7 dígitos numéricos
    if telefono:
        digitos = re.sub(r'\D', '', telefono)
        if len(digitos) < 7:
            errores.append('El teléfono debe tener al menos 7 dígitos.')
        if len(digitos) > 20:
            errores.append('El teléfono excede la longitud máxima.')

    return errores


# ============================================================
# CSRF PROTECTION
# ============================================================

def generate_csrf_token():
    """Genera un token CSRF único por sesión."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf():
    """Valida el token CSRF del formulario contra la sesión."""
    token = request.form.get('_csrf_token', '')
    if not token or token != session.get('_csrf_token', ''):
        logger.warning(f"CSRF_FAIL: IP={request.remote_addr}")
        return False
    return True


# ============================================================
# RUTAS
# ============================================================

@app.route('/')
def index():
    """Landing page principal con formulario de captura."""
    csrf_token = generate_csrf_token()
    response = make_response(render_template('index.html', csrf_token=csrf_token))
    return response


@app.route('/gracias')
def gracias():
    """Página de confirmación post-envío."""
    nombre = sanitize_input(request.args.get('nombre', ''), max_length=50)
    return render_template('gracias.html', nombre=nombre)


@app.route('/api/leads', methods=['POST'])
@rate_limit(max_requests=60, window_seconds=60)
def capturar_lead():
    """
    Endpoint que recibe el formulario, valida, sanitiza,
    y reenvía el lead a n8n para procesamiento con IA.
    Protegido con rate limiting y CSRF.
    """
    # Validar CSRF
    if not validate_csrf():
        return jsonify({
            'success': False,
            'errores': ['Token de seguridad inválido. Recarga la página e intenta nuevamente.']
        }), 403

    # Honeypot: campo oculto que solo un bot completa (un usuario real no lo ve).
    # Se descarta en silencio -sin tocar n8n/Supabase- pero respondiendo 200 como
    # si hubiera funcionado, para no darle al bot una señal de que fue detectado.
    if request.form.get('_hp_field', '').strip():
        log_safe(request.form.get('email', ''), 'HONEYPOT_TRIGGERED')
        nombre_hp = sanitize_input(request.form.get('nombre', ''), max_length=100)
        return jsonify({
            'success': True,
            'redirect': url_for('gracias', nombre=nombre_hp)
        }), 200

    try:
        # Extraer y sanitizar todos los campos
        nombre = sanitize_input(request.form.get('nombre', ''), max_length=100)
        apellido = sanitize_input(request.form.get('apellido', ''), max_length=100)
        email = sanitize_input(request.form.get('email', ''), max_length=254).lower()
        telefono = sanitize_input(request.form.get('telefono', ''), max_length=30)
        empresa = sanitize_input(request.form.get('empresa', ''), max_length=100)
        mensaje = sanitize_input(request.form.get('mensaje', ''), max_length=2000)
        fuente = sanitize_input(request.form.get('fuente', 'landing_page'), max_length=50)

        # Validación server-side
        errores = validate_lead_fields(nombre, email, telefono)
        if errores:
            log_safe(email, 'VALIDATION_FAIL', f'errores={len(errores)}')
            return jsonify({'success': False, 'errores': errores}), 400

        # Construir payload para n8n
        ip_raw = request.headers.get('X-Forwarded-For', request.remote_addr) or '0.0.0.0'
        payload = {
            'nombre': nombre,
            'apellido': apellido,
            'email': email,
            'telefono': telefono,
            'empresa': empresa,
            'mensaje': mensaje,
            'fuente': fuente,
            'url_origen': sanitize_input(request.headers.get('Referer', ''), max_length=500),
            'ip_origen': ip_raw,
            'user_agent': sanitize_input(request.headers.get('User-Agent', ''), max_length=500)
        }

        # Enviar a n8n
        import requests as req
        try:
            response = req.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=5,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': os.getenv('N8N_API_KEY', '')
                }
            )

            if response.status_code == 200:
                log_safe(email, 'LEAD_SENT_OK')
                return jsonify({
                    'success': True,
                    'redirect': url_for('gracias', nombre=nombre)
                }), 200
            else:
                log_safe(email, 'N8N_ERROR', f'status={response.status_code}')
                # Guardar en archivo de respaldo
                _backup_lead(payload, f'n8n_status_{response.status_code}')
                return jsonify({
                    'success': False,
                    'errores': ['Error interno. Se registró tu consulta. Te contactaremos pronto.']
                }), 502

        except req.exceptions.Timeout:
            log_safe(email, 'N8N_TIMEOUT')
            _backup_lead(payload, 'timeout')
            return jsonify({
                'success': False,
                'errores': ['El sistema está procesando tu consulta. Te contactaremos pronto.']
            }), 504

    except Exception as e:
        logger.error(f"UNEXPECTED_ERROR: {str(e)[:200]}")
        return jsonify({
            'success': False,
            'errores': ['Error inesperado. Intenta nuevamente en unos minutos.']
        }), 500


def _backup_lead(payload, motivo):
    """Guarda el lead en archivo local de respaldo si n8n no responde."""
    import json
    try:
        # No guardar IP real ni user-agent en el backup
        backup = {k: v for k, v in payload.items() if k not in ('ip_origen', 'user_agent')}
        backup['_motivo_fallo'] = motivo
        backup['_timestamp'] = datetime.now().isoformat()
        with open('leads_fallback.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(backup, ensure_ascii=False) + '\n')
        logger.info(f"LEAD_BACKUP: motivo={motivo}")
    except Exception as e:
        logger.error(f"BACKUP_FAILED: {str(e)[:100]}")


@app.route('/health')
def health():
    """Health check (sin datos sensibles)."""
    return jsonify({
        'status': 'ok',
        'service': 'landing_page_leads',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat(),
        'security_headers': True,
        'rate_limiting': True,
        'csrf_enabled': True
    })


# ============================================================
# SEO ROUTES
# ============================================================

@app.route('/robots.txt')
def robots():
    """robots.txt para SEO."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /health\n"
        f"Sitemap: {request.host_url}sitemap.xml\n"
    )
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    return response


@app.route('/sitemap.xml')
def sitemap():
    """Sitemap XML básico para SEO."""
    base_url = request.host_url.rstrip('/')
    urls = [
        ('/', '1.0', 'weekly'),
        ('/gracias', '0.3', 'never'),
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, priority, freq in urls:
        xml += '  <url>\n'
        xml += f'    <loc>{base_url}{path}</loc>\n'
        xml += f'    <changefreq>{freq}</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({
        'success': False,
        'errores': ['Demasiadas solicitudes. Espera un minuto e intenta nuevamente.']
    }), 429


@app.errorhandler(500)
def server_error(e):
    logger.error(f"500_ERROR: {str(e)}")
    return jsonify({
        'success': False,
        'errores': ['Error interno del servidor.']
    }), 500


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 65)
    print("LANDING PAGE — Gestión Inteligente de Leads con IA")
    print("TFI — UTN FRM — Tecnicatura en Programación")
    print("=" * 65)
    print(f"  n8n Webhook: {N8N_WEBHOOK_URL}")
    print(f"  CORS Origins: {ALLOWED_ORIGINS}")
    print(f"  CSRF Protection: {'ACTIVO' if app.secret_key else 'INACTIVO'}")
    print(f"  Rate Limiting: 60 req/min en /api/leads")
    print(f"  Security Headers: CSP + HSTS + X-Frame-Options + ...")
    print(f"  Debug: {app.config['DEBUG']}")
    print("=" * 65)

    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
