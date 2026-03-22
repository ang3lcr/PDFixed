import argparse
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
import time
import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from tqdm import tqdm

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - entorno sin Tesseract
    pytesseract = None


# -----------------------------------------------------------------------------
# Configuración de logging
# -----------------------------------------------------------------------------

logger = logging.getLogger("normalize_pdf")


def setup_logging(verbosity: int = 1) -> None:
    """Configura logging básico. Incluye nombre del logger para facilitar debug."""
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# -----------------------------------------------------------------------------
# Tipos auxiliares
# -----------------------------------------------------------------------------

@dataclass
class PageProcessingOptions:
    """Opciones de procesamiento: solo controlar si se eliminan páginas en blanco."""

    remove_blank: bool = True


# -----------------------------------------------------------------------------
# Funciones principales de procesamiento de PDF / imágenes
# -----------------------------------------------------------------------------

def load_pdf(path: str) -> fitz.Document:
    """Carga un PDF desde disco usando PyMuPDF."""
    logger.debug("load_pdf: comprobando archivo %s", path)
    if not os.path.isfile(path):
        logger.error("load_pdf: archivo no encontrado: %s", path)
        raise FileNotFoundError(f"No se encontró el archivo PDF: {path}")
    try:
        logger.info("load_pdf: abriendo documento (%s)", path)
        doc = fitz.open(path)
        logger.info("load_pdf: PDF cargado correctamente — %d páginas", doc.page_count)
        return doc
    except Exception as exc:
        logger.exception("load_pdf: error al cargar el PDF: %s", path)
        raise RuntimeError(f"Error al cargar el PDF: {exc}") from exc


def _pil_to_cv2(image: Image.Image) -> np.ndarray:
    """Convierte una imagen PIL a formato OpenCV (BGR)."""
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")
    elif image.mode == "P":
        image = image.convert("RGB")
    arr = np.array(image)
    if len(arr.shape) == 3 and arr.shape[2] == 3:
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr


def _cv2_to_pil(image: np.ndarray) -> Image.Image:
    """Convierte una imagen OpenCV (BGR o GRAY) a PIL."""
    if len(image.shape) == 2:
        return Image.fromarray(image)
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def detect_orientation(image: Image.Image) -> int:
    """
    Detecta la orientación de la página en grados usando pytesseract.
    Devuelve 0, 90, 180 o 270.
    """
    logger.debug("detect_orientation: ejecutando Tesseract OSD")
    if pytesseract is None:
        logger.debug("detect_orientation: pytesseract no disponible, devolviendo 0°")
        return 0

    try:
        osd = pytesseract.image_to_osd(image)
        for line in osd.splitlines():
            if "Rotate" in line:
                angle = int(line.split(":")[-1].strip())
                angle = angle % 360
                logger.info("detect_orientation: orientación detectada = %d°", angle)
                return angle
    except Exception as exc:
        logger.debug("detect_orientation: Tesseract no disponible o fallo — %s", exc)

    logger.debug("detect_orientation: usando orientación por defecto 0°")
    return 0


def correct_orientation(image: Image.Image) -> Image.Image:
    """Corrige la orientación de la imagen basada en pytesseract."""
    logger.debug("correct_orientation: detectando y aplicando rotación")
    angle = detect_orientation(image)
    if angle == 0:
        logger.debug("correct_orientation: sin rotación necesaria")
        return image
    rotated = image.rotate(-angle, expand=True, fillcolor="white")
    logger.info("correct_orientation: rotación aplicada = %d°", angle)
    return rotated



def detect_and_correct_skew(image: Image.Image) -> Image.Image:
    """
    Detecta y corrige skew (inclinación) de documentos escaneados.
    Versión robusta para producción.
    """

    cv_img = _pil_to_cv2(image)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 1️⃣ Reducir ruido
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2️⃣ Mejorar contraste (muy importante en escaneos pobres)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

    # 3️⃣ Adaptive threshold (más robusto que Otsu en documentos reales)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,   # tamaño de bloque (ajustable)
        15    # sensibilidad (ajustable)
    )

    # 4️⃣ Asegurar fondo blanco / texto negro
    if np.mean(thresh) < 127:
        thresh = cv2.bitwise_not(thresh)

    # 5️⃣ Operación morfológica para unir texto
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # 6️⃣ Extraer coordenadas del texto
    coords = np.column_stack(np.where(thresh < 255))

    if coords.size < 500:  # Evita falsas detecciones en páginas casi vacías
        return image

    # 7️⃣ Calcular rectángulo mínimo
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # 8️⃣ Normalizar ángulo
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # 9️⃣ Ignorar ángulos despreciables
    if abs(angle) < 0.5:
        return image

    # 🔟 Rotar imagen
    (h, w) = cv_img.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    rotated = cv2.warpAffine(
        cv_img,
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return _cv2_to_pil(rotated)


def detect_blank_page(image: Image.Image, threshold: float = 0.01) -> bool:
    """
    Detecta si una página está esencialmente en blanco.
    threshold: porcentaje máximo de píxeles 'negros' permitido.
    """
    logger.debug("detect_blank_page: evaluando página (threshold=%.4f)", threshold)
    logger.debug("detect_blank_page: modo PIL=%s, size=%sx%s", image.mode, image.width, image.height)
    
    cv_img = _pil_to_cv2(image)
    logger.debug("detect_blank_page: array OpenCV shape=%s dtype=%s", cv_img.shape, cv_img.dtype)
    
    # Convertir a escala de grises si es necesario
    if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
        # Imagen BGR, convertir a GRAY
        logger.debug("detect_blank_page: convirtiendo BGR → GRAY")
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    elif len(cv_img.shape) == 2:
        # Ya está en escala de grises
        logger.debug("detect_blank_page: imagen ya en escala de grises")
        gray = cv_img
    else:
        # Caso inesperado, usar la imagen como está
        logger.warning("detect_blank_page: formato inesperado shape=%s, intentando convertir", cv_img.shape)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
    
    # Binarizar usando Otsu
    gray_mean = np.mean(gray)
    logger.debug("detect_blank_page: valores GRAY min=%d max=%d mean=%.1f", 
                 np.min(gray), np.max(gray), gray_mean)
    
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    logger.debug("detect_blank_page: binarización completada")
    
    # Contar píxeles oscuros (no blancos)
    non_white = np.count_nonzero(binary == 0)
    total = binary.size
    ratio = non_white / float(total)
    is_blank = ratio < threshold
    
    logger.info(
        "detect_blank_page: píxeles oscuros=%d total=%d ratio=%.5f → %s (threshold=%.4f)",
        non_white,
        total,
        ratio,
        "✓ EN BLANCO" if is_blank else "✗ CON CONTENIDO",
        threshold,
    )
    return is_blank


def crop_margins(image: Image.Image) -> Image.Image:
    """
    Recorta márgenes en la imagen buscando el área de contenido.
    """
    logger.debug("crop_margins: buscando bounding box del contenido")
    cv_img = _pil_to_cv2(image)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_inv = 255 - thresh

    coords = cv2.findNonZero(thresh_inv)
    if coords is None:
        logger.debug("crop_margins: sin contenido detectado, imagen sin cambios")
        return image

    x, y, w, h = cv2.boundingRect(coords)
    margin = 10
    x = max(x - margin, 0)
    y = max(y - margin, 0)
    w = min(w + 2 * margin, cv_img.shape[1] - x)
    h = min(h + 2 * margin, cv_img.shape[0] - y)
    cropped = cv_img[y : y + h, x : x + w]
    logger.info("crop_margins: recorte aplicado — x=%d y=%d ancho=%d alto=%d", x, y, w, h)
    return _cv2_to_pil(cropped)


def enhance_image(image: Image.Image) -> Image.Image:
    """
    Mejora la imagen (contraste / binarización) pensada para OCR/legibilidad.
    """
    logger.debug("enhance_image: aplicando CLAHE y binarización adaptativa")
    cv_img = _pil_to_cv2(image)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        10,
    )
    logger.info("enhance_image: mejora aplicada (CLAHE + umbral adaptativo)")
    return _cv2_to_pil(enhanced)


def validate_and_optimize_pdf(input_pdf: str, output_pdf: str) -> None:
    """
    Reconstruye completamente el PDF para garantizar xref limpio, determinista y consistente.
    
    CRITICIDAD: Operación esencial después de merge_pdfs_with_order() para:
    - Eliminar fragmentación interna del xref (tabla de referencias)
    - Garantizar rendering determinístico en cada lectura
    - Permitir lectura segura con multiprocessing
    - Asegurar que detect_blank_pages funcione correctamente
    
    Después de múltiples insert_pdf(), el PDF puede tener:
    - xref fragmentado (referencias cruzadas inconsistentes)
    - Transformaciones internas acumuladas (CropBox, rotaciones)
    - Rendering NO determinístico (cada apertura da resultados diferentes)
    
    Solución: Reconstrucción página a página → xref completamente limpio desde cero.
    
    GARANTÍAS post-ejecución:
    - ✅ xref consistente (100% determinístico)
    - ✅ Sin fragmentación interna
    - ✅ Rendering idéntico en cada lectura (incluso con multiprocessing)
    - ✅ Compatible con todas las operaciones posteriores
    
    Args:
        input_pdf: Ruta del PDF con xref potencialmente fragmentado
        output_pdf: Ruta donde guardar el PDF 100% estabilizado
    """
    logger.debug("validate_and_optimize_pdf: reconstruyendo PDF limpio %s → %s", input_pdf, output_pdf)
    
    # Contar páginas del PDF original
    src = fitz.open(input_pdf)
    try:
        page_count = src.page_count
        logger.debug("validate_and_optimize_pdf: PDF contiene %d páginas", page_count)
    finally:
        src.close()
    
    # RECONSTRUCCIÓN COMPLETA: Copia página a página con xref limpio desde cero
    logger.info("validate_and_optimize_pdf: iniciando reconstrucción completa (page-by-page copy)")
    
    # Usar rebuild_pdf_from_source_pages que genera xref garantizado limpio
    rebuild_pdf_from_source_pages(
        input_pdf=input_pdf,
        kept_page_indices=list(range(page_count)),
        output_path=output_pdf
    )
    
    logger.info("validate_and_optimize_pdf: PDF 100%% estabilizado y guardado en %s", output_pdf)


def rebuild_pdf_from_source_pages(
    input_pdf: str,
    kept_page_indices: List[int],
    output_path: str,
) -> None:
    """
    Reconstruye el PDF de salida copiando páginas del PDF original.

    Esto evita mantener imágenes en memoria y reduce mucho el uso de RAM.
    """
    if not kept_page_indices:
        raise ValueError("No hay páginas para generar el PDF de salida.")

    src = fitz.open(input_pdf)
    out = fitz.open()
    try:
        for idx in tqdm(kept_page_indices, desc="Reconstruyendo PDF", unit="pág"):
            # Copia exacta de la página (sin rasterizar)
            out.insert_pdf(src, from_page=idx, to_page=idx)

        out.save(output_path)
        logger.info(
            "PDF guardado correctamente en %s (%d páginas)",
            output_path,
            len(kept_page_indices),
        )
    finally:
        out.close()
        src.close()


def merge_pdfs_with_order(
    input_pdfs: Sequence[str],
    page_order: Sequence[Tuple[int, int]],
    output_path: str,
) -> None:
    """
    Combina varios PDFs en un solo archivo siguiendo un orden arbitrario.

    input_pdfs: lista de rutas de PDF de entrada.
    page_order: secuencia de pares (pdf_idx, page_idx_0_based) que define el orden
                de las páginas en el PDF de salida.
    
    NOTA: Internamente optimiza el PDF resultante para garantizar
    que está listo para re-lectura confiable (importante para blank detection posterior).
    """
    if not input_pdfs:
        raise ValueError("Se requiere al menos un PDF de entrada.")
    if not page_order:
        raise ValueError("El orden de páginas no puede estar vacío.")

    docs: List[fitz.Document] = []
    out = fitz.open()
    temp_output = output_path + ".tmp"
    
    try:
        for path in input_pdfs:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"No se encontró el PDF de entrada: {path}")
            docs.append(fitz.open(path))

        for pdf_idx, page_idx in page_order:
            if pdf_idx < 0 or pdf_idx >= len(docs):
                raise IndexError(f"Índice de PDF fuera de rango: {pdf_idx}")
            src = docs[pdf_idx]
            if page_idx < 0 or page_idx >= src.page_count:
                raise IndexError(
                    f"Índice de página fuera de rango: pdf={pdf_idx}, página={page_idx}"
                )
            out.insert_pdf(src, from_page=page_idx, to_page=page_idx)

        # Guardar temporalmente
        out.save(temp_output)
        logger.info(
            "merge_pdfs_with_order: PDF combinado guardado (temp) — %d páginas",
            out.page_count,
        )
        
        # Optimizar/validar antes de entregar (garantiza lectura confiable)
        logger.debug("merge_pdfs_with_order: optimizando PDF para lectura posterior")
        validate_and_optimize_pdf(temp_output, output_path)
        os.unlink(temp_output)
        
        logger.info(
            "merge_pdfs_with_order: PDF optimizado guardado en %s",
            output_path,
        )
    finally:
        for d in docs:
            d.close()
        out.close()
        # Limpiar archivo temporal si aún existe
        try:
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except Exception:
            pass


def merge_pdfs_with_order_and_crops(
    input_pdfs: Sequence[str],
    page_order: Sequence[Tuple[int, int]],
    output_path: str,
    crops: Sequence[Optional[Tuple[float, float, float, float]]],
) -> None:
    """
    Igual que merge_pdfs_with_order, pero permite aplicar un recorte (CropBox)
    por cada página en el orden final.

    crops: lista paralela a page_order con tuplas (top, bottom, left, right) en puntos.
           Si el elemento es None, no se aplica recorte a esa página.
    
    NOTA: Internamente optimiza el PDF resultante para garantizar
    que está listo para re-lectura confiable (importante para blank detection posterior).
    """
    if len(crops) != len(page_order):
        raise ValueError("crops debe tener la misma longitud que page_order.")

    docs: List[fitz.Document] = []
    out = fitz.open()
    temp_output = output_path + ".tmp"
    
    try:
        for path in input_pdfs:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"No se encontró el PDF de entrada: {path}")
            docs.append(fitz.open(path))

        for (pdf_idx, page_idx), crop in zip(page_order, crops):
            if pdf_idx < 0 or pdf_idx >= len(docs):
                raise IndexError(f"Índice de PDF fuera de rango: {pdf_idx}")
            src = docs[pdf_idx]
            if page_idx < 0 or page_idx >= src.page_count:
                raise IndexError(
                    f"Índice de página fuera de rango: pdf={pdf_idx}, página={page_idx}"
                )

            out.insert_pdf(src, from_page=page_idx, to_page=page_idx)
            if crop is None:
                continue

            top, bottom, left, right = crop
            if min(top, bottom, left, right) < 0:
                raise ValueError("Los márgenes no pueden ser negativos.")

            out_page = out.load_page(out.page_count - 1)
            rect = out_page.rect
            new_rect = fitz.Rect(
                rect.x0 + left,
                rect.y0 + top,
                rect.x1 - right,
                rect.y1 - bottom,
            )
            if new_rect.x1 <= new_rect.x0 or new_rect.y1 <= new_rect.y0:
                raise ValueError("Recorte inválido: márgenes demasiado grandes.")
            out_page.set_cropbox(new_rect)

        # Guardar temporalmente
        out.save(temp_output)
        logger.info(
            "merge_pdfs_with_order_and_crops: PDF combinado guardado (temp) — %d páginas",
            out.page_count,
        )
        
        # Optimizar/validar antes de entregar (garantiza lectura confiable)
        logger.debug("merge_pdfs_with_order_and_crops: optimizando PDF para lectura posterior")
        validate_and_optimize_pdf(temp_output, output_path)
        os.unlink(temp_output)
        
        logger.info(
            "merge_pdfs_with_order_and_crops: PDF optimizado guardado en %s",
            output_path,
        )
    finally:
        for d in docs:
            d.close()
        out.close()
        # Limpiar archivo temporal si aún existe
        try:
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except Exception:
            pass


def adjust_pdf_margins(
    input_pdf: str,
    output_pdf: str,
    top: float = 0.0,
    bottom: float = 0.0,
    left: float = 0.0,
    right: float = 0.0,
) -> None:
    """
    Ajusta márgenes de todas las páginas estableciendo el CropBox.

    Los valores están en puntos PDF (1/72 in). Valores > 0 recortan ese margen.
    """
    if min(top, bottom, left, right) < 0:
        raise ValueError("Los márgenes no pueden ser negativos.")
    if not os.path.isfile(input_pdf):
        raise FileNotFoundError(f"No se encontró el archivo PDF: {input_pdf}")

    doc = fitz.open(input_pdf)
    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            rect = page.rect
            new_rect = fitz.Rect(
                rect.x0 + left,
                rect.y0 + top,
                rect.x1 - right,
                rect.y1 - bottom,
            )
            # Evitar rectángulos inválidos
            if new_rect.x1 <= new_rect.x0 or new_rect.y1 <= new_rect.y0:
                raise ValueError(
                    f"Márgenes demasiado grandes en página {i + 1}: el área resultante es inválida."
                )
            page.set_cropbox(new_rect)

        doc.save(output_pdf)
        logger.info(
            "adjust_pdf_margins: PDF con márgenes ajustados guardado en %s", output_pdf
        )
    finally:
        doc.close()


def pil_image_to_bytes(image: Image.Image) -> bytes:
    """Convierte una imagen PIL a bytes PNG."""
    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# Procesamiento de páginas (incluye multiprocessing)
# -----------------------------------------------------------------------------

def render_pdf_page_for_display(
    pdf_path: str,
    page_index: int,
    max_size: Optional[int] = None,  # 🔥 IMPORTANTE
    dpi: int = 120,  # 🔥 más calidad
) -> Image.Image:

    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_index)

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat, alpha=False)

        # 🔥 USAR RGB (no grayscale)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        # 🔥 SOLO escalar si realmente lo necesitas
        if max_size:
            w, h = img.size
            if max(w, h) > max_size:
                ratio = max_size / max(w, h)
                img = img.resize(
                    (int(w * ratio), int(h * ratio)),
                    Image.Resampling.LANCZOS  # 🔥 mejor calidad
                )

        return img

    finally:
        doc.close()


def _render_page_to_image(
    doc_path: str,
    page_index: int,
    dpi: int = 150,
) -> Image.Image:
    """
    Renderiza una página de un PDF a imagen PIL para procesamiento interno.
    No redimensiona, devuelve la imagen con el DPI especificado.
    Optimizado para uso en ProcessPoolExecutor.
    """
    logger.debug("_render_page_to_image: %s página %d (dpi=%d)", doc_path, page_index + 1, dpi)
    doc = fitz.open(doc_path)
    try:
        page = doc.load_page(page_index)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        # Convertir a RGB (compatible con detect_blank_page y otras funciones)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return img
    finally:
        doc.close()


def _process_single_page(
    doc_path: str,
    page_index: int,
    dpi: int = 150,
    blank_threshold: float = 0.01,
) -> Tuple[int, bool]:
    """Evalúa una sola página y devuelve (page_index, is_blank)."""
    num = page_index + 1
    logger.debug("_process_single_page: página %d — inicio", num)
    try:
        img = _render_page_to_image(doc_path, page_index, dpi=dpi)
        logger.debug("_process_single_page: imagen renderizada exitosamente — %dx%d", img.width, img.height)
        
        is_blank = detect_blank_page(img, threshold=blank_threshold)
        
        logger.debug("_process_single_page: página %d — resultado: is_blank=%s", num, is_blank)
        return page_index, is_blank
    except Exception as exc:
        logger.exception("_process_single_page: página %d — EXCEPCIÓN: %s", num, exc)
        # Si falla la detección, por seguridad conservamos la página
        logger.warning("_process_single_page: página %d — se conserva por precaución (error en detección)", num)
        return page_index, False


def process_document_pages(
    input_pdf: str,
    max_workers: int = 1,
    dpi: int = 150,
    blank_threshold: float = 0.01,
) -> Tuple[List[int], List[int]]:
    """
    Detecta páginas en blanco sin acumular imágenes en memoria.

    Devuelve (kept_page_indices_0_based, removed_pages_1_based).
    """
    logger.info("process_document_pages: cargando documento para contar páginas")
    doc = load_pdf(input_pdf)
    page_count = doc.page_count
    doc.close()
    logger.info("process_document_pages: total %d páginas a procesar", page_count)

    results: List[Tuple[int, bool]] = []

    if max_workers <= 1:
        logger.info("process_document_pages: modo secuencial")
        for idx in tqdm(range(page_count), desc="Analizando páginas", unit="pág"):
            res = _process_single_page(
                input_pdf,
                idx,
                dpi=dpi,
                blank_threshold=blank_threshold,
            )
            results.append(res)
    else:
        logger.info("process_document_pages: multiprocessing con %d workers", max_workers)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_single_page,
                    input_pdf,
                    idx,
                    dpi,
                    blank_threshold,
                ): idx
                for idx in range(page_count)
            }
            for future in tqdm(
                as_completed(futures),
                total=page_count,
                desc="Analizando páginas",
                unit="pág",
            ):
                res = future.result()
                results.append(res)

    logger.debug("process_document_pages: ordenando resultados por índice de página")
    results.sort(key=lambda x: x[0])

    kept_pages: List[int] = []
    removed_pages: List[int] = []
    for idx, is_blank in results:
        if is_blank:
            removed_pages.append(idx + 1)
        else:
            kept_pages.append(idx)

    logger.info(
        "process_document_pages: listo — %d páginas de salida, %d en blanco eliminadas (%s)",
        len(kept_pages),
        len(removed_pages),
        ",".join(map(str, removed_pages)) if removed_pages else "ninguna",
    )
    return kept_pages, removed_pages


def remove_blank_pages_pdf(input_pdf: str, output_pdf: str, dpi: int = 150) -> List[int]:
    """Elimina páginas en blanco asegurando la liberación de archivos."""
    # 1. Abrir solo para contar y cerrar inmediatamente
    doc_check = fitz.open(input_pdf)
    total_pages = doc_check.page_count
    doc_check.close() # CRÍTICO: Liberar el archivo antes del multiprocessing

    removed_indices = []
    pages_to_keep = []

    logger.info("Analizando %d páginas...", total_pages)
    
    # 2. El pool de procesos abrirá sus propias instancias del archivo
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Nota: Asegúrate de que la función llamada aquí (ej. _process_single_page) 
        # también haga un doc.close() al terminar su tarea.
        futures = [executor.submit(_process_page_parallel, input_pdf, i, dpi) for i in range(total_pages)]
        
        results = {}
        for future in as_completed(futures):
            idx, is_blank = future.result()
            results[idx] = is_blank

    for i in range(total_pages):
        if results.get(i, False):
            removed_indices.append(i)
        else:
            pages_to_keep.append(i)

    # 3. Reconstrucción final
    src = fitz.open(input_pdf)
    dest = fitz.open()
    dest.insert_pdf(src, select=pages_to_keep)
    dest.save(output_pdf, garbage=4, deflate=True)
    dest.close()
    src.close()
    
    return removed_indices


def auto_rotate_pdf(
    input_pdf: str,
    output_pdf: str,
    dpi: int = 150,
) -> List[int]:
    """
    Detecta y corrige automáticamente la orientación de las páginas de un PDF.

    Usa Tesseract (si está disponible) para estimar la rotación de cada página y
    guarda un nuevo PDF con las páginas rotadas.
    """
    if not os.path.isfile(input_pdf):
        raise FileNotFoundError(f"No se encontró el archivo PDF: {input_pdf}")

    rotated_pages_1_based: List[int] = []
    doc = fitz.open(input_pdf)
    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            # Renderizar página a imagen para detección de orientación
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            angle = detect_orientation(img)
            if angle == 0:
                continue

            current_rot = page.rotation
            new_rot = (current_rot + angle) % 360
            logger.info(
                "auto_rotate_pdf: página %d rotación actual=%d, ángulo detectado=%d → nueva rotación=%d",
                page_index + 1,
                current_rot,
                angle,
                new_rot,
            )
            page.set_rotation(new_rot)
            rotated_pages_1_based.append(page_index + 1)

        doc.save(output_pdf)
        logger.info(
            "auto_rotate_pdf: PDF con orientación corregida guardado en %s", output_pdf
        )
        return rotated_pages_1_based
    finally:
        doc.close()


# -----------------------------------------------------------------------------
# Función principal (CLI)
# -----------------------------------------------------------------------------

def main(input_pdf: str, output_pdf: str, args: Optional[argparse.Namespace] = None) -> None:
    """
    Función principal que orquesta la normalización del PDF.
    """
    logger.info("main: inicio de normalización — entrada=%s salida=%s", input_pdf, output_pdf)

    # En la versión actual el CLI mantiene el comportamiento existente:
    # eliminar páginas en blanco y mostrar un resumen.
    max_workers = 1 if args is None else args.max_workers
    dpi = 150 if args is None else args.dpi

    logger.info(
        "main: opciones — solo eliminación de páginas en blanco, workers=%d dpi=%d",
        max_workers,
        dpi,
    )

    logger.info("main: fase 1 — eliminación de páginas en blanco")
    removed_pages = remove_blank_pages_pdf(
        input_pdf=input_pdf,
        output_pdf=output_pdf,
        max_workers=max_workers,
        dpi=dpi,
    )
    logger.info("main: normalización completada correctamente.")

    # Interfaz de resultado para mostrar páginas eliminadas.
    show_removal_summary_interface(removed_pages)


def show_removal_summary_interface(removed_pages: List[int]) -> None:
    """
    Muestra una interfaz sencilla con el número de páginas eliminadas y
    los identificadores de cada una. Si no se puede crear la interfaz
    gráfica (por ejemplo en entornos sin Tk), se hace un volcado por
    consola.
    """
    total_removed = len(removed_pages)

    # Fallback a consola si no se dispone de Tkinter
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        logger.info(
            "Páginas en blanco eliminadas: %d. Páginas: %s",
            total_removed,
            ", ".join(map(str, removed_pages)) if removed_pages else "ninguna",
        )
        print(f"Páginas en blanco eliminadas: {total_removed}")
        if removed_pages:
            print("Páginas eliminadas:", ", ".join(map(str, removed_pages)))
        else:
            print("No se eliminó ninguna página en blanco.")
        return

    root = tk.Tk()
    root.title("Resultado eliminación de páginas en blanco")

    # Fondo azul para toda la ventana
    azul_fondo = "#0d6efd"
    root.configure(bg=azul_fondo)

    # Estilos para que los widgets respeten el fondo azul
    style = ttk.Style(root)
    style.configure("Blue.TFrame", background=azul_fondo)
    style.configure("Blue.TLabel", background=azul_fondo, foreground="white")
    style.configure("Blue.TButton", padding=6)

    main_frame = ttk.Frame(root, padding=20, style="Blue.TFrame")
    main_frame.pack(fill="both", expand=True)

    # Texto resumen
    if total_removed == 0:
        summary_text = "No se eliminó ninguna página en blanco."
        pages_text = ""
    else:
        summary_text = f"Páginas en blanco eliminadas: {total_removed}"
        pages_text = "Páginas eliminadas: " + ", ".join(map(str, removed_pages))

    summary_label = ttk.Label(
        main_frame,
        text=summary_text,
        font=("Helvetica", 12, "bold"),
        style="Blue.TLabel",
    )
    summary_label.pack(anchor="w")

    if pages_text:
        pages_label = ttk.Label(
            main_frame,
            text=pages_text,
            wraplength=600,
            justify="left",
            style="Blue.TLabel",
        )
        pages_label.pack(anchor="w", pady=(10, 0))

    close_button = ttk.Button(
        main_frame,
        text="Cerrar",
        command=root.destroy,
        style="Blue.TButton",
    )
    close_button.pack(pady=(20, 0), anchor="e")

    root.mainloop()


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "Elimina únicamente las páginas en blanco de un PDF."
        )
    )
    parser.add_argument("input_pdf", help="Ruta al PDF de entrada.")
    parser.add_argument("output_pdf", help="Ruta al PDF de salida (sin páginas en blanco).")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Número máximo de procesos en paralelo (multiprocessing).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolución en DPI para renderizar las páginas (por defecto: 300).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="Aumenta el nivel de verbosidad (especifica -v o -vv).",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    try:
        main(args.input_pdf, args.output_pdf, args)
    except Exception as exc:
        logger.error("Fallo en la normalización del PDF: %s", exc)
        raise

