"""
Script de Prueba de Rate Limiting / Throttling (Amazon API Gateway / Nginx)
Evaluación N.º 4 - Backend FitLife (Inacap)

Este script realiza una ráfaga concurrente de peticiones HTTP contra un endpoint
del backend para evidenciar el límite de tasa y la respuesta HTTP 429 Too Many Requests.
"""

import sys
import time
import argparse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed


def test_endpoint(url, request_id):
    start = time.time()
    headers = {
        'User-Agent': 'FitLifeRateLimitTester/1.0',
        'Accept': 'application/json'
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            latency = round((time.time() - start) * 1000, 2)
            return {
                'id': request_id,
                'status': response.status,
                'reason': response.reason,
                'latency': latency,
                'throttled': False
            }
    except urllib.error.HTTPError as e:
        latency = round((time.time() - start) * 1000, 2)
        return {
            'id': request_id,
            'status': e.code,
            'reason': e.reason,
            'latency': latency,
            'throttled': (e.code == 429)
        }
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        return {
            'id': request_id,
            'status': 0,
            'reason': str(e),
            'latency': latency,
            'throttled': False
        }


def main():
    parser = argparse.ArgumentParser(
        description="Prueba de Rate Limiting / Throttling para API Gateway / FitLife"
    )
    parser.add_argument(
        "--url",
        default="https://fitlife-inacap.duckdns.org/api/dashboard/aforo/",
        help="URL del endpoint a probar (default: https://fitlife-inacap.duckdns.org/api/dashboard/aforo/)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=15,
        help="Número total de peticiones a enviar en la ráfaga (default: 15)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Número de hilos concurrentes simultáneos (default: 5)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print(" FITLIFE BACKEND - PRUEBA DE RATE LIMITING / THROTTLING")
    print(" Evaluación N.º 4 - Arquitectura AWS API Gateway")
    print("=" * 70)
    print(f"[*] Endpoint de prueba: {args.url}")
    print(f"[*] Ráfaga total:       {args.requests} peticiones")
    print(f"[*] Concurrencia:        {args.concurrency} hilos simultáneos")
    print("-" * 70)
    print(f"{'Req #':<8}{'Status HTTP':<18}{'Latencia (ms)':<16}{'Resultado':<20}")
    print("-" * 70)

    results = []
    t_global_start = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(test_endpoint, args.url, i + 1) for i in range(args.requests)]
        for f in as_completed(futures):
            res = f.result()
            results.append(res)
            
            if res['status'] == 200:
                result_str = "[OK] 200 Exitoso"
            elif res['status'] == 429:
                result_str = "[THROTTLED] 429 Limitado"
            else:
                result_str = f"[{res['status']}] {res['reason']}"

            print(f"{res['id']:<8}{res['status']} {res['reason']:<13}{res['latency']:<16}{result_str:<20}")

    t_global_elapsed = round(time.time() - t_global_start, 2)

    total = len(results)
    ok_count = sum(1 for r in results if r['status'] == 200)
    throttled_count = sum(1 for r in results if r['status'] == 429)
    other_count = total - ok_count - throttled_count
    avg_latency = round(sum(r['latency'] for r in results) / total, 2) if total > 0 else 0

    print("=" * 70)
    print(" RESUMEN DE RESULTADOS DE THROTTLING:")
    print(f" - Total peticiones enviadas:     {total}")
    print(f" - Peticiones exitosas (200 OK):  {ok_count}")
    print(f" - Peticiones limitadas (429):    {throttled_count}")
    print(f" - Otras respuestas/errores:      {other_count}")
    print(f" - Latencia promedio:             {avg_latency} ms")
    print(f" - Tiempo total de ráfaga:        {t_global_elapsed} s")
    print("=" * 70)

    if throttled_count > 0:
        print("[+] RESULTADO: Se evidenció con éxito el código HTTP 429 Too Many Requests.")
        print("    El mecanismo de Throttling protegió el backend de sobrecargas.")
    else:
        print("[!] NOTA: No se recibieron códigos 429. Verifique que la URL apunte al")
        print("    Amazon API Gateway con el Usage Plan configurado (ej: 2 req/s, ráfaga 5).")
    print("=" * 70)


if __name__ == '__main__':
    main()
