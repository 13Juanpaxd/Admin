from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
import cx_Oracle
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    connection = cx_Oracle.connect(
        user='FIDE_ROPASCLARAS',
        password='12345',
        dsn='localhost:1521/xe',
        encoding='UTF-8'
    )
    return connection

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        cedula = request.form['cedula']

        if correo == 'ADMIN@ADMIN.AD' and cedula == '987654321':
            session['user_id'] = 1
            session['is_admin'] = True
            return redirect(url_for('index'))

        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT ID_Cliente FROM FIDE_CLIENTES_TB WHERE Correo = :correo AND Cedula = :cedula', {'correo': correo, 'cedula': cedula})
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user[0]
                session['is_admin'] = False
                return redirect(url_for('home'))

            else:
                flash('Correo o cédula incorrectos. Inténtelo de nuevo.')

    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT ID_Producto, Nombre, Imagen, Precio, Detalle, Cantidad FROM FIDE_INVENTARIO_TB')
        productos = cursor.fetchall()
        
        return render_template('home.html', productos=productos)
    
    except Exception as e:
        print(f"Error al cargar productos: {e}")
        return render_template('home.html', productos=[], error=str(e))
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        cedula = request.form['cedula']
        correo = request.form['correo']
        pais = int(request.form['pais'])  # Asegúrate de convertir a entero
        provincia = int(request.form['provincia'])  # Asegúrate de convertir a entero
        canton = int(request.form['canton'])  # Asegúrate de convertir a entero
        distrito = int(request.form['distrito'])  # Asegúrate de convertir a entero
        foto = request.files['foto']
        foto_blob = foto.read()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO FIDE_CLIENTES_TB 
            (Nombre, Telefono, Cedula, Correo, Pais, Provincia, Canton, Distrito, Foto)
            VALUES (:nombre, :telefono, :cedula, :correo, :pais, :provincia, :canton, :distrito, :foto_blob)
        """, {
            'nombre': nombre,
            'telefono': telefono,
            'cedula': cedula,
            'correo': correo,
            'pais': pais,
            'provincia': provincia,
            'canton': canton,
            'distrito': distrito,
            'foto_blob': foto_blob
        })
        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuario registrado exitosamente. Ahora puede iniciar sesión.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session['user_id']
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        cedula = request.form['cedula']
        correo = request.form['correo']
        pais = request.form['pais']
        provincia = request.form['provincia']
        canton = request.form['canton']
        distrito = request.form['distrito']
        foto = request.files['foto']
        
        if foto:
            foto_blob = foto.read()
            cursor.execute("""
                UPDATE FIDE_CLIENTES_TB SET 
                Nombre=:nombre, Telefono=:telefono, Cedula=:cedula, Correo=:correo, 
                Pais=:pais, Provincia=:provincia, Canton=:canton, Distrito=:distrito, Foto=:foto_blob 
                WHERE ID_Cliente=:user_id
            """, {
                'nombre': nombre,
                'telefono': telefono,
                'cedula': cedula,
                'correo': correo,
                'pais': pais,
                'provincia': provincia,
                'canton': canton,
                'distrito': distrito,
                'foto_blob': foto_blob,
                'user_id': user_id
            })
        else:
            cursor.execute("""
                UPDATE FIDE_CLIENTES_TB SET 
                Nombre=:nombre, Telefono=:telefono, Cedula=:cedula, Correo=:correo, 
                Pais=:pais, Provincia=:provincia, Canton=:canton, Distrito=:distrito
                WHERE ID_Cliente=:user_id
            """, {
                'nombre': nombre,
                'telefono': telefono,
                'cedula': cedula,
                'correo': correo,
                'pais': pais,
                'provincia': provincia,
                'canton': canton,
                'distrito': distrito,
                'user_id': user_id
            })
        
        conn.commit()
        flash('Información actualizada con éxito.')
    
    cursor.execute('SELECT Nombre, Telefono, Cedula, Correo, Pais, Provincia, Canton, Distrito FROM FIDE_CLIENTES_TB WHERE ID_Cliente = :user_id', {'user_id': user_id})
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('profile.html', user_info=user_info) 


@app.route('/user_photo/<int:user_id>')
def user_photo(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT Foto FROM FIDE_CLIENTES_TB WHERE ID_Cliente = :user_id', {'user_id': user_id})
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row and row[0]:
        response = make_response(row[0].read())
        response.headers.set('Content-Type', 'image/jpeg')
        return response
    return 'No image found', 404

@app.route('/inventario', methods=['GET', 'POST'])
def inventario():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            nombre = request.form['nombre']
            precio = request.form['precio']
            detalle = request.form['detalle']
            cantidad = request.form['cantidad']
            categoria = request.form['categoria']
            proveedor_id = request.form['proveedor_id']
            # Elimina el casillero_id ya que no está presente en el formulario
            imagen = request.files['imagen']
            imagen_blob = imagen.read()

            print("Datos recibidos para insertar:")
            print(f"Nombre: {nombre}, Precio: {precio}, Detalle: {detalle}, Cantidad: {cantidad}, Categoría: {categoria}, Proveedor ID: {proveedor_id}, Imagen: {len(imagen_blob)} bytes")

            cursor.execute("""
                INSERT INTO FIDE_INVENTARIO_TB
                (Nombre, Imagen, Precio, Detalle, Cantidad, Categoria, Proveedor_ID, Fecha_Entrada)
                VALUES (:nombre, :imagen_blob, :precio, :detalle, :cantidad, :categoria, :proveedor_id, SYSTIMESTAMP)
            """, {
                'nombre': nombre,
                'imagen_blob': imagen_blob,
                'precio': precio,
                'detalle': detalle,
                'cantidad': cantidad,
                'categoria': categoria,
                'proveedor_id': proveedor_id,
            })
            conn.commit()
            print("Producto insertado correctamente")
        
        cursor.execute('SELECT ID_Producto, Nombre, Imagen, Precio, Detalle, Cantidad, Categoria, Proveedor_ID, Estado_ID, Fecha_Entrada FROM FIDE_INVENTARIO_TB')
        productos = cursor.fetchall()
        print("Productos obtenidos:", productos)
        
        return render_template('inventario.html', productos=productos)
    
    except Exception as e:
        print("Error en la operación:", str(e))
        return render_template('inventario.html', productos=[], error=str(e))
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/imagen/<int:producto_id>')
def imagen(producto_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT Imagen FROM FIDE_INVENTARIO_TB WHERE ID_Producto = :producto_id', {'producto_id': producto_id})
        row = cursor.fetchone()
        if row and row[0]:
            response = make_response(row[0].read())
            
            response.headers.set('Content-Type', 'image/jpeg')
            return response
        else:
            return 'No image found for product ID: {}'.format(producto_id), 404
    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return 'Error fetching image', 500
    finally:
        cursor.close()
        conn.close()

@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        cedula = request.form['cedula']
        correo = request.form['correo']
        pais = request.form['pais']
        provincia = request.form['provincia']
        canton = request.form['canton']
        distrito = request.form['distrito']

        print("Datos recibidos para insertar cliente:")
        print(f"Nombre: {nombre}, Teléfono: {telefono}, Cédula: {cedula}, Correo: {correo}, País: {pais}, Provincia: {provincia}, Cantón: {canton}, Distrito: {distrito}")

        try:
            cursor.execute("""
                INSERT INTO FIDE_CLIENTES_TB 
                (Nombre, Telefono, Cedula, Correo, Pais, Provincia, Canton, Distrito, Estado_ID)
                VALUES (:nombre, :telefono, :cedula, :correo, :pais, :provincia, :canton, :distrito, 1)
            """, {
                'nombre': nombre,
                'telefono': telefono,
                'cedula': cedula,
                'correo': correo,
                'pais': pais,
                'provincia': provincia,
                'canton': canton,
                'distrito': distrito
            })
            conn.commit()
            print("Cliente insertado correctamente")
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            print(f"Error al insertar datos: {error.message}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('clientes'))

    try:
        cursor.execute('SELECT ID_Cliente, Nombre, Telefono, Cedula, Correo, Pais, Provincia, Canton, Distrito, Estado_ID FROM FIDE_CLIENTES_TB')
        rows = cursor.fetchall()
        print("Clientes obtenidos:", rows)
    except cx_Oracle.DatabaseError as e:
        error, = e.args
        print(f"Error al recuperar datos: {error.message}")
        rows = []
    finally:
        cursor.close()
        conn.close()

    return render_template('clientes.html', rows=rows)



@app.route('/proveedores', methods=['GET', 'POST'])
def proveedores():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        detalles = request.form['detalles']

        cursor.execute("""
            INSERT INTO FIDE_PROVEEDORES_TB 
            (Nombre, Detalles)
            VALUES (:nombre, :detalles)
        """, {
            'nombre': nombre,
            'detalles': detalles
        })
        conn.commit()
        flash('Proveedor agregado con éxito', 'success')
    
    cursor.execute('SELECT ID_Proveedor, Nombre, Detalles FROM FIDE_PROVEEDORES_TB')
    proveedores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)


@app.route('/envios')
def envios():
    """
    Página de gestión de envíos.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('envios.html')  

@app.route('/facturas')
def facturas():
    """
    Página de facturas para el cliente.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('facturas.html') 


@app.route('/catalogo', methods=['GET', 'POST'])
def catalogo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            comentario = request.form['comentario']
            producto_id = request.form['producto_id']
            cliente_id = session['user_id']

            cursor.execute("""
                INSERT INTO FIDE_FEEDBACK_TB (Cliente_ID, Producto_ID, Comentario, Estado_ID)
                VALUES (:cliente_id, :producto_id, :comentario, 1)
            """, {
                'cliente_id': cliente_id,
                'producto_id': producto_id,
                'comentario': comentario
            })
            conn.commit()
            flash('Comentario agregado con éxito.', 'success')
        
        # Obtener productos con sus últimos tres comentarios
        cursor.execute("""
            SELECT p.ID_Producto, p.Nombre, p.Imagen, p.Precio, p.Detalle, p.Cantidad,
                   f.ID_Feedback, f.Comentario, c.Nombre AS Cliente_Nombre
            FROM FIDE_INVENTARIO_TB p
            LEFT JOIN FIDE_FEEDBACK_TB f ON p.ID_Producto = f.Producto_ID
            LEFT JOIN FIDE_CLIENTES_TB c ON f.Cliente_ID = c.ID_Cliente
            ORDER BY p.ID_Producto, f.FECHA_CREACION DESC
        """)
        productos = cursor.fetchall()
        print("Productos obtenidos:", productos)  # Línea de impresión para depuración

        # Organizar los comentarios de productos
        productos_dict = {}
        for producto in productos:
            producto_id = producto[0]
            if producto_id not in productos_dict:
                productos_dict[producto_id] = {
                    'info': producto[:6],
                    'comentarios': []
                }
            if producto[6]:  # ID_Feedback es diferente de None
                productos_dict[producto_id]['comentarios'].append({
                    'Cliente_Nombre': producto[8],
                    'Comentario': producto[7]
                })

        return render_template('catalogo.html', productos=list(productos_dict.values()))

    except Exception as e:
        print(f"Error al cargar el catálogo: {e}")
        flash('Error al cargar el catálogo.', 'error')
        return render_template('catalogo.html', productos=[])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """Guarda el feedback de un producto en la base de datos."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    producto_id = request.form['producto_id']
    comentario = request.form.get('feedback', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO FIDE_FEEDBACK_TB (ID_Cliente, ID_Producto, Comentario, Fecha) 
            VALUES (:user_id, :producto_id, :comentario, SYSTIMESTAMP)
        """, {
            'user_id': session['user_id'],
            'producto_id': producto_id,
            'comentario': comentario
        })
        conn.commit()
        flash('Gracias por tu feedback.', 'success')
    except Exception as e:
        flash(f'Error al enviar feedback: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('catalogo'))


@app.route('/feedback/<int:producto_id>')
def feedback(producto_id):
    """Muestra el feedback de un producto."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.Comentario, f.Fecha, c.Nombre 
        FROM FIDE_FEEDBACK_TB f
        JOIN FIDE_CLIENTES_TB c ON f.ID_Cliente = c.ID_Cliente
        WHERE f.ID_Producto = :producto_id
    """, {'producto_id': producto_id})
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('feedback.html', feedbacks=feedbacks, producto_id=producto_id)


@app.route('/proveedores', methods=['GET', 'POST'])
def proveedores_view():
    if request.method == 'POST':
        
        id_proveedor = len(proveedores) + 1
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        producto = request.form['producto']
        precio = request.form['precio']
        
        proveedores.append((id_proveedor, nombre, telefono, correo, producto, float(precio)))
        flash('Proveedor agregado correctamente.', 'success')
        return redirect(url_for('proveedores_view'))
    
    return render_template('proveedores.html', proveedores=proveedores)

@app.route('/facturar', methods=['POST'])
def facturar():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = session['user_id']
        print(f"User ID: {user_id}")
        
        # Obtener los productos del carrito temporal
        cursor.execute("""
            SELECT Producto_ID, Cantidad
            FROM FIDE_CARRITO_TEMP_TB WHERE Cliente_ID = :user_id
        """, {'user_id': user_id})
        carrito_temp = cursor.fetchall()
        print(f"Carrito Temporal: {carrito_temp}")

        # Obtener los detalles de cada producto y calcular el subtotal
        total = 0
        for item in carrito_temp:
            producto_id = item[0]
            cantidad = item[1]
            cursor.execute("SELECT Precio FROM FIDE_INVENTARIO_TB WHERE ID_Producto = :producto_id", {'producto_id': producto_id})
            precio = cursor.fetchone()[0]
            subtotal = precio * cantidad
            total += subtotal
            
            # Insertar los datos en la tabla FIDE_CARRITO_TB
            cursor.execute("""
                INSERT INTO FIDE_CARRITO_TB 
                (ID_CARRITO, Producto_ID, Cantidad, Subtotal, Cliente_ID) 
                VALUES (:ID_CARRITO, :Producto_ID, :Cantidad, :Subtotal, :Cliente_ID)
            """, {
                'ID_CARRITO': producto_id,
                'Producto_ID': producto_id,
                'Cantidad': cantidad,
                'Subtotal': subtotal,
                'Cliente_ID': user_id
            })

        IVA = total * 0.13  # Supongamos que el IVA es del 13%
        Costo_Envio = 1500
        Subtotal = total + IVA
        Total = Subtotal + Costo_Envio

        # Generar un ID único para la factura
        cursor.execute("SELECT MAX(ID_Factura) FROM FIDE_FACTURA_TB")
        max_id = cursor.fetchone()[0] or 0
        new_factura_id = max_id + 1
        
        # Insertar los datos en la tabla FIDE_FACTURA_TB
        cursor.execute("""
            INSERT INTO FIDE_FACTURA_TB 
            (ID_Factura, Cliente_ID, Metodo_ID, Detalle, TotalDeLineas, Total, Subtotal, IVA, Costo_Envio, Carrito_ID)
            VALUES (:ID_Factura, :Cliente_ID, :Metodo_ID, :Detalle, :TotalDeLineas, :Total, :Subtotal, :IVA, :Costo_Envio, :Carrito_ID)
        """, {
            'ID_Factura': new_factura_id,
            'Cliente_ID': user_id,
            'Metodo_ID': 1,  # Asignar un valor aleatorio para el método de pago
            'Detalle': 'Compra de productos',
            'TotalDeLineas': len(carrito_temp),
            'Total': Total,
            'Subtotal': Subtotal,
            'IVA': IVA,
            'Costo_Envio': Costo_Envio,
            'Carrito_ID': new_factura_id  # Usar el ID de factura como ID de carrito
        })

        # Vaciar la tabla FIDE_CARRITO_TEMP_TB para el Cliente_ID correspondiente
        cursor.execute("""
            DELETE FROM FIDE_CARRITO_TEMP_TB WHERE Cliente_ID = :user_id
        """, {'user_id': user_id})
        conn.commit()
        print("Carrito temporal vaciado y factura generada")
        
        flash('Factura generada y carrito vaciado con éxito.', 'success')
        return redirect(url_for('facturas'))

    except Exception as e:
        print(f"Error: {e}")
        flash('Ocurrió un error al generar la factura.', 'error')
        return redirect(url_for('carrito'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()




@app.route('/carrito', methods=['GET', 'POST'])
def carrito():
    if 'user_id' not in session:
        return redirect(url_for('login'))  
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            producto_id = request.form['producto_id']
            cantidad = request.form['cantidad']
            user_id = session['user_id']
            estado_id = 1  
            subtotal = 0  

            cursor.execute("""
                INSERT INTO FIDE_CARRITO_TEMP_TB 
                (Cliente_ID, Producto_ID, Cantidad, Subtotal, Estado_ID) 
                VALUES (:user_id, :producto_id, :cantidad, :subtotal, :estado_id)
            """, {
                'user_id': user_id,
                'producto_id': producto_id,
                'cantidad': cantidad,
                'subtotal': subtotal,
                'estado_id': estado_id
            })
            conn.commit()
            flash('Producto añadido al carrito temporal.', 'success')

        cursor.execute("""
            SELECT c.Producto_ID, i.Nombre, c.Cantidad, i.Precio, (c.Cantidad * i.Precio) AS Total
            FROM FIDE_CARRITO_TEMP_TB c
            JOIN FIDE_INVENTARIO_TB i ON c.Producto_ID = i.ID_Producto
            WHERE c.Cliente_ID = :user_id
        """, {'user_id': session['user_id']})
        carrito = cursor.fetchall()

        total = sum(item[4] for item in carrito)

        return render_template('carrito.html', carrito=carrito, total=total)

    except Exception as e:
        print(f"Error: {e}")
        flash('Ocurrió un error al procesar la solicitud.', 'error')
        return render_template('carrito.html', carrito=[], total=0)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/carrito')
def carrito_page():
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)


@app.route('/agregar_al_carrito/<int:producto_id>', methods=['POST'])
def agregar_al_carrito(producto_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = session['user_id']
        cantidad = int(request.form.get('cantidad', 1))
        estado_id = 1

        # Obtener el precio del producto
        cursor.execute("SELECT Precio FROM FIDE_INVENTARIO_TB WHERE ID_Producto = :producto_id", {'producto_id': producto_id})
        precio = cursor.fetchone()[0]
        subtotal = precio * cantidad

        cursor.execute("""
            INSERT INTO FIDE_CARRITO_TEMP_TB 
            (Cliente_ID, Producto_ID, Cantidad, Subtotal, Estado_ID) 
            VALUES (:user_id, :producto_id, :cantidad, :subtotal, :estado_id)
        """, {
            'user_id': user_id,
            'producto_id': producto_id,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'estado_id': estado_id
        })
        conn.commit()
        flash('Producto añadido al carrito temporal.', 'success')

    except Exception as e:
        print(f"Error al agregar producto al carrito: {e}")
        flash('Ocurrió un error al agregar el producto al carrito.', 'error')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('home'))



@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    if 'user_id' not in session:
        return redirect(url_for('login'))  
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = session['user_id']

        # Eliminar todos los productos del carrito temporal del usuario actual
        cursor.execute("""
            DELETE FROM FIDE_CARRITO_TEMP_TB 
            WHERE Cliente_ID = :user_id
        """, {'user_id': user_id})
        conn.commit()
        flash('Carrito vaciado con éxito.', 'success')

        return redirect(url_for('carrito'))

    except Exception as e:
        print(f"Error: {e}")
        flash('Ocurrió un error al vaciar el carrito.', 'error')
        return redirect(url_for('carrito'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)