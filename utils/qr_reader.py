"""
Motor de lectura/decodificación de QR desde imágenes.
Usa OpenCV como motor principal y pyzbar como motor secundario si está disponible.
"""
import io
import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Optional

# Intentar cargar pyzbar (requiere zbar nativo instalado)
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
except (ImportError, OSError):
    PYZBAR_AVAILABLE = False


def decode_qr_from_bytes(image_bytes: bytes) -> List[Dict]:
    """
    Decodifica uno o múltiples QR desde bytes de imagen.
    Usa OpenCV como motor primario; pyzbar como secundario si está disponible.
    """
    results = []

    # ── Motor 1: OpenCV (siempre disponible) ───────────────────────────────
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        cv_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if cv_img is not None:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

            # Detector nativo de QR de OpenCV
            qr_detector = cv2.QRCodeDetector()
            data, bbox, _ = qr_detector.detectAndDecode(gray)

            if data:
                results.append({
                    "data": data,
                    "type": "QRCODE",
                    "rect": None,
                    "quality": 95,
                })

            # Si no detecta, probar con pre-procesamiento
            if not results:
                for preprocess in [_sharpen, _threshold, _denoise]:
                    try:
                        processed = preprocess(gray)
                        data2, _, _ = qr_detector.detectAndDecode(processed)
                        if data2:
                            results.append({
                                "data": data2,
                                "type": "QRCODE",
                                "rect": None,
                                "quality": 80,
                            })
                            break
                    except Exception:
                        pass
    except Exception:
        pass

    # ── Motor 2: pyzbar (si está disponible - requiere zbar nativo) ─────────
    if PYZBAR_AVAILABLE and not results:
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            decoded = pyzbar.decode(pil_img, symbols=[ZBarSymbol.QRCODE])
            for obj in decoded:
                results.append({
                    "data": obj.data.decode("utf-8", errors="replace"),
                    "type": str(obj.type),
                    "rect": {
                        "left": obj.rect.left, "top": obj.rect.top,
                        "width": obj.rect.width, "height": obj.rect.height
                    },
                    "quality": 100,
                })
        except Exception:
            pass

    return results



def analyze_qr_content(data: str) -> Dict:
    """
    Analiza el contenido decodificado de un QR e identifica su tipo.
    """
    data_lower = data.lower().strip()

    if data_lower.startswith("http://") or data_lower.startswith("https://"):
        return {"type": "URL", "icon": "🔗", "label": "Enlace Web", "content": data}

    elif data_lower.startswith("wifi:"):
        parts = {}
        for part in data[5:].split(";"):
            if ":" in part:
                k, _, v = part.partition(":")
                parts[k.upper()] = v
        return {
            "type": "WIFI",
            "icon": "📶",
            "label": "Red WiFi",
            "content": data,
            "parsed": {
                "ssid": parts.get("S", ""),
                "password": parts.get("P", ""),
                "security": parts.get("T", "WPA"),
            }
        }

    elif data_lower.startswith("begin:vcard"):
        lines = {line.split(":")[0].upper(): ":".join(line.split(":")[1:])
                 for line in data.split("\n") if ":" in line}
        return {
            "type": "VCARD",
            "icon": "👤",
            "label": "Tarjeta de Contacto",
            "content": data,
            "parsed": {
                "name": lines.get("FN", ""),
                "phone": lines.get("TEL", ""),
                "email": lines.get("EMAIL", ""),
                "company": lines.get("ORG", ""),
            }
        }

    elif data_lower.startswith("mailto:") or data_lower.startswith("matmsg:"):
        return {"type": "EMAIL", "icon": "📧", "label": "Email", "content": data}

    elif data_lower.startswith("smsto:") or data_lower.startswith("sms:"):
        return {"type": "SMS", "icon": "💬", "label": "SMS", "content": data}

    elif data_lower.startswith("tel:") or data_lower.startswith("phone:"):
        return {"type": "PHONE", "icon": "📞", "label": "Teléfono", "content": data}

    elif data_lower.startswith("geo:"):
        coords = data[4:].split(",")
        return {
            "type": "GEO",
            "icon": "📍",
            "label": "Ubicación GPS",
            "content": data,
            "parsed": {
                "lat": coords[0] if len(coords) > 0 else "",
                "lon": coords[1].split("?")[0] if len(coords) > 1 else "",
            }
        }

    elif data_lower.startswith("begin:vevent"):
        return {"type": "EVENT", "icon": "📅", "label": "Evento de Calendario", "content": data}

    elif data_lower.startswith("bitcoin:") or data_lower.startswith("ethereum:"):
        coin = data.split(":")[0].upper()
        return {"type": "CRYPTO", "icon": "₿", "label": f"Wallet {coin}", "content": data}

    else:
        return {"type": "TEXT", "icon": "📝", "label": "Texto Plano", "content": data}


def _sharpen(img: np.ndarray) -> np.ndarray:
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    return cv2.filter2D(img, -1, kernel)


def _threshold(img: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )


def _denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(img, h=10)
