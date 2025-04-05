from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import logging
import os

from app.api.api import api_router
from app.core.config import settings
from app.core.cache import get_cache
import app.models.aluno  # Importa os modelos para que eles sejam registrados
import app.models.usuario  # Importa o modelo de usuário
from app.db.database import Base, engine, get_db, SessionLocal
from app.services.usuario_service import UsuarioService

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar cliente RabbitMQ
from app.queue.rabbitmq import get_rabbitmq_client

# Criar as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# Criar a aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas da API
app.include_router(api_router)

# Verificar e criar diretório static se não existir
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def create_admin_user():
    """Função para criar o usuário administrador padrão"""
    try:
        db = SessionLocal()
        try:
            service = UsuarioService(db)
            # Verificar se o usuário admin já existe
            if not service.get_user_by_username("admin"):
                # Criar usuário admin
                admin = service.create_admin_user(
                    username="admin", 
                    email="admin@academia.com", 
                    password="admin"
                )
                logger.info(f"Usuário administrador '{admin.username}' criado com sucesso!")
            else:
                logger.info("Usuário administrador 'admin' já existe.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao criar usuário administrador: {e}")


@app.on_event("startup")
async def startup_event():
    """
    Função executada quando a aplicação inicia.
    """
    # Criar usuário administrador
    create_admin_user()
    
    # Inicializar cache Redis
    try:
        logger.info("Inicializando conexão com Redis Cache...")
        cache = get_cache()
        if cache.is_available():
            logger.info("Conexão com Redis Cache estabelecida com sucesso")
        else:
            if hasattr(cache, 'use_dummy') and cache.use_dummy:
                logger.warning("Redis não disponível. Usando cache em memória como fallback.")
            else:
                logger.warning("Cache Redis não está disponível. Algumas operações podem ser mais lentas.")
    except Exception as e:
        logger.error(f"Erro ao inicializar Redis Cache: {e}")
        logger.warning("A aplicação continuará funcionando, mas o cache não estará disponível")
        
    try:
        # Inicializar cliente RabbitMQ
        logger.info("Inicializando conexão com RabbitMQ...")
        client = get_rabbitmq_client()
        
        # Verificar conexão - apenas testando se o cliente está funcionando
        if client and client.is_connected():
            logger.info("Conexão com RabbitMQ estabelecida com sucesso")
        else:
            logger.warning("RabbitMQ não está disponível. Recursos assíncronos podem não funcionar corretamente.")
    except Exception as e:
        logger.error(f"Erro ao inicializar RabbitMQ: {e}")
        logger.warning("A aplicação continuará funcionando, mas recursos de fila assíncrona não estarão disponíveis")
    
    # Criar arquivo HTML de login se não existir
    login_html_path = os.path.join(static_dir, "login.html")
    if not os.path.exists(login_html_path):
        with open(login_html_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sistema de Academia</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            min-height: 100vh;
        }
        
        /* Barra lateral */
        .sidebar {
            width: 250px;
            background-color: #333;
            color: white;
            padding-top: 20px;
            transition: width 0.3s;
        }
        
        .sidebar-header {
            padding: 0 20px 20px;
            border-bottom: 1px solid #444;
            text-align: center;
        }
        
        .sidebar-header h2 {
            margin: 0;
            font-size: 20px;
        }
        
        .sidebar-menu {
            list-style: none;
            padding: 0;
            margin: 20px 0;
        }
        
        .sidebar-menu li {
            padding: 10px 20px;
            border-bottom: 1px solid #444;
        }
        
        .sidebar-menu li a {
            color: #ddd;
            text-decoration: none;
            display: block;
            transition: color 0.3s;
        }
        
        .sidebar-menu li a:hover {
            color: #4CAF50;
        }
        
        .sidebar-menu li.active {
            background-color: #4CAF50;
        }
        
        .sidebar-menu li.active a {
            color: white;
        }
        
        /* Conteúdo principal */
        .main-content {
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .login-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            padding: 40px;
            width: 350px;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }
        
        button {
            width: 100%;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 12px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        
        button:hover {
            background-color: #45a049;
        }
        
        .error-message {
            color: #f44336;
            margin-top: 20px;
            text-align: center;
            display: none;
        }
        
        .logo {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .logo img {
            max-width: 150px;
        }
        
        .login-info {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
            font-size: 14px;
            color: #666;
            text-align: center;
        }
        
        /* Responsividade */
        @media screen and (max-width: 768px) {
            body {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                min-height: auto;
            }
            
            .login-container {
                width: 90%;
                max-width: 350px;
            }
        }
    </style>
</head>
<body>
    <!-- Barra lateral -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Sistema de Academia</h2>
        </div>
        <ul class="sidebar-menu">
            <li><a href="/">Início</a></li>
            <li class="active"><a href="/login">Login</a></li>
            <li><a href="/docs">Documentação API</a></li>
        </ul>
    </div>

    <!-- Conteúdo principal -->
    <div class="main-content">
        <div class="login-container">
            <div class="logo">
                <h2>Sistema de Academia</h2>
            </div>
            <h1>Login</h1>
            <div id="error-message" class="error-message"></div>
            <form id="login-form">
                <div class="form-group">
                    <label for="username">Usuário</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Senha</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit">Entrar</button>
            </form>
            <div class="login-info">
                <p>Usuário padrão: <strong>admin</strong><br>Senha: <strong>admin</strong></p>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('error-message');
            
            try {
                const response = await fetch('/api/auth/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Erro ao realizar login');
                }
                
                // Armazenar token JWT no localStorage
                localStorage.setItem('access_token', data.access_token);
                
                // Redirecionar para a página principal
                window.location.href = '/';
                
            } catch (error) {
                errorMessage.textContent = error.message;
                errorMessage.style.display = 'block';
            }
        });
    </script>
</body>
</html>""")
        logger.info("Página de login criada com sucesso!")

    # Criar arquivo HTML para a página inicial
    index_html_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_html_path):
        with open(index_html_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Academia</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            display: flex;
            min-height: 100vh;
        }
        
        /* Barra lateral */
        .sidebar {
            width: 250px;
            background-color: #333;
            color: white;
            padding-top: 20px;
            transition: width 0.3s;
        }
        
        .sidebar-header {
            padding: 0 20px 20px;
            border-bottom: 1px solid #444;
            text-align: center;
        }
        
        .sidebar-header h2 {
            margin: 0;
            font-size: 20px;
        }
        
        .sidebar-menu {
            list-style: none;
            padding: 0;
            margin: 20px 0;
        }
        
        .sidebar-menu li {
            padding: 10px 20px;
            border-bottom: 1px solid #444;
        }
        
        .sidebar-menu li a {
            color: #ddd;
            text-decoration: none;
            display: block;
            transition: color 0.3s;
        }
        
        .sidebar-menu li a:hover {
            color: #4CAF50;
        }
        
        .sidebar-menu li.active {
            background-color: #4CAF50;
        }
        
        .sidebar-menu li.active a {
            color: white;
        }
        
        /* Conteúdo principal */
        .main-content {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        
        .header {
            background-color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .user-info {
            display: flex;
            align-items: center;
        }
        
        .user-info button {
            margin-left: 15px;
            padding: 8px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .user-info button:hover {
            background-color: #45a049;
        }
        
        .dashboard {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
            min-width: 250px;
        }
        
        .card h2 {
            margin-top: 0;
            color: #333;
            font-size: 20px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        
        .card ul {
            list-style-type: none;
            padding: 0;
        }
        
        .card li {
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .card li a {
            text-decoration: none;
            color: #2980b9;
        }
        
        .card li a:hover {
            text-decoration: underline;
        }
        
        .login-message {
            text-align: center;
            margin: 100px auto;
            max-width: 500px;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .login-message h2 {
            color: #333;
        }
        
        .login-message a {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        
        .login-message a:hover {
            background-color: #45a049;
        }
        
        .hidden {
            display: none;
        }
        
        /* Responsividade */
        @media screen and (max-width: 768px) {
            body {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                min-height: auto;
            }
            
            .card {
                min-width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- Barra lateral - sempre visível -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Sistema de Academia</h2>
        </div>
        <ul class="sidebar-menu">
            <li class="active"><a href="/">Início</a></li>
            <li><a href="/login">Login</a></li>
            <li><a href="/docs">Documentação API</a></li>
            <li id="menu-alunos" class="hidden"><a href="/api/aluno/">Alunos</a></li>
            <li id="menu-churn" class="hidden"><a href="/docs#/churn">Análise de Churn</a></li>
            <li id="menu-status" class="hidden"><a href="/api/status/">Status do Sistema</a></li>
        </ul>
    </div>

    <!-- Conteúdo para usuários autenticados -->
    <div id="auth-content" class="main-content hidden">
        <div class="header">
            <h1>Painel de Controle</h1>
            <div class="user-info">
                <span id="username-display">Usuário</span>
                <button id="logout-btn">Sair</button>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h2>Alunos</h2>
                <ul>
                    <li><a href="/api/aluno/" target="_blank">Listar todos os alunos</a></li>
                    <li><a href="/docs#/alunos/criar_aluno_aluno_registro_post" target="_blank">Registrar novo aluno</a></li>
                    <li><a href="/docs#/alunos/registrar_checkin_aluno_checkin_post" target="_blank">Registrar check-in</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h2>Análise de Churn</h2>
                <ul>
                    <li><a href="/docs#/churn/calcular_probabilidade_aluno_churn_aluno__aluno_id__get" target="_blank">Verificar risco de churn</a></li>
                    <li><a href="/docs#/churn/treinar_modelo_churn_treinar_modelo_post" target="_blank">Treinar modelo de churn</a></li>
                </ul>
            </div>

            <div class="card">
                <h2>Administração</h2>
                <ul>
                    <li><a href="/api/status/" target="_blank">Status do sistema</a></li>
                    <li><a href="/docs" target="_blank">Documentação da API</a></li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Conteúdo para usuários não autenticados -->
    <div id="no-auth-content" class="main-content">
        <div class="login-message">
            <h2>Bem-vindo ao Sistema de Academia</h2>
            <p>Para acessar o sistema completo, faça login com suas credenciais.</p>
            <p>Usuário padrão: <strong>admin</strong> / Senha: <strong>admin</strong></p>
            <a href="/login">Fazer Login</a>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const authContent = document.getElementById('auth-content');
            const noAuthContent = document.getElementById('no-auth-content');
            const usernameDisplay = document.getElementById('username-display');
            const logoutBtn = document.getElementById('logout-btn');
            const menuAlunos = document.getElementById('menu-alunos');
            const menuChurn = document.getElementById('menu-churn');
            const menuStatus = document.getElementById('menu-status');
            
            // Verificar se o usuário está autenticado
            const token = localStorage.getItem('access_token');
            
            if (token) {
                // Mostrar conteúdo para usuários autenticados
                authContent.classList.remove('hidden');
                noAuthContent.classList.add('hidden');
                
                // Mostrar itens de menu adicionais
                menuAlunos.classList.remove('hidden');
                menuChurn.classList.remove('hidden');
                menuStatus.classList.remove('hidden');
                
                // Obter informações do usuário
                fetchUserInfo(token);
            } else {
                // Mostrar mensagem para usuários não autenticados
                authContent.classList.add('hidden');
                noAuthContent.classList.remove('hidden');
                
                // Esconder itens de menu adicionais
                menuAlunos.classList.add('hidden');
                menuChurn.classList.add('hidden');
                menuStatus.classList.add('hidden');
            }
            
            // Configurar botão de logout
            logoutBtn.addEventListener('click', () => {
                localStorage.removeItem('access_token');
                window.location.href = '/login';
            });
        });
        
        async function fetchUserInfo(token) {
            try {
                const response = await fetch('/api/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const userData = await response.json();
                    document.getElementById('username-display').textContent = userData.username;
                } else {
                    // Token inválido ou expirado
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error('Erro ao obter informações do usuário:', error);
            }
        }
    </script>
</body>
</html>""")
        logger.info("Página inicial criada com sucesso!")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Função executada quando a aplicação encerra.
    """
    try:
        # Fechar conexão com RabbitMQ se estiver aberta
        logger.info("Fechando conexão com RabbitMQ...")
        client = get_rabbitmq_client()
        if client:
            client.close()
    except Exception as e:
        logger.error(f"Erro ao fechar conexão com RabbitMQ: {e}")


@app.get("/", response_class=HTMLResponse)
def root():
    """
    Página inicial do sistema
    """
    with open(os.path.join(static_dir, "index.html"), "r") as f:
        return f.read()


@app.get("/login")
async def login_page():
    """
    Redireciona para a página de login
    """
    return RedirectResponse(url="/static/login.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    ) 