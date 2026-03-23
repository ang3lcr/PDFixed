"""
Interfaz gráfica minimalista para el normalizador de PDFs escaneados.
Permite elegir PDF de entrada, ruta de salida y comparar original vs procesado.
"""

import logging
import os
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional, Tuple

from PIL import Image, ImageTk
from normalize_pdf import validate_and_optimize_pdf

# Logger específico para la GUI
logger = logging.getLogger("normalize_pdf_gui")

# Importar después de configurar log para evitar que normalize_pdf configure root logger
from normalize_pdf import (
    main as normalize_main,
    render_pdf_page_for_display,
    load_pdf,
    setup_logging,
    remove_blank_pages_pdf,
    auto_rotate_pdf,
    merge_pdfs_with_order,
    merge_pdfs_with_order_and_crops,
)

# Tamaño máximo para visualizaciones (en px, calidad mínima para velocidad)
DISPLAY_MAX_SIZE = 400


class SimpleNamespace:
    """Objeto tipo argparse.Namespace para llamar a main() desde la GUI."""

    def __init__(
        self,
        remove_blank=True,
        deskew=True,
        crop_margins=True,
        enhance=True,
        max_workers=1,
        dpi=300,
    ):
        self.remove_blank = remove_blank
        self.deskew = deskew
        self.crop_margins = crop_margins
        self.enhance = enhance
        self.max_workers = max_workers
        self.dpi = dpi


def get_pdf_page_count(pdf_path: str) -> int:
    """Devuelve el número de páginas de un PDF."""
    doc = load_pdf(pdf_path)
    n = doc.page_count
    doc.close()
    return n


class MainWindow:
    """Ventana principal: selección de archivos y botón de procesar."""

    def __init__(self):
        logger.info("Iniciando ventana principal de la GUI.")

        self.root = tk.Tk()
        self.root.title("Procesar PDF")
        self.root.minsize(420, 280)
        self.root.resizable(True, True)

        # Colores y estilos base (tema azul)
        self.primary_bg = "#0d6efd"   # azul principal
        self.primary_fg = "#ffffff"   # texto blanco
        self.secondary_bg = "#0b5ed7" # azul ligeramente más oscuro

        self.root.configure(bg=self.primary_bg)
        self._init_styles()
        self._install_tk_exception_handler()

        # Variables para rutas
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        # Opciones (checkbuttons)
        self.opt_remove_blank = tk.BooleanVar(value=True)
        self.opt_auto_rotate = tk.BooleanVar(value=False)
        self.opt_reorder_insert = tk.BooleanVar(value=False)

        # Configuración para reordenar/insertar
        self.reorder_config: Optional[dict] = None

        # Referencias para ventana de comparación (se habilitan tras procesar)
        self.last_input_pdf: Optional[str] = None
        self.last_output_pdf: Optional[str] = None
        self.compare_btn: Optional[ttk.Button] = None

        # Cache de previsualización (PIL.Image) para miniaturas rápidas
        self._preview_cache: Dict[Tuple[str, int, int], Image.Image] = {}
        self._preload_thread: Optional[threading.Thread] = None
        self._preload_cancel = threading.Event()

        self._build_ui()

    def _install_tk_exception_handler(self):
        """
        Evita que excepciones en callbacks de Tk cierren la app completa.
        Muestra un diálogo y registra el error.
        """

        def _handler(exc, val, tb):
            try:
                import traceback as _traceback

                msg = "".join(_traceback.format_exception(exc, val, tb))
                logger.error("Excepción en callback Tk:\n%s", msg)
                messagebox.showerror(
                    "Error inesperado",
                    f"Ocurrió un error inesperado en la interfaz.\n\n{val}",
                )
            except Exception:
                # Si falla el handler, al menos no reventar aquí
                pass

        # type: ignore[assignment]
        self.root.report_callback_exception = _handler

    def _init_styles(self):
        """Configura estilos ttk para un tema azul sencillo."""
        style = ttk.Style(self.root)

        # Asegurar que usamos un tema basado en Tk (para que los colores se apliquen mejor)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Blue.TFrame",
            background=self.primary_bg,
        )
        style.configure(
            "Blue.TLabelframe",
            background=self.primary_bg,
            foreground=self.primary_fg,
        )
        style.configure(
            "Blue.TLabelframe.Label",
            background=self.primary_bg,
            foreground=self.primary_fg,
        )
        style.configure(
            "Blue.TLabel",
            background=self.primary_bg,
            foreground=self.primary_fg,
        )
        style.configure(
            "Blue.TButton",
            background=self.secondary_bg,
            foreground=self.primary_fg,
            padding=6,
        )
        style.map(
            "Blue.TButton",
            background=[("active", "#0a58ca"), ("disabled", "#6c757d")],
        )
        # Barra de progreso: usamos el estilo por defecto del tema para evitar
        # problemas de layout en algunos entornos de Tk.

    def _build_ui(self):
        # Marco principal con padding
        main = ttk.Frame(self.root, padding=24, style="Blue.TFrame")
        main.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(
            main,
            text="Normalizar PDF escaneado",
            font=("Segoe UI", 14, "bold"),
            style="Blue.TLabel",
        ).pack(pady=(0, 20))

        # PDF de entrada
        f_in = ttk.Frame(main, style="Blue.TFrame")
        f_in.pack(fill=tk.X, pady=6)
        ttk.Label(
            f_in,
            text="PDF a procesar:",
            width=16,
            anchor=tk.W,
            style="Blue.TLabel",
        ).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Entry(f_in, textvariable=self.input_path, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        ttk.Button(
            f_in,
            text="Elegir archivo…",
            command=self._choose_input,
            style="Blue.TButton",
        ).pack(side=tk.RIGHT)

        # Precarga de miniaturas (para reordenar/insertar)
        self.preload_status = ttk.Label(
            main, text="", foreground="white", style="Blue.TLabel"
        )
        self.preload_progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.preload_percent = ttk.Label(
            main, text="", foreground="white", style="Blue.TLabel"
        )
        self.preload_status.pack(pady=(6, 0))
        self.preload_progress.pack(fill=tk.X, pady=(4, 0))
        self.preload_percent.pack(pady=(2, 8))
        self._set_preload_ui(None, 0, 0)

        # Ruta de salida
        f_out = ttk.Frame(main, style="Blue.TFrame")
        f_out.pack(fill=tk.X, pady=6)
        ttk.Label(
            f_out,
            text="Guardar resultado en:",
            width=16,
            anchor=tk.W,
            style="Blue.TLabel",
        ).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Entry(f_out, textvariable=self.output_path, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        ttk.Button(
            f_out,
            text="Elegir carpeta/archivo…",
            command=self._choose_output,
            style="Blue.TButton",
        ).pack(side=tk.RIGHT)

        # Opciones (checkbuttons)
        opts = ttk.LabelFrame(main, text="Opciones", padding=12, style="Blue.TLabelframe")
        opts.pack(fill=tk.X, pady=(16, 6))

        tk.Checkbutton(
            opts,
            text="Eliminar páginas en blanco",
            variable=self.opt_remove_blank,
            bg=self.primary_bg,
            fg=self.primary_fg,
            activebackground=self.primary_bg,
            activeforeground=self.primary_fg,
            selectcolor=self.secondary_bg,
            anchor="w",
        ).pack(fill=tk.X, pady=2)

        tk.Checkbutton(
            opts,
            text="Corregir orientación (auto-rotación)",
            variable=self.opt_auto_rotate,
            bg=self.primary_bg,
            fg=self.primary_fg,
            activebackground=self.primary_bg,
            activeforeground=self.primary_fg,
            selectcolor=self.secondary_bg,
            anchor="w",
        ).pack(fill=tk.X, pady=2)

        reorder_row = ttk.Frame(opts, style="Blue.TFrame")
        reorder_row.pack(fill=tk.X, pady=2)
        tk.Checkbutton(
            reorder_row,
            text="Reordenar / insertar páginas (mezclar PDFs)",
            variable=self.opt_reorder_insert,
            command=self._on_toggle_reorder,
            bg=self.primary_bg,
            fg=self.primary_fg,
            activebackground=self.primary_bg,
            activeforeground=self.primary_fg,
            selectcolor=self.secondary_bg,
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_config_reorder = ttk.Button(
            reorder_row,
            text="Configurar…",
            command=self._open_reorder_window,
            state=tk.DISABLED,
            style="Blue.TButton",
        )
        self.btn_config_reorder.pack(side=tk.RIGHT, padx=(8, 0))

        # Botón procesar + estado (con porcentaje)
        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress_percent = ttk.Label(main, text="", foreground="white", style="Blue.TLabel")
        self.status = ttk.Label(main, text="", foreground="white", style="Blue.TLabel")
        self.status.pack(pady=(8, 0))
        self.progress_percent.pack(pady=(2, 0))

        btn_frame = ttk.Frame(main, style="Blue.TFrame")
        btn_frame.pack(pady=20)
        ttk.Button(
            btn_frame,
            text="Procesar PDF",
            command=self._run_process_selected,
            style="Blue.TButton",
        ).pack(side=tk.LEFT, padx=4)
        self.compare_btn = ttk.Button(
            btn_frame,
            text="Comparar original vs procesado",
            command=self._open_comparison,
            state=tk.DISABLED,
            style="Blue.TButton",
        )
        self.compare_btn.pack(side=tk.LEFT, padx=4)

        # Resumen integrado
        summary_frame = ttk.LabelFrame(
            main, text="Resumen", padding=12, style="Blue.TLabelframe"
        )
        summary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.summary_text = tk.Text(summary_frame, height=8, wrap="word")
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(summary_frame, command=self.summary_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.configure(yscrollcommand=scroll.set)
        self._set_summary("Aún no se ha procesado ningún PDF.")

    def _choose_input(self):
        logger.info("Diálogo para seleccionar PDF de entrada abierto.")
        path = filedialog.askopenfilename(
            title="Seleccionar PDF a procesar",
            filetypes=[("PDF", "*.pdf"), ("Todos los archivos", "*.*")],
        )
        if path:
            logger.info("PDF de entrada seleccionado: %s", path)
            self.input_path.set(path)
            # Sugerir salida en la misma carpeta si está vacío
            if not self.output_path.get().strip():
                base = os.path.splitext(os.path.basename(path))[0]
                folder = os.path.dirname(path)
                self.output_path.set(os.path.join(folder, f"{base}_normalizado.pdf"))

            # Al cargar un PDF, precargar miniaturas para que reordenar sea instantáneo
            self._start_preload_previews(path)

    def _choose_output(self):
        # Permitir elegir archivo de salida directamente
        logger.info("Diálogo para seleccionar ruta de salida abierto.")
        path = filedialog.asksaveasfilename(
            title="Guardar PDF normalizado como",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Todos los archivos", "*.*")],
        )
        if path:
            logger.info("Ruta de salida seleccionada: %s", path)
            self.output_path.set(path)

    def _set_summary(self, text: str):
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, text)
        self.summary_text.configure(state=tk.DISABLED)

    def _set_preload_ui(self, msg: Optional[str], done: int, total: int):
        if not msg:
            self.preload_status.config(text="")
            self.preload_progress["value"] = 0
            self.preload_percent.config(text="")
            return
        self.preload_status.config(text=msg)
        if total <= 0:
            self.preload_progress["value"] = 0
            self.preload_percent.config(text="")
            return
        pct = int((done / total) * 100)
        self.preload_progress["value"] = pct
        self.preload_percent.config(text=f"{pct}% ({done}/{total})")

    def _get_cached_preview(self, pdf_path: str, page_idx: int, max_size: int) -> Optional[Image.Image]:
        return self._preview_cache.get((pdf_path, page_idx, max_size))

    def _cache_preview(self, pdf_path: str, page_idx: int, max_size: int, img: Image.Image):
        self._preview_cache[(pdf_path, page_idx, max_size)] = img

    def _start_preload_previews(self, pdf_path: str, max_size: int = 80):
        # Cancelar precarga anterior si existe
        try:
            self._preload_cancel.set()
        except Exception:
            pass
        self._preload_cancel = threading.Event()

        if not os.path.isfile(pdf_path):
            self._set_preload_ui(None, 0, 0)
            return

        def worker():
            try:
                n = get_pdf_page_count(pdf_path)
                self.root.after(0, self._set_preload_ui, "Precargando miniaturas…", 0, n)
                done = 0
                for i in range(n):
                    if self._preload_cancel.is_set():
                        break
                    key = (pdf_path, i, max_size)
                    if key not in self._preview_cache:
                        img = render_pdf_page_for_display(pdf_path, i, max_size=max_size)
                        self._cache_preview(pdf_path, i, max_size, img)
                    done += 1
                    if i == n - 1 or (i % 2 == 0):
                        self.root.after(0, self._set_preload_ui, "Precargando miniaturas…", done, n)
                if not self._preload_cancel.is_set():
                    self.root.after(0, self._set_preload_ui, "Miniaturas listas.", n, n)
            except Exception as e:
                logger.exception("Error precargando miniaturas: %s", e)
                self.root.after(0, self._set_preload_ui, f"Precarga fallida: {e}", 0, 0)

        t = threading.Thread(target=worker, daemon=True)
        self._preload_thread = t
        t.start()

    def _preload_for_comparison_blocking(
        self, original_pdf: str, processed_pdf: str, max_size: int = 80
    ):
        """
        Precarga (bloqueante) miniaturas para la ventana de comparación.
        Se ejecuta típicamente en un hilo de fondo.
        """
        n1 = get_pdf_page_count(original_pdf)
        n2 = get_pdf_page_count(processed_pdf)
        total = n1 + n2
        done = 0

        def render_all(pdf_path: str, n: int):
            nonlocal done
            for i in range(n):
                key = (pdf_path, i, max_size)
                if key not in self._preview_cache:
                    img = render_pdf_page_for_display(pdf_path, i, max_size=max_size)
                    self._cache_preview(pdf_path, i, max_size, img)
                done += 1
                # Progreso: usamos el tramo final 95-100%
                pct = 95 + int((done / max(1, total)) * 5)
                self.root.after(0, self._set_progress_ui, "Preparando comparación…", pct)

        self.root.after(0, self._set_progress_ui, "Preparando comparación…", 95)
        render_all(original_pdf, n1)
        render_all(processed_pdf, n2)
        self.root.after(0, self._set_progress_ui, "Listo.", 100)

    def _on_toggle_reorder(self):
        enabled = bool(self.opt_reorder_insert.get())
        self.btn_config_reorder.config(state=(tk.NORMAL if enabled else tk.DISABLED))
        if not enabled:
            self.reorder_config = None

    def _run_process_selected(self):
        inp = self.input_path.get().strip()
        out = self.output_path.get().strip()
        if not inp:
            logger.warning("Intento de procesar sin seleccionar PDF de entrada.")
            messagebox.showwarning("Falta archivo", "Elige el PDF a procesar.")
            return
        if not out:
            logger.warning("Intento de procesar sin seleccionar ruta de salida.")
            messagebox.showwarning("Falta destino", "Elige dónde guardar el resultado.")
            return
        if not os.path.isfile(inp):
            logger.error("Archivo de entrada no existe: %s", inp)
            messagebox.showerror("Error", f"No existe el archivo:\n{inp}")
            return

        do_reorder = bool(self.opt_reorder_insert.get())
        do_remove_blank = bool(self.opt_remove_blank.get())
        do_rotate = bool(self.opt_auto_rotate.get())

        if not (do_reorder or do_remove_blank or do_rotate):
            messagebox.showinfo(
                "Sin cambios",
                "No hay opciones seleccionadas. Marca al menos una opción para procesar.",
            )
            return

        if do_reorder and not self.reorder_config:
            messagebox.showwarning(
                "Reordenar / insertar",
                "Marcaste reordenar/insertar pero no lo has configurado. Pulsa “Configurar…”.",
            )
            return

        logger.info(
            "Iniciando procesamiento seleccionado: reorder=%s remove_blank=%s rotate=%s",
            do_reorder,
            do_remove_blank,
            do_rotate,
        )

        self.progress.pack(pady=10, fill=tk.X)
        self.progress["value"] = 0
        self.progress_percent.config(text="0%")
        self.status.config(text="Procesando… (puede tardar unos minutos)", foreground="gray")
        self.compare_btn.config(state=tk.DISABLED)
        self.root.update_idletasks()

        self._pending_input = inp
        self._pending_output = out

        thread = threading.Thread(target=self.run_in_thread, daemon=True)
        thread.start()

    def run_in_thread(self):
            """
            Ejecuta el procesamiento del PDF en un hilo secundario para no congelar la GUI.
            Maneja la cadena de transformaciones: Reordenar -> Eliminar Blancos.
            """
            import tempfile
            import time
            import shutil
            import os

            tmp_files = []
            try:
                # 1. Preparar rutas iniciales
                input_path = self.input_path.get().strip()
                output_path = self.output_path.get().strip()
                current_working_pdf = input_path

                # Validaciones básicas
                if not input_path or not os.path.exists(input_path):
                    raise ValueError("El archivo de entrada no es válido o no existe.")
                if not output_path:
                    raise ValueError("Debes especificar una ruta de salida.")

                # Mostrar progreso inicial en la UI
                self.root.after(0, lambda: self.status.config(text="Iniciando procesamiento...", foreground="blue"))

                # --- FASE 1: REORDENAR / INSERTAR ---
                if self.opt_reorder_insert.get() and hasattr(self, 'reorder_config') and self.reorder_config:
                    self.root.after(0, lambda: self.status.config(text="Fase 1: Reordenando y combinando páginas..."))
                    
                    # Crear archivo temporal para el resultado del reordenado
                    fd, temp_reorder = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    tmp_files.append(temp_reorder)

                    # Ejecutar la unión según la configuración guardada
                    merge_pdfs_with_order(
                        self.reorder_config["input_pdfs"],
                        self.reorder_config["order"],
                        temp_reorder
                    )
                    
                    # El PDF resultante del reordenado es ahora la entrada para el siguiente paso
                    current_working_pdf = temp_reorder
                    
                    # Pausa de estabilización (crucial para Windows y sistemas de archivos lentos)
                    time.sleep(0.4)

                # --- FASE 2: ELIMINACIÓN DE HOJAS EN BLANCO ---
                if self.opt_remove_blank.get():
                    self.root.after(0, lambda: self.status.config(text="Fase 2: Analizando y eliminando hojas en blanco..."))
                    
                    # Crear otro archivo temporal para el resultado de la limpieza
                    fd, temp_blanks = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    tmp_files.append(temp_blanks)

                    # Procesar el PDF (ya sea el original o el reordenado en el paso anterior)
                    # Nota: remove_blank_pages_pdf debe abrir y CERRAR internamente el archivo
                    remove_blank_pages_pdf(current_working_pdf, temp_blanks)
                    
                    current_working_pdf = temp_blanks
                    time.sleep(0.4)

                # --- FASE FINAL: GUARDADO ---
                self.root.after(0, lambda: self.status.config(text="Finalizando y guardando archivo..."))
                
                # Asegurar que el directorio de destino existe
                output_dir = os.path.dirname(os.path.abspath(output_path))
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                # Copiar el último PDF procesado a la ubicación final elegida por el usuario
                shutil.copyfile(current_working_pdf, output_path)

                # Notificar éxito a la UI
                self.root.after(0, self._on_process_success)

            except Exception as e:
                logger.exception("Error durante el procesamiento en hilo")
                # Enviar el error a la UI para mostrarlo en un messagebox
                self.root.after(0, lambda error_msg=str(e): messagebox.showerror("Error de Procesamiento", error_msg))
                self.root.after(0, lambda: self.status.config(text="Error en el proceso", foreground="red"))
            
            finally:
                # Limpieza de todos los archivos temporales creados
                self.root.after(0, lambda: self.status.config(text="Limpiando temporales..."))
                for f in tmp_files:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el temporal {f}: {e}")
            self._pending_input = inp
            self._pending_output = out
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()

    def _set_progress_ui(self, msg: str, pct: int):
        pct = max(0, min(int(pct), 100))
        self.progress["value"] = pct
        self.progress_percent.config(text=f"{pct}%")
        self.status.config(text=msg, foreground="gray")

    def _open_reorder_window(self):
        inp = self.input_path.get().strip()
        if not inp or not os.path.isfile(inp):
            messagebox.showwarning(
                "PDF de entrada",
                "Elige primero un PDF principal en la ventana principal.",
            )
            return
        ReorderWindow(self.root, inp, self)


    def _on_process_ok(
        self,
        error: Optional[str],
        inp: Optional[str] = None,
        out: Optional[str] = None,
        summary: Optional[str] = None,
        compare_ready: bool = False,
    ):
        self.progress.stop()
        self.progress.pack_forget()
        if error:
            logger.error("Procesamiento terminado con error: %s", error)
            self.status.config(text="", foreground="gray")
            messagebox.showerror("Error al procesar", error)
        else:
            logger.info("Procesamiento completado sin errores.")
            self.last_input_pdf = inp or getattr(self, "_pending_input", None)
            self.last_output_pdf = out or getattr(self, "_pending_output", None)
            self.status.config(text="Listo. Puedes comparar el resultado.", foreground="green")
            if summary:
                self._set_summary(summary)
            if self.compare_btn:
                self.compare_btn.config(state=(tk.NORMAL if compare_ready else tk.DISABLED))

    def _open_comparison(self):
        if not self.last_input_pdf or not self.last_output_pdf:
            logger.warning("Se intentó abrir la comparación sin PDFs disponibles.")
            messagebox.showinfo(
                "Comparar",
                "Procesa un PDF primero para habilitar la comparación.",
            )
            return
        if not os.path.isfile(self.last_output_pdf):
            logger.error("No se encuentra el PDF procesado para comparar: %s", self.last_output_pdf)
            messagebox.showerror(
                "Error",
                f"No se encuentra el archivo procesado:\n{self.last_output_pdf}",
            )
            return
        logger.info(
            "Abriendo ventana de comparación. Original=%s, Procesado=%s",
            self.last_input_pdf,
            self.last_output_pdf,
        )
        try:
            ComparisonWindow(
                self,
                self.last_input_pdf,
                self.last_output_pdf,
            )
        except Exception as e:
            logger.exception("Error abriendo ventana de comparación: %s", e)
            messagebox.showerror("Error al comparar", str(e))

    def run(self):
        self.root.mainloop()


class ComparisonWindow:
    """Ventana para comparar original vs procesado página por página."""

    def __init__(self, main_window: MainWindow, original_pdf: str, processed_pdf: str):
        self.main_window = main_window
        self.original_pdf = original_pdf
        self.processed_pdf = processed_pdf
        self.n_original = get_pdf_page_count(original_pdf)
        self.n_processed = get_pdf_page_count(processed_pdf)

        logger.info(
            "Ventana de comparación creada. Original=%s (%d páginas), Procesado=%s (%d páginas)",
            original_pdf,
            self.n_original,
            processed_pdf,
            self.n_processed,
        )

        self.win = tk.Toplevel(main_window.root)
        self.win.title("Comparar: original vs procesado")
        self.win.minsize(900, 620)
        self.win.geometry("1000x650")

        # Aplicar mismo fondo azul que en la ventana principal
        primary_bg = getattr(main_window, "primary_bg", "#0d6efd")
        self.win.configure(bg=primary_bg)

        header = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text=f"Original: {self.n_original} páginas   |   Procesado: {self.n_processed} páginas",
            style="Blue.TLabel",
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.LEFT)

        ctrl = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        ctrl.pack(fill=tk.X)
        self.page_var = tk.IntVar(value=1)
        max_pages = max(self.n_original, self.n_processed, 1)
        ttk.Button(ctrl, text="Anterior", command=self._prev, style="Blue.TButton").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(ctrl, text="Siguiente", command=self._next, style="Blue.TButton").pack(
            side=tk.LEFT, padx=(0, 16)
        )
        ttk.Label(ctrl, text="Página:", style="Blue.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        self.spin = ttk.Spinbox(
            ctrl,
            from_=1,
            to=max_pages,
            width=6,
            textvariable=self.page_var,
            command=self._refresh,
        )
        self.spin.pack(side=tk.LEFT)
        self.spin.bind("<Return>", lambda e: self._refresh())
        self.page_label = ttk.Label(ctrl, text="", style="Blue.TLabel")
        self.page_label.pack(side=tk.LEFT, padx=16)

        container = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(container, text="Original", padding=8, style="Blue.TLabelframe")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = ttk.LabelFrame(container, text="Procesado", padding=8, style="Blue.TLabelframe")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.label_original = ttk.Label(left, text="Cargando…", style="Blue.TLabel")
        self.label_original.pack(fill=tk.BOTH, expand=True)
        self.label_processed = ttk.Label(right, text="Cargando…", style="Blue.TLabel")
        self.label_processed.pack(fill=tk.BOTH, expand=True)

        self._photo_orig: Optional[ImageTk.PhotoImage] = None
        self._photo_proc: Optional[ImageTk.PhotoImage] = None

        self._refresh()

    def _page_index(self) -> int:
        try:
            return max(0, int(self.page_var.get()) - 1)
        except Exception:
            return 0

    def _prev(self):
        i = self._page_index()
        if i <= 0:
            return
        self.page_var.set(i)
        self._refresh()

    def _next(self):
        i = self._page_index()
        max_pages = max(self.n_original, self.n_processed, 1)
        if i >= max_pages - 1:
            return
        self.page_var.set(i + 2)
        self._refresh()

    def _refresh(self):
        idx = self._page_index()
        max_pages = max(self.n_original, self.n_processed, 1)
        if idx >= max_pages:
            idx = max_pages - 1
            self.page_var.set(idx + 1)

        self.page_label.config(text=f"{idx + 1} / {max_pages}")

        # Original
        if idx < self.n_original:
            try:
                img = render_pdf_page_for_display(self.original_pdf, idx, max_size=DISPLAY_MAX_SIZE)
                self._photo_orig = ImageTk.PhotoImage(img)
                self.label_original.config(image=self._photo_orig, text="")
            except Exception as e:
                self._photo_orig = None
                self.label_original.config(image="", text=f"Error: {e}")
        else:
            self._photo_orig = None
            self.label_original.config(image="", text="— Sin página —")

        # Procesado
        if idx < self.n_processed:
            try:
                img = render_pdf_page_for_display(self.processed_pdf, idx, max_size=DISPLAY_MAX_SIZE)
                self._photo_proc = ImageTk.PhotoImage(img)
                self.label_processed.config(image=self._photo_proc, text="")
            except Exception as e:
                self._photo_proc = None
                self.label_processed.config(image="", text=f"Error: {e}")
        else:
            self._photo_proc = None
            self.label_processed.config(image="", text="— Sin página —")


class MarginAdjustWindow:
    """
    Ajuste interactivo de márgenes: arrastra los bordes para ver qué va a desaparecer.
    Optimizado para carga rápida con DPI bajo.
    """

    def __init__(
        self,
        parent: tk.Tk,
        pdf_path: str,
        page_idx: int,
        initial_crop: Optional[Tuple[float, float, float, float]],
        on_save,
        main_window: MainWindow,
    ):
        self.pdf_path = pdf_path
        self.page_idx = page_idx
        self.initial_crop = initial_crop
        self.on_save = on_save
        self.main_window = main_window

        self.win = tk.Toplevel(parent)
        self.win.title(f"Ajustar márgenes — pág. {page_idx + 1}")
        self.win.minsize(700, 600)
        self.win.configure(bg=main_window.primary_bg)

        # Obtener tamaño real en puntos
        doc = load_pdf(pdf_path)
        try:
            page = doc.load_page(page_idx)
            rect = page.rect
            self.page_w_pt = float(rect.width)
            self.page_h_pt = float(rect.height)
        finally:
            doc.close()

        top = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(
            top,
            text="Arrastra los bordes del rectángulo. El área gris será eliminada.",
            style="Blue.TLabel",
        ).pack(side=tk.LEFT)

        btns = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Reset", command=self._reset, style="Blue.TButton").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btns, text="Guardar", command=self._save, style="Blue.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(btns, text="Cancelar", command=self.win.destroy, style="Blue.TButton").pack(
            side=tk.RIGHT, padx=(0, 8)
        )

        # Render de vista previa para ajuste de márgenes con la página completa.
        # No recortamos. Guardar la imagen original para reescalado dinámico.
        self.original_img = render_pdf_page_for_display(pdf_path, page_idx, max_size=None, dpi=200)
        
        # Imagen escalada inicial (será actualizada en el evento Configure)
        self.img = self.original_img
        self.photo = ImageTk.PhotoImage(self.img)
        
        # Factor de escala actual para mapear coordenadas de imagen a puntos PDF
        self.display_scale = 1.0

        # Canvas para mostrar la página completa sin scroll.
        # Configurado para reescalar dinámicamente cuando la ventana cambia de tamaño.
        self.canvas = tk.Canvas(self.win, bg=main_window.primary_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        
        # Vincular evento de redimensionamiento del canvas
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Rectángulo de recorte en coordenadas de la imagen original (sin escalar, px)
        orig_w, orig_h = self.original_img.size
        if initial_crop:
            t, b, l, r = initial_crop
            x0 = (l / self.page_w_pt) * orig_w
            y0 = (t / self.page_h_pt) * orig_h
            x1 = orig_w - (r / self.page_w_pt) * orig_w
            y1 = orig_h - (b / self.page_h_pt) * orig_h
        else:
            x0, y0, x1, y1 = 0, 0, orig_w, orig_h

        # Almacenar coordenadas originales en píxeles (de la imagen sin escalar)
        if initial_crop:
            t, b, l, r = initial_crop
            self.crop_orig = [
                (l / self.page_w_pt) * orig_w,
                (t / self.page_h_pt) * orig_h,
                orig_w - (r / self.page_w_pt) * orig_w,
                orig_h - (b / self.page_h_pt) * orig_h,
            ]
        else:
            self.crop_orig = [0, 0, orig_w, orig_h]

        # Coordenadas escaladas actuales (inicialmente sin escala)
        self.crop = [x0, y0, x1, y1]
        self.rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline="#00ff00", width=3
        )
        # Áreas sombreadas (que serán eliminadas)
        self.shade_ids = [
            self.canvas.create_rectangle(0, 0, 0, 0, fill="#666666", stipple="gray50", outline=""),
            self.canvas.create_rectangle(0, 0, 0, 0, fill="#666666", stipple="gray50", outline=""),
            self.canvas.create_rectangle(0, 0, 0, 0, fill="#666666", stipple="gray50", outline=""),
            self.canvas.create_rectangle(0, 0, 0, 0, fill="#666666", stipple="gray50", outline=""),
        ]

        self._drag_mode: Optional[str] = None
        self._last_xy: Optional[Tuple[float, float]] = None
        self._update_shades()

        # Eventos de interacción
        self.canvas.bind("<ButtonPress-1>", self._on_down)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_up)

        self.info = ttk.Label(self.win, text="Vista completa (sin recortes)", style="Blue.TLabel")
        self.info.pack(padx=12, pady=(0, 12), anchor="w")
        self._update_info()
        
        # Forzar el cálculo de escala después de que la ventana esté lista
        self.win.after(100, self._force_initial_resize)

    def _on_resize(self, event):
        self.canvas.coords(self.img_id, 0, 0)

    def _force_initial_resize(self):
        """
        Fuerza el cálculo inicial de la escala después de que la ventana esté completamente lista.
        Esto asegura que display_scale sea correcto desde el inicio.
        """
        # Obtener el tamaño actual real del canvas
        self.win.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w > 1 and canvas_h > 1:
            # Simular un evento Configure con las dimensiones actuales
            class FakeEvent:
                def __init__(self, width, height):
                    self.width = width
                    self.height = height
            
            event = FakeEvent(canvas_w, canvas_h)
            self._on_canvas_resize(event)

    def _hit_test(self, x: float, y: float) -> str:
        x0, y0, x1, y1 = self.crop
        tol = 12
        if abs(x - x0) <= tol and y0 <= y <= y1:
            return "left"
        if abs(x - x1) <= tol and y0 <= y <= y1:
            return "right"
        if abs(y - y0) <= tol and x0 <= x <= x1:
            return "top"
        if abs(y - y1) <= tol and x0 <= x <= x1:
            return "bottom"
        if x0 < x < x1 and y0 < y < y1:
            return "move"
        return "none"

    def _on_down(self, event):
        mode = self._hit_test(event.x, event.y)
        if mode == "none":
            return
        self._drag_mode = mode
        self._last_xy = (event.x, event.y)

    def _on_move(self, event):
        if not self._drag_mode or not self._last_xy:
            return
        w, h = self.img.size
        x0, y0, x1, y1 = self.crop
        dx = event.x - self._last_xy[0]
        dy = event.y - self._last_xy[1]
        min_size = 30

        if self._drag_mode == "move":
            nx0 = max(0, min(w - (x1 - x0), x0 + dx))
            ny0 = max(0, min(h - (y1 - y0), y0 + dy))
            nx1 = nx0 + (x1 - x0)
            ny1 = ny0 + (y1 - y0)
            self.crop = [nx0, ny0, nx1, ny1]
        elif self._drag_mode == "left":
            nx0 = max(0, min(x1 - min_size, x0 + dx))
            self.crop[0] = nx0
        elif self._drag_mode == "right":
            nx1 = min(w, max(x0 + min_size, x1 + dx))
            self.crop[2] = nx1
        elif self._drag_mode == "top":
            ny0 = max(0, min(y1 - min_size, y0 + dy))
            self.crop[1] = ny0
        elif self._drag_mode == "bottom":
            ny1 = min(h, max(y0 + min_size, y1 + dy))
            self.crop[3] = ny1

        self._last_xy = (event.x, event.y)
        self.canvas.coords(self.rect_id, *self.crop)
        self._update_shades()
        self._update_info()

    def _on_up(self, event):
        self._drag_mode = None
        self._last_xy = None

    def _on_canvas_resize(self, event):
        """
        Maneja el redimensionamiento del canvas.
        Rescala la imagen para que quepa completamente dentro del canvas (comportamiento 'contain').
        Mantiene el aspect ratio y actualiza todas las coordenadas de elementos correspondientes.
        
        Garantiza que la página siempre sea visible sin importar el tamaño del canvas.
        """
        if event.width <= 1 or event.height <= 1:
            return
        
        # Obtener tamaño actual del canvas (disponible para la imagen y elementos)
        # Restar padding (12px a cada lado según pack(padx=12, pady=12))
        available_w = max(1, event.width - 24)  # 12px padding izq + 12px derecha
        available_h = max(1, event.height - 24)  # 12px padding arriba + 12px abajo
        
        # Obtener tamaño original de la imagen sin escalar
        orig_w, orig_h = self.original_img.size
        
        # Calcular factor de escala para que la imagen quepa completamente sin recortes
        # Usar el espacio disponible, no el canvas completo
        scale_w = available_w / orig_w
        scale_h = available_h / orig_h
        new_scale = min(scale_w, scale_h, 1.0)  # No aumentar más allá del tamaño original
        
        # Opcional: permitir upscaling si es necesario para llenar el espacio
        # Descomenta la siguiente línea si quieres que se amplíe si el canvas es muy grande
        # new_scale = min(scale_w, scale_h)
        
        # Si el factor de escala es muy similar al actual, no hacer nada (optimización)
        if abs(new_scale - self.display_scale) < 0.001:
            return
        
        # Reescalar la imagen original
        if new_scale < 1.0:
            scaled_w = max(1, int(orig_w * new_scale))
            scaled_h = max(1, int(orig_h * new_scale))
            # Usar LANCZOS para excelente calidad al reducir tamaño
            new_img = self.original_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            logger.debug(f"MarginAdjustWindow: escalada imagen {orig_w}x{orig_h} → {scaled_w}x{scaled_h} (factor: {new_scale:.3f})")
        else:
            new_img = self.original_img
            logger.debug(f"MarginAdjustWindow: usando imagen original {orig_w}x{orig_h} (factor: {new_scale:.3f})")
        
        # Actualizar almacenamiento de la imagen escalada
        self.img = new_img
        self.photo = ImageTk.PhotoImage(self.img)
        self.display_scale = new_scale
        
        # Rescalar el rectángulo de recorte proporcionalmente
        crop_orig = self.crop_orig
        self.crop = [
            crop_orig[0] * new_scale,
            crop_orig[1] * new_scale,
            crop_orig[2] * new_scale,
            crop_orig[3] * new_scale,
        ]
        
        # Actualizar la imagen en el canvas
        self.canvas.itemconfig(self.img_id, image=self.photo)
        self.canvas.coords(self.img_id, 0, 0)
        
        # Actualizar el rectángulo de recorte
        self.canvas.coords(self.rect_id, *self.crop)
        
        # Actualizar las áreas sombreadas
        self._update_shades()
        
        # Actualizar la información de márgenes
        self._update_info()

    def _update_shades(self):
        w, h = self.img.size
        x0, y0, x1, y1 = self.crop
        # Áreas que serán eliminadas (arriba, abajo, izq, der)
        self.canvas.coords(self.shade_ids[0], 0, 0, w, y0)
        self.canvas.coords(self.shade_ids[1], 0, y1, w, h)
        self.canvas.coords(self.shade_ids[2], 0, y0, x0, y1)
        self.canvas.coords(self.shade_ids[3], x1, y0, w, y1)

    def _crop_to_margins_pt(self) -> Tuple[float, float, float, float]:
        w, h = self.img.size
        x0, y0, x1, y1 = self.crop
        left = (x0 / w) * self.page_w_pt
        top = (y0 / h) * self.page_h_pt
        right = ((w - x1) / w) * self.page_w_pt
        bottom = ((h - y1) / h) * self.page_h_pt
        return (top, bottom, left, right)

    def _update_info(self):
        t, b, l, r = self._crop_to_margins_pt()
        self.info.config(
            text=f"Márgenes (pt): arriba={t:.1f} abajo={b:.1f} izq={l:.1f} der={r:.1f}"
        )

    def _reset(self):
        """Reinicia el rectángulo de recorte a las coordenadas originales sin márgenes."""
        # Usar coordenadas originales escaladas al tamaño actual
        self.crop = [
            self.crop_orig[0] * self.display_scale,
            self.crop_orig[1] * self.display_scale,
            self.crop_orig[2] * self.display_scale,
            self.crop_orig[3] * self.display_scale,
        ]
        self.canvas.coords(self.rect_id, *self.crop)
        self._update_shades()
        self._update_info()

    def _save(self):
        crop = self._crop_to_margins_pt()
        self.on_save(crop)
        self.win.destroy()


class ReorderWindow:
    """
    Ventana para reordenar páginas de un PDF principal y mezclar páginas de PDFs extra.

    Muestra miniaturas en una cuadrícula (con scroll), permite eliminar páginas
    y reordenar con arrastrar y soltar. Cada elemento conoce de qué PDF proviene
    y su índice de página.
    """

    def __init__(self, parent: tk.Tk, main_pdf: str, main_window: MainWindow):
        self.parent = parent
        self.main_pdf = main_pdf
        self.main_window = main_window

        self.win = tk.Toplevel(parent)
        self.win.title("Reordenar / insertar páginas")
        self.win.minsize(700, 500)

        try:
            primary_bg = parent.primary_bg  # type: ignore[attr-defined]
        except Exception:
            primary_bg = "#0d6efd"
        self.win.configure(bg=primary_bg)

        self.input_pdfs = [main_pdf]
        # Tiles persistentes: no se re-renderizan al reordenar
        self.tiles = []  # cada tile: {"pdf_idx": int, "page_idx": int, "label": str, "frame": tk.Frame, "photo": ImageTk.PhotoImage}
        self._tile_frames: list[tk.Frame] = []  # frames en el mismo orden que tiles
        self._cols = 5
        self._thumb_max = 80

        self._drag_src_index: Optional[int] = None
        self._drag_over_index: Optional[int] = None
        self._hover_index: Optional[int] = None
        self._hover_color = "#ffc107"  # amarillo
        self._ghost: Optional[tk.Toplevel] = None
        self._ghost_label: Optional[tk.Label] = None
        self._ghost_photo: Optional[ImageTk.PhotoImage] = None
        self._context_menu = tk.Menu(self.win, tearoff=0)
        self._context_menu.add_command(label="Ajustar márgenes…", command=self._open_margin_adjust_from_context)
        self._context_menu_index: Optional[int] = None

        # Lazy loading: cargar miniaturas bajo demanda
        self._pending_tiles: list[tuple[int, int, str]] = []  # (pdf_idx, page_idx, label)
        self._all_tiles_loaded = False
        self._lazy_thread: Optional[threading.Thread] = None
        self._lazy_cancel = threading.Event()

        # Construir UI
        top = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(
            top,
            text=f"PDF principal: {os.path.basename(main_pdf)}",
            style="Blue.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            top,
            text="Agregar PDFs adicionales…",
            command=self._add_extra_pdfs,
            style="Blue.TButton",
        ).pack(side=tk.RIGHT)

        middle = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        middle.pack(fill=tk.BOTH, expand=True)

        # Canvas scrollable con cuadrícula de miniaturas
        self.canvas = tk.Canvas(middle, highlightthickness=0, bg=primary_bg)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar = ttk.Scrollbar(middle, orient="vertical", command=self.canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=vbar.set)

        self.grid_frame = ttk.Frame(self.canvas, style="Blue.TFrame")
        self._grid_window = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw"
        )

        self.grid_frame.bind("<Configure>", self._on_grid_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Scroll event bindings para lazy loading
        self.canvas.bind("<MouseWheel>", self._on_canvas_scroll)  # Windows/macOS
        self.canvas.bind("<Button-4>", self._on_canvas_scroll)    # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_canvas_scroll)    # Linux scroll down

        bottom = ttk.Frame(self.win, padding=12, style="Blue.TFrame")
        bottom.pack(fill=tk.X)
        ttk.Button(
            bottom,
            text="Guardar configuración",
            command=self._save_config,
            style="Blue.TButton",
        ).pack(side=tk.RIGHT)
        
        # Frame para barra de progreso (inicialmente oculto)
        self._progress_frame = ttk.Frame(self.win, style="Blue.TFrame")
        self._progress_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._progress_label = ttk.Label(
            self._progress_frame,
            text="Preparando configuración…",
            style="Blue.TLabel"
        )
        self._progress_label.pack(fill=tk.X, pady=(0, 6))
        self._progress_bar = ttk.Progressbar(
            self._progress_frame,
            mode="determinate",
            length=400
        )
        self._progress_bar.pack(fill=tk.X, pady=(0, 6))
        self._ready_label = ttk.Label(
            self._progress_frame,
            text="",
            style="Blue.TLabel"
        )
        self._ready_label.pack(fill=tk.X)
        
        # Ocultar componentes de progreso inicialmente
        self._progress_frame.pack_remove()

        # Inicializar lista con todas las páginas del PDF principal
        self._load_initial_pages()

    def _load_initial_pages(self):
        n_main = get_pdf_page_count(self.main_pdf)
        # Mostrar "Cargando..." inmediatamente y luego cargar en hilo de fondo
        loading_label = ttk.Label(self.grid_frame, text="Cargando miniaturas…", style="Blue.TLabel")
        loading_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self._layout_tiles()

        # Lazy loading: cargar SOLO los primeros 15 tiles
        INITIAL_BATCH = 15
        self._remaining_pages = max(0, n_main - INITIAL_BATCH)

        def worker():
            try:
                # Encolar solo primeras 15 páginas
                for i in range(min(n_main, INITIAL_BATCH)):
                    if self._lazy_cancel.is_set():
                        break
                    label = f"[1] {os.path.basename(self.main_pdf)} - pág. {i + 1}"
                    self._pending_tiles.append((0, i, label))
                # Crear los tiles iniciales
                self.win.after(0, self._render_pending_tiles)
                # Empezar monitoreo de scroll después de que los tiles estén listos
                self.win.after(100, self._check_scroll_position)
            except Exception as e:
                logger.error("Error cargando páginas: %s", e)

        t = threading.Thread(target=worker, daemon=True)
        self._lazy_thread = t
        t.start()

    def _render_pending_tiles(self):
        """Renderiza las miniaturas pendientes en el hilo principal."""
        try:
            # Limpiar etiqueta "Cargando..."
            for child in list(self.grid_frame.winfo_children()):
                if isinstance(child, ttk.Label) and "Cargando" in child.cget("text"):
                    child.destroy()

            # Añadir miniaturas
            for pdf_idx, page_idx, label in self._pending_tiles:
                if self._lazy_cancel.is_set():
                    break
                self._add_tile(pdf_idx, page_idx, label)

            self._pending_tiles.clear()
            self._layout_tiles()
        except Exception as e:
            logger.error("Error renderizando tiles pendientes: %s", e)


    def _on_grid_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Ajustar el ancho del frame interno al ancho del canvas
        try:
            self.canvas.itemconfigure(self._grid_window, width=event.width)
        except Exception:
            pass

    def _on_canvas_scroll(self, event=None):
        """Detecta scroll y carga más miniaturas si estamos cerca del final."""
        # Este método se llama después de eventos de scroll
        # Schedulamos un chequeo después para detectar cambios reales
        self.win.after(100, self._check_scroll_position)

    def _check_scroll_position(self):
        """Verifica la posición de scroll y carga más tiles si es necesario."""
        # Verificar que la ventana aún existe
        try:
            self.win.winfo_exists()
        except:
            return  # Ventana cerrada

        if self._remaining_pages <= 0:
            return  # Ya están cargadas todas

        try:
            # Obtener posición de scroll actual (0.0 a 1.0)
            yview = self.canvas.yview()
            if yview and len(yview) >= 2:
                current_frac = yview[1]  # Fracción inferior del viewport

                # Si scrolleamos al 70% del final, cargar más tiles
                if current_frac >= 0.7 and not hasattr(self, '_loading_more'):
                    self._loading_more = True
                    self._load_more_tiles_on_scroll()
            # Continuar monitoreando
            if self.win.winfo_exists():
                self.win.after(500, self._check_scroll_position)
        except Exception as e:
            logger.debug("Error en _check_scroll_position: %s", e)
            # Continuar monitoreando incluso si hay error
            try:
                if self.win.winfo_exists():
                    self.win.after(500, self._check_scroll_position)
            except:
                pass

    def _load_more_tiles_on_scroll(self):
        """Carga el siguiente lote de miniaturas cuando user scrollea."""
        if self._remaining_pages <= 0:
            if hasattr(self, '_loading_more'):
                delattr(self, '_loading_more')
            return

        BATCH_SIZE = 15
        INITIAL_BATCH = 15
        n_main = get_pdf_page_count(self.main_pdf)

        # Calcular cuántos ya se han cargado
        tiles_loaded = len(self.tiles)
        start_idx = tiles_loaded
        end_idx = min(tiles_loaded + BATCH_SIZE, n_main)

        if start_idx >= end_idx:
            # No hay más tiles para cargar
            if hasattr(self, '_loading_more'):
                delattr(self, '_loading_more')
            return

        # Encolar próximas miniaturas
        for i in range(start_idx, end_idx):
            label = f"[1] {os.path.basename(self.main_pdf)} - pág. {i + 1}"
            self._pending_tiles.append((0, i, label))

        self._remaining_pages = max(0, n_main - end_idx)

        # Renderizar en hilo principal
        self.win.after(0, self._render_pending_tiles_and_reset_flag)

    def _render_pending_tiles_and_reset_flag(self):
        """Renderiza tiles pendientes y resetea el flag de carga."""
        self._render_pending_tiles()
        if hasattr(self, '_loading_more'):
            delattr(self, '_loading_more')

    def _add_extra_pdfs(self):
        paths = filedialog.askopenfilenames(
            parent=self.win,
            title="Seleccionar PDFs adicionales",
            filetypes=[("PDF", "*.pdf"), ("Todos los archivos", "*.*")],
        )
        if not paths:
            return

        for path in paths:
            if path in self.input_pdfs:
                continue
            try:
                idx = len(self.input_pdfs)
                self.input_pdfs.append(path)
                n_pages = get_pdf_page_count(path)
                base = os.path.basename(path)
                for i in range(n_pages):
                    label = f"[{idx + 1}] {base} - pág. {i + 1}"
                    self._add_tile(idx, i, label)
            except Exception as e:
                messagebox.showerror(
                    "Error al abrir PDF adicional",
                    f"No se pudo abrir {path}:\n{e}",
                    parent=self.win,
                )
        self._layout_tiles()

    def _add_tile(self, pdf_idx: int, page_idx: int, label: str):
        # Frame exterior para placeholder (borde)
        tile = tk.Frame(
            self.grid_frame,
            bg=self.main_window.primary_bg,
            highlightthickness=2,
            highlightbackground=self.main_window.primary_bg,
            highlightcolor=self.main_window.primary_bg,
        )
        inner = ttk.Frame(tile, padding=3, style="Blue.TFrame")
        inner.pack(fill=tk.BOTH, expand=True)

        photo: Optional[ImageTk.PhotoImage] = None
        try:
            pdf_path = self.input_pdfs[pdf_idx]
            cached = self.main_window._get_cached_preview(pdf_path, page_idx, self._thumb_max)
            if cached is None:
                # Usar DPI muy bajo para miniaturas rápidas
                cached = render_pdf_page_for_display(pdf_path, page_idx, max_size=self._thumb_max, dpi=40)
                self.main_window._cache_preview(pdf_path, page_idx, self._thumb_max, cached)
            photo = ImageTk.PhotoImage(cached)
            lbl_img = ttk.Label(inner, image=photo, style="Blue.TLabel")
            lbl_img.pack()
        except Exception as e:
            lbl_img = ttk.Label(inner, text=f"Error:\n{e}", style="Blue.TLabel")
            lbl_img.pack()

        ttk.Label(
            inner,
            text=label,
            wraplength=self._thumb_max,
            justify="center",
            style="Blue.TLabel",
        ).pack(pady=(2, 0))

        self.tiles.append(
            {
                "pdf_idx": pdf_idx,
                "page_idx": page_idx,
                "label": label,
                "frame": tile,
                "photo": photo,
                "crop": None,  # (top, bottom, left, right) en puntos
            }
        )
        self._tile_frames.append(tile)

        # X eliminar (con índice dinámico)
        btn_x = tk.Button(
            inner,
            text="X",
            command=lambda f=tile: self._delete_tile_by_frame(f),
            bg="#dc3545",
            fg="white",
            relief="flat",
            padx=4,
            pady=0,
        )
        btn_x.place(relx=1.0, rely=0.0, anchor="ne")

        # Drag & drop bindings (tile y sus hijos)
        self._bind_drag(tile)
        for w in inner.winfo_children():
            self._bind_drag(w)
        # Clic derecho para menú contextual (Linux: Button-3)
        tile.bind("<Button-3>", self._on_right_click)
        for w in inner.winfo_children():
            w.bind("<Button-3>", self._on_right_click)

        # Indicador visual si hay recorte
        badge = tk.Label(
            inner,
            text="✂",
            bg=self.main_window.secondary_bg,
            fg="white",
            padx=4,
            pady=0,
            font=("Segoe UI", 9, "bold"),
        )
        badge.place(relx=0.0, rely=0.0, anchor="nw")
        badge.lower()  # oculto por defecto
        self.tiles[-1]["_badge"] = badge

    def _layout_tiles(self):
        self._hover_index = None

        # Limpiar mensaje "sin páginas"
        for child in list(self.grid_frame.winfo_children()):
            # solo removemos etiquetas "sin páginas"
            if isinstance(child, ttk.Label) and child.cget("text") == "(Sin páginas)":
                child.destroy()

        if not self.tiles:
            ttk.Label(self.grid_frame, text="(Sin páginas)", style="Blue.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            return

        for idx, t in enumerate(self.tiles):
            r = idx // self._cols
            c = idx % self._cols
            t["frame"].grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            # mostrar/ocultar badge según crop
            try:
                badge = t.get("_badge")
                if badge:
                    if t.get("crop") is None:
                        badge.lower()
                    else:
                        badge.lift()
            except Exception:
                pass

        for c in range(self._cols):
            self.grid_frame.grid_columnconfigure(c, weight=1)

    def _bind_drag(self, widget: tk.Widget):
        widget.bind("<ButtonPress-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<ButtonRelease-1>", self._on_drag_release)

    def _delete_tile_by_frame(self, frame: tk.Frame):
        idx = self._tile_index_from_frame(frame)
        if idx is None:
            return
        try:
            self.tiles[idx]["frame"].destroy()
        except Exception:
            pass
        self.tiles.pop(idx)
        self._tile_frames.pop(idx)
        self._layout_tiles()

    def _on_right_click(self, event):
        frame = self._find_tile_frame(event.widget)
        if frame is None:
            return
        idx = self._tile_index_from_frame(frame)
        if idx is None:
            return
        self._context_menu_index = idx
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._context_menu.grab_release()
            except Exception:
                pass

    def _open_margin_adjust_from_context(self):
        idx = self._context_menu_index
        if idx is None or idx < 0 or idx >= len(self.tiles):
            return
        t = self.tiles[idx]
        pdf_path = self.input_pdfs[t["pdf_idx"]]
        page_idx = t["page_idx"]
        current_crop = t.get("crop")

        def on_save(new_crop):
            t["crop"] = new_crop
            self._layout_tiles()

        MarginAdjustWindow(
            parent=self.win,
            pdf_path=pdf_path,
            page_idx=page_idx,
            initial_crop=current_crop,
            on_save=on_save,
            main_window=self.main_window,
        )

    def _tile_index_from_frame(self, frame: tk.Frame) -> Optional[int]:
        for i, t in enumerate(self.tiles):
            if t.get("frame") is frame:
                return i
        return None

    def _find_tile_frame(self, widget: tk.Widget) -> Optional[tk.Frame]:
        w = widget
        while w is not None:
            if isinstance(w, tk.Frame) and w.master is self.grid_frame:
                return w
            try:
                w = w.master  # type: ignore[assignment]
            except Exception:
                return None
        return None

    def _on_drag_start(self, event):
        frame = self._find_tile_frame(event.widget)
        if frame is None:
            return
        idx = self._tile_index_from_frame(frame)
        if idx is None:
            return
        self._drag_src_index = idx
        self._drag_over_index = idx
        self._create_ghost(idx, event.x_root, event.y_root)

    def _on_drag_motion(self, event):
        if self._drag_src_index is None:
            return
        self._move_ghost(event.x_root, event.y_root)
        over = self._index_from_pointer(event.x_root, event.y_root)
        if over is None:
            return
        self._drag_over_index = over
        self._set_hover(over)

    def _on_drag_release(self, event):
        if self._drag_src_index is None:
            return
        dst = self._index_from_pointer(event.x_root, event.y_root)
        src = self._drag_src_index
        self._drag_src_index = None
        self._drag_over_index = None
        self._clear_hover()
        self._destroy_ghost()
        if dst is None or dst == src:
            return
        if src < 0 or src >= len(self.tiles):
            return
        dst = max(0, min(dst, len(self.tiles) - 1))
        item = self.tiles.pop(src)
        item_frame = self._tile_frames.pop(src)
        self.tiles.insert(dst, item)
        self._tile_frames.insert(dst, item_frame)
        self._layout_tiles()
        self._pulse_placeholder(dst)

    def _create_ghost(self, idx: int, x_root: int, y_root: int):
        try:
            t = self.tiles[idx]
        except Exception:
            return
        photo = t.get("photo")
        if photo is None:
            return
        self._ghost_photo = photo
        g = tk.Toplevel(self.win)
        g.overrideredirect(True)
        g.attributes("-topmost", True)
        lbl = tk.Label(g, image=photo, bd=0)
        lbl.pack()
        self._ghost = g
        self._ghost_label = lbl
        self._move_ghost(x_root, y_root)

        # hacer el tile original "apagado"
        try:
            t["frame"].configure(bg=self.main_window.secondary_bg)
        except Exception:
            pass

    def _move_ghost(self, x_root: int, y_root: int):
        if not self._ghost:
            return
        # offset para que el cursor no tape la miniatura
        x = x_root + 12
        y = y_root + 12
        try:
            self._ghost.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _destroy_ghost(self):
        # restaurar todos los tiles al color normal
        for t in self.tiles:
            try:
                t["frame"].configure(bg=self.main_window.primary_bg)
            except Exception:
                pass
        if self._ghost:
            try:
                self._ghost.destroy()
            except Exception:
                pass
        self._ghost = None
        self._ghost_label = None
        self._ghost_photo = None

    def _pulse_placeholder(self, idx: int, pulses: int = 6):
        # pequeña animación: parpadeo del borde del destino
        if idx < 0 or idx >= len(self._tile_frames):
            return
        f = self._tile_frames[idx]
        bg = self.main_window.primary_bg
        c1 = self._hover_color

        def step(n: int):
            try:
                f.configure(
                    highlightbackground=(c1 if n % 2 == 0 else bg),
                    highlightcolor=(c1 if n % 2 == 0 else bg),
                )
            except Exception:
                return
            if n < pulses:
                self.win.after(60, step, n + 1)
            else:
                try:
                    f.configure(highlightbackground=bg, highlightcolor=bg)
                except Exception:
                    pass

        step(0)

    def _set_hover(self, idx: int):
        if idx == self._hover_index:
            return
        self._clear_hover()
        if idx < 0 or idx >= len(self._tile_frames):
            return
        self._hover_index = idx
        f = self._tile_frames[idx]
        f.configure(highlightbackground=self._hover_color, highlightcolor=self._hover_color)

    def _clear_hover(self):
        if self._hover_index is None:
            return
        try:
            f = self._tile_frames[self._hover_index]
            bg = self.main_window.primary_bg
            f.configure(highlightbackground=bg, highlightcolor=bg)
        except Exception:
            pass
        self._hover_index = None

    def _index_from_pointer(self, x_root: int, y_root: int) -> Optional[int]:
        # Calcular fila/columna según la posición en el frame interno
        try:
            fx = self.grid_frame.winfo_rootx()
            fy = self.grid_frame.winfo_rooty()
            x = x_root - fx
            y = y_root - fy
        except Exception:
            return None

        # Estimar el "slot" en la cuadrícula usando el tamaño del primer tile
        if not self._tile_frames:
            return None
        t0 = self._tile_frames[0]
        tw = max(1, t0.winfo_width() + 12)
        th = max(1, t0.winfo_height() + 12)
        col = max(0, min(self._cols - 1, x // tw))
        row = max(0, y // th)
        idx = int(row * self._cols + col)
        if idx < 0:
            return None
        if idx >= len(self.tiles):
            return len(self.tiles) - 1
        return idx

    def _save_config(self):
        if not self.tiles:
            messagebox.showwarning(
                "Sin páginas",
                "No hay páginas en la lista para generar el PDF.",
                parent=self.win,
            )
            return
        order = [(t["pdf_idx"], t["page_idx"]) for t in self.tiles]
        crops = [t.get("crop") for t in self.tiles]
        self.main_window.reorder_config = {
            "input_pdfs": list(self.input_pdfs),
            "order": order,
            "crops": crops,
        }
        messagebox.showinfo(
            "Configuración guardada",
            "La configuración de reordenar/insertar se guardó. Ahora puedes pulsar “Procesar PDF”.",
            parent=self.win,
        )
        self.win.destroy()


def run_gui():
    """Punto de entrada para ejecutar la interfaz gráfica."""
    # Configurar logging para ver el progreso en la terminal desde la GUI.
    # Nivel 1 → INFO, suficiente para seguir el flujo sin saturar.
    setup_logging(1)
    logger.info("Aplicación GUI iniciada.")
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    run_gui()
