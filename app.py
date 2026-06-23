from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import redis
import json
from functools import wraps
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# ============ CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ============
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'firma_contable'),
    'password': os.getenv('DB_PASSWORD', 'Alopro123'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'client_encoding': 'UTF8'  # ✅ AÑADIDO: Forzar codificación UTF-8
}

PORT = int(os.getenv('PORT', 3000))

print("=" * 60)
print("📋 CONFIGURACIÓN CARGADA:")
print(f"   Base de datos: {DB_CONFIG['database']} en {DB_CONFIG['host']}:{DB_CONFIG['port']}")
print(f"   Usuario: {DB_CONFIG['user']}")
print(f"   Codificación: {DB_CONFIG.get('client_encoding', 'UTF8')}")
print(f"   Puerto servidor: {PORT}")
print("=" * 60)

# ============ SIRVE ARCHIVOS ESTÁTICOS ============
@app.route('/styles.css')
def serve_css():
    return send_from_directory('.', 'styles.css')

# ============ CONFIGURACIÓN DE CACHÉ CON REDIS ============
CACHE_CONFIG = {
    'servicios': 3600,
    'estadisticas': 60,
    'citas_recientes': 30,
    'clientes': 600,
}

try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True,
        db=0
    )
    redis_client.ping()
    print("✅ Conectado a Redis")
except Exception as e:
    print(f"⚠️ Redis no disponible: {e}")
    redis_client = None

def cache_response(cache_type='default'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if redis_client is None:
                return func(*args, **kwargs)
            
            ttl = CACHE_CONFIG.get(cache_type, 60)
            cache_key = f"{cache_type}:{func.__name__}:{request.path}:{request.args}"
            
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    print(f"✅ [CACHÉ] {cache_type.upper()} - Respuesta desde caché")
                    return json.loads(cached_data)
            except Exception as e:
                print(f"⚠️ Error leyendo caché: {e}")
            
            result = func(*args, **kwargs)
            
            if result and hasattr(result, 'status_code') and result.status_code == 200:
                try:
                    response_data = result.get_data(as_text=True)
                    redis_client.setex(cache_key, ttl, response_data)
                    print(f"💾 [CACHÉ] {cache_type.upper()} - Guardado en caché")
                except Exception as e:
                    print(f"⚠️ Error guardando en caché: {e}")
            
            return result
        return wrapper
    return decorator

def limpiar_cache_por_tipo(cache_type=None):
    if redis_client is None:
        return
    
    if cache_type:
        pattern = f"{cache_type}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            print(f"🗑️ [CACHÉ] Limpiado caché de tipo: {cache_type}")
    else:
        redis_client.flushall()
        print("🗑️ [CACHÉ] Caché completamente limpiado")

# ============ CONFIGURACIÓN DE LA BASE DE DATOS ============
def get_db_connection():
    try:
        # ✅ CONEXIÓN CON CODIFICACIÓN UTF-8
        conn = psycopg2.connect(**DB_CONFIG)
        # Establecer la codificación explícitamente
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return None

# ============ CONFIGURACIÓN CORS ============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ============ RUTAS DE PÁGINAS HTML ============
@app.route('/')
def pagina_inicio():
    try:
        return render_template('ELOHANU_BUSINESS.html')
    except Exception as e:
        return f"Error: No se encontró ELOHANU_BUSINESS.html - {e}"

@app.route('/quienes-somos')
def pagina_quienes_somos():
    try:
        return render_template('quienes-somos.html')
    except Exception as e:
        return f"Error: No se encontró quienes-somos.html - {e}"

@app.route('/blog-noticias')
def pagina_blog():
    try:
        return render_template('blog-noticias.html')
    except Exception as e:
        return f"Error: No se encontró blog-noticias.html - {e}"

@app.route('/contactanos')
def pagina_contactanos():
    try:
        return render_template('contactanos.html')
    except Exception as e:
        return f"Error: No se encontró contactanos.html - {e}"

@app.route('/dashboard')
def pagina_dashboard():
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"Error: No se encontró dashboard.html - {e}"

@app.route('/login')
def pagina_login():
    try:
        return render_template('login.html')
    except Exception as e:
        return f"Error: No se encontró login.html - {e}"

# ============ RUTAS CON EXTENSIÓN .HTML ============
@app.route('/ELOHANU_BUSINESS.html')
def pagina_inicio_html():
    return render_template('ELOHANU_BUSINESS.html')

@app.route('/quienes-somos.html')
def pagina_quienes_somos_html():
    return render_template('quienes-somos.html')

@app.route('/blog-noticias.html')
def pagina_blog_html():
    return render_template('blog-noticias.html')

@app.route('/contactanos.html')
def pagina_contactanos_html():
    return render_template('contactanos.html')

@app.route('/dashboard.html')
def pagina_dashboard_html():
    return render_template('dashboard.html')

@app.route('/login.html')
def pagina_login_html():
    return render_template('login.html')

# ============ ENDPOINTS DE LA API ============

@app.route('/api/contacto', methods=['POST', 'OPTIONS'])
def guardar_contacto():
    limpiar_cache_por_tipo('citas_recientes')
    limpiar_cache_por_tipo('estadisticas')
    
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("📩 Recibida petición POST /api/contacto")
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
        
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        email = data.get('email', '').strip()
        telefono = data.get('telefono', '').strip()
        ciudad = data.get('ciudad', '').strip()
        direccion = data.get('direccion', '').strip()
        servicio = data.get('servicio', '')
        fecha = data.get('fecha')
        hora = data.get('hora')
        
        if not all([nombre, apellido, email, telefono, ciudad]):
            return jsonify({'success': False, 'message': 'Todos los campos obligatorios (*) deben ser completados'}), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'message': 'Por favor ingresa un correo electrónico válido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT id_cliente FROM clientes WHERE email = %s", (email,))
            cliente_existente = cur.fetchone()
            
            if cliente_existente:
                cliente_id = cliente_existente[0]
                cur.execute("""
                    UPDATE clientes 
                    SET nombre = %s, apellido = %s, telefono = %s, 
                        ciudad = %s, direccion = %s
                    WHERE id_cliente = %s
                """, (nombre, apellido, telefono, ciudad, direccion, cliente_id))
                print(f"✅ Cliente actualizado - ID: {cliente_id}")
            else:
                cur.execute("""
                    INSERT INTO clientes (nombre, apellido, email, telefono, ciudad, direccion, fecha_registro) 
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)
                    RETURNING id_cliente
                """, (nombre, apellido, email, telefono, ciudad, direccion))
                cliente_id = cur.fetchone()[0]
                print(f"✅ Nuevo cliente creado - ID: {cliente_id}")
            
            id_servicio = None
            if servicio:
                cur.execute("SELECT id_servicio FROM servicios WHERE nombre = %s", (servicio,))
                resultado = cur.fetchone()
                if resultado:
                    id_servicio = resultado[0]
            
            cur.execute("""
                INSERT INTO citas (id_cliente, fecha, hora, estado, id_servicio)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_cita
            """, (cliente_id, fecha, hora, 'pendiente', id_servicio))
            
            cita_id = cur.fetchone()[0]
            conn.commit()
            
            print(f"✅ Cita guardada - ID: {cita_id}")
            
            return jsonify({
                'success': True,
                'message': 'Mensaje enviado exitosamente. Te contactaremos pronto.',
                'cita_id': cita_id,
                'cliente_id': cliente_id
            }), 201
            
        except psycopg2.Error as e:
            conn.rollback()
            print(f"❌ Error de PostgreSQL: {e}")
            return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'}), 500
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/citas', methods=['GET'])
@cache_response(cache_type='citas_recientes')
def obtener_todas_citas():
    try:
        print("📋 Obteniendo todas las citas...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                c.id_cita,
                c.estado,
                c.fecha,
                c.hora,
                c.id_cliente,
                cl.nombre,
                cl.apellido,
                cl.email,
                cl.telefono,
                cl.ciudad
            FROM citas c
            LEFT JOIN clientes cl ON c.id_cliente = cl.id_cliente
            ORDER BY c.fecha DESC, c.hora DESC
            LIMIT 100
        """
        
        cur.execute(query)
        citas = cur.fetchall()
        
        for cita in citas:
            if cita.get('fecha'):
                cita['fecha'] = str(cita['fecha'])
            if cita.get('hora'):
                cita['hora'] = str(cita['hora'])
        
        cur.close()
        conn.close()
        
        print(f"✅ Encontradas {len(citas)} citas")
        return jsonify(citas), 200
        
    except Exception as e:
        print(f"❌ Error al obtener citas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/citas/<int:cita_id>/estado', methods=['PUT'])
def actualizar_estado_cita(cita_id):
    limpiar_cache_por_tipo('citas_recientes')
    limpiar_cache_por_tipo('estadisticas')
    
    try:
        data = request.json
        nuevo_estado = data.get('estado')
        
        estados_validos = ['pendiente', 'confirmada', 'completada', 'cancelada']
        if nuevo_estado not in estados_validos:
            return jsonify({'error': 'Estado no válido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE citas 
            SET estado = %s 
            WHERE id_cita = %s
            RETURNING id_cita
        """, (nuevo_estado, cita_id))
        
        if cur.fetchone():
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Estado actualizado correctamente'}), 200
        else:
            cur.close()
            conn.close()
            return jsonify({'error': 'Cita no encontrada'}), 404
            
    except Exception as e:
        print(f"❌ Error al actualizar estado: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servicios', methods=['GET'])
@cache_response(cache_type='servicios')
def obtener_servicios():
    try:
        print("🔧 Obteniendo servicios...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id_servicio, nombre, descripcion, precio, duracion 
            FROM servicios 
            ORDER BY id_servicio
        """)
        
        servicios = cur.fetchall()
        
        cur.close()
        conn.close()
        
        print(f"✅ Encontrados {len(servicios)} servicios")
        return jsonify(servicios), 200
        
    except Exception as e:
        print(f"❌ Error al obtener servicios: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servicios', methods=['POST'])
def crear_servicio():
    limpiar_cache_por_tipo('servicios')
    limpiar_cache_por_tipo('estadisticas')
    
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '').strip()
        precio = data.get('precio')
        duracion = data.get('duracion')
        
        if not nombre:
            return jsonify({'error': 'El nombre del servicio es requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO servicios (nombre, descripcion, precio, duracion)
            VALUES (%s, %s, %s, %s)
            RETURNING id_servicio
        """, (nombre, descripcion, precio, duracion))
        
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Servicio creado exitosamente',
            'id_servicio': nuevo_id
        }), 201
        
    except Exception as e:
        print(f"❌ Error al crear servicio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servicios/<int:servicio_id>', methods=['PUT'])
def actualizar_servicio(servicio_id):
    limpiar_cache_por_tipo('servicios')
    limpiar_cache_por_tipo('estadisticas')
    
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '').strip()
        precio = data.get('precio')
        duracion = data.get('duracion')
        
        if not nombre:
            return jsonify({'error': 'El nombre del servicio es requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE servicios 
            SET nombre = %s, descripcion = %s, precio = %s, duracion = %s
            WHERE id_servicio = %s
            RETURNING id_servicio
        """, (nombre, descripcion, precio, duracion, servicio_id))
        
        if cur.fetchone():
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Servicio actualizado exitosamente'}), 200
        else:
            cur.close()
            conn.close()
            return jsonify({'error': 'Servicio no encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error al actualizar servicio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servicios/<int:servicio_id>', methods=['DELETE'])
def eliminar_servicio(servicio_id):
    limpiar_cache_por_tipo('servicios')
    limpiar_cache_por_tipo('estadisticas')
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM citas WHERE id_servicio = %s", (servicio_id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            cur.close()
            conn.close()
            return jsonify({'error': f'No se puede eliminar el servicio porque tiene {count} cita(s) asociada(s)'}), 400
        
        cur.execute("DELETE FROM servicios WHERE id_servicio = %s RETURNING id_servicio", (servicio_id,))
        
        if cur.fetchone():
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Servicio eliminado exitosamente'}), 200
        else:
            cur.close()
            conn.close()
            return jsonify({'error': 'Servicio no encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error al eliminar servicio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@cache_response(cache_type='estadisticas')
def obtener_estadisticas():
    try:
        print("📊 Calculando estadísticas...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT COUNT(*) as total FROM citas")
        total_citas = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM clientes")
        total_clientes = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM servicios")
        total_servicios = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM citas WHERE fecha = CURRENT_DATE")
        citas_hoy = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total_citas': total_citas,
            'total_clientes': total_clientes,
            'total_servicios': total_servicios,
            'citas_hoy': citas_hoy
        }), 200
        
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clientes', methods=['GET'])
@cache_response(cache_type='clientes')
def obtener_clientes():
    try:
        print("👥 Obteniendo clientes...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id_cliente, nombre, apellido, email, telefono, ciudad, fecha_registro
            FROM clientes 
            ORDER BY id_cliente DESC 
            LIMIT 50
        """)
        
        clientes = cur.fetchall()
        
        for cliente in clientes:
            if cliente.get('fecha_registro'):
                cliente['fecha_registro'] = str(cliente['fecha_registro'])
        
        cur.close()
        conn.close()
        
        print(f"✅ Encontrados {len(clientes)} clientes")
        return jsonify(clientes), 200
        
    except Exception as e:
        print(f"❌ Error al obtener clientes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache-status', methods=['GET'])
def cache_status():
    if redis_client is None:
        return jsonify({'status': 'disabled', 'message': 'Redis no disponible'}), 200
    
    stats = {}
    for cache_type in CACHE_CONFIG.keys():
        pattern = f"{cache_type}:*"
        keys = redis_client.keys(pattern)
        stats[cache_type] = {
            'ttl_seconds': CACHE_CONFIG[cache_type],
            'ttl_minutes': CACHE_CONFIG[cache_type] // 60,
            'cached_items': len(keys)
        }
    
    return jsonify({
        'status': 'active',
        'redis_connected': True,
        'cache_config': CACHE_CONFIG,
        'current_stats': stats
    }), 200

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    data = request.json or {}
    cache_type = data.get('type', None)
    
    limpiar_cache_por_tipo(cache_type)
    
    return jsonify({
        'success': True,
        'message': f'Caché limpiado' + (f' para tipo: {cache_type}' if cache_type else ' completamente')
    }), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    # Intentar conectar a la base de datos para verificar estado
    db_status = "disconnected"
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            db_status = "connected"
    except:
        pass
    
    return jsonify({
        'status': 'OK',
        'timestamp': str(datetime.now()),
        'server': 'Flask',
        'database': db_status,
        'redis': 'connected' if redis_client else 'disconnected'
    }), 200

@app.route('/api/indices-recomendados', methods=['GET'])
def indices_recomendados():
    indices_sql = """
    -- ÍNDICES RECOMENDADOS PARA OPTIMIZACIÓN
    CREATE INDEX IF NOT EXISTS idx_clientes_email ON clientes(email);
    CREATE INDEX IF NOT EXISTS idx_citas_fecha_estado ON citas(fecha, estado);
    CREATE INDEX IF NOT EXISTS idx_citas_id_cliente ON citas(id_cliente);
    CREATE INDEX IF NOT EXISTS idx_servicios_nombre ON servicios(nombre);
    """
    
    return jsonify({'recomendaciones': indices_sql}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': '🚀 Servidor Flask de ELOHANU BUSINESS funcionando',
        'version': '2.0 - Optimizado',
        'cache_status': 'Redis activo' if redis_client else 'Redis no disponible',
        'ttl_config': CACHE_CONFIG,
        'endpoints': {
            '📋 Páginas': {
                'GET /': 'Página de inicio',
                'GET /quienes-somos': 'Quiénes Somos',
                'GET /blog-noticias': 'Blog',
                'GET /contactanos': 'Contáctanos',
                'GET /dashboard': 'Dashboard',
                'GET /login': 'Login'
            },
            '📊 API': {
                'GET /api/citas': 'Ver citas',
                'GET /api/servicios': 'Ver servicios',
                'GET /api/stats': 'Ver estadísticas',
                'GET /api/clientes': 'Ver clientes',
                'POST /api/contacto': 'Enviar contacto',
                'PUT /api/citas/<id>/estado': 'Actualizar estado de cita',
                'POST /api/servicios': 'Crear servicio',
                'PUT /api/servicios/<id>': 'Actualizar servicio',
                'DELETE /api/servicios/<id>': 'Eliminar servicio'
            },
            '🔧 Sistema': {
                'GET /api/health': 'Estado del sistema',
                'GET /api/cache-status': 'Estado del caché',
                'POST /api/clear-cache': 'Limpiar caché',
                'GET /api/indices-recomendados': 'Índices SQL recomendados'
            }
        }
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Iniciando servidor Flask de ELOHANU BUSINESS")
    print("=" * 60)
    print(f"📡 Servidor corriendo en: http://localhost:{PORT}")
    print(f"💾 Estado del caché: {'Redis activo' if redis_client else 'Redis no disponible'}")
    print("=" * 60)
    print("📍 Páginas disponibles (sin .html):")
    print(f"   http://localhost:{PORT}/              - Inicio")
    print(f"   http://localhost:{PORT}/quienes-somos - Quiénes Somos")
    print(f"   http://localhost:{PORT}/blog-noticias - Blog")
    print(f"   http://localhost:{PORT}/contactanos   - Contáctanos")
    print(f"   http://localhost:{PORT}/dashboard     - Dashboard")
    print(f"   http://localhost:{PORT}/login         - Login")
    print("=" * 60)
    print("📍 Páginas disponibles (con .html):")
    print(f"   http://localhost:{PORT}/ELOHANU_BUSINESS.html - Inicio")
    print(f"   http://localhost:{PORT}/quienes-somos.html    - Quiénes Somos")
    print(f"   http://localhost:{PORT}/blog-noticias.html    - Blog")
    print(f"   http://localhost:{PORT}/contactanos.html      - Contáctanos")
    print(f"   http://localhost:{PORT}/dashboard.html        - Dashboard")
    print(f"   http://localhost:{PORT}/login.html            - Login")
    print("=" * 60)
    print("📊 Endpoints API disponibles:")
    print(f"   GET  http://localhost:{PORT}/api/citas")
    print(f"   GET  http://localhost:{PORT}/api/servicios")
    print(f"   GET  http://localhost:{PORT}/api/stats")
    print(f"   GET  http://localhost:{PORT}/api/clientes")
    print(f"   POST http://localhost:{PORT}/api/contacto")
    print(f"   GET  http://localhost:{PORT}/api/health")
    print("=" * 60)
    
    try:
        app.run(debug=True, port=PORT, host='0.0.0.0')
    except Exception as e:
        print(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)