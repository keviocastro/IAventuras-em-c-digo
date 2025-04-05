import requests
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
import random

# Configuração da API
API_URL = settings.API_URL

# Função para extrair o token JWT do request e criar headers apropriados
def get_auth_headers(request):
    """
    Extrai o token JWT do cabeçalho Authorization do request ou dos cookies,
    e retorna headers para a requisição à API.
    """
    headers = {}
    
    # Tentar obter o token do cabeçalho Authorization
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        headers['Authorization'] = f'Bearer {token}'
        return headers
    
    # Tentar obter o token da sessão
    token = request.session.get('access_token')
    if token:
        print("Usando token da sessão")
        headers['Authorization'] = f'Bearer {token}'
        return headers
    
    # Tentar obter o token do cookie
    token = request.COOKIES.get('access_token')
    if token:
        print("Usando token do cookie")
        headers['Authorization'] = f'Bearer {token}'
        return headers
    
    # Se não encontrar o token, verificar se há parâmetros na URL
    token = request.GET.get('token')
    if token:
        print("Usando token da URL")
        headers['Authorization'] = f'Bearer {token}'
    
    print(f"Headers para API: {headers}")
    return headers

# Função para fazer requisições à API com autenticação
def api_request(request, method, endpoint, **kwargs):
    """
    Função auxiliar para fazer requisições à API com autenticação.
    
    Args:
        request: O request HTTP original do Django
        method: Método HTTP (get, post, put, delete)
        endpoint: Endpoint da API, sem a URL base
        **kwargs: Argumentos adicionais para a requisição
    
    Returns:
        Resposta da API
    """
    # Garantir que o endpoint comece com / e não tenha barras duplicadas
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    
    # Construir a URL completa
    url = f"{settings.API_URL}{endpoint}"
    
    # Obter headers de autenticação
    headers = get_auth_headers(request)
    
    # Mesclar com headers existentes, se houver
    if 'headers' in kwargs:
        for key, value in headers.items():
            kwargs['headers'][key] = value
    else:
        kwargs['headers'] = headers
    
    # Definir timeout padrão se não for especificado
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 10
    
    # Fazer a requisição
    api_func = getattr(requests, method.lower())
    return api_func(url, **kwargs)

def index(request):
    """
    Exibe o dashboard principal com estatísticas gerais.
    """
    estatisticas = {
        'frequencia': None,
        'planos': None
    }
    alunos_risco = []
    mensagem_erro = ""
    
    try:
        # Verificar se foi solicitada recalculação dos gráficos
        recalcular_frequencia = request.GET.get('recalcular_frequencia') == '1'
        recalcular_planos = request.GET.get('recalcular_planos') == '1'
        
        # Obter estatísticas de frequência
        freq_params = {'recalcular': '1'} if recalcular_frequencia else {}
        freq_response = api_request(
            request,
            'get',
            '/estatisticas/frequencia',
            params=freq_params
        )
        
        if freq_response.status_code == 200:
            estatisticas['frequencia'] = freq_response.json()
        
        # Obter estatísticas de planos
        planos_params = {'recalcular': '1'} if recalcular_planos else {}
        planos_response = api_request(
            request,
            'get',
            '/estatisticas/planos',
            params=planos_params
        )
        
        if planos_response.status_code == 200:
            estatisticas['planos'] = planos_response.json()
        
        # Obter os top 10 alunos com maior risco de churn (usando o endpoint completo)
        try:
            # Usar o novo endpoint que inclui todos os dados necessários em uma única requisição
            churn_response = api_request(
                request,
                'get',
                '/estatisticas/churn/top-risco-completo'
            )
            
            if churn_response.status_code == 200:
                alunos_risco = churn_response.json().get('alunos_risco', [])
            else:
                # Fallback para o endpoint original se o novo não estiver disponível
                churn_response = api_request(
                    request,
                    'get',
                    '/estatisticas/churn/top-risco'
                )
                
                if churn_response.status_code == 200:
                    alunos_risco = churn_response.json().get('alunos_risco', [])
        except Exception as e:
            # Se ocorrer algum erro, continuamos com a lista vazia
            pass
            
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    # Se a solicitação foi para recalcular e foi bem-sucedida, redirecionar para limpar parâmetros da URL
    if (recalcular_frequencia or recalcular_planos) and not mensagem_erro:
        messages.success(request, "Gráficos recalculados com sucesso!")
        return redirect('dashboard:index')
    
    context = {
        'estatisticas': estatisticas,
        'mensagem_erro': mensagem_erro,
        'alunos_risco': alunos_risco[:10]  # Garantir que são no máximo 10
    }
    
    return render(request, 'dashboard/index.html', context)


def lista_alunos(request):
    """
    Listar todos os alunos cadastrados.
    """
    alunos = []
    mensagem_erro = ""
    
    try:
        # Obter parâmetros de filtro (se existirem)
        nome = request.GET.get('nome', '')
        email = request.GET.get('email', '')
        ativo = request.GET.get('ativo', '')
        
        # Construir parâmetros de consulta
        params = {}
        if nome:
            params['nome'] = nome
        if email:
            params['email'] = email
        if ativo in ['0', '1']:
            params['ativo'] = ativo
        
        # Obter lista de alunos da API
        response = api_request(
            request,
            'get',
            "/aluno/",
            params=params
        )
        
        if response.status_code == 200:
            alunos_api = response.json()
            
            # Buscar probabilidades de churn para todos os alunos de uma vez
            try:
                # Obter os top alunos com risco de churn (inclui todos os alunos com probabilidade calculada)
                churn_response = api_request(
                    request,
                    'get',
                    "/estatisticas/churn/top-risco",
                    params={"limit": 1000}
                )
                
                if churn_response.status_code == 200:
                    churn_data = churn_response.json()
                    
                    # Criar um dicionário mapeando aluno_id para seus dados de churn
                    churn_map = {aluno['aluno_id']: {
                        'probabilidade_churn': aluno['probabilidade_churn'],
                        'dias_desde_ultima_visita': aluno.get('dias_desde_ultima_visita')
                    } for aluno in churn_data['alunos_risco']}
                    
                    # Adicionar dados de churn aos alunos
                    for aluno in alunos_api:
                        if aluno['id'] in churn_map:
                            aluno['probabilidade_churn'] = churn_map[aluno['id']]['probabilidade_churn']
                            aluno['dias_desde_ultima_visita'] = churn_map[aluno['id']]['dias_desde_ultima_visita']
                        else:
                            aluno['probabilidade_churn'] = None
                            aluno['dias_desde_ultima_visita'] = None
                else:
                    # Se a API retornar erro, definir valores padrão
                    for aluno in alunos_api:
                        aluno['probabilidade_churn'] = None
                        aluno['dias_desde_ultima_visita'] = None
            except Exception as e:
                # Se houver erro, definir valores padrão para todos os alunos
                for aluno in alunos_api:
                    aluno['probabilidade_churn'] = None
                    aluno['dias_desde_ultima_visita'] = None
                mensagem_erro = f"Erro ao obter dados de churn: {str(e)}"
            
            alunos = alunos_api
        else:
            mensagem_erro = f"Erro ao obter lista de alunos: {response.status_code} - {response.text}"
    
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    context = {
        'alunos': alunos,
        'mensagem_erro': mensagem_erro,
        'filtro_nome': nome,
        'filtro_email': email,
        'filtro_ativo': ativo,
    }
    
    return render(request, 'dashboard/lista_alunos.html', context)


def detalhe_aluno(request, aluno_id):
    """
    Exibe os detalhes de um aluno específico.
    """
    aluno = None
    churn_info = None
    mensagem_erro = ""
    
    try:
        # Obter dados do aluno
        response = api_request(request, 'get', f"/aluno/{aluno_id}")
        
        if response.status_code == 200:
            aluno = response.json()
            
            # Obter informações de churn
            try:
                churn_response = api_request(request, 'get', f"/churn/aluno/{aluno_id}")
                if churn_response.status_code == 200:
                    churn_info = churn_response.json()
            except Exception as e:
                mensagem_erro = f"Erro ao obter informações de churn: {str(e)}"
        else:
            mensagem_erro = f"Erro ao obter dados do aluno: {response.status_code} - {response.text}"
    
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    context = {
        'aluno': aluno,
        'churn_info': churn_info,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/detalhe_aluno.html', context)


def frequencia_aluno(request, aluno_id):
    """
    Exibe o histórico de frequência de um aluno.
    """
    try:
        # Fazer requisição para a API
        response = api_request(request, 'get', f"/aluno/{aluno_id}/frequencia")
        
        if response.status_code == 200:
            dados = response.json()
            return render(request, 'dashboard/frequencia_aluno.html', {'dados': dados, 'aluno_id': aluno_id})
        else:
            messages.error(request, f"Erro ao obter frequência do aluno: {response.status_code}")
            return redirect('dashboard:detalhe_aluno', aluno_id=aluno_id)
    except Exception as e:
        messages.error(request, f"Erro ao conectar com a API: {str(e)}")
        return redirect('dashboard:detalhe_aluno', aluno_id=aluno_id)


def risco_churn_aluno(request, aluno_id):
    """
    Exibe a análise de risco de churn para um aluno específico.
    """
    try:
        # Obter dados do aluno
        aluno_response = api_request(request, 'get', f"/aluno/{aluno_id}")
        if aluno_response.status_code != 200:
            messages.error(request, f"Erro ao obter dados do aluno: {aluno_response.status_code}")
            return redirect('dashboard:lista_alunos')
            
        aluno = aluno_response.json()
        
        # Fazer requisição para a API de churn
        churn_response = api_request(request, 'get', f"/churn/aluno/{aluno_id}")
        
        if churn_response.status_code == 200:
            churn_info = churn_response.json()
            return render(request, 'dashboard/risco_churn.html', {
                'aluno': aluno,
                'churn_info': churn_info,
                'aluno_id': aluno_id
            })
        else:
            messages.error(request, f"Erro ao obter análise de risco do aluno: {churn_response.status_code}")
            return redirect('dashboard:detalhe_aluno', aluno_id=aluno_id)
    except Exception as e:
        messages.error(request, f"Erro ao conectar com a API: {str(e)}")
        return redirect('dashboard:detalhe_aluno', aluno_id=aluno_id)


def evolucao_aluno(request):
    """
    Página para visualizar a evolução de um aluno ao longo do tempo.
    """
    aluno_id = request.GET.get('aluno_id')
    periodo = request.GET.get('periodo', '3m')  # Padrão: 3 meses
    
    # Se não tiver aluno_id, redirecionar para lista de alunos
    if not aluno_id:
        messages.warning(request, "Selecione um aluno para visualizar sua evolução")
        return redirect('dashboard:lista_alunos')
    
    aluno = None
    dados_evolucao = None
    mensagem_erro = ""
    
    try:
        # Obter dados do aluno
        aluno_response = api_request(request, 'get', f"/aluno/{aluno_id}")
        
        if aluno_response.status_code == 200:
            aluno = aluno_response.json()
            
            # Obter dados de evolução
            evolucao_response = api_request(
                request,
                'get',
                f"/aluno/{aluno_id}/evolucao",
                params={'periodo': periodo}
            )
            
            if evolucao_response.status_code == 200:
                dados_evolucao = evolucao_response.json()
            else:
                mensagem_erro = f"Erro ao obter dados de evolução: {evolucao_response.status_code}"
                
        else:
            mensagem_erro = f"Erro ao obter dados do aluno: {aluno_response.status_code}"
            
    except Exception as e:
        mensagem_erro = f"Erro ao processar requisição: {str(e)}"
    
    context = {
        'aluno': aluno,
        'dados_evolucao': dados_evolucao,
        'periodo': periodo,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/evolucao_aluno.html', context)


def checkin(request):
    """
    Página para registrar entrada/saída de alunos.
    """
    checkins_ativos = []
    
    # Buscar check-ins ativos
    try:
        response = api_request(request, 'get', "/checkin/ativos")
        if response.status_code == 200:
            checkins_ativos = response.json()
    except Exception as e:
        messages.error(request, f"Erro ao buscar check-ins ativos: {str(e)}")
    
    if request.method == 'POST':
        try:
            # Verificar qual ação está sendo tomada
            if 'aluno_id' in request.POST:
                # Registro de check-in individual
                aluno_id = request.POST.get('aluno_id')
                
                # Dados para enviar à API
                dados = {
                    'aluno_id': int(aluno_id)
                }
                
                # Fazer requisição para a API usando api_request para incluir autenticação
                response = api_request(
                    request,
                    'post',
                    "/aluno/checkin",
                    json=dados
                )
                
                if response.status_code in [200, 201]:
                    messages.success(request, "Checkin registrado com sucesso!")
                    # Redirecionar para atualizar a lista
                    return redirect('dashboard:checkin')
                else:
                    messages.error(request, f"Erro ao registrar checkin: {response.status_code}")
            
            elif 'fechar_todos' in request.POST:
                # Fechar todos os check-ins ativos
                response = api_request(
                    request,
                    'post',
                    "/checkin/fechar-todos"
                )
                
                if response.status_code == 200:
                    resultado = response.json()
                    # Verificar as chaves que existem na resposta
                    if 'total_fechados' in resultado:
                        if resultado['total_fechados'] > 0:
                            messages.success(request, f"{resultado['total_fechados']} check-ins fechados com sucesso!")
                        else:
                            messages.info(request, "Não havia check-ins ativos para fechar.")
                    elif 'message' in resultado:
                        messages.info(request, resultado['message'])
                    else:
                        messages.success(request, "Operação concluída com sucesso!")
                    # Redirecionar para a mesma página para atualizar a lista
                    return redirect('dashboard:checkin')
                else:
                    messages.error(request, f"Erro ao fechar check-ins: {response.status_code}")
                    if response.text:
                        messages.error(request, response.text)
        
        except Exception as e:
            messages.error(request, f"Erro ao conectar com a API: {str(e)}")
    
    # Obter lista de alunos para o formulário
    try:
        response = api_request(request, 'get', "/aluno/")
        alunos = response.json() if response.status_code == 200 else []
        
        # Criar um dicionário de alunos para busca rápida por ID
        alunos_dict = {aluno['id']: aluno for aluno in alunos}
        
        # Adicionar nomes de alunos aos check-ins ativos
        for checkin in checkins_ativos:
            aluno_id = checkin.get('aluno_id')
            if aluno_id in alunos_dict:
                checkin['nome_aluno'] = alunos_dict[aluno_id]['nome']
            else:
                checkin['nome_aluno'] = f'Aluno #{aluno_id}'
    except Exception as e:
        alunos = []
        messages.error(request, f"Erro ao obter lista de alunos: {str(e)}")
    
    return render(request, 'dashboard/checkin.html', {
        'alunos': alunos,
        'checkins_ativos': checkins_ativos,
        'total_ativos': len(checkins_ativos)
    })


def cadastro_aluno(request):
    """
    Página para cadastrar um novo aluno.
    """
    if request.method == 'POST':
        try:
            # Pegar dados do formulário
            nome = request.POST.get('nome')
            email = request.POST.get('email')
            telefone = request.POST.get('telefone')
            data_nascimento = request.POST.get('data_nascimento')
            plano_id = request.POST.get('plano_id')
            
            # Dados para enviar à API
            dados = {
                'nome': nome,
                'email': email,
                'telefone': telefone,
                'plano_id': int(plano_id)
            }
            
            # Formatar a data de nascimento para o formato ISO 8601 apenas se não estiver vazia
            if data_nascimento and data_nascimento.strip():
                dados['data_nascimento'] = f"{data_nascimento}T00:00:00"
            
            # Fazer requisição para a API
            response = api_request(
                request,
                'post',
                "/aluno/registro",
                json=dados
            )
            
            if response.status_code in [200, 201]:
                messages.success(request, "Aluno cadastrado com sucesso!")
                return redirect('dashboard:lista_alunos')
            else:
                messages.error(request, f"Erro ao cadastrar aluno: {response.text}")
        
        except Exception as e:
            messages.error(request, f"Erro ao conectar com a API: {str(e)}")
    
    # Obter lista de planos disponíveis
    try:
        response = api_request(request, 'get', "/plano/")
        planos = response.json() if response.status_code == 200 else []
    except Exception:
        planos = []
    
    return render(request, 'dashboard/cadastro_aluno.html', {'planos': planos})


def cadastro_aluno_sintetico(request):
    """
    Página para cadastrar um aluno sintético com parâmetros específicos para teste do modelo de churn.
    """
    mensagem_erro = ""
    
    if request.method == 'POST':
        try:
            # Dados básicos do aluno
            nome = request.POST.get('nome')
            email = request.POST.get('email')
            telefone = request.POST.get('telefone')
            data_nascimento = request.POST.get('data_nascimento')
            plano_id = request.POST.get('plano_id')
            
            # Parâmetros de comportamento para checkins sintéticos
            visitas_semana = float(request.POST.get('visitas_semana', 0))
            duracao_media = int(request.POST.get('duracao_media', 0))
            dias_desde_ultima = int(request.POST.get('dias_desde_ultima', 0))
            
            # Determinar um período de histórico fixo (últimos 90 dias)
            # Isso substitui o parâmetro semanas_historico que podia conflitar com dias_desde_ultima
            periodo_historico_dias = 90
            
            # Passo 1: Dados para cadastrar o aluno
            dados_aluno = {
                'nome': nome,
                'email': email,
                'telefone': telefone,
                'plano_id': int(plano_id)
            }
            
            # Formatar a data de nascimento para o formato ISO 8601 apenas se não estiver vazia
            if data_nascimento and data_nascimento.strip():
                dados_aluno['data_nascimento'] = f"{data_nascimento}T00:00:00"
            
            # Cadastrar o aluno
            aluno_response = api_request(
                request,
                'post',
                "/aluno/registro",
                json=dados_aluno
            )
            
            if aluno_response.status_code in [200, 201]:
                aluno = aluno_response.json()
                aluno_id = aluno['id']
                data_atual = datetime.now()
                
                # Passo 2: Gerar checkins sintéticos
                if visitas_semana > 0:
                    checkins = []
                    
                    # Calcular quantidade total de visitas no período, exceto durante o período de inatividade
                    periodo_ativo_dias = periodo_historico_dias - dias_desde_ultima
                    if periodo_ativo_dias <= 0:
                        # Se o período de inatividade for maior que o período histórico, não criar checkins
                        periodo_ativo_dias = 0
                        total_visitas = 0
                    else:
                        # Calcular visitas no período ativo
                        total_visitas = round(visitas_semana * (periodo_ativo_dias / 7))
                    
                    # Gerar datas das visitas (distribuídas uniformemente no período ativo)
                    datas_visitas = []
                    if total_visitas > 0:
                        # Determinar a data da primeira visita (mais antiga)
                        data_inicio_ativo = data_atual - timedelta(days=periodo_historico_dias)
                        data_fim_ativo = data_atual - timedelta(days=dias_desde_ultima)
                        
                        # Distribuir as visitas uniformemente no período ativo
                        if total_visitas == 1:
                            # Se só houver uma visita, colocá-la no meio do período ativo
                            meio_periodo = data_inicio_ativo + (data_fim_ativo - data_inicio_ativo) / 2
                            datas_visitas.append(meio_periodo)
                        else:
                            # Distribuir visitas uniformemente
                            intervalo = (data_fim_ativo - data_inicio_ativo) / (total_visitas - 1) if total_visitas > 1 else timedelta(days=0)
                            for i in range(total_visitas):
                                data_visita = data_inicio_ativo + intervalo * i
                                # Adicionar aleatoriedade na hora/minuto
                                data_visita = data_visita.replace(
                                    hour=random.randint(7, 21),
                                    minute=random.randint(0, 59)
                                )
                                datas_visitas.append(data_visita)
                    
                    # Criar checkins para cada data de visita
                    for data_visita in datas_visitas:
                        # Adicionar duração aleatória em torno da média
                        variacao = duracao_media * 0.2  # 20% de variação
                        duracao = max(10, int(duracao_media + random.uniform(-variacao, variacao)))
                        
                        # Calcular data de saída
                        data_saida = data_visita + timedelta(minutes=duracao)
                        
                        # Adicionar à lista de checkins
                        checkins.append({
                            'aluno_id': aluno_id,
                            'data_entrada': data_visita.isoformat(),
                            'data_saida': data_saida.isoformat(),
                            'duracao_minutos': duracao
                        })
                    
                    # Enviar checkins em lote para processamento
                    if checkins:
                        payload = {
                            'checkins': checkins,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        checkin_response = api_request(
                            request,
                            'post',
                            "/checkin/batch",
                            json=payload
                        )
                        
                        if checkin_response.status_code == 202:
                            messages.success(request, f"Aluno sintético cadastrado com {total_visitas} checkins!")
                            messages.info(request, f"Última visita: {dias_desde_ultima} dias atrás")
                        else:
                            messages.warning(request, f"Aluno cadastrado, mas houve erro ao gerar checkins: {checkin_response.status_code}")
                else:
                    messages.success(request, "Aluno sintético cadastrado sem histórico de checkins!")
                
                # Solicitar cálculo da probabilidade de churn para o novo aluno
                try:
                    churn_response = api_request(
                        request,
                        'get',
                        f"/churn/aluno/{aluno_id}",
                        params={"recalcular": True}
                    )
                    
                    if churn_response.status_code == 200:
                        churn_info = churn_response.json()
                        messages.info(request, f"Probabilidade de churn calculada: {churn_info['probabilidade_churn']:.2f}")
                    else:
                        messages.warning(request, "Aluno cadastrado, mas não foi possível calcular a probabilidade de churn.")
                except Exception as e:
                    messages.warning(request, f"Erro ao calcular probabilidade de churn: {str(e)}")
                
                return redirect('dashboard:detalhe_aluno', aluno_id=aluno_id)
            else:
                mensagem_erro = f"Erro ao cadastrar aluno: {aluno_response.text}"
        
        except Exception as e:
            mensagem_erro = f"Erro ao processar a solicitação: {str(e)}"
    
    # Obter lista de planos disponíveis
    try:
        response = api_request(request, 'get', "/plano/")
        planos = response.json() if response.status_code == 200 else []
    except Exception:
        planos = []
    
    context = {
        'planos': planos,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/cadastro_aluno_sintetico.html', context)


# Novas views para RabbitMQ

def checkin_batch(request):
    """
    Página para registrar check-in em massa para vários alunos.
    """
    if request.method == 'POST':
        try:
            # Pegar IDs dos alunos selecionados
            alunos_ids = request.POST.getlist('alunos_ids')
            
            if not alunos_ids:
                messages.warning(request, "Nenhum aluno selecionado!")
                return redirect('dashboard:checkin_batch')
            
            # Preparar dados para API
            checkins = []
            for aluno_id in alunos_ids:
                checkins.append({
                    'aluno_id': int(aluno_id),
                    'data_entrada': datetime.now().isoformat()
                })
            
            # Estrutura a mensagem conforme esperado pelo consumidor
            payload = {
                'checkins': checkins,
                'timestamp': datetime.now().isoformat()
            }
            
            # Fazer requisição para a API
            response = api_request(
                request,
                'post',
                "/checkin/batch",
                json=payload
            )
            
            if response.status_code == 202:  # 202 Accepted
                messages.success(request, f"{len(alunos_ids)} check-ins enviados para processamento em segundo plano!")
            else:
                messages.error(request, f"Erro ao registrar check-ins em lote: {response.status_code}")
                if response.text:
                    messages.error(request, response.text)
        
        except Exception as e:
            messages.error(request, f"Erro ao conectar com a API: {str(e)}")
    
    # Obter lista de alunos para o formulário
    try:
        response = api_request(request, 'get', "/aluno/")
        alunos = response.json() if response.status_code == 200 else []
    except Exception:
        alunos = []
    
    return render(request, 'dashboard/checkin_batch.html', {'alunos': alunos})


def relatorios(request):
    """
    Página para gerenciar relatórios e atualização do modelo de predição.
    """
    resposta_relatorio = None
    resposta_modelo = None
    resposta_probabilidades = None
    relatorios_gerados = []
    
    # Listar relatórios existentes
    try:
        response = api_request(request, 'get', "/relatorio/listar")
        if response.status_code == 200:
            relatorios_gerados = response.json()
    except Exception as e:
        messages.error(request, f"Erro ao obter lista de relatórios: {str(e)}")
    
    if request.method == 'POST':
        try:
            # Verificar qual formulário foi submetido
            if 'gerar_relatorio' in request.POST:
                # Pegar data do formulário ou usar None para data atual
                data = request.POST.get('data_relatorio')
                
                # Verificar se a data está em formato válido
                if data:
                    try:
                        # Certificar que a data está no formato YYYY-MM-DD
                        datetime.strptime(data, '%Y-%m-%d')
                        payload = {'data': data}
                    except ValueError:
                        messages.error(request, "Formato de data inválido. Use o formato YYYY-MM-DD.")
                        return redirect('dashboard:relatorios')
                else:
                    payload = {}
                
                # Fazer requisição para a API
                response = api_request(
                    request,
                    'post',
                    "/relatorio/diario",
                    json=payload
                )
                
                if response.status_code == 202:  # 202 Accepted
                    messages.success(request, "Solicitação de relatório enviada com sucesso! Atualize a página em alguns segundos para ver o relatório.")
                    resposta_relatorio = response.json()
                else:
                    messages.error(request, f"Erro ao solicitar relatório: {response.status_code}")
                    if response.text:
                        messages.error(request, response.text)
                    
            elif 'atualizar_modelo' in request.POST:
                # Fazer requisição para a API
                response = api_request(request, 'post', "/relatorio/churn/atualizar-modelo")
                
                if response.status_code == 202:  # 202 Accepted
                    messages.success(request, "Solicitação de atualização do modelo enviada com sucesso!")
                    resposta_modelo = response.json()
                else:
                    messages.error(request, f"Erro ao solicitar atualização do modelo: {response.status_code}")
                    if response.text:
                        messages.error(request, response.text)
            
            elif 'calcular_probabilidades' in request.POST:
                # Fazer requisição para a API
                response = api_request(request, 'post', "/relatorio/churn/calcular-probabilidades")
                
                if response.status_code == 202:  # 202 Accepted
                    messages.success(request, "Solicitação de cálculo de probabilidades de churn enviada com sucesso!")
                    resposta_probabilidades = response.json()
                else:
                    messages.error(request, f"Erro ao solicitar cálculo de probabilidades: {response.status_code}")
                    if response.text:
                        messages.error(request, response.text)
        
        except Exception as e:
            messages.error(request, f"Erro ao conectar com a API: {str(e)}")
    
    return render(request, 'dashboard/relatorios.html', {
        'resposta_relatorio': resposta_relatorio,
        'resposta_modelo': resposta_modelo,
        'resposta_probabilidades': resposta_probabilidades,
        'relatorios_gerados': relatorios_gerados,
        'data_hoje': datetime.now().strftime('%Y-%m-%d')
    })


def download_relatorio(request, nome_arquivo):
    """
    View para download de relatório.
    """
    try:
        response = api_request(request, 'get', f"/relatorio/download/{nome_arquivo}", stream=True)
        
        if response.status_code == 200:
            # Preparar a resposta para download
            django_response = HttpResponse(
                response.content,
                content_type="text/csv"
            )
            django_response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return django_response
        else:
            messages.error(request, f"Erro ao baixar relatório: {response.status_code}")
            return redirect('dashboard:relatorios')
    
    except Exception as e:
        messages.error(request, f"Erro ao conectar com a API: {str(e)}")
        return redirect('dashboard:relatorios')


def status_sistema(request):
    """
    Exibe informações sobre o status do sistema.
    """
    status = {}
    mensagem_erro = ""
    
    try:
        # Obter status do sistema usando api_request
        response = api_request(request, 'get', "/status/")
        
        if response.status_code == 200:
            status = response.json()
            
            # Verificar se todos os serviços estão online
            servicos = ['api', 'database', 'redis', 'cache', 'rabbitmq']
            status_servicos = {}
            
            # Verificar cada serviço
            for servico in servicos:
                if servico in status:
                    status_servicos[servico] = (status.get(servico, {}).get('status') == 'online')
            
            # Tratar caso especial: se tanto redis quanto cache estiverem presentes
            if 'redis' in status_servicos and 'cache' in status_servicos:
                # Usar apenas um deles para evitar duplicidade
                del status_servicos['cache']
            
            # Considerar serviços como online apenas se todos os serviços cadastrados estiverem online
            status['todos_servicos_online'] = all(status_servicos.values()) if status_servicos else False
            
            # Log para debug
            print(f"Status dos serviços: {status_servicos}")
            print(f"Todos serviços online: {status['todos_servicos_online']}")
            
        else:
            mensagem_erro = f"Erro ao obter status do sistema: {response.status_code}"
            if response.text:
                # Limitar o tamanho da resposta para evitar mensagens muito grandes
                texto_erro = response.text[:200]
                if len(response.text) > 200:
                    texto_erro += "..."
                mensagem_erro += f" - {texto_erro}"
    
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    context = {
        'status': status,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/status_sistema.html', context)


def estatisticas_modelo(request):
    """
    Exibe estatísticas dos modelos de churn treinados.
    """
    modelos = []
    mensagem_erro = ""
    
    try:
        # Obter lista de modelos da API
        response = api_request(request, 'get', "/churn/modelos")
        
        if response.status_code == 200:
            modelos = response.json().get('modelos', [])
            
            # Adicionar informações formatadas para exibição
            for modelo in modelos:
                # Formatar data de criação
                if 'data_criacao' in modelo:
                    try:
                        data_criacao = datetime.fromisoformat(modelo['data_criacao'].replace('Z', '+00:00'))
                        modelo['data_criacao_formatada'] = data_criacao.strftime('%d/%m/%Y %H:%M')
                    except:
                        modelo['data_criacao_formatada'] = modelo['data_criacao']
                
                # Formatar métricas como percentuais
                for metrica in ['acuracia', 'precisao', 'recall', 'f1_score', 'auc']:
                    if metrica in modelo and modelo[metrica] is not None:
                        modelo[f'{metrica}_pct'] = f"{modelo[metrica]*100:.2f}%"
                
                # Adicionar contagem de ativos/inativos
                modelo['total_amostras_formatado'] = f"{modelo.get('total_amostras', 0):,}".replace(',', '.')
                
        else:
            mensagem_erro = f"Erro ao obter lista de modelos: {response.status_code} - {response.text}"
    
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    # Adiciona ação para treinar um novo modelo
    if request.method == 'POST' and 'treinar_modelo' in request.POST:
        try:
            treinar_response = api_request(request, 'post', "/churn/modelo/treinar")
            if treinar_response.status_code == 202:
                messages.success(request, "Solicitação para treinar novo modelo enviada com sucesso!")
            else:
                mensagem_erro = f"Erro ao solicitar treinamento do modelo: {treinar_response.status_code} - {treinar_response.text}"
                messages.error(request, mensagem_erro)
        except Exception as e:
            mensagem_erro = f"Erro ao solicitar treinamento: {str(e)}"
            messages.error(request, mensagem_erro)
        
        return redirect('dashboard:estatisticas_modelo')
    
    context = {
        'modelos': modelos,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/estatisticas_modelo.html', context)


def detalhe_modelo(request, modelo_id):
    """
    Exibe detalhes de um modelo específico.
    """
    modelo = None
    mensagem_erro = ""
    
    try:
        # Obter detalhes do modelo
        response = api_request(request, 'get', f"/churn/modelos/{modelo_id}")
        
        if response.status_code == 200:
            modelo = response.json()
            
            # Formatar data de criação
            if 'data_criacao' in modelo:
                try:
                    data_criacao = datetime.fromisoformat(modelo['data_criacao'].replace('Z', '+00:00'))
                    modelo['data_criacao_formatada'] = data_criacao.strftime('%d/%m/%Y %H:%M')
                except:
                    modelo['data_criacao_formatada'] = modelo['data_criacao']
            
            # Formatar métricas como percentuais
            for metrica in ['acuracia', 'precisao', 'recall', 'f1_score', 'auc']:
                if metrica in modelo and modelo[metrica] is not None:
                    modelo[f'{metrica}_pct'] = f"{modelo[metrica]*100:.2f}%"
            
            # Calcular proporção de ativos/inativos para o gráfico
            total = modelo.get('qtd_ativos', 0) + modelo.get('qtd_inativos', 0)
            if total > 0:
                modelo['pct_ativos'] = modelo.get('qtd_ativos', 0) / total * 100
                modelo['pct_inativos'] = modelo.get('qtd_inativos', 0) / total * 100
            else:
                modelo['pct_ativos'] = 0
                modelo['pct_inativos'] = 0
                
            # Formatar importância das features para exibição
            if 'importancia_features' in modelo and modelo['importancia_features']:
                # Ordenar por importância e limitar a top N features
                importancia_ordenada = sorted(
                    modelo['importancia_features'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]  # Top 10 features
                
                modelo['top_features'] = [
                    {'nome': nome, 'importancia': valor, 'importancia_pct': f"{valor*100:.2f}%"}
                    for nome, valor in importancia_ordenada
                ]
            
            # Processar matriz de confusão
            if 'matriz_confusao' in modelo and modelo['matriz_confusao']:
                cm = modelo['matriz_confusao']
                if len(cm) == 2 and len(cm[0]) == 2:
                    tn, fp = cm[0]
                    fn, tp = cm[1]
                    modelo['matriz_confusao_formatada'] = {
                        'tn': tn,
                        'fp': fp,
                        'fn': fn,
                        'tp': tp,
                        'total': tn + fp + fn + tp
                    }
                
        else:
            mensagem_erro = f"Erro ao obter detalhes do modelo: {response.status_code} - {response.text}"
    
    except requests.RequestException as e:
        mensagem_erro = f"Erro de conexão com a API: {str(e)}"
    except Exception as e:
        mensagem_erro = f"Erro inesperado: {str(e)}"
    
    context = {
        'modelo': modelo,
        'mensagem_erro': mensagem_erro
    }
    
    return render(request, 'dashboard/detalhe_modelo.html', context)


def login_view(request):
    """
    Exibe a página de login.
    """
    return render(request, 'dashboard/login.html')


def logout_view(request):
    """
    Realiza o logout do usuário e redireciona para a página de login.
    """
    # Não precisamos fazer nada além de redirecionar para a página de login
    # O logout será feito pelo JavaScript no frontend
    return redirect('dashboard:login')


def sync_token(request):
    """
    Recebe o token JWT do cliente e o armazena na sessão.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            
            if token:
                # Armazenar o token na sessão
                request.session['access_token'] = token
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Token não fornecido'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405) 