import customtkinter as ctk
import sys
import os
import requests  
import uuid
from datetime import datetime
from tkinter import filedialog, messagebox
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# -------------------- CONFIGURACIÓN DE TEMAS --------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Colores personalizados (AZUL + MORADO)
COLOR_PRINCIPAL = "#2980b9"      # Azul
COLOR_PRINCIPAL_HOVER = "#1f6da9"
COLOR_REPORTES = "#8e44ad"       # Morado
COLOR_REPORTES_HOVER = "#6c3483"
COLOR_FONDO = "#1a1a1a"
COLOR_TARJETA = "#2d2d2d"
COLOR_TEXTO = "#f0f0f0"
COLOR_TEXTO_SECUNDARIO = "#b0b0b0"

# ---------- NUEVA URL DE POCKETBASE EN LA NUBE ----------
POCKETBASE_URL = "https://tienditabyb.onrender.com"

class TienditaBbBApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🏪 Tiendita B&B POS - Panel de Control")
        ancho = 1200
        alto = 800
        pantalla_ancho = self.winfo_screenwidth()
        pantalla_alto = self.winfo_screenheight()
        x = int((pantalla_ancho / 2) - (ancho / 2))
        y = int((pantalla_alto / 2) - (alto / 2))
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        
        # Variables
        self.ruta_foto_seleccionada = ""  
        self.imagenes_referencia = [] 
        self.modo_vista = "grid" 
        self.categoria_seleccionada_filtro = "Todas"
        self.texto_busqueda = ""  # Para el buscador de inventario
        self.carrito = []
        self.lista_productos_raw = []
        self.categoria_filtro_ventas = "Todas"
        
        self.filtro_estado_domicilios = "Todos"
        self.filtro_fecha_desde = ""
        self.filtro_fecha_hasta = ""
        self.filtro_tipo_venta = "Todos"
        
        self.tipo_venta_var = ctk.StringVar(value="Local")
        
        # ---------- HEADER ----------
        self.header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=COLOR_PRINCIPAL)
        self.header_frame.pack(fill="x", side="top")
        
        ctk.CTkLabel(
            self.header_frame, 
            text="🏪 Tiendita B&B POS", 
            font=ctk.CTkFont(size=28, weight="bold", family="Segoe UI"), 
            text_color="white"
        ).pack(side="left", padx=30, pady=20)
        
        ctk.CTkLabel(
            self.header_frame,
            text="Sistema de Ventas e Inventario",
            font=ctk.CTkFont(size=14, family="Segoe UI"),
            text_color="#d4d4d4"
        ).pack(side="left", padx=10, pady=20)
        
        # ---------- SIDEBAR ----------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#2c2c2c")
        self.sidebar_frame.pack(fill="y", side="left")
        
        btn_config = {
            "fg_color": "#3a3a3a",
            "hover_color": COLOR_PRINCIPAL,
            "text_color": "white",
            "corner_radius": 8,
            "height": 45,
            "font": ctk.CTkFont(size=14, weight="bold")
        }
        
        ctk.CTkButton(self.sidebar_frame, text="📦 Inventario", **btn_config, command=self.cargar_inventario).pack(padx=15, pady=12, fill="x")
        ctk.CTkButton(self.sidebar_frame, text="💰 Ventas", **btn_config, command=self.pantalla_ventas).pack(padx=15, pady=12, fill="x")
        ctk.CTkButton(self.sidebar_frame, text="🛵 Domicilios", **btn_config, command=self.mostrar_domicilios).pack(padx=15, pady=12, fill="x")
        ctk.CTkButton(
            self.sidebar_frame, 
            text="📊 Reportes", 
            fg_color=COLOR_REPORTES,
            hover_color=COLOR_REPORTES_HOVER,
            text_color="white",
            corner_radius=8,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.pantalla_reportes
        ).pack(padx=15, pady=12, fill="x")

        # ---------- FRAME PRINCIPAL ----------
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=COLOR_FONDO)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.cargar_inventario()

    # ---------- FUNCIONES AUXILIARES ----------
    def tachar_texto(self, texto):
        return "".join([c + "\u0336" for c in texto])

    def cambiar_vista(self, modo):
        self.modo_vista = modo
        self.cargar_inventario()

    def obtener_categorias(self):
        try:
            response = requests.get(f'{POCKETBASE_URL}/api/collections/Categoria/records', timeout=3)
            if response.status_code == 200:
                items = response.json().get('items', [])
                cats = [c['nombre'] for c in items if c.get('nombre')]
                return cats if cats else ["General"]
        except: pass
        return ["General"]

    def calcular_ganancia_venta(self, venta):
        total_venta = float(venta.get('total', 0))
        productos_str = venta.get('productos_json', '')
        nombres = [p.strip() for p in productos_str.split(",") if p.strip()]
        suma_costos = 0.0
        for nombre in nombres:
            prod = next((p for p in self.lista_productos_raw if (p.get('Nombre') or '').strip().lower() == nombre.lower()), None)
            if prod:
                costo = float(prod.get('Precio_Costo') or prod.get('precio_costo') or 0)
                suma_costos += costo
        return total_venta - suma_costos

    def actualizar_estado_domicilio(self, record_id, nuevo_estado):
        try:
            requests.patch(
                f'{POCKETBASE_URL}/api/collections/domicilios/records/{record_id}',
                json={"Estado": nuevo_estado}
            )
            self.mostrar_domicilios()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar el estado: {e}")

    # ---------- DOMICILIOS ----------
    def mostrar_domicilios(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        
        top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_frame.pack(fill="x", pady=15, padx=10)
        
        ctk.CTkLabel(
            top_frame, 
            text="🛵 Gestión de Domicilios", 
            font=ctk.CTkFont(size=26, weight="bold", family="Segoe UI"),
            text_color=COLOR_PRINCIPAL
        ).pack(side="left")
        
        filtro_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        filtro_frame.pack(side="right")
        ctk.CTkLabel(filtro_frame, text="Filtrar por estado:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 10))
        
        opciones_estado = ["Todos", "Pendiente", "En camino", "Entregado"]
        self.menu_filtro_estado = ctk.CTkOptionMenu(
            filtro_frame,
            values=opciones_estado,
            width=150,
            fg_color="#3a3a3a",
            button_color=COLOR_PRINCIPAL,
            button_hover_color=COLOR_PRINCIPAL_HOVER,
            command=self.aplicar_filtro_domicilios
        )
        self.menu_filtro_estado.pack(side="left")
        self.menu_filtro_estado.set(self.filtro_estado_domicilios)
        
        try:
            response = requests.get(f'{POCKETBASE_URL}/api/collections/domicilios/records?sort=-created', timeout=5)
            items = response.json().get('items', []) if response.status_code == 200 else []
            
            if self.filtro_estado_domicilios != "Todos":
                items = [dom for dom in items if dom.get('Estado', '') == self.filtro_estado_domicilios]
            
            if not items:
                ctk.CTkLabel(self.main_frame, text="No hay domicilios que coincidan con el filtro.", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO_SECUNDARIO).pack(pady=40)
                return
                
            for dom in items:
                record_id = dom.get('id')
                cliente = dom.get('Cliente_Nombre', 'Sin nombre')
                direccion = dom.get('Direccion_Entrega', 'Sin dirección')
                telefono = dom.get('Telefono', 'Sin teléfono')
                detalles = dom.get('Detalles', '')
                estado = dom.get('Estado', 'Pendiente')
                
                if estado == "Pendiente":
                    color_estado = "#e67e22"
                    bg_estado = "#3d2a1a"
                elif estado == "En camino":
                    color_estado = "#f1c40f"
                    bg_estado = "#3d3a1a"
                else:
                    color_estado = "#2ecc71"
                    bg_estado = "#1a3d2a"
                
                card = ctk.CTkFrame(self.main_frame, fg_color=COLOR_TARJETA, corner_radius=12, border_width=1, border_color="#444444")
                card.pack(fill="x", pady=10, padx=8)
                
                top_card = ctk.CTkFrame(card, fg_color="transparent")
                top_card.pack(fill="x", padx=20, pady=(15, 5))
                
                cliente_frame = ctk.CTkFrame(top_card, fg_color="transparent")
                cliente_frame.pack(side="left")
                ctk.CTkLabel(cliente_frame, text=f"👤 {cliente}", font=ctk.CTkFont(size=18, weight="bold", family="Segoe UI"), text_color=COLOR_TEXTO, anchor="w").pack(anchor="w")
                ctk.CTkLabel(cliente_frame, text=f"📞 {telefono}", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO_SECUNDARIO, anchor="w").pack(anchor="w")
                
                menu_frame = ctk.CTkFrame(top_card, fg_color="transparent")
                menu_frame.pack(side="right")
                ctk.CTkLabel(menu_frame, text="Cambiar:", font=ctk.CTkFont(size=13), text_color=COLOR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 8))
                
                opciones_estado_menu = ["Pendiente", "En camino", "Entregado"]
                menu_estado = ctk.CTkOptionMenu(
                    menu_frame,
                    values=opciones_estado_menu,
                    width=130,
                    height=35,
                    fg_color="#3a3a3a",
                    button_color=COLOR_PRINCIPAL,
                    button_hover_color=COLOR_PRINCIPAL_HOVER,
                    command=lambda nuevo_estado, r_id=record_id: self.actualizar_estado_domicilio(r_id, nuevo_estado)
                )
                menu_estado.pack(side="left")
                menu_estado.set(estado)
                
                center_card = ctk.CTkFrame(card, fg_color="transparent")
                center_card.pack(fill="x", padx=20, pady=(5, 10))
                
                ctk.CTkLabel(
                    center_card, 
                    text=f"📍 {direccion}", 
                    font=ctk.CTkFont(size=14), 
                    text_color="#3498db", 
                    anchor="w",
                    wraplength=700
                ).pack(fill="x", pady=(4, 2))
                
                if detalles:
                    if " | Notas:" in detalles:
                        partes = detalles.split(" | Notas:", 1)
                        productos_text = partes[0].replace("Productos: ", "")
                        notas_text = partes[1]
                    else:
                        productos_text = detalles.replace("Productos: ", "") if "Productos:" in detalles else detalles
                        notas_text = ""
                    
                    if productos_text:
                        ctk.CTkLabel(
                            center_card, 
                            text=f"📦 {productos_text}", 
                            font=ctk.CTkFont(size=14), 
                            text_color=COLOR_TEXTO, 
                            anchor="w",
                            wraplength=700
                        ).pack(fill="x", pady=(4, 2))
                    
                    if notas_text:
                        notas_frame = ctk.CTkFrame(center_card, fg_color="#2a2a2a", corner_radius=8)
                        notas_frame.pack(fill="x", pady=(4, 0))
                        ctk.CTkLabel(
                            notas_frame, 
                            text=f"📝 {notas_text}", 
                            font=ctk.CTkFont(size=13), 
                            text_color=COLOR_TEXTO_SECUNDARIO, 
                            anchor="w",
                            wraplength=680,
                            padx=15,
                            pady=8
                        ).pack(fill="x")
                
                bottom_card = ctk.CTkFrame(card, fg_color="transparent")
                bottom_card.pack(fill="x", padx=20, pady=(5, 15))
                
                ctk.CTkLabel(bottom_card, text="Estado actual:", font=ctk.CTkFont(size=13), text_color=COLOR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 8))
                
                ctk.CTkLabel(
                    bottom_card,
                    text=f"● {estado}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=color_estado,
                    fg_color=bg_estado,
                    corner_radius=8,
                    padx=15,
                    pady=5
                ).pack(side="left")
                
        except Exception as e:
            ctk.CTkLabel(self.main_frame, text=f"Error cargando domicilios: {e}", text_color="#e74c3c").pack(pady=20)

    def aplicar_filtro_domicilios(self, opcion):
        self.filtro_estado_domicilios = opcion
        self.mostrar_domicilios()

    # ---------- INVENTARIO CON BUSCADOR ----------
    def pantalla_categorias(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        ctk.CTkButton(self.main_frame, text="⬅️ Volver", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.cargar_inventario).pack(anchor="w", pady=15)
        ctk.CTkLabel(self.main_frame, text="Gestionar Categorías", font=ctk.CTkFont(size=22, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).pack(pady=15, anchor="w")
        self.ent_nueva_cat = ctk.CTkEntry(self.main_frame, placeholder_text="Nombre de la nueva categoría...", width=350, fg_color="#2d2d2d", text_color="white")
        self.ent_nueva_cat.pack(pady=5, anchor="w")
        ctk.CTkButton(self.main_frame, text="Guardar Categoría", fg_color=COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=self.guardar_categoria).pack(pady=10, anchor="w")
        for cat in self.obtener_categorias():
            ctk.CTkLabel(self.main_frame, text=f"🏷️ {cat}", font=ctk.CTkFont(size=15), text_color=COLOR_TEXTO).pack(anchor="w", padx=15, pady=4)

    def guardar_categoria(self):
        nombre = self.ent_nueva_cat.get().strip()
        if nombre:
            try:
                requests.post(f'{POCKETBASE_URL}/api/collections/Categoria/records', json={"nombre": nombre})
                self.pantalla_categorias()
            except: pass

    def buscar_productos(self):
        self.texto_busqueda = self.entry_buscar.get().strip()
        self.cargar_inventario()

    def limpiar_busqueda(self):
        self.entry_buscar.delete(0, "end")
        self.texto_busqueda = ""
        self.cargar_inventario()

    def cargar_inventario(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.imagenes_referencia.clear()
        
        top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text="📦 Inventario", font=ctk.CTkFont(size=26, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).pack(side="left")
        
        actions_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_frame.pack(side="right")
        ctk.CTkButton(actions_frame, text="🔲", width=45, fg_color="#3a3a3a" if self.modo_vista == "grid" else COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=lambda: self.cambiar_vista("grid")).pack(side="right", padx=3)
        ctk.CTkButton(actions_frame, text="📋", width=45, fg_color="#3a3a3a" if self.modo_vista == "list" else COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=lambda: self.cambiar_vista("list")).pack(side="right", padx=3)
        ctk.CTkButton(actions_frame, text="🏷️ Categoría", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, width=100, command=self.pantalla_categorias).pack(side="right", padx=5)
        ctk.CTkButton(actions_frame, text="➕ Añadir", fg_color=COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, width=100, command=self.pantalla_nuevo_producto).pack(side="right", padx=5)

        filter_bar = ctk.CTkFrame(self.main_frame, fg_color="#2d2d2d", corner_radius=10)
        filter_bar.pack(fill="x", pady=12, padx=2)
        ctk.CTkLabel(filter_bar, text="🔍 Filtrar por categoría:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=20, pady=10)
        
        lista_cats_filtro = ["Todas"] + self.obtener_categorias()
        self.menu_filtro_cat = ctk.CTkOptionMenu(filter_bar, values=lista_cats_filtro, width=200, fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER, command=lambda v: self.cambiar_filtro_categoria(v))
        self.menu_filtro_cat.pack(side="left", padx=15, pady=10)
        self.menu_filtro_cat.set(self.categoria_seleccionada_filtro)

        search_frame = ctk.CTkFrame(self.main_frame, fg_color="#2d2d2d", corner_radius=10)
        search_frame.pack(fill="x", pady=(0, 12), padx=2)
        ctk.CTkLabel(search_frame, text="🔎 Buscar:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=20, pady=10)
        self.entry_buscar = ctk.CTkEntry(search_frame, width=300, placeholder_text="Nombre o código de barras...", fg_color="#1a1a1a", text_color="white")
        self.entry_buscar.pack(side="left", padx=10, pady=10)
        self.entry_buscar.bind("<Return>", lambda e: self.buscar_productos())
        ctk.CTkButton(search_frame, text="Buscar", width=80, fg_color=COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=self.buscar_productos).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(search_frame, text="Limpiar", width=80, fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.limpiar_busqueda).pack(side="left", padx=5, pady=10)
        if self.texto_busqueda:
            self.entry_buscar.insert(0, self.texto_busqueda)

        try:
            response = requests.get(f'{POCKETBASE_URL}/api/collections/productos/records?perPage=100', timeout=5)
            items = response.json().get("items", []) if response.status_code == 200 else []
            self.lista_productos_raw = items
            
            productos_validos = [p for p in items if (p.get('Nombre') or p.get('nombre'))]
            if self.categoria_seleccionada_filtro != "Todas":
                productos_validos = [p for p in productos_validos if (p.get('Categoria') or p.get('categoria') or "").strip().lower() == self.categoria_seleccionada_filtro.strip().lower()]
            
            if self.texto_busqueda:
                busq = self.texto_busqueda.lower()
                productos_validos = [
                    p for p in productos_validos
                    if (busq in (p.get('Nombre') or '').lower() or 
                        busq in (p.get('Codigo_de_Barras') or '').lower())
                ]

            if self.modo_vista == "grid":
                grid_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
                grid_frame.pack(fill="both", expand=True, pady=10)
                grid_frame.columnconfigure((0, 1, 2), weight=1)
                row_idx, col_idx = 0, 0
                for producto in productos_validos:
                    nombre = producto.get('Nombre') or producto.get('nombre')
                    record_id = producto.get('id')
                    cat = producto.get('Categoria') or producto.get('categoria') or "General"
                    venta = float(producto.get('Precio_Venta') or producto.get('precio_venta') or 0)
                    oferta = float(producto.get('Precio_Oferta') or producto.get('precio_oferta') or 0)
                    stock = int(producto.get('Stock') or producto.get('stock') or 0)
                    foto_archivo = producto.get('Foto') or producto.get('foto') or ""
                    
                    card = ctk.CTkFrame(grid_frame, corner_radius=12, border_width=1, border_color="#444444", fg_color=COLOR_TARJETA)
                    card.grid(row=row_idx, column=col_idx, padx=12, pady=12, sticky="nsew")
                    
                    lbl_foto = ctk.CTkLabel(card, text="Sin foto", width=150, height=150, corner_radius=8, fg_color="#2d2d2d")
                    lbl_foto.pack(pady=15, padx=15)
                    if foto_archivo:
                        try:
                            url = f"{POCKETBASE_URL}/api/files/productos/{record_id}/{foto_archivo}"
                            img_response = requests.get(url, timeout=3)
                            if img_response.status_code == 200:
                                pil_img = Image.open(BytesIO(img_response.content)).resize((150, 150), Image.Resampling.LANCZOS)
                                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 150))
                                lbl_foto.configure(image=ctk_img, text="")
                                self.imagenes_referencia.append(ctk_img)
                        except: pass

                    ctk.CTkLabel(card, text=nombre, font=ctk.CTkFont(size=16, weight="bold", family="Segoe UI"), text_color=COLOR_TEXTO).pack(padx=15, anchor="w")
                    ctk.CTkLabel(card, text=f"Categoría: {cat}", font=ctk.CTkFont(size=13), text_color="#3498db").pack(padx=15, anchor="w")
                    ctk.CTkLabel(card, text=f"Stock: {stock} uds", font=ctk.CTkFont(size=13), text_color=COLOR_TEXTO_SECUNDARIO).pack(padx=15, anchor="w")
                    
                    if oferta > 0 and oferta < venta:
                        ctk.CTkLabel(card, text=f"Precio anterior: {self.tachar_texto(f'${venta:.2f}')}", font=ctk.CTkFont(size=12), text_color=COLOR_TEXTO_SECUNDARIO).pack(padx=15, anchor="w")
                        ctk.CTkLabel(card, text=f"🔥 OFERTA: ${oferta:.2f}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#e74c3c").pack(padx=15, anchor="w", pady=2)
                    else:
                        ctk.CTkLabel(card, text=f"Precio: ${venta:.2f}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#2ecc71").pack(padx=15, anchor="w", pady=2)
                    
                    ctk.CTkButton(card, text="✏️ Editar", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, height=35, command=lambda p=producto: self.pantalla_editar_producto(p)).pack(fill="x", padx=15, pady=(10, 2))
                    ctk.CTkButton(card, text="🗑️ Eliminar", fg_color="#a83232", hover_color="#7a1f1f", height=35, command=lambda r_id=record_id: self.eliminar_producto(r_id)).pack(fill="x", padx=15, pady=(2, 15))
                    
                    col_idx += 1
                    if col_idx > 2: col_idx, row_idx = 0, row_idx + 1
            else:
                for producto in productos_validos:
                    nombre = producto.get('Nombre') or producto.get('nombre')
                    record_id = producto.get('id')
                    venta = float(producto.get('Precio_Venta') or producto.get('precio_venta') or 0)
                    oferta = float(producto.get('Precio_Oferta') or producto.get('precio_oferta') or 0)
                    row_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, border_width=1, fg_color=COLOR_TARJETA)
                    row_frame.pack(fill="x", pady=6, padx=5)
                    
                    if oferta > 0 and oferta < venta:
                        precio_txt = f"Precio anterior: {self.tachar_texto(f'${venta:.2f}')} ➔ 🔥 OFERTA: ${oferta:.2f}"
                    else:
                        precio_txt = f"Precio: ${venta:.2f}"
                    ctk.CTkLabel(row_frame, text=f"📦 {nombre} | {precio_txt}", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(side="left", padx=15, pady=15)
                    ctk.CTkButton(row_frame, text="🗑️", fg_color="#a83232", hover_color="#7a1f1f", width=45, command=lambda r_id=record_id: self.eliminar_producto(r_id)).pack(side="right", padx=5)
                    ctk.CTkButton(row_frame, text="✏️", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, width=45, command=lambda p=producto: self.pantalla_editar_producto(p)).pack(side="right", padx=5)
        except Exception as e:
            ctk.CTkLabel(self.main_frame, text=f"Error cargando inventario: {e}", text_color="#e74c3c").pack(pady=20)

    # ---------- ELIMINAR CON CONFIRMACIÓN ----------
    def eliminar_producto(self, record_id):
        if messagebox.askyesno("Confirmar eliminación", "¿Estás seguro de que deseas eliminar este producto? Esta acción no se puede deshacer."):
            try:
                response = requests.delete(f'{POCKETBASE_URL}/api/collections/productos/records/{record_id}')
                if response.status_code in [200, 204]:
                    messagebox.showinfo("Éxito", "El producto ha sido eliminado correctamente.")
                    self.cargar_inventario()
                else:
                    messagebox.showerror("Error", f"No se pudo eliminar el producto. Código: {response.status_code}\nRespuesta: {response.text}")
            except requests.exceptions.ConnectionError:
                messagebox.showerror("Error de conexión", "No se pudo conectar con PocketBase. Asegúrate de que el servidor esté corriendo.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar: {e}")

    def cambiar_filtro_categoria(self, nueva_categoria):
        self.categoria_seleccionada_filtro = nueva_categoria
        self.cargar_inventario()

    def seleccionar_foto(self):
        file_path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.png")])
        if file_path:
            self.ruta_foto_seleccionada = file_path
            self.lbl_nombre_foto.configure(text=f"✅ {os.path.basename(file_path)}")

    def pantalla_nuevo_producto(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.ruta_foto_seleccionada = ""
        
        ctk.CTkButton(self.main_frame, text="⬅️ Volver", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.cargar_inventario).pack(anchor="w", pady=15)
        ctk.CTkLabel(self.main_frame, text="➕ Nuevo Producto", font=ctk.CTkFont(size=22, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.main_frame, text="Nombre:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_nombre = ctk.CTkEntry(self.main_frame, width=350, fg_color="#2d2d2d", text_color="white")
        self.ent_nombre.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Categoría:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.menu_categoria = ctk.CTkOptionMenu(self.main_frame, values=self.obtener_categorias(), width=350, fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER)
        self.menu_categoria.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Código de Barras:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_codigo = ctk.CTkEntry(self.main_frame, width=350, fg_color="#2d2d2d", text_color="white")
        self.ent_codigo.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Precio Costo:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_costo = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_costo.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Precio Venta:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_venta = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_venta.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Precio Oferta (Opcional):", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_oferta = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_oferta.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.main_frame, text="Stock:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_stock = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_stock.pack(anchor="w", padx=5, pady=2)
        
        ctk.CTkButton(self.main_frame, text="🖼️ Seleccionar Foto", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.seleccionar_foto).pack(anchor="w", pady=10)
        self.lbl_nombre_foto = ctk.CTkLabel(self.main_frame, text="Sin foto", text_color=COLOR_TEXTO_SECUNDARIO)
        self.lbl_nombre_foto.pack(anchor="w")
        
        ctk.CTkButton(self.main_frame, text="Guardar Producto", fg_color=COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=self.guardar_producto).pack(anchor="w", pady=20)

    def guardar_producto(self):
        data = {
            "Nombre": self.ent_nombre.get(), 
            "Categoria": self.menu_categoria.get(), 
            "Codigo_de_Barras": self.ent_codigo.get(),
            "Precio_Costo": self.ent_costo.get(),
            "Precio_Venta": self.ent_venta.get(), 
            "Precio_Oferta": self.ent_oferta.get() or "0", 
            "Stock": self.ent_stock.get()
        }
        if self.ruta_foto_seleccionada:
            with open(self.ruta_foto_seleccionada, 'rb') as f:
                requests.post(f'{POCKETBASE_URL}/api/collections/productos/records', data=data, files={'Foto': f})
        else:
            requests.post(f'{POCKETBASE_URL}/api/collections/productos/records', json=data)
        self.cargar_inventario()

    def pantalla_editar_producto(self, producto):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.ruta_foto_seleccionada = ""
        record_id = producto.get('id')
        
        ctk.CTkButton(self.main_frame, text="⬅️ Volver", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.cargar_inventario).pack(anchor="w", pady=15)
        ctk.CTkLabel(self.main_frame, text=f"✏️ Editar: {producto.get('Nombre', '')}", font=ctk.CTkFont(size=22, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.main_frame, text="Nombre:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_nombre = ctk.CTkEntry(self.main_frame, width=350, fg_color="#2d2d2d", text_color="white")
        self.ent_nombre.pack(anchor="w", padx=5, pady=2)
        self.ent_nombre.insert(0, str(producto.get('Nombre', '')))
        
        ctk.CTkLabel(self.main_frame, text="Categoría:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.menu_categoria = ctk.CTkOptionMenu(self.main_frame, values=self.obtener_categorias(), width=350, fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER)
        self.menu_categoria.pack(anchor="w", padx=5, pady=2)
        cat_actual = producto.get('Categoria', '')
        if cat_actual in self.menu_categoria.cget("values"):
            self.menu_categoria.set(cat_actual)
        
        ctk.CTkLabel(self.main_frame, text="Código de Barras:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_codigo = ctk.CTkEntry(self.main_frame, width=350, fg_color="#2d2d2d", text_color="white")
        self.ent_codigo.pack(anchor="w", padx=5, pady=2)
        self.ent_codigo.insert(0, str(producto.get('Codigo_de_Barras', '')))
        
        ctk.CTkLabel(self.main_frame, text="Precio Costo:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_costo = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_costo.pack(anchor="w", padx=5, pady=2)
        self.ent_costo.insert(0, str(producto.get('Precio_Costo', '')))
        
        ctk.CTkLabel(self.main_frame, text="Precio Venta:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_venta = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_venta.pack(anchor="w", padx=5, pady=2)
        self.ent_venta.insert(0, str(producto.get('Precio_Venta', '')))

        ctk.CTkLabel(self.main_frame, text="Precio Oferta (Opcional):", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_oferta = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_oferta.pack(anchor="w", padx=5, pady=2)
        self.ent_oferta.insert(0, str(producto.get('Precio_Oferta', '0')))
        
        ctk.CTkLabel(self.main_frame, text="Stock:", font=ctk.CTkFont(size=14), text_color=COLOR_TEXTO).pack(anchor="w", padx=5, pady=2)
        self.ent_stock = ctk.CTkEntry(self.main_frame, width=180, fg_color="#2d2d2d", text_color="white")
        self.ent_stock.pack(anchor="w", padx=5, pady=2)
        self.ent_stock.insert(0, str(producto.get('Stock', '')))
        
        ctk.CTkButton(self.main_frame, text="🖼️ Cambiar Foto", fg_color="#3a3a3a", hover_color=COLOR_PRINCIPAL, command=self.seleccionar_foto).pack(anchor="w", pady=10)
        self.lbl_nombre_foto = ctk.CTkLabel(self.main_frame, text="Dejar en blanco para mantener la actual", text_color=COLOR_TEXTO_SECUNDARIO)
        self.lbl_nombre_foto.pack(anchor="w")
        
        ctk.CTkButton(self.main_frame, text="💾 Actualizar Producto", fg_color=COLOR_PRINCIPAL, hover_color=COLOR_PRINCIPAL_HOVER, command=lambda: self.actualizar_producto_db(record_id)).pack(anchor="w", pady=20)

    def actualizar_producto_db(self, record_id):
        data = {
            "Nombre": self.ent_nombre.get(),
            "Categoria": self.menu_categoria.get(),
            "Codigo_de_Barras": self.ent_codigo.get(),
            "Precio_Costo": self.ent_costo.get(),
            "Precio_Venta": self.ent_venta.get(),
            "Precio_Oferta": self.ent_oferta.get() or "0",
            "Stock": self.ent_stock.get()
        }
        url_api = f'{POCKETBASE_URL}/api/collections/productos/records/{record_id}'
        if self.ruta_foto_seleccionada:
            with open(self.ruta_foto_seleccionada, 'rb') as f:
                requests.patch(url_api, data=data, files={'Foto': f})
        else:
            requests.patch(url_api, data=data)
        self.cargar_inventario()

    # ---------- VENTAS ----------
    def pantalla_ventas(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.tipo_venta_var.set("Local")
        
        main_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(main_container, text="🛒 Punto de Venta", font=ctk.CTkFont(size=26, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        top_row = ctk.CTkFrame(main_container, fg_color="#2d2d2d", corner_radius=10)
        top_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)
        
        tipo_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        tipo_frame.grid(row=0, column=0, sticky="w", padx=20, pady=12)
        ctk.CTkLabel(tipo_frame, text="Tipo de Venta:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(0, 10))
        self.menu_tipo_venta = ctk.CTkOptionMenu(
            tipo_frame, values=["Local", "Domicilio"], width=200,
            fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER,
            variable=self.tipo_venta_var, command=self.cambiar_tipo_venta
        )
        self.menu_tipo_venta.pack(side="left")
        
        cat_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        cat_frame.grid(row=0, column=1, sticky="e", padx=20, pady=12)
        ctk.CTkLabel(cat_frame, text="Categoría:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(0, 10))
        
        lista_cats = ["Todas"] + self.obtener_categorias()
        self.menu_filtro_ventas = ctk.CTkOptionMenu(
            cat_frame,
            values=lista_cats,
            width=200,
            fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER,
            command=self.cambiar_filtro_ventas
        )
        self.menu_filtro_ventas.pack(side="left")
        self.menu_filtro_ventas.set(self.categoria_filtro_ventas)
        
        self.frame_datos_domicilio = ctk.CTkFrame(main_container, fg_color="#1e1e1e", corner_radius=10)
        
        seleccion_frame = ctk.CTkFrame(main_container, fg_color="#2d2d2d", corner_radius=10)
        seleccion_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        producto_frame = ctk.CTkFrame(seleccion_frame, fg_color="transparent")
        producto_frame.pack(padx=20, pady=12, fill="x")
        
        ctk.CTkLabel(producto_frame, text="📦 Producto:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(0, 10))
        
        try:
            resp = requests.get(f'{POCKETBASE_URL}/api/collections/productos/records?perPage=100')
            if resp.status_code == 200:
                self.lista_productos_raw = resp.json().get('items', [])
        except:
            self.lista_productos_raw = []
        
        self.menu_productos = ctk.CTkOptionMenu(producto_frame, width=250, values=["Cargando..."], fg_color="#3a3a3a", button_color=COLOR_PRINCIPAL, button_hover_color=COLOR_PRINCIPAL_HOVER)
        self.menu_productos.pack(side="left", padx=5)
        
        ctk.CTkButton(
            producto_frame,
            text="➕ Añadir",
            width=100,
            fg_color=COLOR_PRINCIPAL,
            hover_color=COLOR_PRINCIPAL_HOVER,
            command=self.agregar_al_carrito
        ).pack(side="left", padx=10)
        
        self.actualizar_productos_ventas()
        
        carrito_frame = ctk.CTkFrame(main_container, fg_color="#1e1e1e", corner_radius=12, border_width=1, border_color="#444444")
        carrito_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=10)
        carrito_frame.grid_rowconfigure(0, weight=1)
        carrito_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(carrito_frame, text="🛒 Carrito de Compra", font=ctk.CTkFont(size=18, weight="bold", family="Segoe UI"), text_color=COLOR_PRINCIPAL).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.frame_carrito = ctk.CTkScrollableFrame(carrito_frame, height=220, fg_color="transparent")
        self.frame_carrito.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        carrito_frame.grid_rowconfigure(1, weight=1)
        carrito_frame.grid_columnconfigure(0, weight=1)
        
        total_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        total_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.lbl_total = ctk.CTkLabel(
            total_frame,
            text="💰 Total: $0.00",
            font=ctk.CTkFont(size=30, weight="bold", family="Segoe UI"),
            text_color=COLOR_PRINCIPAL
        )
        self.lbl_total.pack(anchor="center", pady=10)
        
        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Finalizar Venta",
            width=200,
            height=45,
            fg_color=COLOR_PRINCIPAL,
            hover_color=COLOR_PRINCIPAL_HOVER,
            command=self.procesar_venta
        ).pack(side="left", padx=20, expand=True)
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ Vaciar Carrito",
            width=200,
            height=45,
            fg_color="#a83232",
            hover_color="#7a1f1f",
            command=self.vaciar_carrito
        ).pack(side="right", padx=20, expand=True)
        
        self.actualizar_vista_carrito()
        main_container.grid_rowconfigure(3, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)

    def cambiar_filtro_ventas(self, categoria):
        self.categoria_filtro_ventas = categoria
        self.actualizar_productos_ventas()

    def actualizar_productos_ventas(self):
        if not self.lista_productos_raw:
            self.menu_productos.configure(values=["Sin productos"])
            self.menu_productos.set("Sin productos")
            return
        
        if self.categoria_filtro_ventas == "Todas":
            filtrados = self.lista_productos_raw
        else:
            filtrados = [
                p for p in self.lista_productos_raw
                if (p.get('Categoria') or p.get('categoria') or "").strip().lower() == self.categoria_filtro_ventas.strip().lower()
            ]
        
        nombres = [p.get('Nombre', '') for p in filtrados if p.get('Nombre')]
        if nombres:
            self.menu_productos.configure(values=nombres)
            self.menu_productos.set(nombres[0])
        else:
            self.menu_productos.configure(values=["Sin productos en esta categoría"])
            self.menu_productos.set("Sin productos en esta categoría")

    def vaciar_carrito(self):
        if self.carrito:
            if messagebox.askyesno("Confirmar", "¿Seguro que quieres vaciar el carrito?"):
                self.carrito = []
                self.actualizar_vista_carrito()
        else:
            messagebox.showinfo("Carrito vacío", "No hay productos en el carrito.")

    def cambiar_tipo_venta(self, tipo):
        if tipo == "Domicilio":
            self.frame_datos_domicilio.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 10))
            if not self.frame_datos_domicilio.winfo_children():
                ctk.CTkLabel(self.frame_datos_domicilio, text="Datos del Domicilio", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_PRINCIPAL).pack(anchor="w", padx=20, pady=(15, 5))
                ctk.CTkLabel(self.frame_datos_domicilio, text="Nombre del Cliente:", text_color=COLOR_TEXTO).pack(anchor="w", padx=20, pady=2)
                self.ent_venta_cliente = ctk.CTkEntry(self.frame_datos_domicilio, width=400, fg_color="#2d2d2d", text_color="white")
                self.ent_venta_cliente.pack(anchor="w", padx=20, pady=2)
                ctk.CTkLabel(self.frame_datos_domicilio, text="Dirección:", text_color=COLOR_TEXTO).pack(anchor="w", padx=20, pady=2)
                self.ent_venta_dir = ctk.CTkEntry(self.frame_datos_domicilio, width=500, fg_color="#2d2d2d", text_color="white")
                self.ent_venta_dir.pack(anchor="w", padx=20, pady=2)
                ctk.CTkLabel(self.frame_datos_domicilio, text="Teléfono:", text_color=COLOR_TEXTO).pack(anchor="w", padx=20, pady=2)
                self.ent_venta_tel = ctk.CTkEntry(self.frame_datos_domicilio, width=250, fg_color="#2d2d2d", text_color="white")
                self.ent_venta_tel.pack(anchor="w", padx=20, pady=2)
                ctk.CTkLabel(self.frame_datos_domicilio, text="Detalles de Entrega (Opcional):", text_color=COLOR_TEXTO).pack(anchor="w", padx=20, pady=2)
                self.ent_venta_detalles = ctk.CTkEntry(self.frame_datos_domicilio, width=500, fg_color="#2d2d2d", text_color="white", placeholder_text="Ej: Tocar timbre, portón azul...")
                self.ent_venta_detalles.pack(anchor="w", padx=20, pady=(2, 15))
        else:
            self.frame_datos_domicilio.grid_forget()

    def agregar_al_carrito(self):
        nombre_sel = self.menu_productos.get()
        prod = next((p for p in self.lista_productos_raw if p.get('Nombre') == nombre_sel), None)
        if prod:
            item = prod.copy()
            item['carrito_id'] = str(uuid.uuid4())
            self.carrito.append(item)
            self.actualizar_vista_carrito()
        else:
            messagebox.showwarning("Aviso", "Selecciona un producto válido.")

    def actualizar_vista_carrito(self):
        for widget in self.frame_carrito.winfo_children(): widget.destroy()
        total = 0
        if not self.carrito:
            ctk.CTkLabel(self.frame_carrito, text="El carrito está vacío", text_color=COLOR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=15)).pack(pady=40)
        else:
            for item in self.carrito:
                row = ctk.CTkFrame(self.frame_carrito, fg_color="transparent")
                row.pack(fill="x", pady=6)
                
                v_venta = float(item.get('Precio_Venta', 0))
                v_oferta = float(item.get('Precio_Oferta', 0))
                precio = v_oferta if (v_oferta > 0 and v_oferta < v_venta) else v_venta
                total += precio
                
                ctk.CTkLabel(row, text=f"📦 {item.get('Nombre')}", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=10)
                ctk.CTkLabel(row, text=f"${precio:.2f}", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_PRINCIPAL).pack(side="left", padx=10)
                ctk.CTkButton(
                    row, text="✕", width=30, height=30, fg_color="#a83232", hover_color="#7a1f1f",
                    command=lambda id=item['carrito_id']: self.eliminar_del_carrito(id)
                ).pack(side="right", padx=10)
        
        self.lbl_total.configure(text=f"💰 Total: ${total:.2f}")

    def eliminar_del_carrito(self, carrito_id):
        self.carrito = [p for p in self.carrito if p['carrito_id'] != carrito_id]
        self.actualizar_vista_carrito()

    def procesar_venta(self):
        if not self.carrito: 
            messagebox.showwarning("Aviso", "El carrito está vacío")
            return
        
        tipo_venta = self.tipo_venta_var.get()
        
        if tipo_venta == "Domicilio":
            cliente = self.ent_venta_cliente.get().strip() if hasattr(self, 'ent_venta_cliente') and self.ent_venta_cliente else ""
            direccion = self.ent_venta_dir.get().strip() if hasattr(self, 'ent_venta_dir') and self.ent_venta_dir else ""
            
            if not cliente or not direccion:
                messagebox.showwarning("Aviso", "Para ventas a domicilio debes ingresar al menos el nombre del cliente y la dirección.")
                return
        
        try:
            total_venta = 0
            nombres_productos = []
            for p in self.carrito:
                v_venta = float(p.get('Precio_Venta', 0))
                v_oferta = float(p.get('Precio_Oferta', 0))
                precio = v_oferta if (v_oferta > 0 and v_oferta < v_venta) else v_venta
                total_venta += precio
                nombres_productos.append(p.get('Nombre', 'Producto'))

                stock_actual = int(p.get('Stock', 0))
                nuevo_stock = max(0, stock_actual - 1)
                requests.patch(f'{POCKETBASE_URL}/api/collections/productos/records/{p["id"]}', json={"Stock": nuevo_stock})
            
            fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            venta_data = {
                "productos_json": ", ".join(nombres_productos),
                "total": total_venta,
                "fecha": fecha_hora_actual,
                "Tipo": tipo_venta
            }
            
            resp = requests.post(f'{POCKETBASE_URL}/api/collections/Ventas/records', json=venta_data)
            if resp.status_code != 200:
                print("Error al guardar venta:", resp.text)

            if tipo_venta == "Domicilio":
                detalles_usuario = self.ent_venta_detalles.get().strip() if hasattr(self, 'ent_venta_detalles') and self.ent_venta_detalles else ""
                texto_detalles_final = f"Productos: {', '.join(nombres_productos)}"
                if detalles_usuario:
                    texto_detalles_final += f" | Notas: {detalles_usuario}"

                domicilio_data = {
                    "Cliente_Nombre": self.ent_venta_cliente.get() if hasattr(self, 'ent_venta_cliente') else "",
                    "Direccion_Entrega": self.ent_venta_dir.get() if hasattr(self, 'ent_venta_dir') else "",
                    "Telefono": self.ent_venta_tel.get() if hasattr(self, 'ent_venta_tel') else "",
                    "Detalles": texto_detalles_final,
                    "Estado": "Pendiente"
                }
                requests.post(f'{POCKETBASE_URL}/api/collections/domicilios/records', json=domicilio_data)
                
            messagebox.showinfo("Éxito", f"Venta ({tipo_venta}) procesada correctamente y registrada.")
            self.carrito = []
            self.pantalla_ventas()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar la venta: {e}")

    # ---------- REPORTES CON EXPORTACIÓN A PDF ----------
    def pantalla_reportes(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        
        top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text="📊 Reporte de Ventas", font=ctk.CTkFont(size=26, weight="bold", family="Segoe UI"), text_color=COLOR_REPORTES).pack(side="left")
        
        # Botón para exportar PDF
        ctk.CTkButton(
            top_bar,
            text="📄 Exportar PDF",
            width=140,
            height=35,
            fg_color=COLOR_REPORTES,
            hover_color=COLOR_REPORTES_HOVER,
            command=self.exportar_pdf
        ).pack(side="right", padx=10, pady=5)
        
        filtros_frame = ctk.CTkFrame(self.main_frame, fg_color="#2d2d2d", corner_radius=10)
        filtros_frame.pack(fill="x", pady=15, padx=5)
        
        fecha_frame = ctk.CTkFrame(filtros_frame, fg_color="transparent")
        fecha_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(fecha_frame, text="📅 Fecha desde:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(0, 10))
        self.entry_fecha_desde = ctk.CTkEntry(fecha_frame, width=150, fg_color="#1a1a1a", text_color="white", placeholder_text="YYYY-MM-DD")
        self.entry_fecha_desde.pack(side="left", padx=5)
        if self.filtro_fecha_desde:
            self.entry_fecha_desde.insert(0, self.filtro_fecha_desde)
        
        ctk.CTkLabel(fecha_frame, text="hasta:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(10, 10))
        self.entry_fecha_hasta = ctk.CTkEntry(fecha_frame, width=150, fg_color="#1a1a1a", text_color="white", placeholder_text="YYYY-MM-DD")
        self.entry_fecha_hasta.pack(side="left", padx=5)
        if self.filtro_fecha_hasta:
            self.entry_fecha_hasta.insert(0, self.filtro_fecha_hasta)
        
        ctk.CTkButton(
            fecha_frame,
            text="Aplicar filtros",
            width=130,
            height=35,
            fg_color=COLOR_REPORTES,
            hover_color=COLOR_REPORTES_HOVER,
            command=self.aplicar_filtros_reportes
        ).pack(side="left", padx=(20, 0))
        
        estado_frame = ctk.CTkFrame(filtros_frame, fg_color="transparent")
        estado_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(estado_frame, text="Filtrar por tipo de venta:", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO).pack(side="left", padx=(0, 10))
        
        opciones_tipo = ["Todos", "Local", "Domicilio"]
        self.menu_filtro_tipo = ctk.CTkOptionMenu(
            estado_frame,
            values=opciones_tipo,
            width=150,
            fg_color="#3a3a3a", button_color=COLOR_REPORTES, button_hover_color=COLOR_REPORTES_HOVER,
            command=self.aplicar_filtros_reportes
        )
        self.menu_filtro_tipo.pack(side="left")
        self.menu_filtro_tipo.set(self.filtro_tipo_venta)
        
        ctk.CTkButton(
            estado_frame,
            text="🔄 Limpiar filtros",
            width=130,
            height=35,
            fg_color="#a83232",
            hover_color="#7a1f1f",
            command=self.limpiar_filtros_reportes
        ).pack(side="left", padx=(20, 0))
        
        self.reportes_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", height=480)
        self.reportes_frame.pack(fill="both", expand=True, pady=10, padx=5)
        
        self.pintar_reportes()

    def pintar_reportes(self):
        for widget in self.reportes_frame.winfo_children():
            widget.destroy()
        
        try:
            response = requests.get(f'{POCKETBASE_URL}/api/collections/Ventas/records?sort=-created&perPage=200', timeout=5)
            items = response.json().get("items", []) if response.status_code == 200 else []
            
            if not items:
                ctk.CTkLabel(self.reportes_frame, text="No hay ventas registradas.", font=ctk.CTkFont(size=15), text_color=COLOR_TEXTO_SECUNDARIO).pack(pady=40)
                return
            
            fecha_desde = self.filtro_fecha_desde
            fecha_hasta = self.filtro_fecha_hasta
            if fecha_desde or fecha_hasta:
                items_filtrados = []
                for v in items:
                    fecha_venta = v.get('fecha', '')
                    fecha_venta_solo = fecha_venta[:10] if len(fecha_venta) >= 10 else ""
                    if fecha_desde and fecha_venta_solo < fecha_desde:
                        continue
                    if fecha_hasta and fecha_venta_solo > fecha_hasta:
                        continue
                    items_filtrados.append(v)
                items = items_filtrados
            
            tipo_filtro = self.filtro_tipo_venta
            if tipo_filtro != "Todos":
                items = [v for v in items if (v.get('Tipo') or v.get('tipo') or 'Local') == tipo_filtro]
            
            if not items:
                ctk.CTkLabel(self.reportes_frame, text="No hay ventas que coincidan con los filtros.", font=ctk.CTkFont(size=15), text_color=COLOR_TEXTO_SECUNDARIO).pack(pady=40)
                return
            
            total_ventas = sum(float(item.get('total', 0)) for item in items)
            ganancia_total = 0.0
            for v in items:
                ganancia_total += self.calcular_ganancia_venta(v)
            
            resumen_frame = ctk.CTkFrame(self.reportes_frame, fg_color=COLOR_TARJETA, corner_radius=12)
            resumen_frame.pack(fill="x", pady=15, padx=5)
            
            ctk.CTkLabel(resumen_frame, text=f"💰 Total Acumulado en Ventas: ${total_ventas:.2f}", font=ctk.CTkFont(size=18, weight="bold", family="Segoe UI"), text_color=COLOR_REPORTES).pack(padx=20, pady=(15, 5), anchor="w")
            ctk.CTkLabel(resumen_frame, text=f"📈 Ganancia Total: ${ganancia_total:.2f}", font=ctk.CTkFont(size=18, weight="bold", family="Segoe UI"), text_color="#f1c40f").pack(padx=20, pady=(5, 15), anchor="w")
            
            for venta in items:
                fecha = venta.get('fecha', 'Fecha desconocida')
                productos = venta.get('productos_json', 'Sin productos')
                total = float(venta.get('total', 0))
                ganancia = self.calcular_ganancia_venta(venta)
                tipo = venta.get('Tipo') or venta.get('tipo') or 'Local'
                icono_tipo = "🛵 Domicilio" if tipo == "Domicilio" else "🏢 Local"
                color_tipo = "#e67e22" if tipo == "Domicilio" else "#3498db"
                
                card = ctk.CTkFrame(self.reportes_frame, fg_color=COLOR_TARJETA, corner_radius=12, border_width=1, border_color="#444444")
                card.pack(fill="x", pady=8, padx=2)
                
                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)
                
                fila_superior = ctk.CTkFrame(info_frame, fg_color="transparent")
                fila_superior.pack(fill="x")
                ctk.CTkLabel(fila_superior, text=f"📅 {fecha}", font=ctk.CTkFont(size=12), text_color="#3498db", anchor="w").pack(side="left")
                ctk.CTkLabel(fila_superior, text=f" | {icono_tipo}", font=ctk.CTkFont(size=12, weight="bold"), text_color=color_tipo, anchor="w").pack(side="left", padx=5)
                
                ctk.CTkLabel(info_frame, text=f"📦 {productos}", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO, anchor="w").pack(fill="x", pady=(5, 0))
                ctk.CTkLabel(info_frame, text=f"📈 Ganancia: ${ganancia:.2f}", font=ctk.CTkFont(size=13), text_color="#f1c40f", anchor="w").pack(fill="x")
                
                right_frame = ctk.CTkFrame(card, fg_color="transparent")
                right_frame.pack(side="right", padx=20, pady=15)
                
                ctk.CTkLabel(right_frame, text=f"${total:.2f}", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_REPORTES).pack(anchor="e")
                
                ctk.CTkButton(
                    right_frame,
                    text="🔍 Detalles",
                    width=110,
                    height=32,
                    fg_color=COLOR_REPORTES,
                    hover_color=COLOR_REPORTES_HOVER,
                    command=lambda v=venta: self.mostrar_detalle_venta(v)
                ).pack(anchor="e", pady=(8, 0))
                
        except Exception as e:
            ctk.CTkLabel(self.reportes_frame, text=f"Error cargando reportes: {e}", text_color="#e74c3c").pack(pady=20)

    # ---------- EXPORTAR A PDF ----------
    def exportar_pdf(self):
        """Genera un PDF con las ventas actuales (filtros aplicados)."""
        try:
            # Obtener los mismos datos que se muestran en la pantalla
            response = requests.get(f'{POCKETBASE_URL}/api/collections/Ventas/records?sort=-created&perPage=200', timeout=5)
            items = response.json().get("items", []) if response.status_code == 200 else []
            
            if not items:
                messagebox.showwarning("Sin datos", "No hay ventas para exportar.")
                return
            
            # Aplicar los mismos filtros
            fecha_desde = self.filtro_fecha_desde
            fecha_hasta = self.filtro_fecha_hasta
            if fecha_desde or fecha_hasta:
                items_filtrados = []
                for v in items:
                    fecha_venta = v.get('fecha', '')
                    fecha_venta_solo = fecha_venta[:10] if len(fecha_venta) >= 10 else ""
                    if fecha_desde and fecha_venta_solo < fecha_desde:
                        continue
                    if fecha_hasta and fecha_venta_solo > fecha_hasta:
                        continue
                    items_filtrados.append(v)
                items = items_filtrados
            
            tipo_filtro = self.filtro_tipo_venta
            if tipo_filtro != "Todos":
                items = [v for v in items if (v.get('Tipo') or v.get('tipo') or 'Local') == tipo_filtro]
            
            if not items:
                messagebox.showwarning("Sin datos", "No hay ventas que coincidan con los filtros actuales.")
                return
            
            # Calcular totales
            total_ventas = sum(float(item.get('total', 0)) for item in items)
            ganancia_total = 0.0
            for v in items:
                ganancia_total += self.calcular_ganancia_venta(v)
            
            # Crear el PDF
            fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            nombre_archivo = f"reporte_ventas_{fecha_hora}.pdf"
            
            # Preguntar al usuario dónde guardar
            archivo = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=nombre_archivo,
                title="Guardar reporte PDF"
            )
            if not archivo:
                return  # Usuario canceló
            
            # Crear el documento
            doc = SimpleDocTemplate(archivo, pagesize=A4)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Title'],
                fontName='Helvetica-Bold',
                fontSize=16,
                alignment=1,  # Centrado
                spaceAfter=12
            )
            subtitle_style = ParagraphStyle(
                'SubtitleStyle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                alignment=1,
                textColor=colors.gray,
                spaceAfter=20
            )
            
            # Contenido del PDF
            elementos = []
            
            # Título
            elementos.append(Paragraph("📊 Reporte de Ventas", title_style))
            elementos.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", subtitle_style))
            
            # Resumen
            resumen_data = [
                ["Total Ventas", f"${total_ventas:.2f}"],
                ["Ganancia Total", f"${ganancia_total:.2f}"],
                ["N° de Ventas", str(len(items))]
            ]
            resumen_tabla = Table(resumen_data, colWidths=[2*inch, 2*inch])
            resumen_tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elementos.append(resumen_tabla)
            elementos.append(Spacer(1, 0.3*inch))
            
            # Tabla de ventas
            data = [["Fecha", "Productos", "Total", "Tipo", "Ganancia"]]
            for v in items:
                fecha = v.get('fecha', '')[:16]  # Cortar para mostrar solo fecha y hora
                productos = v.get('productos_json', '')[:40]  # Limitar longitud
                total = f"${float(v.get('total', 0)):.2f}"
                tipo = v.get('Tipo') or v.get('tipo') or 'Local'
                ganancia = f"${self.calcular_ganancia_venta(v):.2f}"
                data.append([fecha, productos, total, tipo, ganancia])
            
            # Ajustar anchos de columnas
            col_widths = [1.4*inch, 2.5*inch, 1*inch, 1*inch, 1*inch]
            tabla = Table(data, colWidths=col_widths, repeatRows=1)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_REPORTES)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elementos.append(tabla)
            
            # Pie de página
            elementos.append(Spacer(1, 0.5*inch))
            elementos.append(Paragraph("Reporte generado por Tiendita B&B POS", styles['Normal']))
            
            # Construir el PDF
            doc.build(elementos)
            
            messagebox.showinfo("Éxito", f"PDF generado correctamente:\n{archivo}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

    def aplicar_filtros_reportes(self, *args):
        self.filtro_fecha_desde = self.entry_fecha_desde.get().strip()
        self.filtro_fecha_hasta = self.entry_fecha_hasta.get().strip()
        self.filtro_tipo_venta = self.menu_filtro_tipo.get()
        self.pintar_reportes()

    def limpiar_filtros_reportes(self):
        self.entry_fecha_desde.delete(0, "end")
        self.entry_fecha_hasta.delete(0, "end")
        self.menu_filtro_tipo.set("Todos")
        self.filtro_fecha_desde = ""
        self.filtro_fecha_hasta = ""
        self.filtro_tipo_venta = "Todos"
        self.pintar_reportes()

    def mostrar_detalle_venta(self, venta):
        top = ctk.CTkToplevel(self)
        top.title("🔍 Detalle de Venta - Tiendita B&B")
        top.geometry("480x480")
        top.attributes("-topmost", True)
        top.grab_set()

        ctk.CTkLabel(top, text="🔍 Reporte Desglosado", font=ctk.CTkFont(size=20, weight="bold", family="Segoe UI"), text_color=COLOR_REPORTES).pack(pady=(20, 10))
        
        fecha = venta.get('fecha', 'N/A')
        total = float(venta.get('total', 0))
        productos_str = venta.get('productos_json', '')
        tipo = venta.get('Tipo') or venta.get('tipo') or 'Local'
        icono_tipo = "🛵 Domicilio" if tipo == "Domicilio" else "🏢 Local"
        ganancia = self.calcular_ganancia_venta(venta)

        info_box = ctk.CTkFrame(top, fg_color=COLOR_TARJETA, corner_radius=10)
        info_box.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(info_box, text=f"📅 Fecha: {fecha}", font=ctk.CTkFont(size=14), text_color="#3498db").pack(anchor="w", padx=20, pady=(12, 4))
        ctk.CTkLabel(info_box, text=f"🏷️ Tipo: {icono_tipo}", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e67e22" if tipo == "Domicilio" else "#3498db").pack(anchor="w", padx=20, pady=4)
        ctk.CTkLabel(info_box, text=f"💵 Total: ${total:.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_REPORTES).pack(anchor="w", padx=20, pady=4)
        ctk.CTkLabel(info_box, text=f"📈 Ganancia: ${ganancia:.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f1c40f").pack(anchor="w", padx=20, pady=(4, 12))

        ctk.CTkLabel(top, text="Artículos:", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXTO).pack(anchor="w", padx=30, pady=(10, 5))

        lista_box = ctk.CTkScrollableFrame(top, height=150, fg_color="#1a1a1a", corner_radius=8)
        lista_box.pack(fill="both", expand=True, padx=25, pady=5)

        lista_items = [p.strip() for p in productos_str.split(",") if p.strip()]
        for item_nombre in lista_items:
            prod_encontrado = next((p for p in self.lista_productos_raw if (p.get('Nombre') or '').strip().lower() == item_nombre.lower()), None)
            
            if prod_encontrado:
                v_venta = float(prod_encontrado.get('Precio_Venta') or prod_encontrado.get('precio_venta') or 0)
                v_oferta = float(prod_encontrado.get('Precio_Oferta') or prod_encontrado.get('precio_oferta') or 0)
                precio_item = v_oferta if (v_oferta > 0 and v_oferta < v_venta) else v_venta
            else:
                precio_item = 0.0

            fila_item = ctk.CTkFrame(lista_box, fg_color="transparent")
            fila_item.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(fila_item, text=f"• {item_nombre}", font=ctk.CTkFont(size=13), text_color=COLOR_TEXTO).pack(side="left")
            ctk.CTkLabel(fila_item, text=f"${precio_item:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_REPORTES).pack(side="right")

if __name__ == "__main__":
    app = TienditaBbBApp()
    app.mainloop()