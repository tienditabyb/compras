import streamlit as st
import requests
import uuid
from datetime import datetime
from PIL import Image
from io import BytesIO
import urllib.parse

# -------------------- CONFIGURACIÓN --------------------
st.set_page_config(
    page_title="Tiendita B&B - Tienda Online",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Colores
COLOR_PRINCIPAL = "#2980b9"
COLOR_SECUNDARIO = "#f39c12"
COLOR_FONDO = "#0d0d0d"
COLOR_TARJETA = "#181818"
COLOR_BORDE = "#2a2a2a"
COLOR_TEXTO = "#f0f0f0"
COLOR_TEXTO_SEC = "#aaaaaa"

POCKETBASE_URL = "https://tienditabyb.onrender.com"
WHATSAPP_NUMBER = "5353803134"

# Estado de la sesión
if "carrito" not in st.session_state:
    st.session_state.carrito = []
if "mostrar_carrito" not in st.session_state:
    st.session_state.mostrar_carrito = False
if "categoria_sel" not in st.session_state:
    st.session_state.categoria_sel = "Todo"
if "imagen_zoom" not in st.session_state:
    st.session_state.imagen_zoom = None

# -------------------- FUNCIONES --------------------
def obtener_productos():
    try:
        resp = requests.get(f"{POCKETBASE_URL}/api/collections/productos/records?perPage=100", timeout=3)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [p for p in items if int(p.get("Stock", 0)) > 0]
    except:
        pass
    return []

def obtener_categorias():
    try:
        resp = requests.get(f"{POCKETBASE_URL}/api/collections/Categoria/records", timeout=3)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [c["nombre"] for c in items if c.get("nombre")]
    except:
        pass
    return ["General"]

def obtener_precio_final(producto):
    venta = float(producto.get("Precio_Venta", 0))
    oferta = float(producto.get("Precio_Oferta", 0))
    return oferta if (oferta > 0 and oferta < venta) else venta

# -------------------- CSS MEJORADO (INDEX) --------------------
st.markdown("""
<style>
    /* Fondo general */
    .stApp {
        background-color: #0d0d0d;
    }
    /* HEADER */
    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        letter-spacing: 2px;
        margin-top: -5px;
    }
    .header-title span {
        color: #2980b9;
    }
    .header-sub {
        text-align: center;
        color: #aaaaaa;
        font-size: 0.9rem;
        margin-top: -8px;
        margin-bottom: 15px;
    }
    /* CATEGORÍAS (pestañas redondeadas) */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px;
        margin: 10px 0 15px 0;
    }
    .chip {
        background-color: #1e1e1e;
        color: #cccccc;
        padding: 6px 18px;
        border-radius: 30px;
        font-size: 0.8rem;
        border: 1px solid #333;
        cursor: pointer;
        transition: 0.2s;
        user-select: none;
        font-weight: 500;
    }
    .chip:hover {
        background-color: #2a2a2a;
        border-color: #2980b9;
        transform: translateY(-1px);
    }
    .chip-active {
        background-color: #2980b9;
        color: white;
        border-color: #2980b9;
        box-shadow: 0 0 20px rgba(41, 128, 185, 0.2);
    }
    /* CONTADOR */
    .product-count {
        text-align: center;
        color: #aaaaaa;
        font-size: 0.85rem;
        margin: 5px 0 15px 0;
    }
    /* TARJETAS DE PRODUCTO */
    .product-card {
        background-color: #181818;
        border-radius: 14px;
        padding: 12px 10px 14px 10px;
        margin: 8px 0;
        border: 1px solid #2a2a2a;
        text-align: center;
        transition: 0.25s;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .product-card:hover {
        border-color: #2980b9;
        box-shadow: 0 4px 25px rgba(41, 128, 185, 0.15);
        transform: translateY(-3px);
    }
    .product-img {
        cursor: pointer;
        border-radius: 10px;
        width: 100%;
        max-height: 120px;
        object-fit: cover;
        transition: 0.2s;
    }
    .product-img:hover {
        opacity: 0.85;
    }
    .product-name {
        font-size: 0.9rem;
        font-weight: 600;
        color: #f0f0f0;
        margin: 8px 0 3px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .product-price {
        font-size: 1.1rem;
        font-weight: bold;
        color: #2ecc71;
        margin: 2px 0 5px 0;
    }
    .product-price-old {
        font-size: 0.75rem;
        text-decoration: line-through;
        color: #888;
        margin-right: 6px;
    }
    .product-offer {
        color: #e74c3c;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .product-stock {
        font-size: 0.7rem;
        color: #888;
        margin-bottom: 6px;
    }
    .btn-add {
        background-color: #2980b9 !important;
        color: white !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 5px 14px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        width: 100%;
        transition: 0.2s;
    }
    .btn-add:hover {
        background-color: #1f6da9 !important;
        transform: scale(1.03);
    }
    /* BOTÓN CARRITO EN CABECERA */
    .cart-btn {
        background: transparent;
        border: none;
        color: white;
        font-size: 1.8rem;
        cursor: pointer;
        position: relative;
        padding: 0;
    }
    .cart-badge {
        position: absolute;
        top: -6px;
        right: -8px;
        background-color: #e74c3c;
        color: white;
        border-radius: 50%;
        padding: 1px 6px;
        font-size: 0.65rem;
        font-weight: bold;
    }
    /* ZOOM DE IMAGEN */
    .zoom-overlay {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: rgba(0,0,0,0.88);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        cursor: pointer;
    }
    .zoom-overlay img {
        max-width: 92%;
        max-height: 92%;
        border-radius: 14px;
        box-shadow: 0 0 60px rgba(0,0,0,0.6);
    }
    /* WHATSAPP FLOTANTE */
    .whatsapp-float {
        position: fixed;
        bottom: 22px;
        right: 22px;
        z-index: 1000;
        background-color: #25d366;
        color: white;
        border-radius: 50px;
        padding: 12px 20px;
        font-size: 1rem;
        font-weight: bold;
        text-decoration: none;
        box-shadow: 0 4px 20px rgba(37, 211, 102, 0.3);
        transition: 0.3s;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .whatsapp-float:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 30px rgba(37, 211, 102, 0.5);
    }
    /* RESPONSIVE */
    @media (max-width: 600px) {
        .header-title { font-size: 1.6rem; }
        .chip { font-size: 0.7rem; padding: 4px 12px; }
        .product-name { font-size: 0.8rem; }
        .product-price { font-size: 0.95rem; }
        .product-card { padding: 8px; }
        .cart-btn { font-size: 1.5rem; }
        .whatsapp-float { padding: 8px 14px; font-size: 0.85rem; bottom: 14px; right: 14px; }
        .product-img { max-height: 85px; }
    }
</style>
""", unsafe_allow_html=True)

# -------------------- HEADER CON CARRITO --------------------
col_titulo, col_cart = st.columns([5, 1])
with col_titulo:
    st.markdown('<div class="header-title">🏪 <span>Tiendita B&B</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">Todo lo que necesitas en un solo lugar</div>', unsafe_allow_html=True)

with col_cart:
    total_items = len(st.session_state.carrito)
    badge = f'<span class="cart-badge">{total_items}</span>' if total_items > 0 else ''
    if st.button("🛒", key="btn_cart", help="Ver carrito", use_container_width=True):
        st.session_state.mostrar_carrito = not st.session_state.mostrar_carrito
        st.rerun()
    st.markdown(f'<div style="position:relative;display:inline-block;margin-left:10px;top:-28px;">{badge}</div>', unsafe_allow_html=True)

# -------------------- CATEGORÍAS (CON "Todo") --------------------
categorias = ["Todo"] + obtener_categorias()

st.markdown('<div class="chip-container">', unsafe_allow_html=True)
cols = st.columns(len(categorias))
for i, cat in enumerate(categorias):
    with cols[i]:
        if cat == st.session_state.categoria_sel:
            st.markdown(f'<div class="chip chip-active">{cat}</div>', unsafe_allow_html=True)
        else:
            if st.button(cat, key=f"cat_{i}", use_container_width=True):
                st.session_state.categoria_sel = cat
                st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- PRODUCTOS --------------------
productos = obtener_productos()
if st.session_state.categoria_sel != "Todo":
    productos = [p for p in productos if (p.get("Categoria") or "General").strip().lower() == st.session_state.categoria_sel.strip().lower()]

st.markdown(f'<div class="product-count">📦 {len(productos)} productos</div>', unsafe_allow_html=True)

if not productos:
    st.info("No hay productos disponibles en esta categoría.")
else:
    cols = st.columns(4)
    for idx, prod in enumerate(productos):
        with cols[idx % 4]:
            with st.container():
                st.markdown('<div class="product-card">', unsafe_allow_html=True)
                
                foto_archivo = prod.get("Foto") or prod.get("foto")
                img_url = None
                if foto_archivo:
                    try:
                        url_foto = f"{POCKETBASE_URL}/api/files/productos/{prod['id']}/{foto_archivo}"
                        img_response = requests.get(url_foto, timeout=2)
                        if img_response.status_code == 200:
                            img_url = url_foto
                    except:
                        pass
                
                if img_url:
                    if st.button("", key=f"zoom_{prod['id']}", use_container_width=True):
                        st.session_state.imagen_zoom = img_url
                        st.rerun()
                    st.image(img_url, use_container_width=True, output_format="JPEG")
                else:
                    st.image("https://via.placeholder.com/300x200/333/666?text=Sin+foto", use_container_width=True)
                
                st.markdown(f'<div class="product-name">{prod.get("Nombre", "Sin nombre")}</div>', unsafe_allow_html=True)
                
                precio = float(prod.get("Precio_Venta", 0))
                oferta = float(prod.get("Precio_Oferta", 0))
                if oferta > 0 and oferta < precio:
                    st.markdown(f'<div class="product-price"><span class="product-price-old">${precio:.2f}</span> ${oferta:.2f} <span class="product-offer">🔥</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="product-price">${precio:.2f}</div>', unsafe_allow_html=True)
                
                stock = int(prod.get("Stock", 0))
                if stock < 5:
                    st.markdown(f'<div class="product-stock">⚠️ {stock} uds</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="product-stock">📦 {stock}</div>', unsafe_allow_html=True)
                
                if st.button("➕ Agregar", key=f"add_{prod['id']}", use_container_width=True):
                    item = prod.copy()
                    item["carrito_id"] = str(uuid.uuid4())
                    st.session_state.carrito.append(item)
                    st.success("✅ Agregado")
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

# -------------------- ZOOM --------------------
if st.session_state.imagen_zoom:
    st.markdown(f"""
    <div class="zoom-overlay" onclick="document.location.href='?';">
        <img src="{st.session_state.imagen_zoom}" />
    </div>
    """, unsafe_allow_html=True)
    if st.button("Cerrar zoom", key="close_zoom"):
        st.session_state.imagen_zoom = None
        st.rerun()

# -------------------- CARRITO (SIDEBAR) --------------------
if st.session_state.mostrar_carrito:
    with st.sidebar:
        st.markdown("## 🛒 Tu Carrito")
        st.divider()
        if not st.session_state.carrito:
            st.info("El carrito está vacío.")
        else:
            total = 0
            for idx, item in enumerate(st.session_state.carrito):
                precio = obtener_precio_final(item)
                total += precio
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.write(f"{item.get('Nombre', '')[:20]}")
                    st.caption(f"${precio:.2f}")
                with col2:
                    if st.button("➕", key=f"inc_{item['carrito_id']}"):
                        nuevo = item.copy()
                        nuevo["carrito_id"] = str(uuid.uuid4())
                        st.session_state.carrito.append(nuevo)
                        st.rerun()
                with col3:
                    if st.button("✕", key=f"rem_{item['carrito_id']}"):
                        st.session_state.carrito = [i for i in st.session_state.carrito if i["carrito_id"] != item["carrito_id"]]
                        st.rerun()
                st.divider()
            
            st.markdown(f"### 💰 Total: ${total:.2f}")
            
            with st.form("form_pedido_sidebar"):
                nombre = st.text_input("Nombre completo *", placeholder="Tu nombre")
                telefono = st.text_input("Teléfono *", placeholder="Ej: 3001234567")
                direccion = st.text_area("Dirección de entrega *", placeholder="Calle, número, barrio...")
                notas = st.text_area("Notas adicionales", placeholder="Ej: Tocar timbre...")
                
                enviado = st.form_submit_button("📲 Enviar pedido por WhatsApp", use_container_width=True, type="primary")
                if enviado:
                    if not nombre or not telefono or not direccion:
                        st.error("Completa todos los campos obligatorios (*)")
                    else:
                        productos_str = "\n".join([f"- {p.get('Nombre', 'Producto')}: ${obtener_precio_final(p):.2f}" for p in st.session_state.carrito])
                        mensaje = f"*Nuevo pedido*\n\n👤 Cliente: {nombre}\n📞 Teléfono: {telefono}\n📍 Dirección: {direccion}\n\n📦 Productos:\n{productos_str}\n\n💰 Total: ${total:.2f}"
                        if notas:
                            mensaje += f"\n\n📝 Notas: {notas}"
                        mensaje += "\n\n¡Gracias por tu compra! 🏪"
                        
                        mensaje_codificado = urllib.parse.quote(mensaje)
                        url_whatsapp = f"https://wa.me/{WHATSAPP_NUMBER}?text={mensaje_codificado}"
                        
                        st.markdown(f'<a href="{url_whatsapp}" target="_blank" style="display:block;text-align:center;background-color:#25d366;color:white;padding:10px;border-radius:30px;text-decoration:none;font-weight:bold;">Abrir WhatsApp</a>', unsafe_allow_html=True)
                        st.info("Envía el mensaje para confirmar tu pedido.")
        
        if st.button("Cerrar carrito", use_container_width=True):
            st.session_state.mostrar_carrito = False
            st.rerun()

# -------------------- WHATSAPP FLOTANTE --------------------
st.markdown(f"""
<a href="https://wa.me/{WHATSAPP_NUMBER}" class="whatsapp-float" target="_blank">
    💬 WhatsApp
</a>
""", unsafe_allow_html=True)

# -------------------- PIE DE PÁGINA --------------------
st.divider()
st.caption("🏪 Tiendita B&B - Todos los derechos reservados")