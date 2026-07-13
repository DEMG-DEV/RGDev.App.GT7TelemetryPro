import logging
import functools

def safe_slot(func):
    """
    Decorador para métodos de la UI (Slots).
    Atrapa cualquier excepción lanzada durante la ejecución del método y la envía al logger global,
    evitando que la aplicación falle silenciosamente en PyQt6.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"UI Error in {func.__name__}: {e}", exc_info=True)
            # Aquí podríamos opcionalmente conectar con un statusBar global si lo quisiéramos
    return wrapper
