#!/usr/bin/env python3
"""
Meet Your IA - Proxy Server
Serveur proxy pour forwarder les requêtes Roblox vers Groq API
"""

import os
import json
import logging
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MeetYourIA-Proxy')

# Charger les variables d'environnement
load_dotenv()

# Configuration Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Créer l'app Flask
app = Flask(__name__)

# Configuration CORS pour Roblox
from flask_cors import CORS
CORS(app)

# ===== LOGGING =====

@app.before_request
def log_request():
    logger.info(f"📨 Requête: {request.method} {request.path}")
    logger.info(f"   Depuis: {request.remote_addr}")

@app.after_request
def log_response(response):
    logger.info(f"📤 Réponse: {response.status_code}")
    return response

# ===== ROUTES =====

@app.route("/", methods=["GET"])
def index():
    """Route racine - Info du serveur"""
    return jsonify({
        "message": "🚀 Meet Your IA Proxy Server is running!",
        "service": "MeetYourIA Proxy",
        "endpoints": ["/health", "/chat", "/status"]
    }), 200

@app.route("/health", methods=["GET"])
def health():
    """Vérifier que le serveur est en ligne"""
    return jsonify({
        "status": "online",
        "service": "MeetYourIA Proxy",
        "groq_configured": GROQ_API_KEY is not None
    }), 200

@app.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint principal pour discuter avec Groq
    Reçoit un message et optionnellement un historique
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        message = data.get("message", "")
        history = data.get("history", [])  # Historique optionnel
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        logger.info(f"💬 Message reçu: {message[:50]}...")
        logger.info(f"   Historique: {len(history)} messages")
        
        # Vérifier la clé API
        if not GROQ_API_KEY:
            return jsonify({
                "error": "Groq API key not configured",
                "message": "Configure GROQ_API_KEY dans le fichier .env"
            }), 500
        
        # Préparer les messages pour Groq
        messages = []
        
        # Ajouter le system message
        messages.append({
            "role": "system",
            "content": "Tu es Luna, une IA amicale pour Roblox. Lis bien l'historique pour rester cohérent. Réponds en français de manière naturelle et concise."
        })
        
        # Ajouter l'historique
        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Ajouter le nouveau message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Appeler Groq API
        logger.info(f"📤 Envoi à Groq avec {len(messages)} messages")
        
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=30
        )
        
        # Vérifier la réponse
        if response.status_code != 200:
            logger.error(f"❌ Erreur Groq: {response.status_code}")
            logger.error(f"   Réponse: {response.text[:200]}")
            
            return jsonify({
                "error": f"Groq API error: {response.status_code}",
                "details": response.text[:500]
            }), response.status_code
        
        # Parser la réponse
        result = response.json()
        
        if "choices" not in result or not result["choices"]:
            logger.error("❌ Réponse Groq vide")
            return jsonify({
                "error": "No response from Groq",
                "raw": result
            }), 500
        
        ia_response = result["choices"][0]["message"]["content"]
        logger.info(f"✅ Réponse: {ia_response[:50]}...")
        
        return jsonify({
            "success": True,
            "response": ia_response,
            "model": GROQ_MODEL,
            "tokens_used": {
                "input": result.get("usage", {}).get("prompt_tokens", 0),
                "output": result.get("usage", {}).get("completion_tokens", 0)
            }
        }), 200
    
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout - Groq API prend trop de temps")
        return jsonify({
            "error": "Groq API timeout",
            "message": "La requête a pris trop de temps"
        }), 504
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Erreur connexion: {e}")
        return jsonify({
            "error": "Connection error",
            "message": str(e)
        }), 502
    
    except Exception as e:
        logger.error(f"❌ Erreur: {e}", exc_info=True)
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

@app.route("/status", methods=["GET"])
def status():
    """Info sur le serveur"""
    return jsonify({
        "service": "MeetYourIA Proxy",
        "version": "1.0",
        "status": "running",
        "groq_model": GROQ_MODEL,
        "api_configured": GROQ_API_KEY is not None,
        "endpoints": {
            "/": "GET - Info du serveur",
            "/health": "GET - Vérifier que le serveur est en ligne",
            "/chat": "POST - Discuter avec Groq",
            "/status": "GET - Infos du serveur"
        }
    }), 200

# ===== ERREURS =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not found",
        "available_endpoints": ["/", "/health", "/chat", "/status"]
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Server error",
        "message": str(e)
    }), 500

# ===== DÉMARRAGE =====

if __name__ == "__main__":
    # Vérifications
    print("\n" + "="*50)
    print("🚀 Meet Your IA - Proxy Server (Groq)")
    print("="*50)
    
    if not GROQ_API_KEY:
        print("⚠️  ATTENTION: GROQ_API_KEY non configurée!")
        print("   Configure le fichier .env avec ta clé Groq")
    else:
        print("✅ Groq API configurée")
    
    print(f"📝 Modèle: {GROQ_MODEL}")
    print("="*50 + "\n")
    
    # Lancer le serveur
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Serveur démarré sur http://{host}:{port}")
    logger.info(f"   Teste avec: curl http://{host}:{port}/health")
    
    app.run(
        host=host,
        port=port,
        debug=os.getenv("DEBUG", "False").lower() == "true",
        threaded=True
    )
