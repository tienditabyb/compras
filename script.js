// -------------------- CONFIGURACIÓN --------------------
const POCKETBASE_URL = "http://127.0.0.1:8090";
const WHATSAPP_NUMBER = "5353803134"; // Sin +

// -------------------- ESTADO GLOBAL --------------------
let productos = [];
let carrito = [];
let categoriaActiva = "Todo";

// Referencias DOM
const productsGrid = document.getElementById("products-grid");
const categoriesContainer = document.getElementById("categories-container");
const productCount = document.getElementById("product-count");
const cartCount = document.getElementById("cart-count");
const cartSidebar = document.getElementById("cart-sidebar");
const cartItems = document.getElementById("cart-items");
const cartTotal = document.getElementById("cart-total");
const zoomOverlay = document.getElementById("zoom-overlay");
const zoomImage = document.getElementById("zoom-image");

// -------------------- FUNCIONES --------------------
async function obtenerProductos() {
    try {
        const resp = await fetch(`${POCKETBASE_URL}/api/collections/productos/records?perPage=100`);
        if (!resp.ok) throw new Error("Error al cargar productos");
        const data = await resp.json();
        productos = data.items.filter(p => parseInt(p.Stock || 0) > 0);
        renderizarProductos();
        actualizarContador();
    } catch (error) {
        console.error("Error:", error);
        productsGrid.innerHTML = `<p style="color:#e74c3c;">Error al cargar productos: ${error.message}</p>`;
    }
}

async function obtenerCategorias() {
    try {
        const resp = await fetch(`${POCKETBASE_URL}/api/collections/Categoria/records`);
        if (!resp.ok) return ["General"];
        const data = await resp.json();
        const cats = data.items.map(c => c.nombre);
        return cats.length ? cats : ["General"];
    } catch {
        return ["General"];
    }
}

function renderizarCategorias(categorias) {
    categoriesContainer.innerHTML = `<button class="chip chip-active" data-category="Todo">Todo</button>`;
    categorias.forEach(cat => {
        const btn = document.createElement("button");
        btn.className = "chip";
        btn.dataset.category = cat;
        btn.textContent = cat;
        btn.addEventListener("click", () => {
            categoriaActiva = cat;
            document.querySelectorAll(".chip").forEach(c => c.classList.remove("chip-active"));
            btn.classList.add("chip-active");
            renderizarProductos();
        });
        categoriesContainer.appendChild(btn);
    });
}

function renderizarProductos() {
    const filtrados = categoriaActiva === "Todo"
        ? productos
        : productos.filter(p => (p.Categoria || "General").toLowerCase() === categoriaActiva.toLowerCase());

    if (filtrados.length === 0) {
        productsGrid.innerHTML = `<p style="color:#aaa; grid-column:1/-1; text-align:center;">No hay productos en esta categoría.</p>`;
        return;
    }

    let html = "";
    filtrados.forEach(prod => {
        const nombre = prod.Nombre || "Sin nombre";
        const precio = parseFloat(prod.Precio_Venta || 0);
        const oferta = parseFloat(prod.Precio_Oferta || 0);
        const precioFinal = (oferta > 0 && oferta < precio) ? oferta : precio;
        const stock = parseInt(prod.Stock || 0);
        const foto = prod.Foto || prod.foto;
        const imgUrl = foto ? `${POCKETBASE_URL}/api/files/productos/${prod.id}/${foto}` : "";

        let precioHTML = `<span class="product-price">$${precioFinal.toFixed(2)}</span>`;
        if (oferta > 0 && oferta < precio) {
            precioHTML = `
                <span class="product-price">
                    <span class="price-old">$${precio.toFixed(2)}</span>
                    $${oferta.toFixed(2)}
                    <span class="offer">🔥</span>
                </span>
            `;
        }

        html += `
            <div class="product-card" data-id="${prod.id}">
                ${imgUrl ? `<img src="${imgUrl}" alt="${nombre}" class="product-img" onclick="abrirZoom('${imgUrl}')">` : `<div class="product-img" style="background:#333;display:flex;align-items:center;justify-content:center;color:#888;font-size:0.7rem;">Sin foto</div>`}
                <div class="product-name">${nombre}</div>
                ${precioHTML}
                <div class="product-stock">📦 ${stock} uds</div>
                <button class="btn-add" onclick="agregarAlCarrito('${prod.id}')">➕ Agregar</button>
            </div>
        `;
    });

    productsGrid.innerHTML = html;
    actualizarContador(filtrados.length);
}

function actualizarContador(cantidad) {
    const total = cantidad !== undefined ? cantidad : productos.length;
    productCount.textContent = `📦 ${total} productos`;
}

function agregarAlCarrito(id) {
    const prod = productos.find(p => p.id === id);
    if (!prod) return;
    const item = { ...prod, carritoId: Date.now() + Math.random() };
    carrito.push(item);
    actualizarCarritoUI();
    mostrarNotificacion("✅ Producto agregado");
}

function actualizarCarritoUI() {
    const count = carrito.length;
    cartCount.textContent = count;

    if (count === 0) {
        cartItems.innerHTML = `<p style="color:#888;text-align:center;padding:20px 0;">El carrito está vacío.</p>`;
        cartTotal.textContent = "Total: $0.00";
        return;
    }

    let total = 0;
    let html = "";
    carrito.forEach((item, index) => {
        const precio = (parseFloat(item.Precio_Oferta || 0) > 0 && parseFloat(item.Precio_Oferta || 0) < parseFloat(item.Precio_Venta || 0))
            ? parseFloat(item.Precio_Oferta || 0)
            : parseFloat(item.Precio_Venta || 0);
        total += precio;
        html += `
            <div class="cart-item">
                <span>${item.Nombre || "Producto"}</span>
                <span>$${precio.toFixed(2)}</span>
                <div>
                    <button class="qty-btn" onclick="duplicarItem(${index})">➕</button>
                    <button class="remove-btn" onclick="eliminarItem(${index})">✕</button>
                </div>
            </div>
        `;
    });

    cartItems.innerHTML = html;
    cartTotal.textContent = `Total: $${total.toFixed(2)}`;
}

function duplicarItem(index) {
    const item = carrito[index];
    if (!item) return;
    const nuevo = { ...item, carritoId: Date.now() + Math.random() };
    carrito.splice(index + 1, 0, nuevo);
    actualizarCarritoUI();
}

function eliminarItem(index) {
    carrito.splice(index, 1);
    actualizarCarritoUI();
}

function vaciarCarrito() {
    carrito = [];
    actualizarCarritoUI();
}

// -------------------- ZOOM DE IMAGEN --------------------
function abrirZoom(url) {
    zoomImage.src = url;
    zoomOverlay.classList.add("active");
    document.body.style.overflow = "hidden";
}

function cerrarZoom() {
    zoomOverlay.classList.remove("active");
    document.body.style.overflow = "";
}

// Cerrar zoom al hacer clic fuera de la imagen
zoomOverlay.addEventListener("click", (e) => {
    if (e.target === zoomOverlay) cerrarZoom();
});

// Cerrar zoom con tecla ESC
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") cerrarZoom();
});

// -------------------- CARRITO (abrir/cerrar sidebar) --------------------
document.getElementById("cart-btn").addEventListener("click", () => {
    cartSidebar.classList.toggle("open");
});

document.getElementById("close-cart-btn").addEventListener("click", () => {
    cartSidebar.classList.remove("open");
});

// Cerrar carrito al hacer clic fuera (opcional)
document.addEventListener("click", (e) => {
    if (cartSidebar.classList.contains("open") && !cartSidebar.contains(e.target) && e.target.id !== "cart-btn") {
        cartSidebar.classList.remove("open");
    }
});

// -------------------- PEDIDO POR WHATSAPP --------------------
document.getElementById("whatsapp-order-btn").addEventListener("click", () => {
    const nombre = document.getElementById("customer-name").value.trim();
    const telefono = document.getElementById("customer-phone").value.trim();
    const direccion = document.getElementById("customer-address").value.trim();
    const notas = document.getElementById("customer-notes").value.trim();

    if (!nombre || !telefono || !direccion) {
        alert("Por favor, completa todos los campos obligatorios (*)");
        return;
    }

    if (carrito.length === 0) {
        alert("El carrito está vacío. Agrega productos primero.");
        return;
    }

    // Calcular total
    let total = 0;
    let productosStr = "";
    carrito.forEach(item => {
        const precio = (parseFloat(item.Precio_Oferta || 0) > 0 && parseFloat(item.Precio_Oferta || 0) < parseFloat(item.Precio_Venta || 0))
            ? parseFloat(item.Precio_Oferta || 0)
            : parseFloat(item.Precio_Venta || 0);
        total += precio;
        productosStr += `- ${item.Nombre || "Producto"}: $${precio.toFixed(2)}\n`;
    });

    let mensaje = `*Nuevo pedido*\n\n👤 Cliente: ${nombre}\n📞 Teléfono: ${telefono}\n📍 Dirección: ${direccion}\n\n📦 Productos:\n${productosStr}\n💰 Total: $${total.toFixed(2)}`;
    if (notas) mensaje += `\n\n📝 Notas: ${notas}`;
    mensaje += "\n\n¡Gracias por tu compra! 🏪";

    const mensajeCodificado = encodeURIComponent(mensaje);
    const url = `https://wa.me/${WHATSAPP_NUMBER}?text=${mensajeCodificado}`;
    window.open(url, "_blank");

    // Opcional: limpiar carrito después de enviar
    // carrito = [];
    // actualizarCarritoUI();
    // cartSidebar.classList.remove("open");
});

// -------------------- NOTIFICACIONES --------------------
function mostrarNotificacion(texto) {
    const existing = document.querySelector(".toast-notification");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast-notification";
    toast.textContent = texto;
    toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: #2ecc71;
        color: white;
        padding: 10px 20px;
        border-radius: 30px;
        font-weight: bold;
        font-size: 0.9rem;
        z-index: 999;
        box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4);
        animation: fadeInUp 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = "opacity 0.3s ease";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// -------------------- INICIALIZAR --------------------
(async function init() {
    const categorias = await obtenerCategorias();
    renderizarCategorias(categorias);
    await obtenerProductos();
    actualizarCarritoUI();
})();

// Agregar estilo para la notificación
const style = document.createElement("style");
style.textContent = `
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateX(-50%) translateY(20px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
`;
document.head.appendChild(style);