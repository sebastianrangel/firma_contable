from flask import Flask, request, jsonify
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

app = Flask(__name__)

# Configurar CORS manualmente
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Configuración de la base de datos
DB_CONFIG = {
    'user': 'postgres',
    'host': 'localhost',
    'database': 'firma_contable',
    'password': '60447744',  # Cambia por tu contraseña real
    'port': 5432
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return None

# ============ ENDPOINT PARA OBTENER CITAS (VERSIÓN CORREGIDA) ============

@app.route('/api/citas', methods=['GET'])
def obtener_todas_citas():
    try:
        print("📋 Obteniendo todas las citas...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Consulta adaptada a tu tabla
        query = """
            SELECT 
                c.id_cita,
                c.estado,
                c.fecha,
                c.hora,
                c.id_cliente,
                COALESCE(c.id_servicio, 0) as id_servicio,
                cl.nombre,
                cl.apellido,
                cl.email,
                cl.telefono,
                cl.ciudad,
                cl.direccion
            FROM citas c
            LEFT JOIN clientes cl ON c.id_cliente = cl.id_cliente
            ORDER BY c.fecha DESC, c.hora DESC
        """
        
        cur.execute(query)
        citas = cur.fetchall()
        
        print(f"✅ Encontradas {len(citas)} citas")
        
        # Convertir fechas a string y manejar NULLs
        for cita in citas:
            if cita.get('fecha'):
                cita['fecha'] = str(cita['fecha'])
            else:
                cita['fecha'] = None
            if cita.get('hora'):
                cita['hora'] = str(cita['hora'])
            
            # Asegurar que todos los campos existan
            if 'nombre' not in cita or cita['nombre'] is None:
                cita['nombre'] = 'Cliente no encontrado'
            if 'apellido' not in cita:
                cita['apellido'] = ''
            if 'email' not in cita:
                cita['email'] = 'No registrado'
            if 'telefono' not in cita:
                cita['telefono'] = 'No registrado'
        
        cur.close()
        conn.close()
        
        return jsonify(citas), 200
        
    except Exception as e:
        print(f"❌ Error al obtener citas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
# ============ ENDPOINTS PARA SERVICIOS ============

@app.route('/api/servicios', methods=['GET'])
def obtener_servicios():
    try:
        print("🔧 Obteniendo todos los servicios...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar si la tabla servicios existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'servicios'
            )
        """)
        tabla_existe = cur.fetchone()['exists']
        
        if not tabla_existe:
            print("⚠️ La tabla 'servicios' no existe")
            return jsonify([]), 200
        
        cur.execute("""
            SELECT id_servicio, nombre, descripcion, precio, duracion
            FROM servicios
            ORDER BY id_servicio
        """)
        
        servicios = cur.fetchall()
        print(f"✅ Encontrados {len(servicios)} servicios")
        
        cur.close()
        conn.close()
        
        return jsonify(servicios), 200
        
    except Exception as e:
        print(f"❌ Error al obtener servicios: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servicios', methods=['POST'])
def crear_servicio():
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
            return jsonify({'error': 'Error de conexión'}), 500
        
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
        
        print(f"✅ Servicio creado: {nombre} (ID: {nuevo_id})")
        
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
            return jsonify({'error': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE servicios 
            SET nombre = %s, descripcion = %s, precio = %s, duracion = %s
            WHERE id_servicio = %s
            RETURNING id_servicio
        """, (nombre, descripcion, precio, duracion, servicio_id))
        
        if cur.fetchone():
            conn.commit()
            print(f"✅ Servicio {servicio_id} actualizado")
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
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Verificar si hay citas usando este servicio
        cur.execute("SELECT COUNT(*) FROM citas WHERE id_servicio = %s", (servicio_id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            cur.close()
            conn.close()
            return jsonify({'error': f'No se puede eliminar el servicio porque tiene {count} cita(s) asociada(s)'}), 400
        
        cur.execute("DELETE FROM servicios WHERE id_servicio = %s RETURNING id_servicio", (servicio_id,))
        
        if cur.fetchone():
            conn.commit()
            print(f"✅ Servicio {servicio_id} eliminado")
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

@app.route('/api/citas/<int:cita_id>/estado', methods=['PUT'])
def actualizar_estado_cita(cita_id):
    try:
        data = request.json
        nuevo_estado = data.get('estado')
        
        estados_validos = ['pendiente', 'confirmada', 'completada', 'cancelada']
        if nuevo_estado not in estados_validos:
            return jsonify({'error': 'Estado no válido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE citas 
            SET estado = %s 
            WHERE id_cita = %s
            RETURNING id_cita
        """, (nuevo_estado, cita_id))
        
        if cur.fetchone():
            conn.commit()
            print(f"✅ Estado de cita {cita_id} actualizado a {nuevo_estado}")
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

@app.route('/api/stats', methods=['GET'])
def obtener_estadisticas():
    try:
        print("📊 Obteniendo estadísticas...")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión'}), 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total de citas
        cur.execute("SELECT COUNT(*) as total FROM citas")
        total_citas = cur.fetchone()['total']
        
        # Total de clientes
        cur.execute("SELECT COUNT(*) as total FROM clientes")
        total_clientes = cur.fetchone()['total']
        
        # Total de servicios
        cur.execute("SELECT COUNT(*) as total FROM servicios")
        total_servicios = cur.fetchone()['total']
        
        # Citas de hoy
        cur.execute("""
            SELECT COUNT(*) as total 
            FROM citas 
            WHERE fecha = CURRENT_DATE
        """)
        citas_hoy = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        print(f"✅ Estadísticas: {total_citas} citas, {total_clientes} clientes")
        
        return jsonify({
            'total_citas': total_citas,
            'total_clientes': total_clientes,
            'total_servicios': total_servicios,
            'citas_hoy': citas_hoy
        }), 200
        
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacto', methods=['POST', 'OPTIONS'])
def guardar_contacto():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("📩 Recibida petición POST /api/contacto")
        
        data = request.json
        print(f"Datos recibidos: {data}")
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos'
            }), 400
        
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
            return jsonify({
                'success': False,
                'message': 'Todos los campos obligatorios (*) deben ser completados'
            }), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Por favor ingresa un correo electrónico válido'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
        
        cur = conn.cursor()
        
        try:
            # Verificar si el cliente existe
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
            
            # Obtener id_servicio si existe
            id_servicio = None
            if servicio:
                cur.execute("SELECT id_servicio FROM servicios WHERE nombre = %s", (servicio,))
                resultado = cur.fetchone()
                if resultado:
                    id_servicio = resultado[0]
            
            # Insertar la cita
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
            return jsonify({
                'success': False,
                'message': f'Error al guardar: {str(e)}'
            }), 500
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'OK',
        'timestamp': str(datetime.now()),
        'server': 'Flask'
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Servidor Flask de ELOHANU BUSINESS funcionando',
        'endpoints': {
            'GET /': 'Esta información',
            'GET /api/health': 'Verificar estado',
            'POST /api/contacto': 'Enviar mensaje de contacto',
            'GET /api/citas': 'Ver todas las citas',
            'GET /api/servicios': 'Ver servicios',
            'GET /api/stats': 'Ver estadísticas'
        }
    }), 200

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Iniciando servidor Flask de ELOHANU BUSINESS")
    print("=" * 50)
    print(f"📡 Servidor corriendo en: http://localhost:3000")
    print("=" * 50)
    
    try:
        app.run(debug=True, port=3000, host='0.0.0.0')
    except Exception as e:
        print(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)