#!/usr/bin/env python3
"""
OSINT Tools API Server
Wrapper unificado para Social Mapper, EagleEye e TheHarvester
Expõe REST API para consumo do backend Node.js
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
import subprocess
import logging
from functools import wraps
from pathlib import Path
import redis
import hashlib

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações
API_KEY = os.getenv('API_KEY', 'secret-key-change-me')
SOCIAL_MAPPER_PATH = os.getenv('SOCIAL_MAPPER_PATH', '/app/tools/social-mapper')
EAGLEEYE_PATH = os.getenv('EAGLEEYE_PATH', '/app/tools/eagleeye')
THEHARVESTER_PATH = os.getenv('THEHARVESTER_PATH', '/app/tools/theharvester')
UPLOADS_DIR = Path('/app/uploads')
RESULTS_DIR = Path('/app/results')

# Redis para cache
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis not available: {e}. Caching disabled.")
    redis_client = None

# Criar diretórios se não existirem
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Middleware de autenticação
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if api_key != API_KEY:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper: Gerar cache key
def get_cache_key(tool: str, params: dict) -> str:
    """Gera chave de cache baseada na ferramenta e parâmetros"""
    param_str = json.dumps(params, sort_keys=True)
    return f"osint:{tool}:{hashlib.md5(param_str.encode()).hexdigest()}"

# Helper: Executar comando com timeout
def run_tool_command(cmd: list, cwd: str = None, timeout: int = 300) -> dict:
    """
    Executa comando de ferramenta OSINT
    Returns: {"success": bool, "output": str, "error": str}
    """
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

# Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'tools': {
            'social_mapper': os.path.exists(SOCIAL_MAPPER_PATH),
            'eagleeye': os.path.exists(EAGLEEYE_PATH),
            'theharvester': os.path.exists(THEHARVESTER_PATH)
        },
        'redis': redis_client is not None and redis_client.ping()
    })

@app.route('/api/social-mapper', methods=['POST'])
@require_api_key
def social_mapper_search():
    """
    Busca perfis em redes sociais usando reconhecimento facial
    Body: {"imagePath": str, "platforms": [str]}
    """
    data = request.get_json()
    image_path = data.get('imagePath')
    platforms = data.get('platforms', ['linkedin', 'facebook', 'twitter'])
    
    if not image_path:
        return jsonify({'error': 'imagePath is required'}), 400
    
    # Verificar cache
    cache_key = get_cache_key('social-mapper', data)
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info("Returning cached result")
            return jsonify(json.loads(cached))
    
    # Executar Social Mapper
    # Nota: ajustar comando conforme interface real da ferramenta
    cmd = [
        'python3',
        'social_mapper.py',
        '-f', image_path,
        '-m', 'fast',
        '-a', ','.join(platforms)
    ]
    
    result = run_tool_command(cmd, cwd=SOCIAL_MAPPER_PATH, timeout=600)
    
    response = {
        'tool': 'social-mapper',
        'success': result['success'],
        'results': result['output'] if result['success'] else None,
        'error': result['error'] if not result['success'] else None
    }
    
    # Cache por 1 hora
    if redis_client and result['success']:
        redis_client.setex(cache_key, 3600, json.dumps(response))
    
    return jsonify(response)

@app.route('/api/eagleeye', methods=['POST'])
@require_api_key
def eagleeye_search():
    """
    Busca reversa de imagens
    Body: {"imagePath": str, "engines": [str]}
    """
    data = request.get_json()
    image_path = data.get('imagePath')
    engines = data.get('engines', ['google', 'yandex', 'bing'])
    
    if not image_path:
        return jsonify({'error': 'imagePath is required'}), 400
    
    cache_key = get_cache_key('eagleeye', data)
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
    
    cmd = [
        'python3',
        'eagleeye.py',
        '--image', image_path,
        '--engines', ','.join(engines)
    ]
    
    result = run_tool_command(cmd, cwd=EAGLEEYE_PATH, timeout=300)
    
    response = {
        'tool': 'eagleeye',
        'success': result['success'],
        'results': result['output'] if result['success'] else None,
        'error': result['error'] if not result['success'] else None
    }
    
    if redis_client and result['success']:
        redis_client.setex(cache_key, 3600, json.dumps(response))
    
    return jsonify(response)

@app.route('/api/theharvester', methods=['POST'])
@require_api_key
def theharvester_search():
    """
    Coleta informações de domínio
    Body: {"domain": str, "sources": [str], "limit": int}
    """
    data = request.get_json()
    domain = data.get('domain')
    sources = data.get('sources', ['google', 'bing'])
    limit = data.get('limit', 500)
    
    if not domain:
        return jsonify({'error': 'domain is required'}), 400
    
    cache_key = get_cache_key('theharvester', data)
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
    
    cmd = [
        'python3',
        'theHarvester.py',
        '-d', domain,
        '-b', ','.join(sources),
        '-l', str(limit)
    ]
    
    result = run_tool_command(cmd, cwd=THEHARVESTER_PATH, timeout=300)
    
    response = {
        'tool': 'theharvester',
        'success': result['success'],
        'results': result['output'] if result['success'] else None,
        'error': result['error'] if not result['success'] else None
    }
    
    if redis_client and result['success']:
        redis_client.setex(cache_key, 3600, json.dumps(response))
    
    return jsonify(response)

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_file():
    """
    Upload de imagem para análise
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Salvar arquivo
    filename = hashlib.md5(file.filename.encode()).hexdigest() + Path(file.filename).suffix
    filepath = UPLOADS_DIR / filename
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'path': str(filepath),
        'filename': filename
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting OSINT API server on port {port}")
    logger.info(f"Social Mapper path: {SOCIAL_MAPPER_PATH}")
    logger.info(f"EagleEye path: {EAGLEEYE_PATH}")
    logger.info(f"TheHarvester path: {THEHARVESTER_PATH}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
