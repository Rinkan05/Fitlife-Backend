import json
import urllib.request
import urllib.error
import ssl
from django.conf import settings

# ==============================================================================
# SERVICIO OFICIAL TRANSBANK WEBPAY PLUS (REST API v1.2) - AMBIENTE INTEGRACIÓN
# ==============================================================================

# Credenciales oficiales de Sandbox provistas por Transbank Developers
TBK_COMMERCE_CODE = '597055555532'
TBK_API_KEY = '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C'
WEBPAY_API_BASE = 'https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions'



class WebpayService:
    """
    Servicio de integración directa con Transbank Webpay Plus usando la API REST v1.2.
    No requiere librerías binarias externas y funciona de forma nativa en Python.
    """

    @classmethod
    def _get_headers(cls):
        return {
            'Tbk-Api-Key-Id': TBK_COMMERCE_CODE,
            'Tbk-Api-Key-Secret': TBK_API_KEY,
            'Content-Type': 'application/json',
        }

    @classmethod
    def iniciar_transaccion(cls, buy_order: str, session_id: str, amount: int, return_url: str):
        """
        Crea una transacción en Webpay Plus.
        Retorna dict con 'token' y 'url' hacia la pasarela de pago.
        """
        payload = {
            'buy_order': str(buy_order),
            'session_id': str(session_id),
            'amount': int(amount),
            'return_url': return_url,
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            WEBPAY_API_BASE,
            data=data,
            headers=cls._get_headers(),
            method='POST'
        )

        context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Error HTTP {e.code} de Transbank: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Error conectando con Webpay Transbank: {str(e)}")

    @classmethod
    def confirmar_transaccion(cls, token_ws: str):
        """
        Confirma (Commit) una transacción en Webpay Plus luego de que el usuario
        completa el pago en el formulario bancario.
        """
        url = f"{WEBPAY_API_BASE}/{token_ws}"
        req = urllib.request.Request(
            url,
            data=b'',
            headers=cls._get_headers(),
            method='PUT'
        )

        context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Error HTTP {e.code} al confirmar pago Transbank: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Error confirmando pago en Webpay: {str(e)}")

