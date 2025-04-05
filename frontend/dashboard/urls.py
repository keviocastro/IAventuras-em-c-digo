from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('alunos/', views.lista_alunos, name='lista_alunos'),
    path('alunos/<int:aluno_id>/', views.detalhe_aluno, name='detalhe_aluno'),
    path('alunos/<int:aluno_id>/frequencia/', views.frequencia_aluno, name='frequencia_aluno'),
    path('alunos/<int:aluno_id>/risco-churn/', views.risco_churn_aluno, name='risco_churn_aluno'),
    path('alunos/cadastro/', views.cadastro_aluno, name='cadastro_aluno'),
    path('alunos/sintetico/', views.cadastro_aluno_sintetico, name='cadastro_aluno_sintetico'),
    path('checkin/', views.checkin, name='checkin'),
    path('checkin/batch/', views.checkin_batch, name='checkin_batch'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('evolucao-aluno/', views.evolucao_aluno, name='evolucao_aluno'),
    path('status-sistema/', views.status_sistema, name='status_sistema'),
    path('sync-token/', views.sync_token, name='sync_token'),
    
    # Estatísticas do modelo de churn
    path('modelo-churn/', views.estatisticas_modelo, name='estatisticas_modelo'),
    path('modelo-churn/<int:modelo_id>/', views.detalhe_modelo, name='detalhe_modelo'),
    
    # Novas URLs para testes do RabbitMQ
    path('relatorios/download/<str:nome_arquivo>/', views.download_relatorio, name='download_relatorio'),
] 