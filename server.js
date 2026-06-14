const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');

const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Conexión a PostgreSQL (cambia la contraseña si es necesario)
const pool = new Pool({
    user: 'postgres',
    host: 'localhost',
    database: 'firma_contable',
    password: 'postgres',  // ← Cambia por tu contraseña
    port: 5432,
});

// Verificar conexión
pool.connect((err) => {
    if (err) {
        console.error('❌ Error conectando a PostgreSQL:', err.stack);
    } else {
        console.log('✅ Conectado a PostgreSQL');
    }
});

// Endpoint para guardar mensajes/citas
app.post('/api/contacto', async (req, res) => {
    const { nombre, apellido, email, telefono, ciudad, direccion, servicio, fecha, hora, mensaje } = req.body;
    
    try {
        // 1. Registrar o actualizar cliente
        let clienteId;
        
        const clienteExistente = await pool.query(
            'SELECT id_cliente FROM clientes WHERE email = $1',
            [email]
        );
        
        if (clienteExistente.rows.length > 0) {
            clienteId = clienteExistente.rows[0].id_cliente;
            
            // Actualizar datos del cliente
            await pool.query(
                `UPDATE clientes 
                 SET nombre = $1, apellido = $2, telefono = $3, ciudad = $4, direccion = $5
                 WHERE id_cliente = $6`,
                [nombre, apellido, telefono, ciudad, direccion, clienteId]
            );
        } else {
            // Crear nuevo cliente
            const nuevoCliente = await pool.query(
                `INSERT INTO clientes (nombre, apellido, email, telefono, ciudad, direccion, fecha_registro) 
                 VALUES ($1, $2, $3, $4, $5, $6, CURRENT_DATE) 
                 RETURNING id_cliente`,
                [nombre, apellido, email, telefono, ciudad, direccion]
            );
            clienteId = nuevoCliente.rows[0].id_cliente;
        }
        
        // 2. Guardar el mensaje/consulta (puedes crear una tabla "mensajes" o guardarlo en citas)
        // Por ahora, guardamos en citas con datos básicos
        const query = `
            INSERT INTO citas (id_cliente, fecha, hora, estado)
            VALUES ($1, $2, $3, $4)
            RETURNING id_cita
        `;
        
        const resultado = await pool.query(query, [
            clienteId,
            fecha || null,
            hora || null,
            'pendiente'
        ]);
        
        console.log(`✅ Mensaje guardado - ID Cita: ${resultado.rows[0].id_cita}`);
        
        res.status(201).json({
            success: true,
            message: 'Mensaje enviado exitosamente',
            cita_id: resultado.rows[0].id_cita
        });
        
    } catch (error) {
        console.error('Error al guardar:', error);
        res.status(500).json({
            success: false,
            message: 'Error al enviar el mensaje',
            error: error.message
        });
    }
});

// Endpoint para ver todos los mensajes (admin)
app.get('/api/mensajes', async (req, res) => {
    try {
        const result = await pool.query(
            `SELECT c.id_cita, c.fecha, c.hora, c.estado, c.fecha_creacion,
                    cl.nombre, cl.apellido, cl.email, cl.telefono, cl.ciudad, cl.direccion
             FROM citas c
             LEFT JOIN clientes cl ON c.id_cliente = cl.id_cliente
             ORDER BY c.fecha_creacion DESC`
        );
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`🚀 Servidor corriendo en http://localhost:${port}`);
    console.log(`📋 Endpoints:`);
    console.log(`   POST /api/contacto - Guardar mensaje`);
    console.log(`   GET  /api/mensajes - Ver mensajes (admin)`);
});