"""
Motor de generación de QR avanzado con estilos, colores, logos y múltiples tipos.
"""
import io
import os
import qrcode
import qrcode.constants
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    RoundedModuleDrawer, CircleModuleDrawer,
    SquareModuleDrawer, GappedSquareModuleDrawer,
    HorizontalBarsDrawer, VerticalBarsDrawer
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask, RadialGradiantColorMask,
    SquareGradiantColorMask, HorizontalGradiantColorMask,
    VerticalGradiantColorMask
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional, Tuple
from config import (
    QR_DEFAULT_ERROR_CORRECTION, QR_DEFAULT_BORDER,
    QR_DEFAULT_BOX_SIZE, QR_STYLES, QR_OUTPUT_DIR
)


# Mapeo de nivel de corrección de errores
ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

# Estilos de módulos disponibles
MODULE_DRAWERS = {
    "cuadrado":    SquareModuleDrawer(),
    "redondeado":  RoundedModuleDrawer(),
    "circulo":     CircleModuleDrawer(),
    "barras_h":    HorizontalBarsDrawer(),
    "barras_v":    VerticalBarsDrawer(),
    "gapped":      GappedSquareModuleDrawer(),
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convierte color hex a tupla RGB."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_qr_basic(
    content: str,
    style: str = "clasico",
    module_style: str = "redondeado",
    error_correction: str = QR_DEFAULT_ERROR_CORRECTION,
    box_size: int = QR_DEFAULT_BOX_SIZE,
    border: int = QR_DEFAULT_BORDER,
    logo_path: Optional[str] = None,
    label: Optional[str] = None,
) -> bytes:
    """
    Genera un QR con estilo visual avanzado.
    Retorna bytes de la imagen PNG.
    """
    style_config = QR_STYLES.get(style, QR_STYLES["clasico"])
    fill_color = style_config["fill_color"]
    back_color = style_config["back_color"]

    fill_rgb = _hex_to_rgb(fill_color) if fill_color.startswith("#") else _name_to_rgb(fill_color)
    back_rgb = _hex_to_rgb(back_color) if back_color.startswith("#") else _name_to_rgb(back_color)

    drawer = MODULE_DRAWERS.get(module_style, MODULE_DRAWERS["redondeado"])

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECTION_MAP.get(error_correction, qrcode.constants.ERROR_CORRECT_H),
        box_size=box_size,
        border=border,
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer,
        color_mask=SolidFillColorMask(
            back_color=back_rgb,
            front_color=fill_rgb,
        )
    ).convert("RGBA")

    # Embeber logo si se especifica
    if logo_path and os.path.exists(logo_path):
        img = _embed_logo(img, logo_path)

    # Añadir etiqueta de texto si se especifica
    if label:
        img = _add_label(img, label, fill_rgb)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def generate_qr_gradient(
    content: str,
    color1: str = "#0066CC",
    color2: str = "#00CCFF",
    gradient_type: str = "radial",
    module_style: str = "redondeado",
    error_correction: str = "H",
    box_size: int = 10,
    border: int = 4,
    logo_path: Optional[str] = None,
    label: Optional[str] = None,
) -> bytes:
    """Genera un QR con gradiente de colores."""
    c1 = _hex_to_rgb(color1) if color1.startswith("#") else _name_to_rgb(color1)
    c2 = _hex_to_rgb(color2) if color2.startswith("#") else _name_to_rgb(color2)
    drawer = MODULE_DRAWERS.get(module_style, MODULE_DRAWERS["redondeado"])

    gradient_masks = {
        "radial":     RadialGradiantColorMask(back_color=(255, 255, 255), center_color=c1, edge_color=c2),
        "square":     SquareGradiantColorMask(back_color=(255, 255, 255), center_color=c1, edge_color=c2),
        "horizontal": HorizontalGradiantColorMask(back_color=(255, 255, 255), left_color=c1, right_color=c2),
        "vertical":   VerticalGradiantColorMask(back_color=(255, 255, 255), top_color=c1, bottom_color=c2),
    }
    mask = gradient_masks.get(gradient_type, gradient_masks["radial"])

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECTION_MAP.get(error_correction, qrcode.constants.ERROR_CORRECT_H),
        box_size=box_size,
        border=border,
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer,
        color_mask=mask
    ).convert("RGBA")

    if logo_path and os.path.exists(logo_path):
        img = _embed_logo(img, logo_path)
    if label:
        img = _add_label(img, label, c1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def _embed_logo(qr_img: Image.Image, logo_path: str, logo_ratio: float = 0.25) -> Image.Image:
    """Embebe un logo en el centro del QR."""
    logo = Image.open(logo_path).convert("RGBA")
    qr_w, qr_h = qr_img.size
    logo_size = int(min(qr_w, qr_h) * logo_ratio)

    # Redimensionar logo
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Crear fondo blanco circular para el logo
    bg_size = int(logo_size * 1.2)
    bg = Image.new("RGBA", (bg_size, bg_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(bg)
    draw.ellipse([0, 0, bg_size, bg_size], fill=(255, 255, 255, 255))

    # Centrar logo en el fondo
    logo_x = (bg_size - logo_size) // 2
    logo_y = (bg_size - logo_size) // 2
    bg.paste(logo, (logo_x, logo_y), logo)

    # Pegar en el centro del QR
    pos_x = (qr_w - bg_size) // 2
    pos_y = (qr_h - bg_size) // 2
    qr_img.paste(bg, (pos_x, pos_y), bg)

    return qr_img


def _add_label(img: Image.Image, label: str, color: Tuple = (0, 0, 0)) -> Image.Image:
    """Añade una etiqueta de texto debajo del QR."""
    label = label[:50]  # Limitar longitud
    w, h = img.size
    padding = 20
    font_size = max(16, w // 25)

    # Crear imagen expandida
    new_img = Image.new("RGBA", (w, h + font_size + padding * 2), (255, 255, 255, 255))
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Centrar texto
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (w - text_w) // 2
    text_y = h + padding

    draw.text((text_x, text_y), label, fill=(*color, 255), font=font)
    return new_img


def _name_to_rgb(name: str) -> Tuple[int, int, int]:
    """Convierte nombre de color simple a RGB."""
    colors = {
        "black": (0, 0, 0), "white": (255, 255, 255),
        "red": (204, 0, 0), "blue": (0, 102, 204),
        "green": (0, 102, 51), "yellow": (255, 204, 0),
    }
    return colors.get(name.lower(), (0, 0, 0))


# ── CONTENIDO FORMATEADO POR TIPO ─────────────────────────────────────────────

def format_wifi_content(ssid: str, password: str, security: str = "WPA") -> str:
    return f"WIFI:T:{security};S:{ssid};P:{password};;"


def format_vcard_content(
    name: str, phone: str = "", email: str = "",
    company: str = "", url: str = "", address: str = ""
) -> str:
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"FN:{name}",
        f"N:{name};;;;"
    ]
    if phone:   lines.append(f"TEL:{phone}")
    if email:   lines.append(f"EMAIL:{email}")
    if company: lines.append(f"ORG:{company}")
    if url:     lines.append(f"URL:{url}")
    if address: lines.append(f"ADR:{address}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def format_email_content(to: str, subject: str = "", body: str = "") -> str:
    parts = [f"MATMSG:TO:{to}"]
    if subject: parts.append(f"SUB:{subject}")
    if body:    parts.append(f"BODY:{body}")
    return ";".join(parts) + ";;"


def format_sms_content(phone: str, message: str = "") -> str:
    if message:
        return f"SMSTO:{phone}:{message}"
    return f"SMSTO:{phone}"


def format_geo_content(lat: float, lon: float, label: str = "") -> str:
    base = f"geo:{lat},{lon}"
    if label:
        return f"{base}?q={lat},{lon}({label})"
    return base


def format_event_content(
    summary: str, dtstart: str, dtend: str,
    location: str = "", description: str = ""
) -> str:
    lines = [
        "BEGIN:VEVENT",
        f"SUMMARY:{summary}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
    ]
    if location:    lines.append(f"LOCATION:{location}")
    if description: lines.append(f"DESCRIPTION:{description}")
    lines.append("END:VEVENT")
    return "\n".join(lines)


def format_crypto_content(coin: str, address: str, amount: str = "") -> str:
    base = f"{coin.lower()}:{address}"
    if amount:
        return f"{base}?amount={amount}"
    return base
