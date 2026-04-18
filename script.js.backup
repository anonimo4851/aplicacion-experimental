// API URL actualizada automáticamente
const API_URL = 'https://subchronically-flocculable-jenise.ngrok-free.dev/api';

// Configuración
const API_URL = (function() {
    // Si estamos en localhost, usar localhost
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('📍 Modo local detectado');
        return 'http://localhost:8081/api';
    }
    // Si estamos en una URL de ngrok, usar esa misma URL
    else if (window.location.hostname.includes('ngrok')) {
        console.log('🌐 Modo ngrok detectado:', window.location.origin);
        return window.location.origin + '/api';
    }
    // Fallback a localhost
    else {
        console.log('⚠️ Usando fallback localhost');
        return 'http://localhost:8081/api';
    }
})();

console.log('🔌 API_URL configurada como:', API_URL);
let productos = [];
let carrito = [];
let categorias = new Set();
let descuentoAplicado = null;
let categoriaActual = 'todas';
let busquedaActual = '';

// Elementos DOM
const productsGrid = document.getElementById('productsGrid');
const categoriesContainer = document.getElementById('categoriesContainer');
const cartItems = document.getElementById('cartItems');
const cartCount = document.getElementById('cartCount');
const cartTotal = document.getElementById('cartTotal');
const cartTotalNav = document.getElementById('cartTotalNav');
const subtotalSpan = document.getElementById('subtotal');
const searchInput = document.getElementById('searchInput');
const clearSearch = document.getElementById('clearSearch');
const sortSelect = document.getElementById('sortSelect');
const cartToggle = document.getElementById('cartToggle');
const cartPanel = document.getElementById('cartPanel');
const closeCart = document.getElementById('closeCart');
const checkoutBtn = document.getElementById('checkoutBtn');
const checkoutModal = document.getElementById('checkoutModal');
const closeModal = document.getElementById('closeModal');
const cancelCheckout = document.getElementById('cancelCheckout');
const checkoutForm = document.getElementById('checkoutForm');
const confirmationModal = document.getElementById('confirmationModal');
const newOrderBtn = document.getElementById('newOrderBtn');

// ========== CARGAR DATOS INICIALES ==========
// ========== CARGAR DATOS INICIALES ==========
async function cargarProductos() {
    try {
        console.log('🔄 Cargando productos...');
        
        const response = await fetch(`${API_URL}/productos`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('✅ Datos recibidos:', data);
        
        // ✅ CORRECCIÓN: Aceptar tanto "productos" como "products"
        productos = data.productos || data.products || [];
        
        // Si no hay productos, mostrar mensaje
        if (productos.length === 0) {
            console.warn('⚠️ No se recibieron productos');
        }
        
        // Extraer categorías
        categorias.clear();
        productos.forEach(p => {
            const cat = p.categoria || p.category || 'Sin categoría';
            categorias.add(cat);
        });
        
        renderizarCategorias();
        filtrarYRenderizar();
        cargarOfertasDestacadas();
        
        console.log(`✅ ${productos.length} productos cargados, ${categorias.size} categorías`);
        
    } catch (error) {
        console.error('❌ Error cargando productos:', error);
        mostrarToast('Error al conectar con el servidor', 'error');
        
        // Mostrar mensaje en el grid
        if (productsGrid) {
            productsGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px;">
                    <h3>⚠️ Error de conexión</h3>
                    <p>No se pudieron cargar los productos.</p>
                    <p style="color: #666; font-size: 0.9em;">${error.message}</p>
                    <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px;">
                        🔄 Reintentar
                    </button>
                </div>
            `;
        }
    }
}

// ========== CARGAR OFERTAS DESTACADAS ==========
function cargarOfertasDestacadas() {
    const featuredGrid = document.getElementById('featuredGrid');
    const productosConStock = productos.filter(p => p.cantidad > 0);
    const ofertas = productosConStock
        .sort(() => 0.5 - Math.random())
        .slice(0, 3);
    
    featuredGrid.innerHTML = '';
    
    ofertas.forEach(producto => {
        const precioOriginal = producto.precio;
        const precioOferta = precioOriginal * 0.8; // 20% descuento
        
        const card = document.createElement('div');
        card.className = 'featured-card';
        card.innerHTML = `
            <div class="featured-badge">🔥 -20%</div>
            <h3>${producto.nombre}</h3>
            <p>${producto.categoria || ''}</p>
            <div class="featured-price">
                <span class="original-price">$${precioOriginal.toFixed(2)}</span>
                <span class="discount-price">$${precioOferta.toFixed(2)}</span>
            </div>
            <button class="add-to-cart-btn" onclick="agregarOferta('${producto.nombre}', ${precioOferta})">
                🛒 Agregar
            </button>
        `;
        featuredGrid.appendChild(card);
    });
}

// ========== AGREGAR OFERTA ==========
function agregarOferta(nombre, precioOferta) {
    const producto = productos.find(p => p.nombre === nombre);
    if (!producto || producto.cantidad === 0) return;
    
    agregarAlCarrito(nombre, precioOferta);
    mostrarToast(`¡${nombre} agregado con 20% de descuento!`, 'success');
}

// ========== RENDERIZAR CATEGORÍAS ==========
function renderizarCategorias() {
    categoriesContainer.innerHTML = '';
    
    const btnTodas = document.createElement('button');
    btnTodas.className = `category-btn ${categoriaActual === 'todas' ? 'active' : ''}`;
    btnTodas.textContent = '📋 Todos';
    btnTodas.onclick = () => seleccionarCategoria('todas');
    categoriesContainer.appendChild(btnTodas);
    
    Array.from(categorias).sort().forEach(categoria => {
        const btn = document.createElement('button');
        btn.className = `category-btn ${categoriaActual === categoria ? 'active' : ''}`;
        btn.textContent = categoria;
        btn.onclick = () => seleccionarCategoria(categoria);
        categoriesContainer.appendChild(btn);
    });
}

// ========== SELECCIONAR CATEGORÍA ==========
function seleccionarCategoria(categoria) {
    categoriaActual = categoria;
    document.getElementById('currentCategory').textContent = 
        categoria === 'todas' ? 'Todos los productos' : categoria;
    
    renderizarCategorias();
    filtrarYRenderizar();
}

// ========== FILTRAR Y RENDERIZAR ==========
function filtrarYRenderizar() {
    let productosFiltrados = [...productos];
    
    // Filtrar por categoría
    if (categoriaActual !== 'todas') {
        productosFiltrados = productosFiltrados.filter(p => p.categoria === categoriaActual);
    }
    
    // Filtrar por búsqueda
    if (busquedaActual) {
        productosFiltrados = productosFiltrados.filter(p => 
            p.nombre.toLowerCase().includes(busquedaActual.toLowerCase()) ||
            (p.categoria && p.categoria.toLowerCase().includes(busquedaActual.toLowerCase()))
        );
    }
    
    // Ordenar
    const orden = sortSelect.value;
    if (orden === 'name') {
        productosFiltrados.sort((a, b) => a.nombre.localeCompare(b.nombre));
    } else if (orden === 'price-asc') {
        productosFiltrados.sort((a, b) => a.precio - b.precio);
    } else if (orden === 'price-desc') {
        productosFiltrados.sort((a, b) => b.precio - a.precio);
    }
    
    renderizarProductos(productosFiltrados);
}

// ========== RENDERIZAR PRODUCTOS ==========
function renderizarProductos(productosFiltrados) {
    productsGrid.innerHTML = '';
    
    if (productosFiltrados.length === 0) {
        productsGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px;">
                <p style="font-size: 1.2em; color: #999;">😕 No se encontraron productos</p>
            </div>
        `;
        return;
    }
    
    productosFiltrados.forEach(producto => {
        const card = document.createElement('div');
        card.className = 'product-card';
        
        // ✅ Aceptar diferentes nombres de campos
        const nombre = producto.nombre || producto.name || 'N/A';
        const categoria = producto.categoria || producto.category || 'Sin categoría';
        const precio = producto.precio || producto.price || 0;
        const cantidad = producto.cantidad || producto.quantity || producto.stock || 0;
        
        const stockDisponible = cantidad > 0;
        const stockBajo = cantidad > 0 && cantidad <= 5;
        const enCarrito = carrito.find(item => item.nombre === nombre);
        
        card.innerHTML = `
            ${!stockDisponible ? '<div class="product-badge badge-agotado">Agotado</div>' : ''}
            ${stockBajo ? '<div class="product-badge badge-oferta">¡Últimas unidades!</div>' : ''}
            <h3>${nombre}</h3>
            <p class="product-category">${categoria}</p>
            <div class="product-price">$${precio.toFixed(2)}</div>
            <p class="product-stock ${stockBajo ? 'stock-low' : ''}">
                ${stockDisponible ? `📦 Stock: ${cantidad}` : '❌ Agotado'}
            </p>
            ${enCarrito ? `
                <p style="color: var(--secondary-color); margin-bottom: 10px;">
                    ✅ ${enCarrito.cantidad} en carrito
                </p>
            ` : ''}
            <div class="product-actions">
                <div class="quantity-control">
                    <button class="quantity-btn" onclick="cambiarCantidadInput('${nombre}', -1)">-</button>
                    <input type="number" class="quantity-input" id="qty-${nombre.replace(/\s+/g, '')}" 
                           value="1" min="1" max="${cantidad}">
                    <button class="quantity-btn" onclick="cambiarCantidadInput('${nombre}', 1)">+</button>
                </div>
                <button class="add-to-cart-btn" 
                        onclick="agregarDesdeInput('${nombre}', ${precio})"
                        ${!stockDisponible ? 'disabled' : ''}>
                    🛒 Agregar
                </button>
            </div>
        `;
        
        productsGrid.appendChild(card);
    });
}

// ========== FUNCIONES DE CANTIDAD ==========
function cambiarCantidadInput(nombre, cambio) {
    const input = document.getElementById(`qty-${nombre.replace(/\s+/g, '')}`);
    if (input) {
        let valor = parseInt(input.value) + cambio;
        valor = Math.max(1, Math.min(valor, parseInt(input.max)));
        input.value = valor;
    }
}

function agregarDesdeInput(nombre, precio) {
    const input = document.getElementById(`qty-${nombre.replace(/\s+/g, '')}`);
    const cantidad = parseInt(input.value) || 1;
    agregarAlCarrito(nombre, precio, cantidad);
    input.value = 1;
}

// ========== AGREGAR AL CARRITO ==========
function agregarAlCarrito(nombre, precio, cantidad = 1) {
    const producto = productos.find(p => p.nombre === nombre);
    if (!producto || producto.cantidad === 0) {
        mostrarToast('Producto no disponible', 'error');
        return;
    }
    
    const itemExistente = carrito.find(item => item.nombre === nombre);
    const cantidadActual = itemExistente ? itemExistente.cantidad : 0;
    
    if (cantidadActual + cantidad > producto.cantidad) {
        mostrarToast(`Stock insuficiente. Disponible: ${producto.cantidad}`, 'error');
        return;
    }
    
    if (itemExistente) {
        itemExistente.cantidad += cantidad;
    } else {
        carrito.push({
            nombre: nombre,
            precio: precio,
            cantidad: cantidad,
            stockMaximo: producto.cantidad
        });
    }
    
    actualizarCarrito();
    filtrarYRenderizar();
    mostrarToast(`✅ ${cantidad}x ${nombre} agregado al carrito`, 'success');
    
    // Abrir carrito en móvil
    if (window.innerWidth <= 968) {
        cartPanel.classList.add('active');
    }
}

// ========== ACTUALIZAR CARRITO ==========
function actualizarCarrito() {
    // Actualizar contador
    const totalItems = carrito.reduce((sum, item) => sum + item.cantidad, 0);
    cartCount.textContent = totalItems;
    
    if (carrito.length === 0) {
        cartItems.innerHTML = `
            <div class="empty-cart">
                <div class="empty-cart-icon">🛒</div>
                <p>Tu carrito está vacío</p>
                <p class="empty-cart-hint">Agrega productos del menú</p>
            </div>
        `;
        checkoutBtn.disabled = true;
    } else {
        let html = '';
        let subtotal = 0;
        
        carrito.forEach((item, index) => {
            const itemTotal = item.precio * item.cantidad;
            subtotal += itemTotal;
            
            html += `
                <div class="cart-item">
                    <div class="cart-item-info">
                        <div class="cart-item-name">${item.nombre}</div>
                        <div class="cart-item-price">$${item.precio.toFixed(2)} c/u</div>
                    </div>
                    <div class="cart-item-controls">
                        <div class="cart-item-quantity">
                            <button class="quantity-btn" onclick="modificarCantidadCarrito(${index}, -1)">-</button>
                            <span>${item.cantidad}</span>
                            <button class="quantity-btn" onclick="modificarCantidadCarrito(${index}, 1)">+</button>
                        </div>
                        <button class="btn-remove" onclick="eliminarDelCarrito(${index})">🗑️</button>
                    </div>
                </div>
            `;
        });
        
        cartItems.innerHTML = html;
        checkoutBtn.disabled = false;
        
        // Calcular totales
        let descuento = 0;
        if (descuentoAplicado) {
            descuento = subtotal * (descuentoAplicado.valor / 100);
        }
        
        const total = subtotal - descuento;
        
        subtotalSpan.textContent = subtotal.toFixed(2);
        cartTotal.textContent = total.toFixed(2);
        cartTotalNav.textContent = total.toFixed(2);
        
        // Mostrar/ocultar fila de descuento
        const discountRow = document.getElementById('discountRow');
        const discountSpan = document.getElementById('discount');
        if (descuentoAplicado) {
            discountRow.style.display = 'flex';
            discountSpan.textContent = descuento.toFixed(2);
        } else {
            discountRow.style.display = 'none';
        }
    }
}

// ========== MODIFICAR CANTIDAD EN CARRITO ==========
function modificarCantidadCarrito(index, cambio) {
    const item = carrito[index];
    const producto = productos.find(p => p.nombre === item.nombre);
    const nuevaCantidad = item.cantidad + cambio;
    
    if (nuevaCantidad <= 0) {
        carrito.splice(index, 1);
    } else if (producto && nuevaCantidad <= producto.cantidad) {
        item.cantidad = nuevaCantidad;
    } else {
        mostrarToast(`Stock máximo disponible: ${producto.cantidad}`, 'error');
        return;
    }
    
    actualizarCarrito();
    filtrarYRenderizar();
}

// ========== ELIMINAR DEL CARRITO ==========
function eliminarDelCarrito(index) {
    const item = carrito[index];
    carrito.splice(index, 1);
    actualizarCarrito();
    filtrarYRenderizar();
    mostrarToast(`🗑️ ${item.nombre} eliminado del carrito`, 'info');
}

// ========== BUSCAR ==========
searchInput.addEventListener('input', (e) => {
    busquedaActual = e.target.value;
    clearSearch.style.display = busquedaActual ? 'block' : 'none';
    filtrarYRenderizar();
});

clearSearch.addEventListener('click', () => {
    searchInput.value = '';
    busquedaActual = '';
    clearSearch.style.display = 'none';
    filtrarYRenderizar();
});

// ========== ORDENAR ==========
sortSelect.addEventListener('change', filtrarYRenderizar);

// ========== TOGGLE CARRITO (MÓVIL) ==========
cartToggle.addEventListener('click', () => {
    cartPanel.classList.add('active');
});

closeCart.addEventListener('click', () => {
    cartPanel.classList.remove('active');
});

// ========== CHECKOUT ==========
checkoutBtn.addEventListener('click', () => {
    if (carrito.length === 0) return;
    
    // Llenar resumen del modal
    const summaryDiv = document.getElementById('orderSummaryItems');
    let html = '';
    carrito.forEach(item => {
        html += `
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>${item.cantidad}x ${item.nombre}</span>
                <span>$${(item.precio * item.cantidad).toFixed(2)}</span>
            </div>
        `;
    });
    summaryDiv.innerHTML = html;
    document.getElementById('modalTotal').textContent = cartTotal.textContent;
    
    checkoutModal.classList.add('active');
    cartPanel.classList.remove('active');
});

// ========== CERRAR MODALES ==========
function cerrarModales() {
    checkoutModal.classList.remove('active');
    confirmationModal.classList.remove('active');
}

closeModal.addEventListener('click', cerrarModales);
cancelCheckout.addEventListener('click', cerrarModales);

// ========== ENVIAR PEDIDO ==========
checkoutForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btnConfirmar = document.getElementById('confirmOrder');
    const btnText = btnConfirmar.querySelector('.btn-text');
    const btnLoading = btnConfirmar.querySelector('.btn-loading');
    
    btnConfirmar.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';
    
    try {
        // Validar stock
        const validacion = await validarStockPedido();
        
        if (!validacion.valido) {
            throw new Error('Algunos productos ya no tienen stock suficiente');
        }
        
        // Preparar pedido
        const pedido = {
            cliente: document.getElementById('customerName').value,
            telefono: document.getElementById('customerPhone').value,
            direccion: document.getElementById('customerAddress').value,
            notas: document.getElementById('orderNotes').value,
            metodo_pago: document.getElementById('paymentMethod').value,
            horario_entrega: document.getElementById('deliveryTime').value,
            items: carrito.map(item => ({
                nombre: item.nombre,
                cantidad: item.cantidad
            }))
        };
        
        // Enviar pedido
        const response = await fetch(`${API_URL}/pedido`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pedido)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.mensaje || 'Error al crear pedido');
        }
        
        // Mostrar confirmación
        document.getElementById('orderNumber').textContent = data.pedido_id.substring(0, 8);
        document.getElementById('estimatedTime').textContent = data.tiempo_estimado;
        document.getElementById('confirmedTotal').textContent = data.total.toFixed(2);
        
        cerrarModales();
        confirmationModal.classList.add('active');
        
        // Limpiar carrito
        carrito = [];
        descuentoAplicado = null;
        actualizarCarrito();
        checkoutForm.reset();
        
        // Recargar productos
        setTimeout(cargarProductos, 2000);
        
    } catch (error) {
        mostrarToast(error.message, 'error');
    } finally {
        btnConfirmar.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
});

// ========== VALIDAR STOCK ==========
async function validarStockPedido() {
    const items = carrito.map(item => ({
        nombre: item.nombre,
        cantidad: item.cantidad
    }));
    
    const response = await fetch(`${API_URL}/validar-stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
    });
    
    return await response.json();
}

// ========== CUPÓN DE DESCUENTO ==========
document.getElementById('applyCoupon').addEventListener('click', () => {
    const codigo = document.getElementById('couponCode').value.trim().toUpperCase();
    const messageDiv = document.getElementById('couponMessage');
    
    const cupones = {
        'BIENVENIDO10': { valor: 10, tipo: 'porcentaje' },
        'COMIDA20': { valor: 20, tipo: 'porcentaje' },
        'ENVIOGRATIS': { valor: 0, tipo: 'envio' }
    };
    
    if (cupones[codigo]) {
        descuentoAplicado = cupones[codigo];
        actualizarCarrito();
        messageDiv.innerHTML = `<span class="coupon-success">✅ Cupón aplicado: ${descuentoAplicado.valor}% de descuento</span>`;
        mostrarToast(`¡Cupón aplicado! ${descuentoAplicado.valor}% de descuento`, 'success');
    } else {
        messageDiv.innerHTML = '<span class="coupon-error">❌ Cupón inválido</span>';
        mostrarToast('Cupón no válido', 'error');
    }
});

// ========== NUEVO PEDIDO ==========
newOrderBtn.addEventListener('click', () => {
    confirmationModal.classList.remove('active');
    cargarProductos();
});

// ========== TOAST NOTIFICATIONS ==========
function mostrarToast(mensaje, tipo = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;
    
    const iconos = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <span>${iconos[tipo]}</span>
        <span>${mensaje}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ========== INICIAR ==========
document.addEventListener('DOMContentLoaded', () => {
    cargarProductos();
    setInterval(cargarProductos, 60000); // Recargar cada minuto
});

// Click fuera del carrito en móvil
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 968) {
        if (!cartPanel.contains(e.target) && !cartToggle.contains(e.target)) {
            cartPanel.classList.remove('active');
        }
    }
});