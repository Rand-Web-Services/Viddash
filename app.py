from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for, flash, abort, g
import subprocess
import json
import os
import requests
import tempfile
import shutil
from urllib.parse import urlparse
from flask import send_file
import socket
import ipaddress
from functools import wraps
import io
import re
import zipfile
from datetime import datetime
import logging
import csv
import secrets
import sqlite3
import hashlib
import math
import time
import threading
from collections import Counter
from html import escape, unescape
from markupsafe import Markup
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

# Setup logging to file for debugging
log_file = os.path.join(os.path.dirname(__file__), "app.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also print to stdout
    ]
)
logger = logging.getLogger(__name__)

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    # Optional rate limiting (only if dependency installed)
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # pragma: no cover
    Limiter = None
    get_remote_address = None

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None

try:
    import pysrt
except Exception:  # pragma: no cover
    pysrt = None

try:
    import stripe
except Exception:  # pragma: no cover
    stripe = None


DEFAULT_SECRET_KEY = "dev-change-me-viddash-secret"
IS_PRODUCTION = os.environ.get("VIDDASH_ENV", os.environ.get("FLASK_ENV", "")).lower() == "production"
app = Flask(__name__)
app.secret_key = os.environ.get("VIDDASH_SECRET_KEY", DEFAULT_SECRET_KEY)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
)
if stripe:
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("STRIPE_RESTRICTED_KEY")
    stripe.api_version = "2026-04-22.dahlia"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@viddash.app")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@viddash.app")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.environ.get("ADMIN_EMAILS", "").split(",")
    if email.strip()
}

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = {
    "en": {"name": "English", "native": "English"},
    "es": {"name": "Spanish", "native": "Español"},
    "fr": {"name": "French", "native": "Français"},
    "pt": {"name": "Portuguese", "native": "Português"},
    "de": {"name": "German", "native": "Deutsch"},
}
LOCALE_PREFIXES = set(SUPPORTED_LOCALES) - {DEFAULT_LOCALE}

PUBLIC_PAGES = {
    "": "index.html",
    "privacy": "privacy.html",
    "terms": "terms.html",
    "dmca": "dmca.html",
    "tools": "tools.html",
    "pricing": "pricing.html",
    "resources": "resources.html",
    "faq": "faq.html",
    "signup": "signup.html",
    "login": "login.html",
    "about": "about.html",
    "contact": "contact.html",
    "guides": "guides.html",
    "help-center": "help-center.html",
    "api-documentation": "api-documentation.html",
    "video-converter": "video-converter.html",
    "facebook-downloader": "facebook-downloader.html",
    "youtube-downloader": "youtube-downloader.html",
    "tiktok-downloader": "tiktok-downloader.html",
    "video-to-audio": "video-to-audio.html",
    "audio-editor": "audio-editor.html",
    "video-resizer": "video-resizer.html",
    "video-export": "video-export.html",
    "video-compress": "video-compress.html",
    "video-watermark": "video-watermark.html",
    "utm-builder": "utm-builder.html",
    "video-clipper": "video-clipper.html",
    "video-thumbnails": "video-thumbnails.html",
    "transcript-generator": "transcript-generator.html",
    "youtube-transcript-generator": "youtube-transcript-generator.html",
}

SEO_NOINDEX_PAGES = {"login", "signup", "api-documentation"}
SEO_INDEXED_LOCALES = {DEFAULT_LOCALE}
SEO_TOOL_PAGES = {
    "": {"category": "MultimediaApplication", "free": True},
    "tools": {"category": "MultimediaApplication", "free": True},
    "facebook-downloader": {"category": "MultimediaApplication", "free": True},
    "youtube-downloader": {"category": "MultimediaApplication", "free": True},
    "tiktok-downloader": {"category": "MultimediaApplication", "free": True},
    "audio-editor": {"category": "MultimediaApplication", "free": True},
    "video-to-audio": {"category": "MultimediaApplication", "free": False},
    "video-converter": {"category": "MultimediaApplication", "free": False},
    "video-resizer": {"category": "MultimediaApplication", "free": False},
    "video-export": {"category": "MultimediaApplication", "free": False},
    "video-compress": {"category": "MultimediaApplication", "free": False},
    "video-watermark": {"category": "MultimediaApplication", "free": False},
    "video-clipper": {"category": "MultimediaApplication", "free": False},
    "video-thumbnails": {"category": "MultimediaApplication", "free": False},
    "transcript-generator": {"category": "MultimediaApplication", "free": False},
    "youtube-transcript-generator": {"category": "MultimediaApplication", "free": True},
    "utm-builder": {"category": "BusinessApplication", "free": False},
}

SEO_PAGE_FAQS = {
    "audio-editor": [
        (
            "Can I merge MP3 files online with Viddash?",
            "Yes. Add up to 10 audio files, arrange them in playback order, set optional trim points, and export one merged MP3, M4A, WAV, or FLAC file.",
        ),
        (
            "How do I cut part of an audio file?",
            "Upload the recording and enter the start and end times you want to keep. Viddash removes the audio before the start time and after the end time during export.",
        ),
        (
            "What does Studio Voice cleanup change?",
            "Studio Voice reduces steady background noise, removes very low rumble, shapes speech frequencies, compresses volume differences, and normalizes the final loudness for spoken-word listening.",
        ),
        (
            "Are uploaded audio files stored?",
            "No. Uploaded files are held temporarily for the requested edit and deleted after processing completes.",
        ),
        (
            "How many audio files can a free account process?",
            "Free accounts include three successful audio editor exports per day. Failed processing attempts do not use the daily allowance.",
        ),
    ],
    "video-converter": [
        (
            "What is the best video format for most devices?",
            "MP4 is the safest default for most phones, browsers, social platforms, and editing apps. Viddash exports MP4 with H.264 video and AAC audio for broad compatibility.",
        ),
        (
            "Does converting a video reduce its quality?",
            "Video conversion usually requires re-encoding, which can introduce some quality loss. Choose High Quality and keep the original resolution and frame rate when preserving detail matters most.",
        ),
        (
            "Should I choose MP4, MOV, WebM, or GIF?",
            "Choose MP4 for general sharing, MOV for Apple and editing workflows, WebM for web delivery, and GIF only for short silent animations. MKV is useful when container flexibility matters more than device compatibility.",
        ),
        (
            "Can a GIF export include audio?",
            "No. GIF is an image animation format and does not support audio. Choose MP4, MOV, MKV, AVI, or WebM when the converted file needs sound.",
        ),
        (
            "Are uploaded videos stored after conversion?",
            "No. Uploaded videos and generated conversion files are temporary and are deleted after the requested export is delivered.",
        ),
    ],
    "video-compress": [
        (
            "How can I compress a video without obvious quality loss?",
            "Use a moderate target size, keep H.264 for compatibility, and avoid reducing the file far below its original size. Larger reductions require a lower bitrate and make compression artifacts more likely.",
        ),
        (
            "Is H.264 or H.265 better for video compression?",
            "H.264 plays on more devices and platforms. H.265 can produce a smaller file at similar visual quality, but older browsers, devices, and editing apps may not support it.",
        ),
        (
            "Will the compressed video match my target size exactly?",
            "Viddash calculates a video bitrate from the duration, target size, and selected audio bitrate. The result should be close, but container overhead and the source content can cause a small difference.",
        ),
        (
            "Does compression change the video dimensions?",
            "The batch compressor focuses on bitrate and file size rather than changing the frame dimensions. Use the Video Resizer when you need a different resolution or aspect ratio.",
        ),
        (
            "Can I create several compressed sizes at once?",
            "Yes. Select preset sizes or enter custom megabyte targets. Viddash processes each version and returns the completed files together in one ZIP archive.",
        ),
    ],
    "transcript-generator": [
        (
            "What platforms are supported?",
            "Viddash supports local audio and video uploads plus URLs from platforms handled by the downloader, including YouTube, TikTok, Facebook, Instagram, and X. A source must be accessible and permitted for you to process.",
        ),
        (
            "How accurate is automatic transcription?",
            "Accuracy depends on microphone quality, background noise, speaker overlap, accents, language, and specialist vocabulary. Clear speech with little background noise produces the strongest result and every important transcript should be reviewed.",
        ),
        (
            "How long does transcription take?",
            "Existing caption tracks can be extracted quickly. Speech recognition takes longer and processing time depends on recording length, audio quality, server load, and the available hardware.",
        ),
        (
            "Which transcript format should I download?",
            "Use SRT for most video editors and subtitle uploads, VTT for HTML5 web video, TXT for a readable transcript without timing, and JSON when an application needs structured segments and timestamps.",
        ),
        (
            "Can I transcribe a private video?",
            "You can process a private source only when you are authorized to access it. For supported URL sources, session cookies can provide that access; local files can be uploaded directly from your device.",
        ),
    ],
    "video-resizer": [
        (
            "What video size should I use for Reels, TikTok, or Shorts?",
            "Use a 9:16 vertical frame at 1080 by 1920 pixels for Instagram Reels and Stories, TikTok videos, and YouTube Shorts.",
        ),
        (
            "What aspect ratio works best for an Instagram feed video?",
            "A 4:5 frame at 1080 by 1350 pixels uses more vertical feed space, while 1:1 at 1080 by 1080 pixels is the standard square option.",
        ),
        (
            "Will resizing crop part of my video?",
            "Yes. The current presets crop the source to fill the selected aspect ratio, so content near the outer edges can be removed. Keep faces, captions, and logos near the center safe area.",
        ),
        (
            "What format does the resized video use?",
            "Viddash exports resized videos as MP4 with H.264 video and AAC audio, a combination designed for broad social-platform and device compatibility.",
        ),
        (
            "Does Viddash keep uploaded videos?",
            "No. The source and resized output are temporary processing files and are deleted after the export is delivered.",
        ),
    ],
    "youtube-transcript-generator": [
        (
            "How do I get a transcript from a YouTube video?",
            "Paste a public YouTube video URL and choose a caption language. Viddash retrieves an available caption track, removes rolling-caption duplication, and builds a searchable transcript linked to the original timestamps.",
        ),
        (
            "What makes Viddash Transcript Studio different?",
            "Every paragraph, chapter draft, and key moment keeps its source timestamp. You can search the transcript, jump to the exact moment on YouTube, inspect keywords and reading time, and export standard caption formats.",
        ),
        (
            "Can Viddash transcribe a YouTube video without captions?",
            "Pro accounts can fall back to speech recognition when a usable caption track is unavailable. Free processing uses available manual or automatic YouTube captions.",
        ),
        (
            "Are the suggested chapters and key moments AI-generated?",
            "They are extractive drafts calculated from transcript timing, recurring keywords, and representative source segments. They do not invent new claims, and each suggestion links back to the source moment for review.",
        ),
        (
            "How many YouTube transcripts can a free account generate?",
            "Free accounts can generate three successful YouTube transcript projects per day from videos with available captions. Failed requests do not consume the allowance.",
        ),
    ],
}

TRANSLATIONS = {
    "es": {
        "Tools": "Herramientas",
        "Compress": "Comprimir",
        "Convert": "Convertir",
        "AI Tools": "Herramientas de IA",
        "Video Downloader": "Descargador de videos",
        "Video to Audio": "Video a audio",
        "Video Resizer": "Redimensionar video",
        "Export": "Exportar",
        "Watermark": "Marca de agua",
        "Clipper": "Recortador",
        "Thumbnails": "Miniaturas",
        "Image Resizer": "Redimensionar imagen",
        "Pricing": "Precios",
        "Resources": "Recursos",
        "FAQ": "Preguntas frecuentes",
        "Account": "Cuenta",
        "Log in": "Iniciar sesión",
        "Sign up Free": "Regístrate gratis",
        "Account required": "Cuenta requerida",
        "Create a free Viddash account to continue": "Crea una cuenta gratuita de Viddash para continuar",
        "Sign up to use this tool, save your account access, and unlock paid media processing when you need it.": "Regístrate para usar esta herramienta, guardar tu acceso y desbloquear procesamiento multimedia de pago cuando lo necesites.",
        "Your All-in-One": "Tu kit todo en uno",
        "File Conversion": "para convertir archivos",
        "100% Free • No Sign Up Required": "100% gratis • Sin registro obligatorio",
        "Convert, compress, download, transcribe, resize, watermark, and edit your media instantly. Fast, private, and ready for real creator workflows.": "Convierte, comprime, descarga, transcribe, redimensiona, marca y edita tus archivos al instante. Rápido, privado y listo para flujos de trabajo reales.",
        "Start Converting Now": "Empieza a convertir",
        "Explore All Tools": "Explorar herramientas",
        "All Tools": "Todas las herramientas",
        "Everything you need to convert, compress, edit, and optimize files. Fast, free, and easy to use.": "Todo lo que necesitas para convertir, comprimir, editar y optimizar archivos. Rápido, gratis y fácil de usar.",
        "Simple & Transparent Pricing": "Precios simples y transparentes",
        "Clear usage limits that keep conversion fast, reliable, and sustainable.": "Límites claros para mantener la conversión rápida, fiable y sostenible.",
        "Create your account": "Crea tu cuenta",
        "Start on the free plan and upgrade when you need more capacity.": "Empieza con el plan gratuito y mejora cuando necesites más capacidad.",
        "Continue with Google": "Continuar con Google",
        "or use email": "o usa el correo electrónico",
        "Name": "Nombre",
        "Email": "Correo electrónico",
        "Password": "Contraseña",
        "Create Free Account": "Crear cuenta gratuita",
        "Already have an account?": "¿Ya tienes una cuenta?",
        "Welcome back": "Bienvenido de nuevo",
        "Log in to manage your plan, usage, and future API access.": "Inicia sesión para gestionar tu plan, uso y futuro acceso a la API.",
        "New to Viddash?": "¿Nuevo en Viddash?",
        "Create an account": "Crear una cuenta",
    },
    "fr": {
        "Tools": "Outils",
        "Compress": "Compresser",
        "Convert": "Convertir",
        "AI Tools": "Outils IA",
        "Video Downloader": "Téléchargeur vidéo",
        "Video to Audio": "Vidéo en audio",
        "Video Resizer": "Redimensionner vidéo",
        "Export": "Exporter",
        "Watermark": "Filigrane",
        "Clipper": "Découpage",
        "Thumbnails": "Miniatures",
        "Image Resizer": "Redimensionner image",
        "Pricing": "Tarifs",
        "Resources": "Ressources",
        "FAQ": "FAQ",
        "Account": "Compte",
        "Log in": "Connexion",
        "Sign up Free": "Inscription gratuite",
        "Account required": "Compte requis",
        "Create a free Viddash account to continue": "Créez un compte Viddash gratuit pour continuer",
        "Sign up to use this tool, save your account access, and unlock paid media processing when you need it.": "Inscrivez-vous pour utiliser cet outil, conserver votre accès et débloquer le traitement média payant quand vous en avez besoin.",
        "Your All-in-One": "Votre boîte à outils",
        "File Conversion": "de conversion de fichiers",
        "100% Free • No Sign Up Required": "100 % gratuit • Pas d'inscription obligatoire",
        "Convert, compress, download, transcribe, resize, watermark, and edit your media instantly. Fast, private, and ready for real creator workflows.": "Convertissez, compressez, téléchargez, transcrivez, redimensionnez, filigranez et éditez vos médias instantanément. Rapide, privé et prêt pour les vrais workflows de création.",
        "Start Converting Now": "Commencer maintenant",
        "Explore All Tools": "Explorer les outils",
        "All Tools": "Tous les outils",
        "Everything you need to convert, compress, edit, and optimize files. Fast, free, and easy to use.": "Tout pour convertir, compresser, éditer et optimiser vos fichiers. Rapide, gratuit et simple.",
        "Simple & Transparent Pricing": "Tarifs simples et transparents",
        "Clear usage limits that keep conversion fast, reliable, and sustainable.": "Des limites claires pour garder la conversion rapide, fiable et durable.",
        "Create your account": "Créez votre compte",
        "Start on the free plan and upgrade when you need more capacity.": "Commencez gratuitement et passez à un plan supérieur quand vous avez besoin de plus de capacité.",
        "Continue with Google": "Continuer avec Google",
        "or use email": "ou utilisez l'e-mail",
        "Name": "Nom",
        "Email": "E-mail",
        "Password": "Mot de passe",
        "Create Free Account": "Créer un compte gratuit",
        "Already have an account?": "Vous avez déjà un compte ?",
        "Welcome back": "Bon retour",
        "Log in to manage your plan, usage, and future API access.": "Connectez-vous pour gérer votre plan, votre utilisation et le futur accès API.",
        "New to Viddash?": "Nouveau sur Viddash ?",
        "Create an account": "Créer un compte",
    },
    "pt": {
        "Tools": "Ferramentas",
        "Compress": "Comprimir",
        "Convert": "Converter",
        "AI Tools": "Ferramentas de IA",
        "Video Downloader": "Baixador de vídeos",
        "Video to Audio": "Vídeo para áudio",
        "Video Resizer": "Redimensionar vídeo",
        "Export": "Exportar",
        "Watermark": "Marca d'água",
        "Clipper": "Cortador",
        "Thumbnails": "Miniaturas",
        "Image Resizer": "Redimensionar imagem",
        "Pricing": "Preços",
        "Resources": "Recursos",
        "FAQ": "Perguntas frequentes",
        "Account": "Conta",
        "Log in": "Entrar",
        "Sign up Free": "Cadastre-se grátis",
        "Account required": "Conta obrigatória",
        "Create a free Viddash account to continue": "Crie uma conta gratuita da Viddash para continuar",
        "Sign up to use this tool, save your account access, and unlock paid media processing when you need it.": "Cadastre-se para usar esta ferramenta, salvar seu acesso e desbloquear processamento de mídia pago quando precisar.",
        "Your All-in-One": "Seu kit completo",
        "File Conversion": "de conversão de arquivos",
        "100% Free • No Sign Up Required": "100% grátis • Sem cadastro obrigatório",
        "Convert, compress, download, transcribe, resize, watermark, and edit your media instantly. Fast, private, and ready for real creator workflows.": "Converta, comprima, baixe, transcreva, redimensione, marque e edite sua mídia instantaneamente. Rápido, privado e pronto para fluxos reais de criação.",
        "Start Converting Now": "Comece a converter",
        "Explore All Tools": "Explorar ferramentas",
        "All Tools": "Todas as ferramentas",
        "Everything you need to convert, compress, edit, and optimize files. Fast, free, and easy to use.": "Tudo para converter, comprimir, editar e otimizar arquivos. Rápido, grátis e fácil de usar.",
        "Simple & Transparent Pricing": "Preços simples e transparentes",
        "Clear usage limits that keep conversion fast, reliable, and sustainable.": "Limites claros para manter a conversão rápida, confiável e sustentável.",
        "Create your account": "Crie sua conta",
        "Start on the free plan and upgrade when you need more capacity.": "Comece no plano gratuito e faça upgrade quando precisar de mais capacidade.",
        "Continue with Google": "Continuar com Google",
        "or use email": "ou use e-mail",
        "Name": "Nome",
        "Email": "E-mail",
        "Password": "Senha",
        "Create Free Account": "Criar conta gratuita",
        "Already have an account?": "Já tem uma conta?",
        "Welcome back": "Bem-vindo de volta",
        "Log in to manage your plan, usage, and future API access.": "Entre para gerenciar seu plano, uso e futuro acesso à API.",
        "New to Viddash?": "Novo na Viddash?",
        "Create an account": "Criar uma conta",
    },
    "de": {
        "Tools": "Tools",
        "Compress": "Komprimieren",
        "Convert": "Konvertieren",
        "AI Tools": "KI-Tools",
        "Video Downloader": "Video-Downloader",
        "Video to Audio": "Video zu Audio",
        "Video Resizer": "Video skalieren",
        "Export": "Exportieren",
        "Watermark": "Wasserzeichen",
        "Clipper": "Clipper",
        "Thumbnails": "Thumbnails",
        "Image Resizer": "Bild skalieren",
        "Pricing": "Preise",
        "Resources": "Ressourcen",
        "FAQ": "FAQ",
        "Account": "Konto",
        "Log in": "Anmelden",
        "Sign up Free": "Kostenlos registrieren",
        "Account required": "Konto erforderlich",
        "Create a free Viddash account to continue": "Erstellen Sie ein kostenloses Viddash-Konto, um fortzufahren",
        "Sign up to use this tool, save your account access, and unlock paid media processing when you need it.": "Registrieren Sie sich, um dieses Tool zu nutzen, Ihren Zugriff zu speichern und bei Bedarf kostenpflichtige Medienverarbeitung freizuschalten.",
        "Your All-in-One": "Ihr All-in-One",
        "File Conversion": "Toolkit zur Dateikonvertierung",
        "100% Free • No Sign Up Required": "100 % kostenlos • Keine Registrierung erforderlich",
        "Convert, compress, download, transcribe, resize, watermark, and edit your media instantly. Fast, private, and ready for real creator workflows.": "Konvertieren, komprimieren, herunterladen, transkribieren, skalieren, mit Wasserzeichen versehen und bearbeiten Sie Medien sofort. Schnell, privat und bereit für echte Creator-Workflows.",
        "Start Converting Now": "Jetzt konvertieren",
        "Explore All Tools": "Alle Tools ansehen",
        "All Tools": "Alle Tools",
        "Everything you need to convert, compress, edit, and optimize files. Fast, free, and easy to use.": "Alles zum Konvertieren, Komprimieren, Bearbeiten und Optimieren von Dateien. Schnell, kostenlos und einfach.",
        "Simple & Transparent Pricing": "Einfache und transparente Preise",
        "Clear usage limits that keep conversion fast, reliable, and sustainable.": "Klare Nutzungslimits halten die Konvertierung schnell, zuverlässig und nachhaltig.",
        "Create your account": "Konto erstellen",
        "Start on the free plan and upgrade when you need more capacity.": "Starten Sie kostenlos und upgraden Sie, wenn Sie mehr Kapazität benötigen.",
        "Continue with Google": "Mit Google fortfahren",
        "or use email": "oder E-Mail verwenden",
        "Name": "Name",
        "Email": "E-Mail",
        "Password": "Passwort",
        "Create Free Account": "Kostenloses Konto erstellen",
        "Already have an account?": "Sie haben bereits ein Konto?",
        "Welcome back": "Willkommen zurück",
        "Log in to manage your plan, usage, and future API access.": "Melden Sie sich an, um Plan, Nutzung und zukünftigen API-Zugriff zu verwalten.",
        "New to Viddash?": "Neu bei Viddash?",
        "Create an account": "Konto erstellen",
    },
}

# Configuration for file uploads
DEFAULT_MAX_UPLOAD_MB = 100 if IS_PRODUCTION else 500
REQUESTED_MAX_FILE_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_MB", DEFAULT_MAX_UPLOAD_MB)) * 1024 * 1024
MAX_FILE_UPLOAD_BYTES = REQUESTED_MAX_FILE_UPLOAD_BYTES
MAX_FILE_UPLOAD_BYTES_HARD_LIMIT = int(os.environ.get("MAX_UPLOAD_HARD_LIMIT_MB", 512)) * 1024 * 1024
# Ensure hard limit is respected
if MAX_FILE_UPLOAD_BYTES > MAX_FILE_UPLOAD_BYTES_HARD_LIMIT:
    MAX_FILE_UPLOAD_BYTES = MAX_FILE_UPLOAD_BYTES_HARD_LIMIT
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_UPLOAD_BYTES

# Optional: basic rate limiting if Flask-Limiter is installed
limiter = None
if Limiter and get_remote_address:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[os.environ.get("RATELIMIT_DEFAULT", "200/hour")],
        storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    )


DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE_PATH = os.environ.get("VIDDASH_DATABASE", os.path.join(os.path.dirname(__file__), "viddash.db"))
USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))
DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if psycopg:
    DB_INTEGRITY_ERRORS = DB_INTEGRITY_ERRORS + (psycopg.errors.UniqueViolation,)


def validate_production_config():
    if not IS_PRODUCTION:
        return
    errors = []
    if app.secret_key == DEFAULT_SECRET_KEY:
        errors.append("VIDDASH_SECRET_KEY must be set to a strong random value.")
    if not os.environ.get("RATELIMIT_STORAGE_URI"):
        errors.append("RATELIMIT_STORAGE_URI must point to shared storage such as Redis.")
    if not USE_POSTGRES:
        errors.append("DATABASE_URL must point to PostgreSQL for production customer data.")
    if USE_POSTGRES and psycopg is None:
        errors.append("psycopg is required for PostgreSQL DATABASE_URL support.")
    if REQUESTED_MAX_FILE_UPLOAD_BYTES > MAX_FILE_UPLOAD_BYTES_HARD_LIMIT:
        errors.append("MAX_UPLOAD_SIZE_MB cannot exceed MAX_UPLOAD_HARD_LIMIT_MB.")
    if errors:
        raise RuntimeError("Production configuration is not safe:\n- " + "\n- ".join(errors))


validate_production_config()


def get_request_locale():
    first_segment = request.path.strip("/").split("/", 1)[0]
    if first_segment in LOCALE_PREFIXES:
        return first_segment
    return DEFAULT_LOCALE


def strip_locale_from_path(path):
    normalized = path.strip("/")
    if not normalized:
        return ""
    first, _, rest = normalized.partition("/")
    if first in LOCALE_PREFIXES:
        return rest
    return normalized


def localized_path(path="/", locale=None):
    locale = locale or getattr(g, "locale", DEFAULT_LOCALE)
    parsed = urlparse(path or "/")
    clean_path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    if locale == DEFAULT_LOCALE:
        return clean_path + query
    if clean_path == "/":
        return f"/{locale}/" + query
    return f"/{locale}{clean_path}" + query


def locale_switch_path(locale):
    public_path = getattr(g, "public_page_path", None)
    if public_path is not None:
        return localized_path("/" + public_path if public_path else "/", locale)
    clean_path = "/" + strip_locale_from_path(request.path)
    if clean_path == "/":
        clean_path = request.path
    query = f"?{request.query_string.decode('utf-8')}" if request.query_string else ""
    return localized_path(clean_path + query, locale)


def translate_text(text, default=None):
    locale = getattr(g, "locale", DEFAULT_LOCALE)
    if locale == DEFAULT_LOCALE:
        return default if default is not None else text
    return TRANSLATIONS.get(locale, {}).get(text, default if default is not None else text)


def public_page_path():
    path = strip_locale_from_path(request.path)
    return path if path in PUBLIC_PAGES else None


def build_alternate_links(path):
    root = app_base_url()
    page_path = path.strip("/")
    default_url = f"{root}/{page_path}" if page_path else f"{root}/"
    links = [
        f'<link rel="alternate" hreflang="en" href="{escape(default_url, quote=True)}" />'
    ]
    for locale in sorted(SEO_INDEXED_LOCALES - {DEFAULT_LOCALE}):
        href = f"{root}/{locale}/{page_path}" if page_path else f"{root}/{locale}/"
        links.append(f'<link rel="alternate" hreflang="{locale}" href="{escape(href, quote=True)}" />')
    links.append(f'<link rel="alternate" hreflang="x-default" href="{escape(default_url, quote=True)}" />')
    return "\n    ".join(links)


def build_canonical_url(path):
    root = app_base_url()
    page_path = path.strip("/")
    if getattr(g, "locale", DEFAULT_LOCALE) == DEFAULT_LOCALE:
        return f"{root}/{page_path}" if page_path else f"{root}/"
    return f"{root}/{g.locale}/{page_path}" if page_path else f"{root}/{g.locale}/"


def render_public_page(template_name, path=None):
    if path is not None:
        g.public_page_path = path
    return render_template(template_name)


@app.before_request
def set_locale():
    g.request_started_at = time.monotonic()
    g.request_id = request.headers.get("X-Request-ID") or secrets.token_hex(8)
    g.locale = get_request_locale()
    g.public_page_path = public_page_path()


@app.context_processor
def inject_i18n_helpers():
    return {
        "current_locale": getattr(g, "locale", DEFAULT_LOCALE),
        "supported_locales": SUPPORTED_LOCALES,
        "locale_prefixes": LOCALE_PREFIXES,
        "localized_path": localized_path,
        "locale_switch_path": locale_switch_path,
        "t": translate_text,
    }


def client_ip():
    return (
        request.headers.get("CF-Connecting-IP")
        or (request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip())
        or request.remote_addr
        or ""
    )


def should_record_telemetry():
    if request.path.startswith("/static/"):
        return False
    if request.path in {"/robots.txt", "/sitemap.xml"}:
        return False
    return True


def record_request_telemetry(resp: Response) -> None:
    if not should_record_telemetry():
        return
    try:
        duration_ms = int((time.monotonic() - getattr(g, "request_started_at", time.monotonic())) * 1000)
        created_at = datetime.utcnow().isoformat(timespec="seconds")
        user_agent = (request.headers.get("User-Agent") or "")[:500]
        referrer = (request.headers.get("Referer") or "")[:500]
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO app_telemetry (
                    request_id, user_id, method, path, endpoint, status_code,
                    duration_ms, ip, user_agent, referrer, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    getattr(g, "request_id", ""),
                    session.get("user_id"),
                    request.method,
                    request.path[:300],
                    (request.endpoint or "")[:120],
                    int(resp.status_code),
                    duration_ms,
                    client_ip()[:120],
                    user_agent,
                    referrer,
                    created_at,
                ),
            )
    except Exception:
        logger.exception("Could not record request telemetry path=%s", request.path)


def _extract_head_text(body: str, pattern: str, default: str) -> str:
    match = re.search(pattern, body, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return default
    return unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() or default


def _upsert_head_meta(body: str, attribute: str, key: str, content: str) -> str:
    tag = f'<meta {attribute}="{escape(key, quote=True)}" content="{escape(content, quote=True)}" />'
    pattern = rf'<meta\s+{attribute}=["\']{re.escape(key)}["\'][^>]*>'
    if re.search(pattern, body, flags=re.IGNORECASE):
        return re.sub(pattern, tag, body, count=1, flags=re.IGNORECASE)
    return body.replace("</head>", f"    {tag}\n  </head>", 1)


def build_public_page_schema(path: str, title: str, description: str) -> dict:
    root = app_base_url()
    canonical = build_canonical_url(path)
    page_name = re.split(r"\s+[\-—–]\s+", title, maxsplit=1)[0].strip()
    graph = [
        {
            "@type": "Organization",
            "@id": f"{root}/#organization",
            "name": "Viddash App",
            "url": f"{root}/",
            "logo": {
                "@type": "ImageObject",
                "url": f"{root}/static/viddash-logo.png",
                "width": 1247,
                "height": 313,
            },
            "email": SUPPORT_EMAIL,
        },
        {
            "@type": "WebSite",
            "@id": f"{root}/#website",
            "url": f"{root}/",
            "name": "Viddash App",
            "description": "Online tools for downloading, converting, compressing, editing, and transcribing media files.",
            "publisher": {"@id": f"{root}/#organization"},
            "inLanguage": getattr(g, "locale", DEFAULT_LOCALE),
        },
    ]

    if path:
        graph.append({
            "@type": "BreadcrumbList",
            "@id": f"{canonical}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{root}/"},
                {"@type": "ListItem", "position": 2, "name": page_name, "item": canonical},
            ],
        })

    tool = SEO_TOOL_PAGES.get(path)
    if tool:
        free = bool(tool["free"])
        graph.append({
            "@type": "WebApplication",
            "@id": f"{canonical}#application",
            "name": page_name,
            "url": canonical,
            "description": description,
            "applicationCategory": tool["category"],
            "applicationSubCategory": "Online media tool",
            "operatingSystem": "Any operating system with a modern web browser",
            "browserRequirements": "JavaScript and file upload support",
            "isAccessibleForFree": free,
            "offers": {
                "@type": "Offer",
                "price": "0.00" if free else "15.00",
                "priceCurrency": "USD",
                "category": "Free tier" if free else "Pro subscription",
                "url": canonical if free else f"{root}/pricing",
            },
            "publisher": {"@id": f"{root}/#organization"},
        })

    faqs = SEO_PAGE_FAQS.get(path)
    if faqs:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in faqs
            ],
        })

    return {"@context": "https://schema.org", "@graph": graph}


# Security headers
@app.after_request
def add_security_headers(resp: Response):
    if resp.mimetype == "text/html" and getattr(g, "public_page_path", None) is not None:
        body = resp.get_data(as_text=True)
        locale = getattr(g, "locale", DEFAULT_LOCALE)
        body = re.sub(r'<html lang="[^"]*"', f'<html lang="{locale}"', body, count=1)
        canonical = f'<link rel="canonical" href="{escape(build_canonical_url(g.public_page_path), quote=True)}" />'
        if re.search(r'<link rel="canonical"[^>]*>', body):
            body = re.sub(r'<link rel="canonical"[^>]*>', canonical, body, count=1)
        else:
            body = body.replace("</head>", f"    {canonical}\n  </head>", 1)
        alternates = build_alternate_links(g.public_page_path)
        body = body.replace("</head>", f"    {Markup(alternates)}\n  </head>", 1)
        title = _extract_head_text(body, r"<title[^>]*>(.*?)</title>", "Viddash App")
        description = _extract_head_text(
            body,
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>',
            "Online tools for converting, editing, and preparing media files.",
        )
        canonical_url = build_canonical_url(g.public_page_path)
        share_image = f"{app_base_url()}/static/og-placeholder.svg"
        is_indexable = (
            g.public_page_path not in SEO_NOINDEX_PAGES
            and locale in SEO_INDEXED_LOCALES
        )
        robots = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" if is_indexable else "noindex,follow"
        for attribute, key, value in (
            ("name", "robots", robots),
            ("property", "og:type", "website"),
            ("property", "og:site_name", "Viddash App"),
            ("property", "og:title", title),
            ("property", "og:description", description),
            ("property", "og:url", canonical_url),
            ("property", "og:image", share_image),
            ("property", "og:image:width", "1200"),
            ("property", "og:image:height", "630"),
            ("name", "twitter:card", "summary_large_image"),
            ("name", "twitter:title", title),
            ("name", "twitter:description", description),
            ("name", "twitter:image", share_image),
        ):
            body = _upsert_head_meta(body, attribute, key, value)
        if is_indexable:
            schema = json.dumps(
                build_public_page_schema(g.public_page_path, title, description),
                ensure_ascii=False,
                separators=(",", ":"),
            ).replace("<", "\\u003c")
            body = body.replace("</head>", f'    <script type="application/ld+json">{schema}</script>\n  </head>', 1)
        resp.set_data(body)
        resp.headers["Content-Length"] = str(len(resp.get_data()))
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # CSP allowing our domains, CDNs, and Google AdSense
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://pagead2.googlesyndication.com https://www.googletagmanager.com https://www.google.com https://www.clarity.ms; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://i.ytimg.com https://*.fbcdn.net https://*.googleusercontent.com https://pagead2.googlesyndication.com https://*.clarity.ms; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' https://cdn.jsdelivr.net https://pagead2.googlesyndication.com https://*.adtrafficquality.google https://*.clarity.ms; "
        "frame-src 'self' https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net; "
        "frame-ancestors 'none'"
    )
    resp.headers.setdefault("Content-Security-Policy", csp)
    # HSTS should be set only when behind HTTPS in production
    if request.host and not request.host.startswith("localhost"):
        resp.headers.setdefault("Strict-Transport-Security", "max-age=15552000; includeSubDomains")
    resp.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
    record_request_telemetry(resp)
    return resp


# SSRF guard helpers
PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_TOTAL_BYTES = 100 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp"}
SEO_SLUG_RE = re.compile(r"[^a-z0-9]+")
OAUTH_PROVIDERS = {
    "google": {
        "name": "Google",
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "name": "GitHub",
        "client_id": os.environ.get("GITHUB_CLIENT_ID"),
        "client_secret": os.environ.get("GITHUB_CLIENT_SECRET"),
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "email_url": "https://api.github.com/user/emails",
        "scope": "read:user user:email",
    },
}
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_TO_PLAN = {
    os.environ.get("STRIPE_PRICE_PRO_MONTHLY"): "pro",
    os.environ.get("STRIPE_PRICE_PRO_YEARLY"): "pro",
    os.environ.get("STRIPE_PRICE_BUSINESS_MONTHLY"): "business",
    os.environ.get("STRIPE_PRICE_BUSINESS_YEARLY"): "business",
}
STRIPE_PRICE_TO_PLAN = {price: plan for price, plan in STRIPE_PRICE_TO_PLAN.items() if price}
PLAN_RANK = {"free": 0, "pro": 1, "business": 2}
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due"}


def _postgres_sql(sql: str) -> str:
    return sql.replace("?", "%s")


class PostgresConnection:
    def __init__(self):
        if psycopg is None:
            raise RuntimeError("psycopg is required when DATABASE_URL uses PostgreSQL.")
        self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.conn.__exit__(exc_type, exc, tb)

    def execute(self, sql: str, params=()):
        return self.conn.execute(_postgres_sql(sql), params)


def get_db():
    if USE_POSTGRES:
        return PostgresConnection()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    with get_db() as conn:
        if USE_POSTGRES:
            conn.execute("SELECT pg_advisory_lock(hashtext('viddash_auth_schema'))")
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGSERIAL PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        password_hash TEXT,
                        provider TEXT NOT NULL DEFAULT 'local',
                        provider_id TEXT,
                        plan TEXT NOT NULL DEFAULT 'free',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id)"
                )
                migrations = {
                    "stripe_customer_id": "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT",
                    "stripe_subscription_id": "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT",
                    "stripe_price_id": "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_price_id TEXT",
                    "subscription_status": "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'free'",
                    "current_period_end": "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_period_end TEXT",
                }
                for sql in migrations.values():
                    conn.execute(sql)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                        action TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'success',
                        summary TEXT NOT NULL,
                        metadata TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_activity_user_created ON user_activity(user_id, created_at DESC)"
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_telemetry (
                        id BIGSERIAL PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                        method TEXT NOT NULL,
                        path TEXT NOT NULL,
                        endpoint TEXT,
                        status_code INTEGER NOT NULL,
                        duration_ms INTEGER NOT NULL,
                        ip TEXT,
                        user_agent TEXT,
                        referrer TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_telemetry_created ON app_telemetry(created_at DESC)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_telemetry_status_created ON app_telemetry(status_code, created_at DESC)"
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS media_jobs (
                        id TEXT PRIMARY KEY,
                        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                        job_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        output_path TEXT,
                        output_name TEXT,
                        error TEXT,
                        metadata TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_media_jobs_user_created ON media_jobs(user_id, created_at DESC)"
                )
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtext('viddash_auth_schema'))")
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT,
                    provider TEXT NOT NULL DEFAULT 'local',
                    provider_id TEXT,
                    plan TEXT NOT NULL DEFAULT 'free',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id)"
            )
            existing_cols = {
                row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            migrations = {
                "stripe_customer_id": "ALTER TABLE users ADD COLUMN stripe_customer_id TEXT",
                "stripe_subscription_id": "ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT",
                "stripe_price_id": "ALTER TABLE users ADD COLUMN stripe_price_id TEXT",
                "subscription_status": "ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'free'",
                "current_period_end": "ALTER TABLE users ADD COLUMN current_period_end TEXT",
            }
            for col, sql in migrations.items():
                if col not in existing_cols:
                    conn.execute(sql)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'success',
                    summary TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_activity_user_created ON user_activity(user_id, created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    user_id INTEGER,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    endpoint TEXT,
                    status_code INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    ip TEXT,
                    user_agent TEXT,
                    referrer TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_telemetry_created ON app_telemetry(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_telemetry_status_created ON app_telemetry(status_code, created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_jobs (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    output_path TEXT,
                    output_name TEXT,
                    error TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_jobs_user_created ON media_jobs(user_id, created_at DESC)"
            )


def insert_user(conn, columns: list[str], values: tuple) -> int:
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    sql = f"INSERT INTO users ({column_sql}) VALUES ({placeholders})"
    if USE_POSTGRES:
        row = conn.execute(sql + " RETURNING id", values).fetchone()
        return row["id"]
    cur = conn.execute(sql, values)
    return cur.lastrowid


init_auth_db()


def record_user_activity(user_id: int | None, action: str, summary: str, status: str = "success", metadata: dict | None = None) -> None:
    if not user_id:
        return
    try:
        created_at = datetime.utcnow().isoformat(timespec="seconds")
        metadata_json = json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True)
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO user_activity (user_id, action, status, summary, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, action, status, summary[:300], metadata_json, created_at),
            )
    except Exception:
        logger.exception("Could not record user activity action=%s user_id=%s", action, user_id)


def record_current_user_activity(action: str, summary: str, status: str = "success", metadata: dict | None = None) -> None:
    user_id = session.get("user_id")
    record_user_activity(user_id, action, summary, status, metadata)


def get_user_activity(user_id: int, limit: int = 25):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT action, status, summary, metadata, created_at
            FROM user_activity
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def get_audio_edits_used_today(user_id: int) -> int:
    day_start = datetime.utcnow().date().isoformat() + "T00:00:00"
    with get_db() as conn:
        return int(scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM user_activity
            WHERE user_id = ? AND action = ? AND status = ? AND created_at >= ?
            """,
            (user_id, "media.audio_edit", "success", day_start),
        ))


def get_youtube_transcripts_used_today(user_id: int) -> int:
    day_start = datetime.utcnow().date().isoformat() + "T00:00:00"
    with get_db() as conn:
        return int(scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM user_activity
            WHERE user_id = ? AND action = ? AND status = ? AND created_at >= ?
            """,
            (user_id, "media.youtube_transcript", "success", day_start),
        ))


def scalar(conn, sql: str, params=(), default=0):
    row = conn.execute(sql, params).fetchone()
    if not row:
        return default
    if hasattr(row, "keys"):
        return next(iter(dict(row).values()), default)
    return row[0]


def get_admin_dashboard_data():
    with get_db() as conn:
        totals = {
            "users": scalar(conn, "SELECT COUNT(*) FROM users"),
            "pro_users": scalar(conn, "SELECT COUNT(*) FROM users WHERE plan = ?", ("pro",)),
            "business_users": scalar(conn, "SELECT COUNT(*) FROM users WHERE plan = ?", ("business",)),
            "requests": scalar(conn, "SELECT COUNT(*) FROM app_telemetry"),
            "errors": scalar(conn, "SELECT COUNT(*) FROM app_telemetry WHERE status_code >= 400"),
            "activity": scalar(conn, "SELECT COUNT(*) FROM user_activity"),
        }
        recent_requests = conn.execute(
            """
            SELECT t.created_at, t.method, t.path, t.endpoint, t.status_code, t.duration_ms,
                   t.ip, u.email
            FROM app_telemetry t
            LEFT JOIN users u ON u.id = t.user_id
            ORDER BY t.created_at DESC, t.id DESC
            LIMIT 50
            """
        ).fetchall()
        recent_errors = conn.execute(
            """
            SELECT t.created_at, t.method, t.path, t.endpoint, t.status_code, t.duration_ms,
                   t.ip, u.email
            FROM app_telemetry t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE t.status_code >= 400
            ORDER BY t.created_at DESC, t.id DESC
            LIMIT 30
            """
        ).fetchall()
        recent_activity = conn.execute(
            """
            SELECT a.created_at, a.action, a.status, a.summary, u.email
            FROM user_activity a
            LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT 50
            """
        ).fetchall()
        slow_requests = conn.execute(
            """
            SELECT t.created_at, t.method, t.path, t.endpoint, t.status_code, t.duration_ms,
                   t.ip, u.email
            FROM app_telemetry t
            LEFT JOIN users u ON u.id = t.user_id
            ORDER BY t.duration_ms DESC, t.created_at DESC
            LIMIT 20
            """
        ).fetchall()
        top_paths = conn.execute(
            """
            SELECT path, COUNT(*) AS count, MAX(duration_ms) AS max_duration_ms
            FROM app_telemetry
            GROUP BY path
            ORDER BY count DESC
            LIMIT 20
            """
        ).fetchall()
        users = conn.execute(
            """
            SELECT id, email, name, provider, plan, subscription_status, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()
    return {
        "totals": totals,
        "recent_requests": recent_requests,
        "recent_errors": recent_errors,
        "recent_activity": recent_activity,
        "slow_requests": slow_requests,
        "top_paths": top_paths,
        "users": users,
    }


def create_media_job(user_id: int, job_type: str, message: str, metadata: dict | None = None) -> str:
    job_id = secrets.token_urlsafe(18)
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO media_jobs (
                id, user_id, job_type, status, message, metadata, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                user_id,
                job_type,
                "queued",
                message,
                json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True),
                now,
                now,
            ),
        )
    return job_id


def update_media_job(job_id: str, status: str, message: str | None = None, output_path: str | None = None, output_name: str | None = None, error: str | None = None) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    completed_at = now if status in {"complete", "failed"} else None
    with get_db() as conn:
        conn.execute(
            """
            UPDATE media_jobs
            SET status = ?, message = COALESCE(?, message), output_path = COALESCE(?, output_path),
                output_name = COALESCE(?, output_name), error = COALESCE(?, error),
                updated_at = ?, completed_at = COALESCE(?, completed_at)
            WHERE id = ?
            """,
            (status, message, output_path, output_name, error, now, completed_at, job_id),
        )


def get_media_job(job_id: str, user_id: int):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, user_id, job_type, status, message, output_path, output_name, error,
                   metadata, created_at, updated_at, completed_at
            FROM media_jobs
            WHERE id = ? AND user_id = ?
            """,
            (job_id, user_id),
        ).fetchone()


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def validate_csrf():
    form_token = request.form.get("_csrf_token")
    if not form_token or form_token != session.get("_csrf_token"):
        flash("Your session expired. Please try again.", "error")
        return False
    return True


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, email, name, provider, plan, created_at, stripe_customer_id,
                   stripe_subscription_id, stripe_price_id, subscription_status,
                   current_period_end
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()


@app.context_processor
def inject_auth_context():
    configured = {
        key: bool(provider.get("client_id") and provider.get("client_secret"))
        for key, provider in OAUTH_PROVIDERS.items()
    }
    return {
        "current_user": get_current_user(),
        "oauth_configured": configured,
    }


def login_user(user_id: int):
    session.clear()
    session["user_id"] = user_id
    csrf_token()


def is_api_request() -> bool:
    return request.path.startswith("/api/") or request.is_json


def is_browser_navigation() -> bool:
    accept = request.headers.get("Accept", "")
    return request.method == "GET" and "text/html" in accept and not request.headers.get("X-Requested-With")


def api_error(message: str, status: int, code: str | None = None):
    payload = {"error": code or message, "message": message}
    return jsonify(payload), status


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if is_browser_navigation():
                flash("Create a free account to download files from Viddash.", "error")
                return redirect(url_for("signup", next=request.referrer or url_for("index")))
            if is_api_request():
                return api_error("Log in to use this endpoint.", 401, "login_required")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def is_admin_user(user=None) -> bool:
    user = user or get_current_user()
    if not user or not ADMIN_EMAILS:
        return False
    return (user["email"] or "").lower() in ADMIN_EMAILS


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("login", next=request.path))
        if not is_admin_user(user):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def find_or_create_oauth_user(provider_key: str, provider_id: str, email: str, name: str):
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
            (provider_key, provider_id),
        ).fetchone()
        if user:
            conn.execute(
                "UPDATE users SET email = ?, name = ?, updated_at = ? WHERE id = ?",
                (email, name, now, user["id"]),
            )
            return user["id"], False

        existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET provider = ?, provider_id = ?, name = ?, updated_at = ? WHERE id = ?",
                (provider_key, provider_id, name, now, existing["id"]),
            )
            return existing["id"], False

        user_id = insert_user(
            conn,
            ["email", "name", "provider", "provider_id", "created_at", "updated_at"],
            (email, name, provider_key, provider_id, now, now),
        )
        return user_id, True


def stripe_ready() -> bool:
    return bool(stripe and stripe.api_key)


def get_price_id(plan: str, billing: str) -> str | None:
    env_key = f"STRIPE_PRICE_{plan.upper()}_{billing.upper()}"
    return os.environ.get(env_key)


def plan_allows(user, required_plan: str) -> bool:
    user_plan = user["plan"] if user else "free"
    return PLAN_RANK.get(user_plan, 0) >= PLAN_RANK.get(required_plan, 0)


def app_base_url() -> str:
    return os.environ.get("VIDDASH_PUBLIC_URL", "https://viddash.app").rstrip("/")


def safe_url_fingerprint(url: str | None) -> str:
    if not url:
        return ""
    return hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()[:16]


def sanitize_process_output(text: str | None, max_chars: int = 1200) -> str:
    redacted = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if "cookie:" in lowered or "set-cookie" in lowered or "authorization:" in lowered:
            continue
        redacted.append(line)
    return "\n".join(redacted)[-max_chars:].strip()


def browser_error_response(title: str, message: str, status: int):
    if not is_browser_navigation():
        return jsonify({"error": title, "message": message}), status
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)} - Viddash</title>
    <link href="/static/styles.css?v=2.2" rel="stylesheet" />
  </head>
  <body>
    <main class="page-main">
      <section class="app-container page-hero-compact text-center">
        <h1>{escape(title)}</h1>
        <p>{escape(message)}</p>
        <div class="hero-actions justify-content-center">
          <a class="btn btn-primary" href="/">Try another format</a>
          <a class="btn btn-outline-secondary" href="/help-center">Get help</a>
        </div>
      </section>
    </main>
  </body>
</html>"""
    return Response(html, status=status, mimetype="text/html")


def email_layout(title: str, body_html: str, cta_label: str | None = None, cta_url: str | None = None) -> str:
    cta = ""
    if cta_label and cta_url:
        cta = f"""
        <p style="margin:28px 0">
          <a href="{escape(cta_url)}" style="background:#15a63e;color:#fff;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:700;display:inline-block">{escape(cta_label)}</a>
        </p>
        """
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#f6f8fb;padding:28px;color:#071225">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:28px">
        <h1 style="margin:0 0 16px;font-size:24px;line-height:1.2">{escape(title)}</h1>
        {body_html}
        {cta}
        <p style="margin-top:28px;color:#56637a;font-size:14px">Need help? Reply to this email or contact <a href="mailto:{escape(SUPPORT_EMAIL)}">{escape(SUPPORT_EMAIL)}</a>.</p>
        <p style="margin-top:18px;color:#94a3b8;font-size:12px">Viddash App, automated account notification.</p>
      </div>
    </div>
    """


def send_email(to_email: str | None, subject: str, html: str) -> bool:
    if not RESEND_API_KEY or not to_email:
        return False
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"Viddash <{MAIL_FROM}>",
                "to": to_email,
                "subject": subject,
                "html": html,
                "reply_to": SUPPORT_EMAIL,
            },
            timeout=20,
        )
        if response.status_code >= 400:
            logger.warning("Resend email failed: %s %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception:
        logger.exception("Could not send email via Resend")
        return False


def send_welcome_email(user) -> None:
    name = escape((user.get("name") if hasattr(user, "get") else user["name"]) or "there")
    html = email_layout(
        "Welcome to Viddash",
        f"""
        <p>Hi {name},</p>
        <p>Your Viddash account is ready. You can start with the downloader, image tools, and conversion workflows right away.</p>
        <p>When you need larger files, batch exports, or priority processing, the Pro and Business plans are available from your account.</p>
        """,
        "Open Your Account",
        f"{app_base_url()}/account",
    )
    send_email(user["email"], "Welcome to Viddash", html)


def send_checkout_started_email(user, plan: str, billing: str) -> None:
    html = email_layout(
        f"{plan.title()} checkout started",
        f"""
        <p>Hi {escape(user['name'])},</p>
        <p>You started checkout for Viddash {escape(plan.title())} on {escape(billing)} billing.</p>
        <p>If you did not finish payment, you can return to pricing and choose the same plan again.</p>
        """,
        "Return to Pricing",
        f"{app_base_url()}/pricing",
    )
    send_email(user["email"], f"Complete your Viddash {plan.title()} setup", html)


def send_subscription_email(user, plan: str, status: str | None) -> None:
    if plan == "free":
        title = "Your Viddash plan changed"
        body = """
        <p>Your paid Viddash subscription is no longer active, so your account is now on the Free plan.</p>
        <p>You can restart a paid plan anytime from Pricing.</p>
        """
        cta_label = "View Plans"
        cta_url = f"{app_base_url()}/pricing"
    else:
        title = f"Your Viddash {plan.title()} plan is active"
        body = f"""
        <p>Your Viddash {escape(plan.title())} subscription is active.</p>
        <p>Status: {escape(status or "active")}.</p>
        <p>You now have access to the paid media-processing tools included with your plan.</p>
        """
        cta_label = "Open Your Account"
        cta_url = f"{app_base_url()}/account"
    html = email_layout(title, body, cta_label, cta_url)
    send_email(user["email"], title, html)


def update_subscription_from_stripe(customer_id: str | None, subscription_id: str | None, status: str | None, price_id: str | None, period_end=None):
    plan = STRIPE_PRICE_TO_PLAN.get(price_id, "free")
    if status not in ACTIVE_SUBSCRIPTION_STATUSES:
        plan = "free"
    period_end_value = None
    if period_end:
        period_end_value = datetime.utcfromtimestamp(period_end).isoformat(timespec="seconds")
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as conn:
        if customer_id:
            conn.execute(
                """
                UPDATE users
                SET plan = ?, stripe_subscription_id = ?, stripe_price_id = ?,
                    subscription_status = ?, current_period_end = ?, updated_at = ?
                WHERE stripe_customer_id = ?
                """,
                (plan, subscription_id, price_id, status, period_end_value, now, customer_id),
            )
            user = conn.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            if user:
                record_user_activity(
                    user["id"],
                    "billing.subscription_updated",
                    f"Subscription updated to {plan.title()} ({status or 'unknown'}).",
                    "success" if plan != "free" else "info",
                    {"plan": plan, "status": status, "price_id": price_id},
                )
                send_subscription_email(user, plan, status)


def require_paid_plan(required_plan: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                if is_browser_navigation():
                    flash("Create a free account to continue your download.", "error")
                    return redirect(url_for("signup", next=request.referrer or url_for("index")))
                if is_api_request():
                    return api_error("Log in to use this endpoint.", 401, "login_required")
                return redirect(url_for("login", next=request.path))
            if plan_allows(user, required_plan):
                return view(*args, **kwargs)
            if is_browser_navigation():
                flash(f"Upgrade to {required_plan.title()} to use this feature.", "error")
                return redirect(url_for("page_pricing"))
            return jsonify({
                "error": "upgrade_required",
                "message": f"Upgrade to {required_plan.title()} to use this feature.",
                "required_plan": required_plan,
                "pricing_url": url_for("page_pricing"),
            }), 402

        return wrapped

    return decorator


def is_private_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # treat unresolvable as disallowed
    for info in infos:
        try:
            family = info[0]
            ip_str = info[4][0] if family in (socket.AF_INET, socket.AF_INET6) else None
            if not ip_str:
                continue
            ip_obj = ipaddress.ip_address(ip_str)
            if any(ip_obj in net for net in PRIVATE_NETS):
                return True
        except Exception:
            continue
    return False


def run_yt_dlp(url: str, cookie_string: str | None = None) -> dict:
    """Run yt-dlp to retrieve metadata and formats for the provided URL.

    Returns a dict parsed from yt-dlp JSON output. For playlist-like outputs,
    returns the first item.
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
        "--no-call-home",
        "-R",
        "2",
        url,
    ]
    if cookie_string:
        # Pass cookies via header for private/restricted videos
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])
    completed = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, check=False
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(stderr or "yt-dlp failed")

    # Some URLs may output multiple JSON lines; use the first non-empty one.
    lines = [l for l in (completed.stdout or "").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("No output from yt-dlp")
    data = json.loads(lines[0])
    return data


def _slugify(text: str) -> str:
    base = (text or "").strip().lower()
    base = SEO_SLUG_RE.sub("-", base)
    base = base.strip("-")
    return base or "image"


def _image_ext_from_format(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt == "jpeg":
        return "jpg"
    return fmt


def extract_captions_from_video(
    url: str,
    cookie_string: str | None = None,
    preferred_language: str | None = None,
) -> dict:
    """Extract captions/subtitles from video using yt-dlp.
    
    Returns: {
        'success': bool,
        'captions': list of dicts with 'lang', 'data' (VTT format),
        'duration': float|None (seconds),
        'error': str (if failed)
    }
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--skip-download",
        "-R", "2",
        url,
    ]
    if cookie_string:
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])
    
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=False
        )
        if completed.returncode != 0:
            return {"success": False, "captions": [], "error": "Failed to fetch video info"}
        
        lines = [l for l in (completed.stdout or "").splitlines() if l.strip()]
        if not lines:
            return {"success": False, "captions": [], "error": "No video info found"}
        
        data = json.loads(lines[0])
        subtitles = data.get("subtitles", {})
        automatic_captions = data.get("automatic_captions", {})
        duration = data.get("duration")
        video_meta = {
            "id": data.get("id"),
            "title": data.get("title"),
            "channel": data.get("channel") or data.get("uploader"),
            "thumbnail": data.get("thumbnail"),
            "webpage_url": data.get("webpage_url") or url,
            "duration": duration,
        }
        
        candidates = []
        for caption_type, tracks in (("manual", subtitles), ("automatic", automatic_captions)):
            for lang, formats in tracks.items():
                vtt = next((item for item in formats if item.get("ext") == "vtt" and item.get("url")), None)
                if vtt:
                    candidates.append({"lang": lang, "type": caption_type, "url": vtt["url"]})

        requested = (preferred_language or "").lower()

        def candidate_priority(item):
            lang = str(item["lang"]).lower()
            exact_language = bool(requested) and (lang == requested or lang.startswith(requested + "-"))
            english = lang in {"en", "en-us", "en-gb"}
            return (
                0 if exact_language else 1,
                0 if item["type"] == "manual" else 1,
                0 if english else 1,
            )

        captions = []
        # Signed caption URLs can occasionally be stale or throttled. Try a small
        # prioritized fallback set without downloading every translated track.
        for candidate in sorted(candidates, key=candidate_priority)[:3]:
            try:
                resp = requests.get(candidate["url"], timeout=10)
                caption_data = resp.text.strip() if resp.ok else ""
                if caption_data:
                    captions.append({
                        "lang": candidate["lang"],
                        "type": candidate["type"],
                        "data": caption_data,
                    })
                    break
            except requests.RequestException:
                continue
        
        if captions:
            return {
                "success": True,
                "captions": captions,
                "duration": duration,
                "video": video_meta,
                "error": None,
            }
        else:
            return {
                "success": False,
                "captions": [],
                "duration": duration,
                "video": video_meta,
                "error": "No captions found for this video",
            }
    
    except subprocess.TimeoutExpired:
        return {"success": False, "captions": [], "duration": None, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "captions": [], "duration": None, "error": str(e)}


def transcribe_video_audio(url: str, cookie_string: str | None = None, language: str | None = None) -> dict:
    """Extract audio from video and transcribe using Whisper.
    
    Returns: {
        'success': bool,
        'transcript': str (plain text),
        'segments': list of dicts with timing info,
        'language': detected language,
        'error': str (if failed)
    }
    """
    if WhisperModel is None:
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": "Whisper is not installed"
        }
    
    tmpdir = tempfile.mkdtemp(prefix="transcribe_")
    audio_file = os.path.join(tmpdir, "audio.m4a")
    
    try:
        # Extract audio using yt-dlp
        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--no-call-home",
            "--no-playlist",
            "--extract-audio",
            "--audio-format", "m4a",
            "--audio-quality", "192",
            "-o", "audio.%(ext)s",
            url,
        ]
        if cookie_string:
            cmd.extend(["--add-header", f"Cookie: {cookie_string}"])
        
        completed = subprocess.run(
            cmd,
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        
        if completed.returncode != 0 or not os.path.exists(audio_file):
            return {
                "success": False,
                "transcript": "",
                "segments": [],
                "language": None,
                "error": "Failed to extract audio from video"
            }
        
        # Transcribe using faster-whisper
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            audio_file,
            language=language,
            beam_size=5,
        )
        
        transcript_text = ""
        segments_list = []
        
        for segment in segments:
            transcript_text += segment.text + " "
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "id": segment.id,
            })
        
        transcript_text = transcript_text.strip()
        
        return {
            "success": True,
            "transcript": transcript_text,
            "segments": segments_list,
            "language": info.language,
            "error": None,
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": "Transcription timed out (video may be too long)"
        }
    except Exception as e:
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": str(e)
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def segments_to_srt(segments: list) -> str:
    """Convert segment list to SRT format."""
    srt_content = ""
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_timecode(seg["start"])
        end = _seconds_to_timecode(seg["end"])
        srt_content += f"{i}\n{start} --> {end}\n{seg['text']}\n\n"
    return srt_content.strip()


def segments_to_vtt(segments: list) -> str:
    """Convert segment list to VTT format."""
    vtt_content = "WEBVTT\n\n"
    for seg in segments:
        start = _seconds_to_timecode(seg["start"])
        end = _seconds_to_timecode(seg["end"])
        vtt_content += f"{start} --> {end}\n{seg['text']}\n\n"
    return vtt_content.strip()


def _seconds_to_timecode(seconds: float) -> str:
    """Convert seconds to SRT/VTT timecode format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs % 1) * 1000)
    secs = int(secs)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_local_file(file_path: str, language: str | None = None) -> dict:
    """Transcribe audio from a local video/audio file using Whisper.
    
    Args:
        file_path: Path to the uploaded file
        language: Optional language code for transcription
    
    Returns: {
        'success': bool,
        'transcript': str (plain text),
        'segments': list of dicts with timing info,
        'language': detected language,
        'error': str (if failed)
    }
    """
    if WhisperModel is None:
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": "Whisper is not installed"
        }
    
    if not os.path.exists(file_path):
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": "File not found"
        }
    
    try:
        # Check if file is audio or video
        # If it's video, extract audio first
        tmpdir = None
        audio_file = file_path
        
        # Check file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Video formats that need audio extraction
        video_formats = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.3gp', '.mpg', '.mpeg', '.ts', '.m3u8'}
        
        if ext in video_formats:
            # Extract audio using ffmpeg
            tmpdir = tempfile.mkdtemp(prefix="audio_extract_")
            audio_file = os.path.join(tmpdir, "audio.wav")
            
            # Try to find ffmpeg executable
            ffmpeg_cmd = "ffmpeg"
            project_root = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(project_root, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"),  # Local copy
                r"C:\Program Files\Dubb\resources\app.asar.unpacked\binaries\ffmpeg\ffmpeg.exe",
                r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
                "ffmpeg"  # Try system PATH last
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    ffmpeg_cmd = path
                    break
            
            cmd = [ffmpeg_cmd, "-i", file_path, "-q:a", "9", "-n", audio_file]
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            
            try:
                # Use DEVNULL to prevent deadlock on Windows with large output
                completed = subprocess.run(
                    cmd, 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=300,  # 5 minute timeout
                    check=False
                )
                logger.info(f"FFmpeg completed with code: {completed.returncode}")
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg TIMEOUT after 300 seconds on file: {file_path}")
                if tmpdir:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                return {
                    "success": False,
                    "transcript": "",
                    "segments": [],
                    "language": None,
                    "error": "Audio extraction timed out (>5 min). Video file may be corrupted or codec not supported."
                }
            
            if completed.returncode != 0 or not os.path.exists(audio_file):
                logger.error(f"FFmpeg exit code: {completed.returncode}, audio file exists: {os.path.exists(audio_file)}")
                if tmpdir:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                return {
                    "success": False,
                    "transcript": "",
                    "segments": [],
                    "language": None,
                    "error": f"Failed to extract audio from video. Exit code: {completed.returncode}. Try a different video format (MP4, WebM, etc)."
                }
        
        # Transcribe using faster-whisper
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            audio_file,
            language=language,
            beam_size=5,
        )
        
        transcript_text = ""
        segments_list = []
        
        for segment in segments:
            transcript_text += segment.text + " "
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "id": segment.id,
            })
        
        transcript_text = transcript_text.strip()
        
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        
        return {
            "success": True,
            "transcript": transcript_text,
            "segments": segments_list,
            "language": info.language,
            "error": None,
        }
    
    except subprocess.TimeoutExpired:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": "Transcription timed out (file may be too large)"
        }
    except Exception as e:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return {
            "success": False,
            "transcript": "",
            "segments": [],
            "language": None,
            "error": str(e)
        }


@app.get("/")
def index():
    return render_public_page("index.html", "")


@app.get("/target=image")
def index_target_image():
    # Handle the potential typo where '?' is missing
    return render_public_page("index.html", "")


@app.get("/tools")
def page_tools():
    return render_public_page("tools.html", "tools")


@app.get("/pricing")
def page_pricing():
    return render_public_page("pricing.html", "pricing")


@app.get("/resources")
def page_resources():
    return render_public_page("resources.html", "resources")


@app.get("/faq")
def page_faq():
    return render_public_page("faq.html", "faq")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_public_page("signup.html", "signup")
    if not validate_csrf():
        return render_public_page("signup.html", "signup"), 400

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not name or not email or len(password) < 8:
        flash("Add your name, a valid email, and a password with at least 8 characters.", "error")
        return render_public_page("signup.html", "signup"), 400

    now = datetime.utcnow().isoformat(timespec="seconds")
    try:
        with get_db() as conn:
            user_id = insert_user(
                conn,
                ["email", "name", "password_hash", "provider", "created_at", "updated_at"],
                (email, name, generate_password_hash(password), "local", now, now),
            )
    except DB_INTEGRITY_ERRORS:
        flash("An account with that email already exists. Log in instead.", "error")
        return redirect(url_for("login"))

    login_user(user_id)
    record_user_activity(user_id, "account.signup", "Created a Viddash account with email and password.")
    send_welcome_email({"email": email, "name": name})
    flash("Welcome to Viddash. Your account is ready.", "success")
    next_url = request.form.get("next") or request.args.get("next")
    return redirect(next_url if next_url and next_url.startswith("/") else url_for("account"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_public_page("login.html", "login")
    if not validate_csrf():
        return render_public_page("login.html", "login"), 400

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], password):
        flash("Email or password is incorrect.", "error")
        return render_public_page("login.html", "login"), 401

    login_user(user["id"])
    record_user_activity(user["id"], "account.login", "Logged in with email and password.")
    flash("You are logged in.", "success")
    next_url = request.form.get("next") or request.args.get("next")
    return redirect(next_url if next_url and next_url.startswith("/") else url_for("account"))


@app.post("/logout")
def logout():
    if not validate_csrf():
        return redirect(url_for("account"))
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.get("/account")
@require_login
def account():
    user = get_current_user()
    activity_history = get_user_activity(user["id"], 30) if user else []
    return render_template("account.html", activity_history=activity_history)


@app.get("/admin")
@require_admin
def admin_dashboard():
    return render_template("admin.html", dashboard=get_admin_dashboard_data())


@app.post("/billing/checkout")
@require_login
def billing_checkout():
    if not validate_csrf():
        return redirect(url_for("page_pricing"))
    if not stripe_ready():
        flash("Stripe billing is not configured yet. Add your Stripe API key and price IDs to enable checkout.", "error")
        return redirect(url_for("page_pricing"))

    plan = (request.form.get("plan") or "").lower()
    billing = (request.form.get("billing") or "monthly").lower()
    if plan not in {"pro", "business"} or billing not in {"monthly", "yearly"}:
        flash("Choose a valid paid plan.", "error")
        return redirect(url_for("page_pricing"))

    price_id = get_price_id(plan, billing)
    if not price_id:
        flash(f"The Stripe price for {plan.title()} {billing} is not configured yet.", "error")
        return redirect(url_for("page_pricing"))

    user = get_current_user()
    customer_id = user["stripe_customer_id"]
    try:
        if not customer_id:
            customer = stripe.Customer.create(
                email=user["email"],
                name=user["name"],
                metadata={"viddash_user_id": str(user["id"])},
            )
            customer_id = customer["id"]
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET stripe_customer_id = ?, updated_at = ? WHERE id = ?",
                    (customer_id, datetime.utcnow().isoformat(timespec="seconds"), user["id"]),
                )

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=url_for("billing_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("page_pricing", _external=True),
            metadata={"user_id": str(user["id"]), "plan": plan, "billing": billing},
            subscription_data={"metadata": {"user_id": str(user["id"]), "plan": plan}},
        )
        record_user_activity(user["id"], "billing.checkout_started", f"Started checkout for {plan.title()} ({billing}).")
        send_checkout_started_email(user, plan, billing)
    except Exception as exc:
        logger.exception("Stripe checkout failed")
        flash("Stripe checkout could not be started. Please try again.", "error")
        return redirect(url_for("page_pricing"))

    return redirect(checkout_session.url, code=303)


@app.get("/billing/success")
@require_login
def billing_success():
    flash("Checkout completed. Your subscription will update as soon as Stripe confirms payment.", "success")
    return redirect(url_for("account"))


@app.post("/billing/portal")
@require_login
def billing_portal():
    if not validate_csrf():
        return redirect(url_for("account"))
    if not stripe_ready():
        flash("Stripe billing is not configured yet.", "error")
        return redirect(url_for("account"))

    user = get_current_user()
    if not user["stripe_customer_id"]:
        flash("Start a paid plan before opening the billing portal.", "error")
        return redirect(url_for("page_pricing"))
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=url_for("account", _external=True),
        )
    except Exception:
        logger.exception("Stripe portal failed")
        flash("Billing portal could not be opened. Please try again.", "error")
        return redirect(url_for("account"))
    return redirect(portal_session.url, code=303)


@app.post("/stripe/webhook")
def stripe_webhook():
    if not stripe_ready() or not STRIPE_WEBHOOK_SECRET:
        return jsonify({"error": "stripe_webhook_not_configured"}), 503

    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except Exception:
        logger.warning("Invalid Stripe webhook signature")
        return jsonify({"error": "invalid_signature"}), 400

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = (data.get("metadata") or {}).get("user_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id and customer_id:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET stripe_customer_id = ?, stripe_subscription_id = ?, updated_at = ? WHERE id = ?",
                    (customer_id, subscription_id, datetime.utcnow().isoformat(timespec="seconds"), user_id),
                )
        if customer_id and subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                item = ((subscription.get("items") or {}).get("data") or [{}])[0]
                price_id = ((item.get("price") or {}).get("id"))
                period_end = item.get("current_period_end") or subscription.get("current_period_end")
                update_subscription_from_stripe(
                    customer_id,
                    subscription_id,
                    subscription.get("status"),
                    price_id,
                    period_end,
                )
            except Exception:
                logger.exception("Could not retrieve Stripe subscription after checkout")
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        customer_id = data.get("customer")
        subscription_id = data.get("id")
        status = data.get("status")
        item = ((data.get("items") or {}).get("data") or [{}])[0]
        price_id = ((item.get("price") or {}).get("id"))
        period_end = item.get("current_period_end") or data.get("current_period_end")
        update_subscription_from_stripe(customer_id, subscription_id, status, price_id, period_end)

    return jsonify({"received": True})


@app.get("/auth/<provider>")
def oauth_start(provider):
    provider_config = OAUTH_PROVIDERS.get(provider)
    if not provider_config:
        flash("That identity provider is not supported yet.", "error")
        return redirect(url_for("signup"))
    if not provider_config.get("client_id") or not provider_config.get("client_secret"):
        flash(f"{provider_config['name']} sign-in is not configured on this server yet.", "error")
        return redirect(url_for("signup"))

    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    session["oauth_provider"] = provider
    redirect_uri = url_for("oauth_callback", provider=provider, _external=True)
    params = {
        "client_id": provider_config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": provider_config["scope"],
        "state": state,
    }
    if provider == "google":
        params["access_type"] = "online"
        params["prompt"] = "select_account"
    return redirect(provider_config["authorize_url"] + "?" + urlencode(params))


@app.get("/auth/<provider>/callback")
def oauth_callback(provider):
    provider_config = OAUTH_PROVIDERS.get(provider)
    if not provider_config or provider != session.get("oauth_provider"):
        flash("Identity provider response could not be matched.", "error")
        return redirect(url_for("login"))
    if request.args.get("state") != session.get("oauth_state"):
        flash("Identity provider response failed validation.", "error")
        return redirect(url_for("login"))
    if request.args.get("error"):
        flash("Sign-in was cancelled or denied.", "error")
        return redirect(url_for("login"))

    code = request.args.get("code")
    if not code:
        flash("Identity provider did not return an authorization code.", "error")
        return redirect(url_for("login"))

    redirect_uri = url_for("oauth_callback", provider=provider, _external=True)
    token_resp = requests.post(
        provider_config["token_url"],
        data={
            "client_id": provider_config["client_id"],
            "client_secret": provider_config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=20,
    )
    if token_resp.status_code >= 400:
        flash("Could not complete identity provider sign-in.", "error")
        return redirect(url_for("login"))
    access_token = token_resp.json().get("access_token")
    if not access_token:
        flash("Identity provider did not return an access token.", "error")
        return redirect(url_for("login"))

    userinfo = requests.get(
        provider_config["userinfo_url"],
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    ).json()
    provider_id = str(userinfo.get("id") or userinfo.get("sub") or "")
    email = (userinfo.get("email") or "").lower()
    name = userinfo.get("name") or userinfo.get("login") or email.split("@")[0]

    if provider == "github" and not email:
        emails_resp = requests.get(
            provider_config["email_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=20,
        )
        if emails_resp.ok:
            emails = emails_resp.json()
            primary = next((item for item in emails if item.get("primary") and item.get("verified")), None)
            email = ((primary or {}).get("email") or "").lower()

    if not provider_id or not email:
        flash("Identity provider did not return a verified account email.", "error")
        return redirect(url_for("login"))

    user_id, is_new_user = find_or_create_oauth_user(provider, provider_id, email, name)
    login_user(user_id)
    record_user_activity(
        user_id,
        "account.oauth_signup" if is_new_user else "account.oauth_login",
        f"{'Created account' if is_new_user else 'Logged in'} with {provider_config['name']}.",
    )
    if is_new_user:
        send_welcome_email({"email": email, "name": name})
    flash(f"Signed in with {provider_config['name']}.", "success")
    return redirect(url_for("account"))


@app.get("/<locale>")
def localized_index_no_slash(locale):
    if locale not in LOCALE_PREFIXES:
        abort(404)
    return redirect(f"/{locale}/", code=301)


@app.get("/<locale>/")
@app.get("/<locale>/<path:slug>")
def localized_public_page(locale, slug=""):
    if locale not in LOCALE_PREFIXES:
        abort(404)
    slug = (slug or "").strip("/")
    template_name = PUBLIC_PAGES.get(slug)
    if not template_name:
        abort(404)
    g.locale = locale
    g.public_page_path = slug
    return render_public_page(template_name, slug)


@app.get("/about")
def page_about():
    return render_public_page("about.html", "about")


@app.get("/contact")
def page_contact():
    return render_public_page("contact.html", "contact")


@app.get("/guides")
def page_guides():
    return render_public_page("guides.html", "guides")


@app.get("/help-center")
def page_help_center():
    return render_public_page("help-center.html", "help-center")


@app.get("/api-documentation")
def page_api_documentation():
    return render_public_page("api-documentation.html", "api-documentation")


@app.get("/video-converter")
def page_video_converter():
    return render_public_page("video-converter.html", "video-converter")


@app.get("/privacy")
def privacy():
    return render_public_page("privacy.html", "privacy")


@app.get("/terms")
def terms():
    return render_public_page("terms.html", "terms")


@app.get("/dmca")
def dmca():
    return render_public_page("dmca.html", "dmca")


@app.get("/robots.txt")
def robots_txt():
    base = app_base_url()
    body = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /account
Disallow: /api/
Disallow: /auth/
Disallow: /billing/
Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap_xml():
    base = app_base_url()
    locales = [DEFAULT_LOCALE] + sorted(SEO_INDEXED_LOCALES - {DEFAULT_LOCALE})

    def url_for_locale(path, locale):
        clean = path.strip("/")
        if locale == DEFAULT_LOCALE:
            return f"{base}/{clean}" if clean else f"{base}/"
        return f"{base}/{locale}/{clean}" if clean else f"{base}/{locale}/"

    items = []
    for path in PUBLIC_PAGES:
        if path in SEO_NOINDEX_PAGES:
            continue
        for locale in locales:
            loc = url_for_locale(path, locale)
            alternates = "".join(
                f'<xhtml:link rel="alternate" hreflang="{alt_locale}" href="{escape(url_for_locale(path, alt_locale), quote=True)}" />'
                for alt_locale in locales
            )
            alternates += f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(url_for_locale(path, DEFAULT_LOCALE), quote=True)}" />'
            items.append(
                f"<url><loc>{escape(loc, quote=True)}</loc>{alternates}<changefreq>weekly</changefreq><priority>0.8</priority></url>"
            )
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\" "
        "xmlns:xhtml=\"http://www.w3.org/1999/xhtml\">"
        + "".join(items) +
        "</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@app.get("/facebook-downloader")
def page_facebook():
    return render_public_page("facebook-downloader.html", "facebook-downloader")


@app.get("/youtube-downloader")
def page_youtube():
    return render_public_page("youtube-downloader.html", "youtube-downloader")


@app.get("/tiktok-downloader")
def page_tiktok():
    return render_public_page("tiktok-downloader.html", "tiktok-downloader")


@app.get("/video-to-audio")
def page_video_to_audio():
    return render_public_page("video-to-audio.html", "video-to-audio")


@app.get("/audio-editor")
def page_audio_editor():
    return render_public_page("audio-editor.html", "audio-editor")


@app.get("/video-resizer")
def page_video_resizer():
    return render_public_page("video-resizer.html", "video-resizer")


@app.get("/video-export")
def page_video_export():
    return render_public_page("video-export.html", "video-export")


@app.get("/video-compress")
def page_video_compress():
    return render_public_page("video-compress.html", "video-compress")


@app.get("/video-watermark")
def page_video_watermark():
    return render_public_page("video-watermark.html", "video-watermark")


@app.get("/utm-builder")
def page_utm_builder():
    return render_public_page("utm-builder.html", "utm-builder")


@app.get("/transcript-generator")
def page_transcript_generator():
    return render_public_page("transcript-generator.html", "transcript-generator")


@app.get("/youtube-transcript-generator")
def page_youtube_transcript_generator():
    return render_public_page("youtube-transcript-generator.html", "youtube-transcript-generator")


@app.post("/api/resolve")
@require_login
def resolve():
    user = get_current_user()
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    cookie_string = (payload.get("cookieString") or "").strip() or None
    if not url:
        return jsonify({"error": "Missing url"}), 400
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"error": "Invalid url scheme"}), 400
    if is_private_host(parsed.hostname or ""):
        return jsonify({"error": "Target not allowed"}), 403

    try:
        info = run_yt_dlp(url, cookie_string=cookie_string)
        formats = info.get("formats") or []

        def human_size(n):
            try:
                n = int(n)
            except Exception:
                return None
            units = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            f = float(n)
            while f >= 1024 and i < len(units) - 1:
                f /= 1024
                i += 1
            return f"{f:.1f} {units[i]}"

        result_formats = []
        for f in formats:
            if not f.get("url"):
                continue
            res = f.get("resolution")
            if not res:
                w = f.get("width")
                h = f.get("height")
                if w and h:
                    res = f"{w}x{h}"
            ext = (f.get("ext") or "").lower()
            protocol = (f.get("protocol") or "").lower()
            is_hls = ext == "m3u8" or "m3u8" in protocol
            is_dash = ext in ("mpd", "dash") or "dash" in protocol
            has_audio = (f.get("acodec") and f.get("acodec") != "none")
            has_video = (f.get("vcodec") and f.get("vcodec") != "none")
            item = {
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": res,
                "fps": f.get("fps"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "filesize_human": human_size(
                    f.get("filesize") or f.get("filesize_approx")
                ),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "tbr": f.get("tbr"),
                "url": f.get("url"),
                "format_note": f.get("format_note"),
                "protocol": f.get("protocol"),
                "is_hls": is_hls,
                "is_dash": is_dash,
                "has_audio": has_audio,
                "has_video": has_video,
            }
            result_formats.append(item)

        response = {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "webpage_url": info.get("webpage_url"),
            "formats": result_formats,
        }
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.resolve",
            f"Resolved formats for {parsed.hostname or 'a video link'}.",
            "success",
            {
                "host": parsed.hostname,
                "url_hash": safe_url_fingerprint(url),
                "formats": len(result_formats),
                "title": (info.get("title") or "")[:120],
            },
        )
        return jsonify(response)

    except subprocess.TimeoutExpired:
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.resolve",
            f"Format lookup timed out for {parsed.hostname or 'a video link'}.",
            "error",
            {"host": parsed.hostname, "url_hash": safe_url_fingerprint(url)},
        )
        return jsonify({"error": "Resolver timed out"}), 504
    except Exception as e:
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.resolve",
            f"Format lookup failed for {parsed.hostname or 'a video link'}.",
            "error",
            {"host": parsed.hostname, "url_hash": safe_url_fingerprint(url), "error": str(e)[:200]},
        )
        return jsonify({"error": str(e)}), 500


@app.get("/api/proxy")
@require_login
def proxy_download():
    user = get_current_user()
    target = request.args.get("url", type=str)
    if not target:
        return jsonify({"error": "Missing url"}), 400
    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https"):
        return jsonify({"error": "Invalid url scheme"}), 400
    do_head = request.args.get("head", default="0") in ("1", "true", "True")

    # SSRF guard: block private/link-local/loopback destinations
    if not parsed.netloc:
        return jsonify({"error": "Invalid target"}), 400
    hostname = parsed.hostname or ""
    if is_private_host(hostname):
        return jsonify({"error": "Target not allowed"}), 403

    try:
        headers = {}
        # Forward Range for partial content support (video players, resumable downloads)
        if "Range" in request.headers:
            headers["Range"] = request.headers.get("Range")
        # Supply a reasonable UA to avoid some upstream blocks
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        )
        # Forward common headers if present
        if "Accept" in request.headers:
            headers["Accept"] = request.headers.get("Accept")
        if "Accept-Language" in request.headers:
            headers["Accept-Language"] = request.headers.get("Accept-Language")
        if "Origin" in request.headers:
            headers["Origin"] = request.headers.get("Origin")
        # Some CDNs are picky about these fetch headers
        for key in ("Sec-Fetch-Mode", "Sec-Fetch-Site", "Sec-Fetch-Dest"):
            if key in request.headers:
                headers[key] = request.headers.get(key)
        # Set a site-appropriate Referer for some CDNs
        netloc = parsed.netloc.lower()
        if "googlevideo.com" in netloc:
            headers.setdefault("Referer", "https://www.youtube.com/")
        elif "fbcdn" in netloc or "facebook.com" in netloc or "fna.fbcdn.net" in netloc:
            headers.setdefault("Referer", "https://www.facebook.com/")
        if do_head:
            resp = requests.head(target, headers=headers, allow_redirects=True, timeout=15)
            # Summarize useful headers
            subset = {
                k: v
                for k, v in resp.headers.items()
                if k in ("Content-Type", "Content-Length", "Accept-Ranges", "Content-Range", "Server", "Date", "Cache-Control")
            }
            return jsonify({
                "status": resp.status_code,
                "ok": resp.ok,
                "reason": resp.reason,
                "headers": subset,
                "final_url": str(resp.url),
            }), (200 if resp.ok else 502)

        upstream = requests.get(target, headers=headers, stream=True, timeout=30)
    except requests.RequestException as e:
        return jsonify({"error": f"Upstream error: {e}"}), 502

    # Enforce content type and size limits before streaming
    MAX_BYTES = 1_500_000_000  # ~1.5 GB cap
    allowed_types = ("video/", "audio/", "application/octet-stream")
    ctype = upstream.headers.get("Content-Type", "")
    if not any(ctype.startswith(pfx) for pfx in allowed_types):
        # allow if extension suggests media, else block
        upstream.close()
        return jsonify({"error": f"Disallowed content-type: {ctype}"}), 415

    cl_header = upstream.headers.get("Content-Length")
    try:
        if cl_header and int(cl_header) > MAX_BYTES:
            upstream.close()
            return jsonify({"error": "File too large"}), 413
    except Exception:
        pass

    resp_headers = {}
    ct = upstream.headers.get("Content-Type")
    if ct:
        resp_headers["Content-Type"] = ct
    cl = upstream.headers.get("Content-Length")
    if cl:
        resp_headers["Content-Length"] = cl
    cd = upstream.headers.get("Content-Disposition")
    if cd:
        resp_headers["Content-Disposition"] = cd
    cr = upstream.headers.get("Content-Range")
    if cr:
        resp_headers["Content-Range"] = cr

    total = 0

    def limited_generate():
        nonlocal total
        for chunk in upstream.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                break
            yield chunk
        upstream.close()

    status = upstream.status_code
    record_user_activity(
        user["id"] if user else session.get("user_id"),
        "media.direct_download",
        f"Started a direct download from {hostname or 'a media host'}.",
        "success" if 200 <= status < 400 else "error",
        {
            "host": hostname,
            "url_hash": safe_url_fingerprint(target),
            "status": status,
            "content_type": ctype,
            "content_length": cl_header,
        },
    )
    return Response(limited_generate(), status=status, headers=resp_headers)


@app.route("/api/merge", methods=["GET", "POST"])
@require_paid_plan("pro")
def merge_download():
    """
    Download and merge best video+audio (or selected format) into a single MP4.
    Params:
      - url: original webpage URL (required)
      - format: optional yt-dlp format selector or format_id to prioritize
      - cookies: optional raw Cookie header string
    """
    started = time.monotonic()
    request_id = secrets.token_hex(6)
    user = get_current_user()
    params = request.form if request.method == "POST" else request.args
    page_url = params.get("url", type=str)
    if not page_url:
        logger.info("merge_request_invalid request_id=%s reason=missing_url user_id=%s", request_id, user["id"] if user else None)
        return browser_error_response("Missing video URL", "Please return to the downloader and paste a video URL.", 400)
    parsed = urlparse(page_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        logger.info("merge_request_invalid request_id=%s reason=invalid_url user_id=%s url_hash=%s", request_id, user["id"] if user else None, safe_url_fingerprint(page_url))
        return browser_error_response("Invalid video URL", "That video URL could not be processed. Please check the link and try again.", 400)
    if is_private_host(parsed.hostname or ""):
        logger.warning("merge_request_blocked request_id=%s reason=private_host user_id=%s host=%s url_hash=%s", request_id, user["id"] if user else None, parsed.hostname, safe_url_fingerprint(page_url))
        return browser_error_response("Video host not allowed", "That video host is not allowed for security reasons.", 403)
    cookie_string = params.get("cookies")
    prefer = params.get("format")
    url_hash = safe_url_fingerprint(page_url)
    logger.info(
        "merge_start request_id=%s user_id=%s plan=%s host=%s url_hash=%s format=%s cookies=%s",
        request_id,
        user["id"] if user else None,
        user["plan"] if user else None,
        parsed.hostname,
        url_hash,
        prefer or "auto",
        bool(cookie_string),
    )
    record_user_activity(
        user["id"] if user else session.get("user_id"),
        "media.merge_started",
        f"Started merged MP4 download from {parsed.hostname or 'a video host'}.",
        "info",
        {"host": parsed.hostname, "url_hash": url_hash, "request_id": request_id, "format": prefer or "auto"},
    )

    # Build yt-dlp command to merge to mp4
    # Strategy: try specific format if given; otherwise bestvideo+bestaudio fallback, then best
    fmt_selector = None
    if prefer:
        # If user passes a simple format_id, prefer it combined with bestaudio when possible
        # Otherwise they can pass a full selector like "bv*+ba/b".
        if "+" in prefer or "/" in prefer:
            fmt_selector = prefer
        else:
            fmt_selector = f"{prefer}+bestaudio/b"
    else:
        fmt_selector = "bv*+ba/b[ext=mp4]/best"

    tmpdir = tempfile.mkdtemp(prefix="merge_")
    # Output template: safe default name
    outtmpl = "%(title).80B.%(ext)s"

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--restrict-filenames",
        "--max-filesize",
        "1500M",
        "-f",
        fmt_selector,
        "--merge-output-format",
        "mp4",
        "-o",
        outtmpl,
        page_url,
    ]
    if cookie_string:
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])

    merge_timeout = int(os.environ.get("MERGE_TIMEOUT_SECONDS", "105"))
    try:
        completed = subprocess.run(
            cmd,
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=merge_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        logger.warning(
            "merge_timeout request_id=%s user_id=%s host=%s url_hash=%s elapsed=%.2f timeout=%s",
            request_id,
            user["id"] if user else None,
            parsed.hostname,
            url_hash,
            elapsed,
            merge_timeout,
        )
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.merge_timeout",
            f"Merged MP4 timed out for {parsed.hostname or 'a video host'}.",
            "error",
            {"host": parsed.hostname, "url_hash": url_hash, "request_id": request_id, "elapsed": round(elapsed, 2)},
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
        return browser_error_response(
            "Download took too long",
            "This platform is taking too long to merge video and audio. Try a Direct A+V option if available, or retry with a shorter/public video.",
            504,
        )
    except Exception as e:
        elapsed = time.monotonic() - started
        logger.exception(
            "merge_exception request_id=%s user_id=%s host=%s url_hash=%s elapsed=%.2f",
            request_id,
            user["id"] if user else None,
            parsed.hostname,
            url_hash,
            elapsed,
        )
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.merge_failed",
            f"Merged MP4 failed for {parsed.hostname or 'a video host'}.",
            "error",
            {"host": parsed.hostname, "url_hash": url_hash, "request_id": request_id, "elapsed": round(elapsed, 2)},
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
        return browser_error_response("Download failed", "The merge process failed unexpectedly. Please try again.", 500)

    if completed.returncode != 0:
        stderr = sanitize_process_output(completed.stderr)
        elapsed = time.monotonic() - started
        logger.warning(
            "merge_failed request_id=%s user_id=%s host=%s url_hash=%s elapsed=%.2f returncode=%s stderr=%r",
            request_id,
            user["id"] if user else None,
            parsed.hostname,
            url_hash,
            elapsed,
            completed.returncode,
            stderr[-500:],
        )
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.merge_failed",
            f"Merged MP4 failed for {parsed.hostname or 'a video host'}.",
            "error",
            {
                "host": parsed.hostname,
                "url_hash": url_hash,
                "request_id": request_id,
                "elapsed": round(elapsed, 2),
                "returncode": completed.returncode,
            },
        )
        # Common hint: FFmpeg missing
        if "ffmpeg" in stderr.lower() or "ffprobe" in stderr.lower() or shutil.which("ffmpeg") is None:
            hint = " FFmpeg is required for merging audio + video. Install FFmpeg and ensure it's in PATH."
        else:
            hint = ""
        shutil.rmtree(tmpdir, ignore_errors=True)
        return browser_error_response(
            "Download failed",
            (stderr or "The video platform did not return a downloadable merged file.") + hint,
            502,
        )

    # Determine output file by scanning tmpdir
    def list_files(root):
        out = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                out.append(p)
        return out

    files = list_files(tmpdir)
    # Prefer mp4
    mp4s = [p for p in files if p.lower().endswith(".mp4")]
    filename = None
    if mp4s:
        # choose largest mp4
        filename = max(mp4s, key=lambda p: os.path.getsize(p))
    elif files:
        # fallback: largest file
        filename = max(files, key=lambda p: os.path.getsize(p))

    if not filename or not os.path.exists(filename):
        err_snippet = sanitize_process_output(completed.stderr).splitlines()[-5:]
        elapsed = time.monotonic() - started
        logger.warning(
            "merge_no_output request_id=%s user_id=%s host=%s url_hash=%s elapsed=%.2f stdout=%r stderr=%r",
            request_id,
            user["id"] if user else None,
            parsed.hostname,
            url_hash,
            elapsed,
            sanitize_process_output(completed.stdout, 500),
            "\n".join(err_snippet),
        )
        record_user_activity(
            user["id"] if user else session.get("user_id"),
            "media.merge_no_output",
            f"Merged MP4 produced no downloadable file for {parsed.hostname or 'a video host'}.",
            "error",
            {"host": parsed.hostname, "url_hash": url_hash, "request_id": request_id, "elapsed": round(elapsed, 2)},
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
        return browser_error_response(
            "Merged file not found",
            "The platform did not produce a merged file. Try a Direct A+V option if one is available.",
            500,
        )

    elapsed = time.monotonic() - started
    logger.info(
        "merge_success request_id=%s user_id=%s host=%s url_hash=%s elapsed=%.2f file_size=%s filename=%s",
        request_id,
        user["id"] if user else None,
        parsed.hostname,
        url_hash,
        elapsed,
        os.path.getsize(filename),
        os.path.basename(filename),
    )
    record_user_activity(
        user["id"] if user else session.get("user_id"),
        "media.merge_success",
        f"Prepared merged MP4 from {parsed.hostname or 'a video host'}.",
        "success",
        {
            "host": parsed.hostname,
            "url_hash": url_hash,
            "request_id": request_id,
            "elapsed": round(elapsed, 2),
            "file_size": os.path.getsize(filename),
        },
    )

    # Stream file to client, then cleanup directory after response is closed
    resp = send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename),
        mimetype="video/mp4",
        conditional=True,
        max_age=0,
    )
    resp.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
    return resp


@app.post("/api/video-to-audio")
@require_paid_plan("pro")
def video_to_audio():
    """
    Convert a video URL to audio-only and return the audio file.

    Request JSON:
      - url: video URL (required)
      - cookies: optional cookie string
      - format: optional audio format (mp3, m4a, wav, flac) - default: mp3
    """
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    cookie_string = (payload.get("cookies") or "").strip() or None
    audio_format = (payload.get("format") or "mp3").lower()

    if not url:
        return jsonify({"error": "Missing url"}), 400

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"error": "Invalid url scheme"}), 400
    if is_private_host(parsed.hostname or ""):
        return jsonify({"error": "Target not allowed"}), 403

    allowed_formats = {"mp3", "m4a", "wav", "flac"}
    if audio_format not in allowed_formats:
        return jsonify({"error": "Invalid format. Use mp3, m4a, wav, or flac."}), 400

    tmpdir = tempfile.mkdtemp(prefix="audio_")
    outtmpl = "%(title).80B.%(ext)s"

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--max-filesize",
        "1500M",
        "--extract-audio",
        "--audio-format",
        audio_format,
        "--audio-quality",
        "192",
        "-o",
        outtmpl,
        url,
    ]
    if cookie_string:
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])

    try:
        completed = subprocess.run(
            cmd,
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Audio extraction timed out"}), 504
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        redacted = []
        for line in stderr.splitlines():
            if "cookie:" in line.lower() or "set-cookie" in line.lower():
                continue
            redacted.append(line)
        stderr = "\n".join(redacted).strip()
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": stderr or "yt-dlp failed"}), 502

    def list_files(root):
        out = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                out.append(p)
        return out

    files = list_files(tmpdir)
    preferred = [p for p in files if p.lower().endswith(f".{audio_format}")]
    if preferred:
        filename = max(preferred, key=lambda p: os.path.getsize(p))
    elif files:
        filename = max(files, key=lambda p: os.path.getsize(p))
    else:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Audio file not found"}), 500

    mime_map = {
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
        "flac": "audio/flac",
    }
    mimetype = mime_map.get(audio_format, "application/octet-stream")

    resp = send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename),
        mimetype=mimetype,
        conditional=True,
        max_age=0,
    )
    resp.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
    return resp


@app.post("/api/video-to-audio-file")
@require_paid_plan("pro")
def video_to_audio_file():
    """
    Convert an uploaded video/audio file to audio-only and return the audio file.

    Form data:
      - file: video/audio file (required)
      - format: optional audio format (mp3, m4a, wav, flac) - default: mp3
    """
    if "file" not in request.files:
        return jsonify({"error": "Missing file"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    audio_format = (request.form.get("format") or "mp3").lower()
    allowed_formats = {"mp3", "m4a", "wav", "flac"}
    if audio_format not in allowed_formats:
        return jsonify({"error": "Invalid format. Use mp3, m4a, wav, or flac."}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_UPLOAD_BYTES:
        max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({
            "error": f"File too large. Maximum size is {max_size_mb} MB.",
            "max_size_mb": max_size_mb
        }), 413

    tmpdir = tempfile.mkdtemp(prefix="upload_audio_")
    uploaded_file_path = None

    try:
        filename = os.path.basename(file.filename)
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        uploaded_file_path = os.path.join(tmpdir, filename)
        file.save(uploaded_file_path)

        ffmpeg_cmd = _find_media_binary("ffmpeg")

        base_name = os.path.splitext(filename)[0]
        out_path = os.path.join(tmpdir, f"{base_name}.{audio_format}")

        codec_map = {
            "mp3": ["-vn", "-acodec", "libmp3lame", "-b:a", "192k"],
            "m4a": ["-vn", "-acodec", "aac", "-b:a", "192k"],
            "wav": ["-vn", "-acodec", "pcm_s16le"],
            "flac": ["-vn", "-acodec", "flac"],
        }
        cmd = [ffmpeg_cmd, "-i", uploaded_file_path, *codec_map[audio_format], "-y", out_path]
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")

        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=600,
                check=False
            )
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Audio extraction timed out (>10 min)."}), 504

        if completed.returncode != 0 or not os.path.exists(out_path):
            return jsonify({"error": "Failed to extract audio. Try a different file format."}), 500

        mime_map = {
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
            "flac": "audio/flac",
        }
        mimetype = mime_map.get(audio_format, "application/octet-stream")

        resp = send_file(
            out_path,
            as_attachment=True,
            download_name=os.path.basename(out_path),
            mimetype=mimetype,
            conditional=True,
            max_age=0,
        )
        resp.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
        return resp

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pass


@app.post("/api/video/convert-file")
@require_paid_plan("pro")
def video_convert_file():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "Choose a video file."}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_UPLOAD_BYTES:
        max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({"error": f"File too large. Maximum size is {max_size_mb} MB."}), 413

    output_format = (request.form.get("format") or "mp4").lower()
    quality = (request.form.get("quality") or "balanced").lower()
    resolution = (request.form.get("resolution") or "original").lower()
    fps = (request.form.get("fps") or "original").lower()
    remove_audio = request.form.get("remove_audio") == "1"

    allowed_formats = {"mp4", "mov", "avi", "mkv", "webm", "gif"}
    if output_format not in allowed_formats:
        return jsonify({"error": "Unsupported output format."}), 400
    if quality not in {"high", "balanced", "small"}:
        return jsonify({"error": "Invalid quality option."}), 400
    if resolution not in {"original", "1080", "720", "480"}:
        return jsonify({"error": "Invalid resolution option."}), 400
    if fps not in {"original", "30", "24", "15"}:
        return jsonify({"error": "Invalid frame rate option."}), 400

    tmpdir = tempfile.mkdtemp(prefix="video_convert_")
    try:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(file.filename))
        input_path = os.path.join(tmpdir, safe_name or "source-video")
        file.save(input_path)

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        base_name = _slugify(os.path.splitext(safe_name)[0] or "video")
        output_name = f"{base_name}-viddash.{output_format}"
        output_path = os.path.join(tmpdir, output_name)

        crf_by_quality = {"high": "18", "balanced": "23", "small": "30"}
        filters = []
        if resolution != "original":
            filters.append(f"scale=-2:{resolution}")
        if fps != "original":
            filters.append(f"fps={fps}")

        cmd = [ffmpeg_cmd, "-y", "-i", input_path]
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        if output_format == "gif":
            cmd.extend(["-an", "-loop", "0", output_path])
        elif output_format == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-crf", crf_by_quality[quality], "-b:v", "0"])
            cmd.extend(["-an"] if remove_audio else ["-c:a", "libopus", "-b:a", "128k"])
            cmd.append(output_path)
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", crf_by_quality[quality]])
            cmd.extend(["-an"] if remove_audio else ["-c:a", "aac", "-b:a", "160k"])
            if output_format == "mp4":
                cmd.extend(["-movflags", "+faststart"])
            cmd.append(output_path)

        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False)
        if completed.returncode != 0 or not os.path.exists(output_path):
            stderr = "\n".join((completed.stderr or "").strip().splitlines()[-8:])
            return jsonify({"error": "Video conversion failed.", "details": stderr}), 500

        mimetype = {
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
            "webm": "video/webm",
            "gif": "image/gif",
        }[output_format]
        resp = send_file(output_path, as_attachment=True, download_name=output_name, mimetype=mimetype, max_age=0)
        resp.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
        return resp
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Video conversion timed out."}), 504
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500


@app.post("/api/video/resize")
@require_paid_plan("pro")
def video_resize():
    """
    Resize/crop a video to social media specs.

    Form data:
      - file: video file (required)
      - preset: one of supported presets (required)
    """
    if "file" not in request.files:
        return jsonify({"error": "Missing file"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    preset = (request.form.get("preset") or "").strip()
    presets = {
        "instagram_feed_4x5": {"label": "Instagram Feed (4:5)", "w": 1080, "h": 1350},
        "instagram_square_1x1": {"label": "Instagram Square (1:1)", "w": 1080, "h": 1080},
        "instagram_story_9x16": {"label": "Instagram Story/Reels (9:16)", "w": 1080, "h": 1920},
        "facebook_feed_4x5": {"label": "Facebook Feed (4:5)", "w": 1080, "h": 1350},
        "facebook_landscape_16x9": {"label": "Facebook Landscape (16:9)", "w": 1920, "h": 1080},
        "tiktok_9x16": {"label": "TikTok (9:16)", "w": 1080, "h": 1920},
        "youtube_shorts_9x16": {"label": "YouTube Shorts (9:16)", "w": 1080, "h": 1920},
        "linkedin_feed_1x1": {"label": "LinkedIn Feed (1:1)", "w": 1080, "h": 1080},
        "linkedin_feed_16x9": {"label": "LinkedIn Feed (16:9)", "w": 1920, "h": 1080},
    }
    if preset not in presets:
        return jsonify({"error": "Invalid preset"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_UPLOAD_BYTES:
        max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({
            "error": f"File too large. Maximum size is {max_size_mb} MB.",
            "max_size_mb": max_size_mb
        }), 413

    tmpdir = tempfile.mkdtemp(prefix="video_resize_")

    try:
        filename = os.path.basename(file.filename)
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        uploaded_file_path = os.path.join(tmpdir, filename)
        file.save(uploaded_file_path)

        # Find ffmpeg executable
        ffmpeg_cmd = "ffmpeg"
        project_root = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(project_root, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"),
            r"C:\Program Files\Dubb\resources\app.asar.unpacked\binaries\ffmpeg\ffmpeg.exe",
            r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
            "ffmpeg"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                ffmpeg_cmd = path
                break

        target = presets[preset]
        target_w = target["w"]
        target_h = target["h"]

        # Crop to fill target aspect ratio, then scale to target dims
        vf = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
        base_name = os.path.splitext(filename)[0]
        out_path = os.path.join(tmpdir, f"{base_name}_{preset}.mp4")

        cmd = [
            ffmpeg_cmd,
            "-i", uploaded_file_path,
            "-vf", vf,
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-y", out_path
        ]
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")

        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1200,
                check=False
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return jsonify({"error": "Video resize timed out (>20 min)."}), 504

        if completed.returncode != 0 or not os.path.exists(out_path):
            stderr = sanitize_process_output(completed.stderr)
            logger.warning(
                "video_resize_failed preset=%s returncode=%s stderr=%r",
                preset,
                completed.returncode,
                stderr[-500:],
            )
            shutil.rmtree(tmpdir, ignore_errors=True)
            return jsonify({
                "error": "Failed to resize video. Try a different file format.",
                "details": stderr if app.debug else None,
            }), 500

        resp = send_file(
            out_path,
            as_attachment=True,
            download_name=os.path.basename(out_path),
            mimetype="video/mp4",
            conditional=True,
            max_age=0,
        )
        resp.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
        return resp

    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500


@app.post("/api/video/resize-batch")
@require_paid_plan("pro")
def video_resize_batch():
    """
    Export one video into multiple aspect ratios and return a ZIP.

    Form data:
      - file: video file (optional)
      - url: video URL (optional)
      - cookies: optional cookie string for URL
      - ratios: JSON array of ratios (e.g., ["9:16","4:5","1:1","16:9"])
      - mode: crop|fit|pad|blur (optional, default crop)
    """
    file = request.files.get("file")
    url = (request.form.get("url") or "").strip()
    cookie_string = (request.form.get("cookies") or "").strip() or None
    ratios_raw = request.form.get("ratios") or "[]"
    mode = (request.form.get("mode") or "crop").strip().lower()

    if not file and not url:
        return jsonify({"error": "Provide a file or URL"}), 400
    if file and file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if mode not in ("crop", "fit", "pad", "blur"):
        return jsonify({"error": "Invalid mode"}), 400

    try:
        ratios = json.loads(ratios_raw)
    except Exception:
        return jsonify({"error": "Invalid ratios JSON"}), 400

    if not isinstance(ratios, list) or not ratios:
        return jsonify({"error": "Ratios must be a non-empty array"}), 400

    ratio_presets = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "4:5": (1080, 1350),
    }
    for r in ratios:
        if r not in ratio_presets:
            return jsonify({"error": f"Invalid ratio: {r}"}), 400

    tmpdir = tempfile.mkdtemp(prefix="video_export_")

    try:
        if file:
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({
                    "error": f"File too large. Maximum size is {max_size_mb} MB.",
                    "max_size_mb": max_size_mb
                }), 413

            filename = os.path.basename(file.filename)
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            uploaded_file_path = os.path.join(tmpdir, filename)
            file.save(uploaded_file_path)
        else:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return jsonify({"error": "Invalid url scheme"}), 400
            if is_private_host(parsed.hostname or ""):
                return jsonify({"error": "Target not allowed"}), 403
            uploaded_file_path = _download_video_from_url(url, cookie_string, tmpdir)

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        output_files = []
        base_name = os.path.splitext(os.path.basename(uploaded_file_path))[0]

        for ratio in ratios:
            tw, th = ratio_presets[ratio]
            if mode == "crop":
                vf = f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"
            elif mode in ("fit", "pad"):
                vf = f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black"
            else:  # blur
                vf = (
                    f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,boxblur=20:1,"
                    f"scale={tw}:{th}[bg];"
                    f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                )

            out_name = f"{base_name}_{ratio.replace(':','x')}.mp4"
            out_path = os.path.join(tmpdir, out_name)
            cmd = [
                ffmpeg_cmd,
                "-i", uploaded_file_path,
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-y", out_path
            ]
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1800,
                check=False
            )
            if completed.returncode != 0 or not os.path.exists(out_path):
                return jsonify({"error": f"Failed to export {ratio}"}), 500
            output_files.append(out_path)

        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        zip_name = f"viddash-exports-{stamp}.zip"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in output_files:
                zf.write(p, os.path.basename(p))
        zip_buf.seek(0)

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=zip_name,
            mimetype="application/zip",
            max_age=0,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/api/video/compress-batch")
@require_paid_plan("pro")
def video_compress_batch():
    """
    Compress a video into multiple target sizes and return a ZIP.

    Form data:
      - file: video file (optional)
      - url: video URL (optional)
      - cookies: optional cookie string for URL
      - targets: JSON array of target sizes in MB (e.g., [10,25,100])
      - codec: h264|h265 (optional, default h264)
      - audio: audio bitrate in kbps (optional, default 128)
    """
    file = request.files.get("file")
    url = (request.form.get("url") or "").strip()
    cookie_string = (request.form.get("cookies") or "").strip() or None
    targets_raw = request.form.get("targets") or "[]"
    codec = (request.form.get("codec") or "h264").strip().lower()
    audio_k = request.form.get("audio", type=int) or 128

    if not file and not url:
        return jsonify({"error": "Provide a file or URL"}), 400
    if file and file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if codec not in ("h264", "h265"):
        return jsonify({"error": "Invalid codec"}), 400
    audio_k = max(64, min(audio_k, 256))

    try:
        targets = json.loads(targets_raw)
    except Exception:
        return jsonify({"error": "Invalid targets JSON"}), 400

    if not isinstance(targets, list) or not targets:
        return jsonify({"error": "Targets must be a non-empty array"}), 400

    clean_targets = []
    for t in targets:
        try:
            v = float(t)
        except Exception:
            return jsonify({"error": f"Invalid target size: {t}"}), 400
        if v <= 1 or v > 1024:
            return jsonify({"error": "Target sizes must be between 1 and 1024 MB"}), 400
        clean_targets.append(v)

    tmpdir = tempfile.mkdtemp(prefix="video_compress_")

    try:
        if file:
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({
                    "error": f"File too large. Maximum size is {max_size_mb} MB.",
                    "max_size_mb": max_size_mb
                }), 413

            filename = os.path.basename(file.filename)
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            uploaded_file_path = os.path.join(tmpdir, filename)
            file.save(uploaded_file_path)
        else:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return jsonify({"error": "Invalid url scheme"}), 400
            if is_private_host(parsed.hostname or ""):
                return jsonify({"error": "Target not allowed"}), 403
            uploaded_file_path = _download_video_from_url(url, cookie_string, tmpdir)

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        ffprobe_cmd = _find_media_binary("ffprobe")

        # Get duration (seconds)
        probe = subprocess.run(
            [
                ffprobe_cmd,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                uploaded_file_path
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        if probe.returncode != 0:
            return jsonify({"error": "Failed to read video duration"}), 500
        try:
            duration = float((probe.stdout or "").strip())
        except Exception:
            duration = 0.0
        if duration <= 0:
            return jsonify({"error": "Invalid video duration"}), 500

        vcodec = "libx264" if codec == "h264" else "libx265"
        output_files = []
        base_name = os.path.splitext(os.path.basename(uploaded_file_path))[0]

        for t_mb in clean_targets:
            total_bits = t_mb * 1024 * 1024 * 8
            total_bps = total_bits / duration
            audio_bps = audio_k * 1000
            video_bps = max(int(total_bps - audio_bps), 120_000)

            out_name = f"{base_name}_{int(t_mb)}MB_{codec}.mp4"
            out_path = os.path.join(tmpdir, out_name)
            passlog = os.path.join(tmpdir, f"pass_{int(t_mb)}")

            # Pass 1
            cmd1 = [
                ffmpeg_cmd,
                "-y",
                "-i", uploaded_file_path,
                "-c:v", vcodec,
                "-b:v", str(video_bps),
                "-preset", "medium",
                "-pass", "1",
                "-passlogfile", passlog,
                "-an",
                "-f", "mp4",
                "NUL"
            ]
            subprocess.run(
                cmd1,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1800,
                check=False
            )

            # Pass 2
            cmd2 = [
                ffmpeg_cmd,
                "-y",
                "-i", uploaded_file_path,
                "-c:v", vcodec,
                "-b:v", str(video_bps),
                "-preset", "medium",
                "-pass", "2",
                "-passlogfile", passlog,
                "-c:a", "aac",
                "-b:a", f"{audio_k}k",
                "-movflags", "+faststart",
                out_path
            ]
            completed = subprocess.run(
                cmd2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1800,
                check=False
            )
            if completed.returncode != 0 or not os.path.exists(out_path):
                return jsonify({"error": f"Failed to compress to {t_mb} MB"}), 500

            output_files.append(out_path)

        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        zip_name = f"viddash-compressed-{stamp}.zip"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in output_files:
                zf.write(p, os.path.basename(p))
        zip_buf.seek(0)

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=zip_name,
            mimetype="application/zip",
            max_age=0,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _escape_drawtext(text: str) -> str:
    # Escape for ffmpeg drawtext
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )


def process_watermark_job(job_id: str, user_id: int, tmpdir: str, uploaded_file_path: str, logo_path: str | None, text: str, position: str, source_type: str, source_host: str | None, source_hash: str):
    started = time.monotonic()
    try:
        update_media_job(job_id, "processing", "Applying watermark...")
        ffmpeg_cmd = _find_media_binary("ffmpeg")
        base_name = os.path.splitext(os.path.basename(uploaded_file_path))[0]
        out_path = os.path.join(tmpdir, f"{base_name}_watermark.mp4")

        margin = 24
        overlay_x = f"{margin}" if position == "bottom-left" else f"main_w-overlay_w-{margin}"
        overlay_y = f"main_h-overlay_h-{margin}"
        text_x = f"{margin}" if position == "bottom-left" else f"w-text_w-{margin}"
        text_y = f"h-text_h-{margin}"

        filter_parts = []
        inputs = ["-i", uploaded_file_path]

        if logo_path:
            inputs.extend(["-i", logo_path])
            filter_parts.append("[1:v]scale=iw*0.15:-1[logo]")
            filter_parts.append(f"[0:v][logo]overlay={overlay_x}:{overlay_y}[v0]")
            v_in = "[v0]"
        else:
            v_in = "[0:v]"

        if text:
            font_candidates = [
                r"C:\Windows\Fonts\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ]
            fontfile = next((candidate for candidate in font_candidates if os.path.exists(candidate)), "")
            font_part = f"fontfile='{fontfile}':" if fontfile else ""
            safe_text = _escape_drawtext(text)
            drawtext = (
                f"drawtext={font_part}text='{safe_text}':"
                f"x={text_x}:y={text_y}:fontsize=32:"
                f"fontcolor=white@0.75:shadowcolor=black@0.6:shadowx=2:shadowy=2"
            )
            if v_in == "[0:v]":
                filter_parts.append(f"[0:v]{drawtext}[vout]")
            else:
                filter_parts.append(f"{v_in}{drawtext}[vout]")
        else:
            filter_parts.append(f"{v_in}null[vout]")

        cmd = [
            ffmpeg_cmd,
            *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[vout]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-y", out_path,
        ]
        logger.info(
            "watermark_job_ffmpeg job_id=%s user_id=%s source=%s host=%s url_hash=%s input_size=%s",
            job_id,
            user_id,
            source_type,
            source_host,
            source_hash,
            os.path.getsize(uploaded_file_path) if os.path.exists(uploaded_file_path) else None,
        )
        completed = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=int(os.environ.get("WATERMARK_JOB_TIMEOUT_SECONDS", "1800")),
            check=False,
        )
        elapsed = time.monotonic() - started
        if completed.returncode != 0 or not os.path.exists(out_path):
            stderr = sanitize_process_output(completed.stderr)
            logger.warning(
                "watermark_job_failed job_id=%s user_id=%s elapsed=%.2f returncode=%s stderr=%r",
                job_id,
                user_id,
                elapsed,
                completed.returncode,
                stderr[-500:],
            )
            update_media_job(job_id, "failed", "Watermark failed during processing.", error=stderr or "FFmpeg failed")
            record_user_activity(
                user_id,
                "media.watermark_failed",
                "Video watermark failed during background processing.",
                "error",
                {"job_id": job_id, "source": source_type, "host": source_host, "url_hash": source_hash, "elapsed": round(elapsed, 2), "returncode": completed.returncode},
            )
            shutil.rmtree(tmpdir, ignore_errors=True)
            return

        update_media_job(
            job_id,
            "complete",
            "Watermark complete. Your download is ready.",
            output_path=out_path,
            output_name=os.path.basename(out_path),
        )
        logger.info(
            "watermark_job_success job_id=%s user_id=%s elapsed=%.2f file_size=%s",
            job_id,
            user_id,
            elapsed,
            os.path.getsize(out_path),
        )
        record_user_activity(
            user_id,
            "media.watermark_success",
            "Prepared watermarked video.",
            "success",
            {"job_id": job_id, "source": source_type, "host": source_host, "url_hash": source_hash, "elapsed": round(elapsed, 2), "file_size": os.path.getsize(out_path)},
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        logger.warning("watermark_job_timeout job_id=%s user_id=%s elapsed=%.2f", job_id, user_id, elapsed)
        update_media_job(job_id, "failed", "Watermark took too long.", error="Watermark job timed out")
        record_user_activity(
            user_id,
            "media.watermark_timeout",
            "Video watermark timed out in background processing.",
            "error",
            {"job_id": job_id, "source": source_type, "host": source_host, "url_hash": source_hash, "elapsed": round(elapsed, 2)},
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        logger.exception("watermark_job_exception job_id=%s user_id=%s", job_id, user_id)
        update_media_job(job_id, "failed", "Watermark failed unexpectedly.", error="Unexpected processing error")
        record_user_activity(user_id, "media.watermark_failed", "Video watermark failed unexpectedly.", "error", {"job_id": job_id})
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/api/video/watermark")
@require_paid_plan("pro")
def video_watermark():
    """
    Add an image or text watermark to a video.

    Form data:
      - file: video file (optional)
      - url: video URL (optional)
      - cookies: optional cookie string for URL
      - logo: image file (optional)
      - text: watermark text (optional)
      - position: bottom-left|bottom-right (optional, default bottom-right)
    """
    user = get_current_user()
    file = request.files.get("file")
    url = (request.form.get("url") or "").strip()
    cookie_string = (request.form.get("cookies") or "").strip() or None
    logo = request.files.get("logo")
    text = (request.form.get("text") or "").strip()
    position = (request.form.get("position") or "bottom-right").strip()

    source_type = "upload" if file else "url"
    source_host = None
    source_hash = safe_url_fingerprint(url) if url else ""
    if not file and not url:
        return jsonify({"error": "Provide a file or URL"}), 400
    if file and file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not logo and not text:
        return jsonify({"error": "Provide a logo or text watermark"}), 400
    if position not in ("bottom-left", "bottom-right"):
        return jsonify({"error": "Invalid position"}), 400

    tmpdir = tempfile.mkdtemp(prefix="video_watermark_")

    try:
        if file:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({
                    "error": f"File too large. Maximum size is {max_size_mb} MB.",
                    "max_size_mb": max_size_mb
                }), 413

            filename = os.path.basename(file.filename)
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            uploaded_file_path = os.path.join(tmpdir, filename)
            file.save(uploaded_file_path)
        else:
            parsed = urlparse(url)
            source_host = parsed.hostname
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return jsonify({"error": "Invalid url scheme"}), 400
            if is_private_host(parsed.hostname or ""):
                return jsonify({"error": "Target not allowed"}), 403
            uploaded_file_path = _download_video_from_url(url, cookie_string, tmpdir)

        logo_path = None
        if logo and logo.filename:
            logo_name = os.path.basename(logo.filename)
            logo_name = re.sub(r"[^a-zA-Z0-9._-]", "_", logo_name)
            logo_path = os.path.join(tmpdir, logo_name)
            logo.save(logo_path)

        job_id = create_media_job(
            user["id"],
            "video_watermark",
            "Watermark job queued.",
            {
                "source": source_type,
                "host": source_host,
                "url_hash": source_hash,
                "has_logo": bool(logo_path),
                "has_text": bool(text),
                "position": position,
            },
        )
        logger.info(
            "watermark_job_queued job_id=%s user_id=%s source=%s host=%s url_hash=%s has_logo=%s has_text=%s position=%s",
            job_id,
            user["id"],
            source_type,
            source_host,
            source_hash,
            bool(logo_path),
            bool(text),
            position,
        )
        record_user_activity(
            user["id"],
            "media.watermark_started",
            f"Started video watermark from {'uploaded file' if source_type == 'upload' else source_host or 'video URL'}.",
            "info",
            {"job_id": job_id, "source": source_type, "host": source_host, "url_hash": source_hash, "position": position},
        )
        thread = threading.Thread(
            target=process_watermark_job,
            args=(job_id, user["id"], tmpdir, uploaded_file_path, logo_path, text, position, source_type, source_host, source_hash),
            daemon=True,
        )
        thread.start()
        return jsonify({"job_id": job_id, "status": "queued", "message": "Watermark job queued."}), 202
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


@app.get("/api/jobs/<job_id>")
@require_login
def media_job_status(job_id):
    user = get_current_user()
    job = get_media_job(job_id, user["id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404
    payload = {
        "job_id": job["id"],
        "type": job["job_type"],
        "status": job["status"],
        "message": job["message"],
        "error": job["error"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "download_url": url_for("media_job_download", job_id=job["id"]) if job["status"] == "complete" else None,
    }
    return jsonify(payload)


@app.get("/api/jobs/<job_id>/download")
@require_login
def media_job_download(job_id):
    user = get_current_user()
    job = get_media_job(job_id, user["id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "complete":
        return jsonify({"error": "Job is not complete yet"}), 409
    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        update_media_job(job_id, "failed", "Download file expired or was removed.", error="Output file missing")
        return jsonify({"error": "Download file is no longer available"}), 410
    return send_file(
        output_path,
        as_attachment=True,
        download_name=job["output_name"] or os.path.basename(output_path),
        mimetype="video/mp4",
        conditional=True,
        max_age=0,
    )


@app.post("/api/utm/csv")
def utm_csv():
    """
    Generate a CSV of UTM links.

    JSON body:
      - url: base URL (required)
      - source, medium, campaign: arrays or strings (required)
      - content, term: arrays or strings (optional)
    """
    payload = request.get_json(silent=True) or {}
    base_url = (payload.get("url") or "").strip()
    if not base_url:
        return jsonify({"error": "Missing url"}), 400

    def to_list(val):
        if val is None:
            return []
        if isinstance(val, list):
            return [str(v).strip() for v in val if str(v).strip()]
        return [v.strip() for v in str(val).replace("\r", "").split("\n") if v.strip()]

    sources = to_list(payload.get("source"))
    mediums = to_list(payload.get("medium"))
    campaigns = to_list(payload.get("campaign"))
    contents = to_list(payload.get("content"))
    terms = to_list(payload.get("term"))

    if not sources or not mediums or not campaigns:
        return jsonify({"error": "source, medium, and campaign are required"}), 400

    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        return jsonify({"error": "Invalid url scheme"}), 400

    base_qs = dict(parse_qsl(parsed.query, keep_blank_values=True))

    rows = []
    for s in sources:
        for m in mediums:
            for c in campaigns:
                for cont in (contents or [""]):
                    for t in (terms or [""]):
                        params = {
                            "utm_source": s,
                            "utm_medium": m,
                            "utm_campaign": c,
                        }
                        if cont:
                            params["utm_content"] = cont
                        if t:
                            params["utm_term"] = t
                        full_qs = base_qs.copy()
                        full_qs.update(params)
                        new_query = urlencode(full_qs, doseq=True)
                        url_out = urlunparse(parsed._replace(query=new_query))
                        rows.append({
                            "url": url_out,
                            "utm_source": s,
                            "utm_medium": m,
                            "utm_campaign": c,
                            "utm_content": cont,
                            "utm_term": t,
                        })

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["url", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    out = buf.getvalue().encode()
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return send_file(
        io.BytesIO(out),
        as_attachment=True,
        download_name=f"utm-links-{stamp}.csv",
        mimetype="text/csv",
        max_age=0,
    )

def _find_media_binary(name: str) -> str:
    """Find ffmpeg/ffprobe binary path."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(project_root, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", f"{name}.exe"),
        rf"C:\Program Files\FFmpeg\bin\{name}.exe",
        name,
    ]
    for path in candidates:
        if os.path.exists(path) or path == name:
            return path
    return name


def _probe_audio_duration(path: str) -> float:
    """Return the duration of the first audio stream, rejecting non-audio inputs."""
    cmd = [
        _find_media_binary("ffprobe"),
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type:format=duration",
        "-of", "json",
        path,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
    if completed.returncode != 0:
        raise ValueError("One of the files could not be read as audio.")
    try:
        payload = json.loads(completed.stdout or "{}")
        streams = payload.get("streams") or []
        duration = float((payload.get("format") or {}).get("duration"))
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("One of the files has an unknown audio duration.")
    if not streams or not math.isfinite(duration) or duration <= 0:
        raise ValueError("One of the files does not contain a usable audio track.")
    return duration


@app.post("/api/audio/edit")
def audio_edit():
    """Trim, merge, and optionally clean uploaded audio tracks."""
    user = get_current_user()
    if not user:
        return api_error("Log in to use the audio editor.", 401, "login_required")

    free_daily_limit = 3
    if user["plan"] == "free":
        used_today = get_audio_edits_used_today(user["id"])
        if used_today >= free_daily_limit:
            return jsonify({
                "error": "free_limit_reached",
                "message": "You have used all 3 free audio exports for today. Upgrade for unlimited processing or try again tomorrow.",
                "limit": free_daily_limit,
                "used": used_today,
                "pricing_url": url_for("page_pricing"),
            }), 429

    files = [file for file in request.files.getlist("files") if file and file.filename]
    if not files:
        return jsonify({"error": "Choose at least one audio file."}), 400
    if len(files) > 10:
        return jsonify({"error": "You can merge up to 10 audio files at once."}), 400

    output_format = (request.form.get("format") or "mp3").strip().lower()
    if output_format not in {"mp3", "m4a", "wav", "flac"}:
        return jsonify({"error": "Invalid format. Use mp3, m4a, wav, or flac."}), 400

    cleanup = (request.form.get("cleanup") or "off").strip().lower()
    if cleanup not in {"off", "light", "studio"}:
        return jsonify({"error": "Invalid cleanup profile."}), 400

    try:
        edits = json.loads(request.form.get("edits") or "[]")
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid edit data."}), 400
    if not isinstance(edits, list) or len(edits) != len(files):
        return jsonify({"error": "Each audio file needs matching trim settings."}), 400

    tmpdir = tempfile.mkdtemp(prefix="audio_edit_")
    keep_tmpdir = False
    try:
        input_paths = []
        durations = []
        total_size = 0
        allowed_extensions = {
            ".aac", ".aiff", ".aif", ".alac", ".flac", ".m4a", ".mp3",
            ".ogg", ".opus", ".wav", ".wma", ".webm", ".mp4", ".mov",
        }

        for index, file in enumerate(files):
            extension = os.path.splitext(os.path.basename(file.filename))[1].lower()
            if extension not in allowed_extensions:
                return jsonify({"error": f"Unsupported audio type: {extension or 'unknown'}"}), 415
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            total_size += file_size
            if total_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({"error": f"Combined files exceed the {max_size_mb} MB upload limit."}), 413

            input_path = os.path.join(tmpdir, f"input_{index:02d}{extension}")
            file.save(input_path)
            input_paths.append(input_path)
            durations.append(_probe_audio_duration(input_path))

        trim_ranges = []
        output_duration = 0.0
        for index, (edit, duration) in enumerate(zip(edits, durations), 1):
            if not isinstance(edit, dict):
                return jsonify({"error": f"Invalid trim settings for track {index}."}), 400
            try:
                start = float(edit.get("start", 0))
                raw_end = edit.get("end")
                end = duration if raw_end in (None, "") else float(raw_end)
            except (TypeError, ValueError):
                return jsonify({"error": f"Track {index} has invalid trim times."}), 400
            if not all(math.isfinite(value) for value in (start, end)):
                return jsonify({"error": f"Track {index} has invalid trim times."}), 400
            if start < 0 or end <= start or end > duration + 0.25:
                return jsonify({"error": f"Track {index} trim must stay within its {duration:.1f}s duration."}), 400
            end = min(end, duration)
            trim_ranges.append((start, end))
            output_duration += end - start

        if output_duration > 4 * 60 * 60:
            return jsonify({"error": "The edited result cannot exceed four hours."}), 400

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        cmd = [ffmpeg_cmd, "-hide_banner", "-loglevel", "error", "-y"]
        for input_path in input_paths:
            cmd.extend(["-i", input_path])

        filter_parts = []
        track_labels = []
        for index, (start, end) in enumerate(trim_ranges):
            label = f"track{index}"
            filter_parts.append(
                f"[{index}:a:0]atrim=start={start:.6f}:end={end:.6f},"
                f"asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[{label}]"
            )
            track_labels.append(f"[{label}]")

        if len(track_labels) == 1:
            filter_parts.append(f"{track_labels[0]}anull[joined]")
        else:
            filter_parts.append(f"{''.join(track_labels)}concat=n={len(track_labels)}:v=0:a=1[joined]")

        cleanup_filters = {
            "off": "anull",
            "light": "highpass=f=70,afftdn=nf=-30,loudnorm=I=-16:LRA=9:TP=-1.5,alimiter=limit=0.95",
            "studio": (
                "highpass=f=75,lowpass=f=16000,afftdn=nf=-25:tn=1,"
                "equalizer=f=180:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1:g=3,"
                "acompressor=threshold=0.09:ratio=3:attack=20:release=250:makeup=2,"
                "loudnorm=I=-16:LRA=7:TP=-1.5,alimiter=limit=0.95"
            ),
        }
        filter_parts.append(f"[joined]{cleanup_filters[cleanup]}[outa]")

        output_path = os.path.join(tmpdir, f"viddash-audio-edit.{output_format}")
        codec_options = {
            "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
            "m4a": ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"],
            "wav": ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
        }
        cmd.extend(["-filter_complex", ";".join(filter_parts), "-map", "[outa]"])
        cmd.extend(codec_options[output_format])
        cmd.append(output_path)

        completed = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1200,
            check=False,
        )
        if completed.returncode != 0 or not os.path.exists(output_path):
            stderr = sanitize_process_output(completed.stderr)
            logger.warning("audio_edit_failed cleanup=%s tracks=%s stderr=%r", cleanup, len(files), stderr[-500:])
            return jsonify({
                "error": "Audio processing failed. Check the files and trim times.",
                "details": stderr if app.debug else None,
            }), 500

        mime_types = {
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
            "flac": "audio/flac",
        }
        response = send_file(
            output_path,
            as_attachment=True,
            download_name=os.path.basename(output_path),
            mimetype=mime_types[output_format],
            conditional=True,
            max_age=0,
        )
        record_user_activity(
            user["id"],
            "media.audio_edit",
            f"Edited and exported {len(files)} audio track(s).",
            "success",
            {
                "cleanup": cleanup,
                "duration_seconds": round(output_duration, 2),
                "format": output_format,
                "tracks": len(files),
            },
        )
        keep_tmpdir = True
        response.call_on_close(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
        return response
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Audio processing timed out after 20 minutes."}), 504
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Unexpected audio editor failure")
        return jsonify({"error": "Audio processing failed unexpectedly."}), 500
    finally:
        if not keep_tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _download_video_from_url(url: str, cookie_string: str | None, tmpdir: str) -> str:
    """Download/merge a URL to a local MP4 using yt-dlp. Returns file path."""
    outtmpl = "source.%(ext)s"
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--max-filesize",
        "1500M",
        "-f",
        "bv*+ba/b[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        outtmpl,
        url,
    ]
    if cookie_string:
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])

    completed = subprocess.run(
        cmd,
        cwd=tmpdir,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        redacted = []
        for line in stderr.splitlines():
            if "cookie:" in line.lower() or "set-cookie" in line.lower():
                continue
            redacted.append(line)
        stderr = "\n".join(redacted).strip()
        raise RuntimeError(stderr or "yt-dlp failed")

    # Find output file
    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))]
    mp4s = [p for p in files if p.lower().endswith(".mp4")]
    if mp4s:
        return max(mp4s, key=lambda p: os.path.getsize(p))
    if files:
        return max(files, key=lambda p: os.path.getsize(p))
    raise RuntimeError("Downloaded file not found")


@app.get("/video-clipper")
def page_video_clipper():
    return render_public_page("video-clipper.html", "video-clipper")


@app.get("/video-thumbnails")
def page_video_thumbnails():
    return render_public_page("video-thumbnails.html", "video-thumbnails")


@app.post("/api/video/clip")
@require_paid_plan("pro")
def video_clip():
    """
    Cut one or more clips from a video (file or URL) and return a ZIP of MP4s.

    Form data:
      - file: video file (optional)
      - url: video URL (optional)
      - cookies: optional cookie string for URL
      - segments: JSON array of {start, end} in seconds (required)
      - aspect: original|16:9|9:16|1:1|4:5 (optional, default original)
      - mode: crop|fit|pad|blur (optional, default crop)
    """
    file = request.files.get("file")
    url = (request.form.get("url") or "").strip()
    cookie_string = (request.form.get("cookies") or "").strip() or None
    segments_raw = request.form.get("segments")
    preset_aspect = (request.form.get("aspect") or "original").strip()
    mode = (request.form.get("mode") or "crop").strip().lower()

    if not file and not url:
        return jsonify({"error": "Provide a file or URL"}), 400
    if file and file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not segments_raw:
        return jsonify({"error": "Missing segments"}), 400

    try:
        segments = json.loads(segments_raw)
    except Exception:
        return jsonify({"error": "Invalid segments JSON"}), 400

    if not isinstance(segments, list) or not segments:
        return jsonify({"error": "Segments must be a non-empty array"}), 400

    tmpdir = tempfile.mkdtemp(prefix="video_clip_")

    try:
        if file:
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({
                    "error": f"File too large. Maximum size is {max_size_mb} MB.",
                    "max_size_mb": max_size_mb
                }), 413

            filename = os.path.basename(file.filename)
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            uploaded_file_path = os.path.join(tmpdir, filename)
            file.save(uploaded_file_path)
        else:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return jsonify({"error": "Invalid url scheme"}), 400
            if is_private_host(parsed.hostname or ""):
                return jsonify({"error": "Target not allowed"}), 403
            uploaded_file_path = _download_video_from_url(url, cookie_string, tmpdir)

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        aspect_presets = {
            "original": None,
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "4:5": (1080, 1350),
        }
        target = aspect_presets.get(preset_aspect)
        if preset_aspect not in aspect_presets:
            return jsonify({"error": "Invalid aspect"}), 400
        if mode not in ("crop", "fit", "pad", "blur"):
            return jsonify({"error": "Invalid mode"}), 400

        vf = None
        filter_complex = None
        if target:
            tw, th = target
            if mode == "crop":
                vf = f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"
            elif mode in ("fit", "pad"):
                vf = f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black"
            elif mode == "blur":
                filter_complex = (
                    f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},boxblur=20:1[bg];"
                    f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[vout]"
                )
        else:
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"
        output_files = []

        for idx, seg in enumerate(segments, 1):
            try:
                start = float(seg.get("start"))
                end = float(seg.get("end"))
            except Exception:
                return jsonify({"error": "Segment start/end must be numbers"}), 400
            if start < 0 or end <= start:
                return jsonify({"error": "Each segment must have end > start"}), 400

            out_name = f"clip_{idx:02d}.mp4"
            out_path = os.path.join(tmpdir, out_name)

            cmd = [
                ffmpeg_cmd,
                "-ss", str(start),
                "-i", uploaded_file_path,
                "-t", str(end - start),
            ]
            if filter_complex:
                cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "0:a?"])
            elif vf:
                cmd.extend(["-vf", vf])
                cmd.extend(["-map", "0:v:0", "-map", "0:a?"])
            else:
                cmd.extend(["-map", "0:v:0", "-map", "0:a?"])
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-y", out_path
            ])
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")

            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1200,
                check=False
            )
            if completed.returncode != 0 or not os.path.exists(out_path):
                stderr = sanitize_process_output(completed.stderr)
                logger.warning(
                    "video_clip_failed clip=%s aspect=%s mode=%s returncode=%s stderr=%r",
                    idx,
                    preset_aspect,
                    mode,
                    completed.returncode,
                    stderr[-500:],
                )
                return jsonify({
                    "error": f"Failed to create clip {idx}",
                    "details": stderr if app.debug else None,
                }), 500

            output_files.append(out_path)

        if not output_files:
            return jsonify({"error": "No clips generated"}), 500

        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        zip_name = f"viddash-clips-{stamp}.zip"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in output_files:
                zf.write(p, os.path.basename(p))
        zip_buf.seek(0)

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=zip_name,
            mimetype="application/zip",
            max_age=0,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/api/video/thumbnails")
@require_paid_plan("pro")
def video_thumbnails():
    """
    Generate a thumbnail grid and a 'best' frame from a video (file or URL).

    Form data:
      - file: video file (optional)
      - url: video URL (optional)
      - cookies: optional cookie string for URL
      - count: number of frames to sample (optional, default 12)
      - scene: scene sensitivity 0.1-0.9 (optional, default 0.35)
      - mode: "zip" or "best" (optional, default zip)
    """
    file = request.files.get("file")
    url = (request.form.get("url") or "").strip()
    cookie_string = (request.form.get("cookies") or "").strip() or None
    if not file and not url:
        return jsonify({"error": "Provide a file or URL"}), 400
    if file and file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    count = request.form.get("count", type=int) or 12
    count = max(4, min(count, 48))
    scene = request.form.get("scene", type=float)
    if scene is None:
        scene = 0.35
    scene = max(0.1, min(scene, 0.9))
    mode = (request.form.get("mode") or "zip").strip().lower()
    if mode not in ("zip", "best"):
        return jsonify({"error": "Invalid mode"}), 400

    tmpdir = tempfile.mkdtemp(prefix="video_thumbs_")

    try:
        if file:
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_UPLOAD_BYTES:
                max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
                return jsonify({
                    "error": f"File too large. Maximum size is {max_size_mb} MB.",
                    "max_size_mb": max_size_mb
                }), 413

            filename = os.path.basename(file.filename)
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            uploaded_file_path = os.path.join(tmpdir, filename)
            file.save(uploaded_file_path)
        else:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return jsonify({"error": "Invalid url scheme"}), 400
            if is_private_host(parsed.hostname or ""):
                return jsonify({"error": "Target not allowed"}), 403
            uploaded_file_path = _download_video_from_url(url, cookie_string, tmpdir)

        ffmpeg_cmd = _find_media_binary("ffmpeg")
        ffprobe_cmd = _find_media_binary("ffprobe")

        # Get duration (seconds)
        duration = None
        try:
            probe = subprocess.run(
                [
                    ffprobe_cmd,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    uploaded_file_path
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            if probe.returncode == 0:
                duration = float((probe.stdout or "").strip() or 0)
        except Exception:
            duration = None

        if not duration or duration <= 0:
            duration = 60.0

        # Choose "best" frame using scene detection (fallback to middle frame)
        best_path = None
        scene_dir = os.path.join(tmpdir, "scenes")
        os.makedirs(scene_dir, exist_ok=True)
        cmd_scene = [
            ffmpeg_cmd,
            "-i", uploaded_file_path,
            "-vf", f"select='gt(scene,{scene})'",
            "-vsync", "vfr",
            os.path.join(scene_dir, "scene_%02d.jpg")
        ]
        subprocess.run(
            cmd_scene,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
            check=False
        )
        scene_files = sorted([p for p in os.listdir(scene_dir) if p.lower().endswith(".jpg")])
        if scene_files:
            best_path = os.path.join(scene_dir, scene_files[len(scene_files) // 2])
        else:
            # Fallback: middle frame by timestamp
            fallback_path = os.path.join(tmpdir, "best.jpg")
            mid = max(duration / 2.0, 0)
            cmd_mid = [
                ffmpeg_cmd,
                "-ss", str(mid),
                "-i", uploaded_file_path,
                "-frames:v", "1",
                "-q:v", "2",
                "-y",
                fallback_path
            ]
            subprocess.run(
                cmd_mid,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                check=False
            )
            best_path = fallback_path if os.path.exists(fallback_path) else None

        if mode == "best":
            if not best_path or not os.path.exists(best_path):
                return jsonify({"error": "Failed to generate best thumbnail"}), 500
            return send_file(
                best_path,
                as_attachment=True,
                download_name="best-thumbnail.jpg",
                mimetype="image/jpeg",
                max_age=0,
            )

        interval = max(duration / count, 1.0)
        thumbs_dir = os.path.join(tmpdir, "frames")
        os.makedirs(thumbs_dir, exist_ok=True)

        # Extract evenly spaced frames
        cmd = [
            ffmpeg_cmd,
            "-i", uploaded_file_path,
            "-vf", f"fps=1/{interval}",
            "-frames:v", str(count),
            os.path.join(thumbs_dir, "frame_%02d.jpg")
        ]
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")
        completed = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
            check=False
        )
        if completed.returncode != 0:
            return jsonify({"error": "Failed to extract frames"}), 500

        # Build grid image (simple contact sheet)
        grid_path = os.path.join(tmpdir, "grid.jpg")
        tile = int((count + 3) // 4)  # up to 4 columns
        cols = 4
        rows = max(1, tile)
        cmd_grid = [
            ffmpeg_cmd,
            "-i", os.path.join(thumbs_dir, "frame_%02d.jpg"),
            "-frames:v", "1",
            "-filter_complex", f"tile={cols}x{rows}",
            "-y",
            grid_path
        ]
        subprocess.run(
            cmd_grid,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False
        )

        zip_name = f"viddash-thumbnails-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in os.listdir(thumbs_dir):
                p = os.path.join(thumbs_dir, name)
                if os.path.isfile(p):
                    zf.write(p, f"frames/{name}")
            if best_path and os.path.exists(best_path):
                zf.write(best_path, "best.jpg")
            if os.path.exists(grid_path):
                zf.write(grid_path, "grid.jpg")
        zip_buf.seek(0)

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=zip_name,
            mimetype="application/zip",
            max_age=0,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/api/image/resize")
@require_login
def image_resize():
    if Image is None:
        return jsonify({"error": "Image processing is unavailable (missing Pillow)."}), 500

    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No images uploaded."}), 400

    try:
        width = int(request.form.get("width") or 0)
        height = int(request.form.get("height") or 0)
    except ValueError:
        return jsonify({"error": "Width/height must be numbers."}), 400

    fmt = (request.form.get("format") or "original").lower()
    quality = int(request.form.get("quality") or 82)
    quality = max(40, min(quality, 95))

    if width <= 0 and height <= 0 and fmt == "original":
        return jsonify({"error": "Provide a size or choose a different output format."}), 400

    total_size = 0
    output_files = []

    for f in files:
        if not f or not f.filename:
            continue
        if f.mimetype and not f.mimetype.startswith("image/"):
            return jsonify({"error": "Only image files are supported."}), 400
        data = f.read()
        total_size += len(data)
        if len(data) > MAX_IMAGE_BYTES or total_size > MAX_IMAGE_TOTAL_BYTES:
            return jsonify({"error": "Images are too large."}), 413
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception:
            return jsonify({"error": f"Invalid image: {f.filename}"}), 400

        orig_w, orig_h = img.size
        target_w, target_h = orig_w, orig_h
        if width > 0 and height > 0:
            # Fit inside box without distortion
            target_w, target_h = width, height
            img = img.copy()
            img.thumbnail((width, height), Image.LANCZOS)
        elif width > 0:
            target_w = width
            target_h = max(1, int(orig_h * (width / orig_w)))
            img = img.resize((target_w, target_h), Image.LANCZOS)
        elif height > 0:
            target_h = height
            target_w = max(1, int(orig_w * (height / orig_h)))
            img = img.resize((target_w, target_h), Image.LANCZOS)

        out_fmt = fmt
        if out_fmt == "original":
            out_fmt = (img.format or "PNG").lower()
        if out_fmt == "jpeg":
            out_fmt = "jpg"
        if out_fmt not in ALLOWED_IMAGE_FORMATS:
            return jsonify({"error": "Unsupported output format."}), 400

        seo_base = _slugify(os.path.splitext(f.filename)[0])
        seo_name = f"{seo_base}-{target_w}x{target_h}.{_image_ext_from_format(out_fmt)}"

        buf = io.BytesIO()
        save_kwargs = {}
        if out_fmt in ("jpg", "jpeg"):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
            save_kwargs["progressive"] = True
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", **save_kwargs)
        elif out_fmt == "webp":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6
            img.save(buf, format="WEBP", **save_kwargs)
        else:
            save_kwargs["optimize"] = True
            img.save(buf, format="PNG", **save_kwargs)
        buf.seek(0)
        output_files.append((seo_name, buf.read()))

    if not output_files:
        return jsonify({"error": "No valid images provided."}), 400

    if len(output_files) == 1:
        name, data = output_files[0]
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=name,
            mimetype="application/octet-stream",
            max_age=0,
        )

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    zip_name = f"viddash-images-{stamp}.zip"
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in output_files:
            zf.writestr(name, data)
    zip_buf.seek(0)
    return send_file(
        zip_buf,
        as_attachment=True,
        download_name=zip_name,
        mimetype="application/zip",
        max_age=0,
    )


@app.post("/api/transcribe")
@require_paid_plan("pro")
def transcribe():
    """
    Transcribe video using hybrid approach:
    1. Try to extract captions first (fast, free)
    2. If no captions, transcribe audio using Whisper (slower, but comprehensive)
    
    Request JSON:
      - url: video URL (required)
      - cookies: optional cookie string
      - language: optional language code (e.g., 'en', 'es')
      - format: optional format ('txt', 'srt', 'vtt', 'json') - default: json
    """
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    cookie_string = (payload.get("cookies") or "").strip() or None
    language = (payload.get("language") or "").strip() or None
    out_format = (payload.get("format") or "json").lower()
    
    if not url:
        return jsonify({"error": "Missing url"}), 400
    
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"error": "Invalid url scheme"}), 400
    if is_private_host(parsed.hostname or ""):
        return jsonify({"error": "Target not allowed"}), 403
    
    try:
        # Step 1: Try caption extraction (fast)
        captions_result = extract_captions_from_video(url, cookie_string, language)
        
        if captions_result["success"] and captions_result["captions"]:
            # Found captions! Convert to plain text or requested format
            primary_caption = captions_result["captions"][0]
            vtt_data = primary_caption["data"]
            
            # Parse VTT and extract text
            transcript_text = _parse_vtt_to_text(vtt_data)
            segments = _parse_vtt_to_segments(vtt_data)

            # Guard against incomplete caption tracks
            duration = captions_result.get("duration")
            coverage_ok = True
            if not segments or not transcript_text.strip():
                coverage_ok = False
            elif duration:
                try:
                    last_end = max(seg.get("end", 0) for seg in segments)
                    if last_end < (float(duration) * 0.6):
                        coverage_ok = False
                except Exception:
                    coverage_ok = False

            if not coverage_ok:
                logger.warning(
                    "Captions appear incomplete; falling back to audio transcription. "
                    f"duration={duration}, segments={len(segments)}, text_len={len(transcript_text)}"
                )
            else:
                response_data = {
                    "success": True,
                    "source": "captions",
                    "language": primary_caption["lang"],
                    "type": primary_caption["type"],
                    "transcript": transcript_text,
                    "segments": segments,
                    "error": None,
                }
                
                # Format output
                if out_format == "srt":
                    srt_content = segments_to_srt(segments)
                    return send_file(
                        io.BytesIO(srt_content.encode()),
                        as_attachment=True,
                        download_name="transcript.srt",
                        mimetype="text/plain",
                    )
                elif out_format == "vtt":
                    return send_file(
                        io.BytesIO(vtt_data.encode()),
                        as_attachment=True,
                        download_name="transcript.vtt",
                        mimetype="text/plain",
                    )
                elif out_format == "txt":
                    return send_file(
                        io.BytesIO(transcript_text.encode()),
                        as_attachment=True,
                        download_name="transcript.txt",
                        mimetype="text/plain",
                    )
                else:  # json
                    return jsonify(response_data)
        
        # Step 2: No captions found, use audio transcription
        whisper_result = transcribe_video_audio(url, cookie_string, language)
        
        if whisper_result["success"]:
            response_data = {
                "success": True,
                "source": "audio_transcription",
                "language": whisper_result["language"],
                "type": "generated",
                "transcript": whisper_result["transcript"],
                "segments": whisper_result["segments"],
                "error": None,
            }
            
            # Format output
            if out_format == "srt":
                srt_content = segments_to_srt(whisper_result["segments"])
                return send_file(
                    io.BytesIO(srt_content.encode()),
                    as_attachment=True,
                    download_name="transcript.srt",
                    mimetype="text/plain",
                )
            elif out_format == "vtt":
                vtt_content = segments_to_vtt(whisper_result["segments"])
                return send_file(
                    io.BytesIO(vtt_content.encode()),
                    as_attachment=True,
                    download_name="transcript.vtt",
                    mimetype="text/plain",
                )
            elif out_format == "txt":
                return send_file(
                    io.BytesIO(whisper_result["transcript"].encode()),
                    as_attachment=True,
                    download_name="transcript.txt",
                    mimetype="text/plain",
                )
            else:  # json
                return jsonify(response_data)
        else:
            return jsonify({
                "success": False,
                "source": None,
                "error": whisper_result["error"] or "Failed to transcribe video"
            }), 500
    
    except Exception as e:
        return jsonify({
            "success": False,
            "source": None,
            "error": str(e)
        }), 500


def _parse_vtt_to_text(vtt_data: str) -> str:
    """Extract plain text from VTT content."""
    lines = vtt_data.split("\n")
    text = ""
    for line in lines:
        line = line.strip()
        # Skip header, timecodes, and empty lines
        if line and not line.startswith("WEBVTT") and "-->" not in line:
            text += line + " "
    return text.strip()


def _parse_vtt_to_segments(vtt_data: str) -> list:
    """Parse VTT format into segment objects with timing."""
    segments = []
    lines = vtt_data.split("\n")
    i = 0
    seg_id = 1
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for timecode line
        if "-->" in line:
            try:
                parts = line.split("-->")
                start_str = parts[0].strip()
                end_str = parts[1].strip().split()[0]  # Handle additional params
                
                start = _timecode_to_seconds(start_str)
                end = _timecode_to_seconds(end_str)
                
                # Next non-empty line is the text
                i += 1
                text = ""
                while i < len(lines) and lines[i].strip():
                    text += lines[i].strip() + " "
                    i += 1
                
                if text.strip():
                    segments.append({
                        "id": seg_id,
                        "start": start,
                        "end": end,
                        "text": text.strip(),
                    })
                    seg_id += 1
            except Exception:
                i += 1
        else:
            i += 1
    
    return segments


def _timecode_to_seconds(timecode: str) -> float:
    """Convert VTT/SRT timecode to seconds."""
    try:
        # Format: HH:MM:SS,mmm or HH:MM:SS.mmm
        timecode = timecode.replace(",", ".")
        parts = timecode.split(":")
        hours = int(parts[0]) if len(parts) > 2 else 0
        minutes = int(parts[-2]) if len(parts) > 1 else 0
        secs = float(parts[-1])
        return hours * 3600 + minutes * 60 + secs
    except Exception:
        return 0.0


TRANSCRIPT_STOP_WORDS = {
    "about", "after", "again", "also", "because", "been", "before", "being",
    "between", "both", "could", "does", "doing", "from", "going", "have", "here",
    "into", "just", "like", "more", "most", "other", "over", "really", "should",
    "some", "such", "than", "that", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "very", "want", "what", "when", "where",
    "which", "while", "with", "would", "your", "youre", "were", "will", "yeah",
    "okay", "right", "thing", "things", "think", "know", "video", "today",
}


def _clean_caption_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _remove_caption_overlap(previous: str, current: str) -> str:
    previous_words = previous.split()
    current_words = current.split()
    previous_keys = [re.sub(r"\W+", "", word).lower() for word in previous_words]
    current_keys = [re.sub(r"\W+", "", word).lower() for word in current_words]
    max_overlap = min(len(previous_keys), len(current_keys), 30)
    for size in range(max_overlap, 0, -1):
        if previous_keys[-size:] == current_keys[:size]:
            return " ".join(current_words[size:]).strip()
    return current


def normalize_transcript_segments(segments: list) -> list:
    normalized = []
    for raw in sorted(segments or [], key=lambda item: float(item.get("start", 0))):
        text = _clean_caption_text(str(raw.get("text") or ""))
        if not text:
            continue
        if normalized:
            recent_transcript = " ".join(item["text"] for item in normalized[-5:])
            text = _remove_caption_overlap(recent_transcript, text)
        if not text:
            continue
        start = max(0.0, float(raw.get("start", 0)))
        end = max(start, float(raw.get("end", start)))
        normalized.append({"id": len(normalized) + 1, "start": start, "end": end, "text": text})
    return normalized


def _transcript_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", (text or "").lower())


def _chapter_title(segments: list, keyword_counts: Counter) -> str:
    if not segments:
        return "Untitled section"
    representative = max(
        segments,
        key=lambda segment: sum(keyword_counts.get(word, 0) for word in _transcript_words(segment["text"])),
    )["text"]
    representative = re.sub(
        r"^(so|and|but|okay|now|well|today|in this video|we are going to|we're going to)\b[,:\s-]*",
        "",
        representative,
        flags=re.IGNORECASE,
    )
    words = representative.strip(" .,!?:;-\"").split()
    title = " ".join(words[:9]) or "Key discussion"
    if len(title) > 64:
        title = title[:61].rsplit(" ", 1)[0] + "..."
    return title[0].upper() + title[1:] if title else "Key discussion"


def build_transcript_intelligence(segments: list, duration: float | None = None) -> dict:
    segments = normalize_transcript_segments(segments)
    transcript = " ".join(segment["text"] for segment in segments).strip()
    words = _transcript_words(transcript)
    meaningful = [
        word for word in words
        if len(word) >= 4 and word not in TRANSCRIPT_STOP_WORDS and not word.isdigit()
    ]
    counts = Counter(meaningful)
    keywords = [
        {"term": term, "count": count}
        for term, count in counts.most_common(12)
    ]

    paragraphs = []
    current = None
    for segment in segments:
        segment_words = len(_transcript_words(segment["text"]))
        should_break = (
            current is None
            or segment["start"] - current["end"] > 3
            or current["end"] - current["start"] >= 42
            or current["word_count"] >= 80
        )
        if should_break:
            current = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "word_count": segment_words,
            }
            paragraphs.append(current)
        else:
            current["end"] = segment["end"]
            current["text"] += " " + segment["text"]
            current["word_count"] += segment_words
    for paragraph in paragraphs:
        paragraph.pop("word_count", None)

    scored = []
    for segment in segments:
        segment_words = _transcript_words(segment["text"])
        if len(segment_words) < 5:
            continue
        score = sum(counts.get(word, 0) for word in segment_words) / math.sqrt(len(segment_words))
        if segment["text"].rstrip().endswith((".", "?", "!")):
            score += 1
        scored.append((score, segment))
    key_moments = []
    for _, segment in sorted(scored, key=lambda item: item[0], reverse=True):
        if any(abs(segment["start"] - item["start"]) < 35 for item in key_moments):
            continue
        key_moments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"][:280],
        })
        if len(key_moments) >= 6:
            break
    key_moments.sort(key=lambda item: item["start"])

    total_duration = float(duration or (segments[-1]["end"] if segments else 0))
    target_chapters = max(1, min(8, math.ceil(total_duration / 240))) if total_duration else 0
    chapter_span = total_duration / target_chapters if target_chapters else 0
    chapters = []
    for index in range(target_chapters):
        start = index * chapter_span
        end = total_duration if index == target_chapters - 1 else (index + 1) * chapter_span
        chapter_segments = [segment for segment in segments if start <= segment["start"] < end]
        if not chapter_segments:
            continue
        chapters.append({
            "start": chapter_segments[0]["start"],
            "end": chapter_segments[-1]["end"],
            "title": _chapter_title(chapter_segments, counts),
            "draft": True,
        })

    speaking_minutes = total_duration / 60 if total_duration else 0
    return {
        "transcript": transcript,
        "segments": segments,
        "paragraphs": paragraphs,
        "chapters": chapters,
        "key_moments": key_moments,
        "keywords": keywords,
        "stats": {
            "words": len(words),
            "reading_minutes": max(1, math.ceil(len(words) / 200)) if words else 0,
            "speaking_wpm": round(len(words) / speaking_minutes) if speaking_minutes else 0,
            "duration_seconds": round(total_duration, 2),
        },
    }


def _select_caption(captions: list, language: str | None) -> dict | None:
    if not captions:
        return None
    requested = (language or "").lower()
    if requested:
        for caption in captions:
            caption_language = str(caption.get("lang") or "").lower()
            if caption_language == requested or caption_language.startswith(requested + "-"):
                return caption
    for caption in captions:
        if str(caption.get("lang") or "").lower() in {"en", "en-us", "en-gb"}:
            return caption
    return captions[0]


@app.post("/api/youtube-transcript-studio")
def youtube_transcript_studio():
    user = get_current_user()
    if not user:
        return api_error("Log in to create a YouTube transcript project.", 401, "login_required")

    free_daily_limit = 3
    used_today = get_youtube_transcripts_used_today(user["id"]) if user["plan"] == "free" else 0
    if user["plan"] == "free" and used_today >= free_daily_limit:
        return jsonify({
            "error": "free_limit_reached",
            "message": "You have used all 3 free YouTube transcript projects for today. Try again tomorrow or upgrade for unrestricted processing.",
            "limit": free_daily_limit,
            "used": used_today,
            "pricing_url": url_for("page_pricing"),
        }), 429

    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    language = (payload.get("language") or "").strip() or None
    cookie_string = (payload.get("cookies") or "").strip() or None
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        is_youtube = hostname == "youtu.be" or hostname == "youtube.com" or hostname.endswith(".youtube.com")
        if parsed.scheme not in {"http", "https"} or not is_youtube:
            return jsonify({"error": "invalid_youtube_url", "message": "Paste a valid YouTube video URL."}), 400
        if is_private_host(hostname):
            return jsonify({"error": "Target not allowed"}), 403

        captions_result = extract_captions_from_video(url, cookie_string, language)
        video = captions_result.get("video") or {"webpage_url": url, "duration": captions_result.get("duration")}
        duration = float(video.get("duration") or 0)
        if duration > 4 * 60 * 60:
            return jsonify({"error": "video_too_long", "message": "Videos longer than four hours are not supported."}), 400

        caption = _select_caption(captions_result.get("captions") or [], language)
        if caption:
            source = "manual_captions" if caption.get("type") == "manual" else "automatic_captions"
            source_label = "Creator captions" if source == "manual_captions" else "YouTube automatic captions"
            segments = _parse_vtt_to_segments(caption["data"])
            detected_language = caption.get("lang")
        elif user["plan"] != "free":
            whisper_result = transcribe_video_audio(url, cookie_string, language)
            if not whisper_result.get("success"):
                return jsonify({"error": "transcription_failed", "message": whisper_result.get("error") or "Could not transcribe this video."}), 500
            source = "speech_recognition"
            source_label = "Viddash speech recognition"
            segments = whisper_result.get("segments") or []
            detected_language = whisper_result.get("language")
        else:
            return jsonify({
                "error": "captions_unavailable",
                "message": "This video has no usable caption track. Pro can create a transcript from the audio with speech recognition.",
                "pricing_url": url_for("page_pricing"),
            }), 422

        intelligence = build_transcript_intelligence(segments, duration)
        if not intelligence["segments"] or not intelligence["transcript"]:
            return jsonify({"error": "empty_transcript", "message": "A usable transcript could not be generated from this video."}), 422

        video_id = video.get("id")
        canonical_video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else video.get("webpage_url") or url
        remaining = None if user["plan"] != "free" else max(0, free_daily_limit - used_today - 1)
        record_user_activity(
            user["id"],
            "media.youtube_transcript",
            "Generated a source-linked YouTube transcript project.",
            "success",
            {
                "language": detected_language,
                "source": source,
                "video_id": video_id,
                "words": intelligence["stats"]["words"],
            },
        )
        return jsonify({
            "success": True,
            "video": {
                "id": video_id,
                "title": video.get("title") or "YouTube video",
                "channel": video.get("channel") or "YouTube",
                "thumbnail": video.get("thumbnail"),
                "url": canonical_video_url,
                "duration": duration,
            },
            "source": source,
            "source_label": source_label,
            "language": detected_language,
            "remaining_free_today": remaining,
            **intelligence,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "timeout", "message": "YouTube took too long to respond. Please try again."}), 504
    except Exception:
        logger.exception("YouTube Transcript Studio failed")
        return jsonify({"error": "transcript_failed", "message": "The transcript project could not be generated."}), 500


@app.post("/api/transcribe-file")
@require_paid_plan("pro")
def transcribe_file():
    """
    Transcribe video/audio from uploaded file.
    Uses Whisper for audio transcription.
    
    Form data:
      - file: video/audio file (required, max 1GB default or configurable)
      - language: optional language code (e.g., 'en', 'es')
      - format: optional format ('txt', 'srt', 'vtt', 'json') - default: json
    """
    if 'file' not in request.files:
        return jsonify({"error": "Missing file"}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    language = (request.form.get("language") or "").strip() or None
    out_format = (request.form.get("format") or "json").lower()
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_UPLOAD_BYTES:
        max_size_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({
            "error": f"File too large. Maximum size is {max_size_mb} MB.",
            "max_size_mb": max_size_mb
        }), 413
    
    tmpdir = tempfile.mkdtemp(prefix="upload_transcribe_")
    uploaded_file_path = None
    
    try:
        # Save uploaded file
        filename = os.path.basename(file.filename)
        # Sanitize filename
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        uploaded_file_path = os.path.join(tmpdir, filename)
        file.save(uploaded_file_path)
        
        # Transcribe the file
        result = transcribe_local_file(uploaded_file_path, language)
        
        if not result["success"]:
            return jsonify({
                "success": False,
                "source": None,
                "error": result["error"]
            }), 500
        
        response_data = {
            "success": True,
            "source": "local_file",
            "filename": filename,
            "language": result["language"],
            "type": "generated",
            "transcript": result["transcript"],
            "segments": result["segments"],
            "error": None,
        }
        
        # Format output
        if out_format == "srt":
            srt_content = segments_to_srt(result["segments"])
            return send_file(
                io.BytesIO(srt_content.encode()),
                as_attachment=True,
                download_name=f"{os.path.splitext(filename)[0]}.srt",
                mimetype="text/plain",
            )
        elif out_format == "vtt":
            vtt_content = segments_to_vtt(result["segments"])
            return send_file(
                io.BytesIO(vtt_content.encode()),
                as_attachment=True,
                download_name=f"{os.path.splitext(filename)[0]}.vtt",
                mimetype="text/plain",
            )
        elif out_format == "txt":
            return send_file(
                io.BytesIO(result["transcript"].encode()),
                as_attachment=True,
                download_name=f"{os.path.splitext(filename)[0]}.txt",
                mimetype="text/plain",
            )
        else:  # json
            return jsonify(response_data)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in /api/transcribe-file: {error_details}", flush=True)
        return jsonify({
            "success": False,
            "source": None,
            "error": str(e),
            "details": error_details
        }), 500
    
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.get("/api/max-upload-size")
def get_max_upload_size():
    """Get the current maximum upload size in MB."""
    max_mb = MAX_FILE_UPLOAD_BYTES // (1024 * 1024)
    return jsonify({
        "max_size_mb": max_mb,
        "max_size_bytes": MAX_FILE_UPLOAD_BYTES,
        "hard_limit_mb": MAX_FILE_UPLOAD_BYTES_HARD_LIMIT // (1024 * 1024)
    })


@app.errorhandler(500)
def handle_internal_server_error(e):
    import traceback
    error_details = traceback.format_exc()
    logger.error(f"UNHANDLED EXCEPTION: {error_details}")
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e),
        "details": error_details if app.debug else None
    }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
