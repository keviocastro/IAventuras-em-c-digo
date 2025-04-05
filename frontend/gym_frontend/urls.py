from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse
import requests
from django.conf import settings
import socket
import errno
from requests.exceptions import ConnectionError, Timeout

# Função para encaminhar requisições para a API FastAPI
def proxy_to_api(request: HttpRequest, path: str = '') -> HttpResponse:
    """
    Encaminha requisições para a API FastAPI
    """
    # Garantir que o path comece com /
    if not path.startswith('/'):
        path = '/' + path
    
    # Construir a URL para a API
    api_url = f"{settings.API_URL}{path}"
    
    # Log da URL gerada para debug
    print(f"Proxy para API: {request.method} {api_url}")
    
    try:
        # Obter o método HTTP
        method = request.method.lower()
        
        # Preparar os headers
        headers = {}
        for key, value in request.headers.items():
            # Preservar todos os cabeçalhos, exceto host e content-length
            if key.lower() not in ['host', 'content-length']:
                headers[key] = value
        
        # Garantir que o cabeçalho de autorização seja preservado
        auth_header = request.headers.get('Authorization')
        if auth_header:
            print(f"Encaminhando cabeçalho de autorização: {auth_header[:15]}...")
            headers['Authorization'] = auth_header
        
        # Executar a requisição para a API
        api_func = getattr(requests, method)
        
        # Tratamento específico para cada tipo de requisição
        if method in ['get', 'delete']:
            # Para GET e DELETE, enviar parâmetros da query string
            response = api_func(api_url, headers=headers, params=request.GET, timeout=10)
        elif method in ['post', 'put', 'patch']:
            # Para métodos que enviam dados, verificar o Content-Type
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/x-www-form-urlencoded' in content_type:
                # Enviar como form data (útil para o login)
                form_data = {}
                for key, value in request.POST.items():
                    form_data[key] = value
                

                response = api_func(api_url, headers=headers, data=form_data, timeout=10)
            elif 'application/json' in content_type:
                # Enviar como JSON
                response = api_func(api_url, headers=headers, json=request.body, timeout=10)
            else:
                # Para outros tipos, enviar o corpo da requisição como está
                response = api_func(api_url, headers=headers, data=request.body, timeout=10)
        else:
            # Para outros métodos HTTP
            response = api_func(api_url, headers=headers, timeout=10)
        
        # Construir a resposta Django
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
        
        # Copiar os headers relevantes da resposta
        for key, value in response.headers.items():
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']:
                django_response[key] = value
        
        return django_response
    
    except ConnectionError as e:
        # Tratamento específico para erros de conexão
        error_message = str(e)
        if "Broken pipe" in error_message or "broken pipe" in error_message:
            print(f"Erro de conexão (broken pipe): {error_message}")
            return HttpResponse(
                content='{"detail": "A conexão com o servidor foi interrompida. Por favor, tente novamente."}',
                status=503,  # Service Unavailable
                content_type='application/json'
            )
        elif "Connection refused" in error_message:
            print(f"Erro de conexão (connection refused): {error_message}")
            return HttpResponse(
                content='{"detail": "Não foi possível conectar ao servidor backend. O servidor pode estar offline."}',
                status=503,  # Service Unavailable
                content_type='application/json'
            )
        else:
            print(f"Erro de conexão: {error_message}")
            return HttpResponse(
                content=f'{{"detail": "Erro ao conectar com o servidor backend: {error_message}"}}',
                status=500,
                content_type='application/json'
            )
    
    except Timeout:
        # Tratamento específico para timeout
        print("Timeout ao conectar com a API")
        return HttpResponse(
            content='{"detail": "Tempo limite esgotado ao tentar conectar ao servidor. Por favor, tente novamente mais tarde."}',
            status=504,  # Gateway Timeout
            content_type='application/json'
        )
    
    except socket.error as e:
        # Tratamento específico para erros de socket
        error_code = getattr(e, 'errno', None)
        error_message = str(e)
        print(f"Erro de socket: {error_code} - {error_message}")
        return HttpResponse(
            content=f'{{"detail": "Erro de conexão: {error_message}"}}',
            status=500,
            content_type='application/json'
        )
    
    except requests.RequestException as e:
        # Log detalhado do erro
        print(f"Erro ao conectar com a API: {str(e)}")
        
        # Retornar erro 500 com mensagem explicativa
        return HttpResponse(
            content=f'{{"detail": "Erro ao conectar com o servidor backend: {str(e)}"}}',
            status=500,
            content_type='application/json'
        )
    
    except Exception as e:
        # Log do erro inesperado
        print(f"Erro inesperado no proxy: {str(e)}")
        
        # Retornar erro 500 com mensagem explicativa
        return HttpResponse(
            content=f'{{"detail": "Erro inesperado no servidor: {str(e)}"}}',
            status=500,
            content_type='application/json'
        )

urlpatterns = [
    path('admin/', admin.site.urls),
    # Proxy para endpoints específicos da API FastAPI
    path('auth/token/', csrf_exempt(lambda request: proxy_to_api(request, '/auth/token'))),
    path('auth/me/', csrf_exempt(lambda request: proxy_to_api(request, '/auth/me'))),
    # Proxy genérico para outros endpoints de auth
    path('auth/<path:path>/', csrf_exempt(lambda request: proxy_to_api(request, f'/auth/{path}'))),
    # Proxy genérico para todos os outros endpoints da API
    path('api/<path:path>/', csrf_exempt(lambda request: proxy_to_api(request, f'/{path}'))),
    # As demais URLs do frontend
    path('', include('dashboard.urls')),
] 