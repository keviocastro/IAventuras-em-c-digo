import json
import logging
import datetime
import time
import os
import csv
import joblib
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct, case, cast, String
from sqlalchemy.sql import text

from app.db.database import SessionLocal
from app.models.aluno import Checkin, Aluno, Plano, ChurnProbability, ModeloChurnEstatisticas
from app.services.aluno_service import AlunoService
from app.core.cache import get_cache
from app.queue.rabbitmq import (
    RabbitMQClient, 
    CHECKIN_QUEUE, 
    REPORT_QUEUE, 
    MODEL_UPDATE_QUEUE,
    CHURN_PROB_QUEUE
)

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretório para salvar relatórios
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)


def process_checkin_message(ch, method, properties, body):
    """
    Processa mensagens da fila de checkins em massa.
    """
    try:
        # Converter o body de bytes para string e depois para JSON
        message_str = body.decode('utf-8')
        logger.info(f"Mensagem recebida: {message_str}")
        
        data = json.loads(message_str)
        
        # Verificar se checkins está como string (JSON serializado novamente)
        checkins_data = data.get("checkins", [])
        
        # Se checkins_data for uma string, deserializar novamente
        if isinstance(checkins_data, str):
            try:
                inner_data = json.loads(checkins_data)
                # Verificar se é um dicionário com checkins
                if isinstance(inner_data, dict) and "checkins" in inner_data:
                    checkins = inner_data.get("checkins", [])
                else:
                    checkins = inner_data if isinstance(inner_data, list) else []
            except json.JSONDecodeError:
                logger.error(f"Erro ao decodificar inner JSON: {checkins_data}")
                checkins = []
        else:
            checkins = checkins_data
        
        if not checkins:
            logger.warning("Mensagem de checkin recebida sem dados")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        logger.info(f"Processando {len(checkins)} checkins")
        
        # Criar sessão do banco de dados
        db = SessionLocal()
        try:
            # Processar cada checkin
            for checkin_data in checkins:
                aluno_id = checkin_data.get("aluno_id")
                
                if not aluno_id:
                    logger.warning(f"Checkin sem aluno_id: {checkin_data}")
                    continue
                
                # Verificar se o aluno já está na academia (sem data de saída)
                checkin_aberto = db.query(Checkin).filter(
                    Checkin.aluno_id == aluno_id,
                    Checkin.data_saida.is_(None)
                ).first()

                if checkin_aberto:
                    # Se já houver um checkin aberto, registra a saída
                    logger.info(f"Aluno {aluno_id} já está na academia. Registrando saída.")
                    agora = datetime.datetime.now()
                    duracao = (agora - checkin_aberto.data_entrada).total_seconds() / 60
                    checkin_aberto.data_saida = agora
                    checkin_aberto.duracao_minutos = int(duracao)
                    db.commit()
                    db.refresh(checkin_aberto)
                else:
                    # Registrar novo checkin de entrada
                    data_entrada_str = checkin_data.get("data_entrada")
                    
                    # Criar o checkin com data atual se não fornecida
                    if data_entrada_str:
                        try:
                            data_entrada = datetime.datetime.fromisoformat(data_entrada_str)
                        except (ValueError, TypeError):
                            logger.warning(f"Formato de data inválido: {data_entrada_str}, usando data atual")
                            data_entrada = datetime.datetime.now()
                    else:
                        data_entrada = datetime.datetime.now()
                    
                    # Criar o checkin
                    checkin = Checkin(
                        aluno_id=aluno_id,
                        data_entrada=data_entrada
                    )
                    
                    # Se houver data de saída, adicionar
                    data_saida_str = checkin_data.get("data_saida")
                    if data_saida_str:
                        try:
                            data_saida = datetime.datetime.fromisoformat(data_saida_str)
                            checkin.data_saida = data_saida
                            
                            # Calcular duração em minutos
                            duracao = (data_saida - data_entrada).total_seconds() / 60
                            checkin.duracao_minutos = int(duracao)
                        except (ValueError, TypeError):
                            logger.warning(f"Formato de data de saída inválido: {data_saida_str}")
                    
                    db.add(checkin)
            
            # Commit das alterações
            db.commit()
            logger.info(f"{len(checkins)} checkins processados com sucesso")
            
            # Confirmar mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao processar checkins: {e}")
            # Não confirmar mensagem para que seja reprocessada
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db.close()
            
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}. Body recebido: {body}")
        # Confirmar de qualquer forma para não ficar em loop com mensagens inválidas
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def gerar_relatorio_diario(db, data_relatorio):
    """
    Gera um relatório diário real com informações de frequência.
    
    Args:
        db: Sessão do banco de dados
        data_relatorio: Data do relatório no formato 'YYYY-MM-DD'
    
    Returns:
        str: Caminho do arquivo do relatório gerado
    """
    logger.info(f"Gerando relatório diário para data: {data_relatorio}")
    
    # Converter string para data
    try:
        # Verificar se data_relatorio é um dicionário ou string JSON
        if isinstance(data_relatorio, dict) or (
            isinstance(data_relatorio, str) and (data_relatorio.startswith('{') or data_relatorio.startswith('['))
        ):
            try:
                # Tentar interpretar como JSON se parece ser um
                if isinstance(data_relatorio, str):
                    data_json = json.loads(data_relatorio)
                else:
                    data_json = data_relatorio
                
                # Extrair o campo 'date' se existir
                if isinstance(data_json, dict) and 'date' in data_json:
                    data_relatorio = data_json.get('date')
                else:
                    # Se não conseguir extrair, usar data atual
                    data_relatorio = datetime.datetime.now().strftime("%Y-%m-%d")
            except (json.JSONDecodeError, TypeError):
                # Se falhar ao decodificar, usar data atual
                data_relatorio = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Agora devemos ter uma string de data
        data = datetime.datetime.strptime(data_relatorio, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"Formato de data inválido: {data_relatorio}. Erro: {str(e)}")
        # Usar data atual como fallback
        data = datetime.datetime.now().date()
    
    # Data de início e fim (todo o dia)
    data_inicio = datetime.datetime.combine(data, datetime.time.min)
    data_fim = datetime.datetime.combine(data, datetime.time.max)
    
    # 1. Relatório geral do dia
    checkins_dia = db.query(Checkin).filter(
        Checkin.data_entrada >= data_inicio,
        Checkin.data_entrada <= data_fim
    ).all()
    
    total_checkins = len(checkins_dia)
    alunos_unicos = len(set(c.aluno_id for c in checkins_dia))
    checkins_completos = len([c for c in checkins_dia if c.data_saida is not None])
    
    # 2. Relatório por hora do dia
    checkins_por_hora = {}
    for hora in range(24):
        hora_inicio = datetime.datetime.combine(data, datetime.time(hora, 0))
        hora_fim = datetime.datetime.combine(data, datetime.time(hora, 59, 59))
        
        count = db.query(Checkin).filter(
            Checkin.data_entrada >= hora_inicio,
            Checkin.data_entrada <= hora_fim
        ).count()
        
        checkins_por_hora[hora] = count
    
    # 3. Relatório por plano
    checkins_por_plano = db.query(
        Plano.nome,
        func.count(Checkin.id).label('total')
    ).join(
        Aluno, Aluno.id == Checkin.aluno_id
    ).join(
        Plano, Plano.id == Aluno.plano_id
    ).filter(
        Checkin.data_entrada >= data_inicio,
        Checkin.data_entrada <= data_fim
    ).group_by(
        Plano.nome
    ).all()
    
    # 4. Duração média das visitas
    duracao_media = db.query(
        func.avg(Checkin.duracao_minutos).label('media')
    ).filter(
        Checkin.data_entrada >= data_inicio,
        Checkin.data_entrada <= data_fim,
        Checkin.duracao_minutos.isnot(None)
    ).scalar() or 0
    
    # 5. Lista de alunos presentes
    alunos_presentes = db.query(
        Aluno.id,
        Aluno.nome,
        Checkin.data_entrada,
        Checkin.data_saida,
        Checkin.duracao_minutos
    ).join(
        Checkin, Checkin.aluno_id == Aluno.id
    ).filter(
        Checkin.data_entrada >= data_inicio,
        Checkin.data_entrada <= data_fim
    ).order_by(
        Checkin.data_entrada
    ).all()
    
    # Formatar a data como string para o nome do arquivo
    data_str = data.strftime("%Y-%m-%d")
    
    # Salvar relatório em CSV
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_diario_{data_str}_{timestamp}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Cabeçalho e resumo
            writer.writerow(['RELATÓRIO DIÁRIO DE FREQUÊNCIA'])
            writer.writerow([f'Data: {data_str}'])
            writer.writerow([f'Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
            writer.writerow([])
            
            # Resumo geral
            writer.writerow(['RESUMO GERAL'])
            writer.writerow(['Total de check-ins', total_checkins])
            writer.writerow(['Alunos únicos', alunos_unicos])
            writer.writerow(['Check-ins completos (entrada e saída)', checkins_completos])
            writer.writerow(['Duração média (minutos)', round(duracao_media, 1)])
            writer.writerow([])
            
            # Distribuição por hora
            writer.writerow(['DISTRIBUIÇÃO POR HORA'])
            writer.writerow(['Hora', 'Total de check-ins'])
            for hora, total in checkins_por_hora.items():
                writer.writerow([f'{hora:02d}:00', total])
            writer.writerow([])
            
            # Distribuição por plano
            writer.writerow(['DISTRIBUIÇÃO POR PLANO'])
            writer.writerow(['Plano', 'Total de check-ins'])
            for plano, total in checkins_por_plano:
                writer.writerow([plano, total])
            writer.writerow([])
            
            # Lista de alunos presentes
            writer.writerow(['LISTA DE ALUNOS PRESENTES'])
            writer.writerow(['ID', 'Nome', 'Entrada', 'Saída', 'Duração (min)'])
            for aluno_id, nome, entrada, saida, duracao in alunos_presentes:
                entrada_str = entrada.strftime("%H:%M:%S") if entrada else ''
                saida_str = saida.strftime("%H:%M:%S") if saida else ''
                writer.writerow([aluno_id, nome, entrada_str, saida_str, duracao or ''])
    
    except Exception as e:
        logger.error(f"Erro ao salvar relatório CSV: {e}")
        return None
    
    logger.info(f"Relatório salvo em: {filepath}")
    return filepath


def process_report_message(ch, method, properties, body):
    """
    Processa mensagens da fila de geração de relatórios diários.
    """
    try:
        # Decodificar e converter para JSON
        message_str = body.decode('utf-8')
        logger.info(f"Mensagem recebida para relatório: {message_str}")
        
        data = json.loads(message_str)
        # Extrair apenas o campo date (data) da mensagem
        report_date = data.get("date")
        
        # Se não especificado, usar a data atual
        if not report_date:
            report_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Processando relatório para data: {report_date}")
        
        # Criar sessão do banco de dados
        db = SessionLocal()
        try:
            # Gerar o relatório real
            filepath = gerar_relatorio_diario(db, report_date)
            
            if filepath:
                logger.info(f"Relatório para {report_date} gerado com sucesso: {filepath}")
            else:
                logger.error(f"Falha ao gerar relatório para {report_date}")
            
            # Confirmar mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
            # Não confirmar mensagem para que seja reprocessada
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db.close()
            
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}. Body recebido: {body}")
        # Confirmar de qualquer forma para não ficar em loop com mensagens inválidas
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def process_model_update_message(ch, method, properties, body):
    """
    Processa mensagens da fila de atualização do modelo de previsão de churn.
    """
    try:
        # Decodificar mensagem
        message_str = body.decode('utf-8')
        logger.info(f"Iniciando atualização do modelo de previsão de churn: {message_str}")
        
        # Criar sessão do banco de dados
        db = SessionLocal()
        try:
            # Consulta para obter dados dos alunos e checkins
            query = text("""
                SELECT
                    a.id as aluno_id,
                    a.nome,
                    a.ativo,
                    p.id as plano_id,
                    p.nome as plano_nome,
                    p.valor_mensal,
                    COUNT(c.id) as total_checkins,
                    MAX(c.data_entrada) as ultima_visita,
                    CASE 
                        WHEN MAX(c.data_entrada) IS NOT NULL THEN 
                            EXTRACT(DAY FROM NOW() - MAX(c.data_entrada))
                        ELSE 365
                    END as dias_desde_ultima_visita,
                    AVG(c.duracao_minutos) as duracao_media,
                    CASE 
                        WHEN COUNT(c.id) > 0 THEN 
                            COUNT(c.id) / GREATEST(1, EXTRACT(DAY FROM NOW() - MIN(c.data_entrada)) / 7)
                        ELSE 0
                    END as media_visitas_semanais
                FROM
                    alunos a
                LEFT JOIN
                    planos p ON a.plano_id = p.id
                LEFT JOIN
                    checkins c ON a.id = c.aluno_id
                GROUP BY
                    a.id, a.nome, a.ativo, p.id, p.nome, p.valor_mensal
            """)
            
            # Executar consulta
            result = db.execute(query)
            
            # Converter os resultados para um dicionário que pode ser usado pelo pandas
            rows = [dict(row._mapping) for row in result.all()]
            
            # Converter valores decimais para float para evitar erro "unsupported operand type(s) for -: 'float' and 'decimal.Decimal'"
            for row in rows:
                for key, value in row.items():
                    if hasattr(value, 'quantize'):  # Verifica se é um decimal.Decimal
                        row[key] = float(value)
            
            # Criar DataFrame
            df = pd.DataFrame(rows)
            
            # Verificar se existem dados suficientes
            if len(df) < 10:
                logger.warning("Dados insuficientes para treinar o modelo. São necessários pelo menos 10 alunos.")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Preprocessamento
            df['dias_desde_ultima_visita'].fillna(365, inplace=True)  # Valor alto para alunos sem visitas
            df['duracao_media'].fillna(0, inplace=True)
            df['media_visitas_semanais'].fillna(0, inplace=True)
            
            # Salvar um pouco do ruído no status ativo/inativo para melhorar o modelo
            # Isso cria uma pequena sobreposição entre as classes (5% de chance de inverter o status)
            df['churn'] = 1 - df['ativo']  # Converter ativo (1) para churn (0) e vice-versa
            
            # Definir features numéricas e categóricas
            features_categoricas = ['plano_nome']
            features_numericas = ['total_checkins', 'dias_desde_ultima_visita', 'duracao_media', 
                                 'media_visitas_semanais', 'valor_mensal']
            
            # Remover colunas que não são úteis para o treinamento
            features_para_remover = ['aluno_id', 'nome', 'churn', 'ativo', 'ultima_visita']
            X = df.drop(features_para_remover, axis=1)
            y = df['churn']
            
            # Criar pipeline de pré-processamento
            from sklearn.compose import ColumnTransformer
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler, OneHotEncoder
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score, 
                roc_auc_score, confusion_matrix
            )
            
            # Definir o preprocessador
            preprocessor = ColumnTransformer(
                transformers=[
                    ('num', StandardScaler(), features_numericas),
                    ('cat', OneHotEncoder(handle_unknown='ignore'), features_categoricas)
                ]
            )
            
            # Criar o modelo
            model = Pipeline([
                ('preprocessor', preprocessor),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))
            ])
            
            # Dividir os dados em treino e teste SOMENTE para avaliação de métricas
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=y
            )
            
            # Treinar o modelo com dados de treino para gerar métricas
            model.fit(X_train, y_train)
            
            # Avaliar o modelo
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            
            # Calcular métricas
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            auc = roc_auc_score(y_test, y_prob) if len(np.unique(y_test)) > 1 else 0
            cm = confusion_matrix(y_test, y_pred)
            
            # Extrair importância das features
            feature_names = list(X.columns)
            features_encoded = []
            for name, trans, cols in preprocessor.transformers_:
                if name == 'cat':
                    # Obter nomes após one-hot encoding
                    encoder = trans
                    encoded_features = []
                    for col in cols:
                        if hasattr(encoder, 'categories_'):
                            encoded_features.extend([f"{col}_{cat}" for cat in encoder.categories_[0]])
                        else:
                            encoded_features.append(col)
                    features_encoded.extend(encoded_features)
                else:
                    features_encoded.extend(cols)
            
            # Obter importância das features
            try:
                importances = model.named_steps['classifier'].feature_importances_
                feature_importances = dict(zip(features_encoded, importances))
            except:
                feature_importances = {}
            
            # Salvar estatísticas do modelo no banco de dados
            modelo_estatisticas = ModeloChurnEstatisticas(
                total_amostras=len(df),
                qtd_ativos=int(df['ativo'].sum()),
                qtd_inativos=len(df) - int(df['ativo'].sum()),
                acuracia=float(accuracy),
                precisao=float(precision),
                recall=float(recall),
                f1_score=float(f1),
                auc=float(auc),
                importancia_features=feature_importances,
                matriz_confusao=cm.tolist(),
                metricas_adicionais={
                    "distribuicao_features": {
                        feat: {
                            "mean": float(df[feat].mean()), 
                            "std": float(df[feat].std()),
                            "min": float(df[feat].min()),
                            "max": float(df[feat].max())
                        } for feat in features_numericas
                    },
                    "contagem_categoricas": {
                        feat: df[feat].value_counts().to_dict() for feat in features_categoricas
                    }
                },
                versao_modelo=f"RandomForest_n100_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                descricao="Modelo treinado com RandomForestClassifier, n_estimators=100"
            )
            
            db.add(modelo_estatisticas)
            db.flush()
            logger.info(f"Estatísticas do modelo salvas no banco de dados (ID: {modelo_estatisticas.id})")
            
            # Criar diretório para modelos se não existir
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
            os.makedirs(models_dir, exist_ok=True)
            
            # Agora treinar o modelo final com TODOS os dados para uso em produção
            logger.info("Treinando modelo final com todos os dados para uso em produção...")
            model = Pipeline([
                ('preprocessor', preprocessor),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))
            ])
            model.fit(X, y)
            
            # Salvar o modelo
            model_path = os.path.join(models_dir, "modelo_churn.pkl")
            joblib.dump(model, model_path)
            logger.info(f"Modelo final salvo em: {model_path}")
            
            # Salvar também informações das features para uso futuro
            feature_info = {
                'feature_names': list(X.columns),
                'categorical_features': features_categoricas,
                'numerical_features': features_numericas,
                'model_stats_id': modelo_estatisticas.id
            }
            feature_info_path = os.path.join(models_dir, "feature_info.pkl")
            joblib.dump(feature_info, feature_info_path)
            logger.info(f"Informações das features salvas em: {feature_info_path}")
            
            # Limpar cache de probabilidades de churn
            try:
                cache = get_cache()
                if cache.is_available():
                    logger.info("Invalidando cache de probabilidades de churn após atualização do modelo...")
                    num_keys = cache.clear_pattern("churn:aluno:*")
                    logger.info(f"Cache invalidado: {num_keys} chaves removidas")
                else:
                    logger.warning("Cache não disponível para invalidação após atualização do modelo")
            except Exception as cache_error:
                logger.error(f"Erro ao invalidar cache após atualização do modelo: {cache_error}")
            
            # Commit para salvar as alterações no banco de dados
            db.commit()
            
            # Confirmar mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar modelo: {e}")
            # Não confirmar mensagem para que seja reprocessada
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        # Confirmar de qualquer forma para não ficar em loop com mensagens inválidas
        ch.basic_ack(delivery_tag=method.delivery_tag)


def process_churn_probabilities_message(ch, method, properties, body):
    """
    Processa mensagens da fila de cálculo de probabilidades de churn para todos os alunos.
    """
    try:
        # Decodificar mensagem
        message_str = body.decode('utf-8')
        logger.info(f"Iniciando cálculo de probabilidades de churn para todos os alunos: {message_str}")
        
        # Obter caminho correto para os arquivos do modelo
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
        model_path = os.path.join(models_dir, "modelo_churn.pkl")
        feature_info_path = os.path.join(models_dir, "feature_info.pkl")
        
        if not os.path.exists(model_path) or not os.path.exists(feature_info_path):
            logger.error("Modelo de previsão não encontrado. Treine o modelo primeiro.")
            # Confirmar mensagem para não ficar em loop
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Carregar o modelo e informações das features
        modelo = joblib.load(model_path)
        feature_info = joblib.load(feature_info_path)
        
        # Criar sessão do banco de dados
        db = SessionLocal()
        try:
            # Obter todos os alunos ativos
            alunos = db.query(Aluno).all()
            
            # Contador de processamento
            atualizados = 0
            erros = 0
            
            # Lista para armazenar IDs dos alunos atualizados
            alunos_atualizados = []
            
            # Processar cada aluno
            for aluno in alunos:
                try:
                    # Extrair características do aluno
                    features = extrair_features_aluno(aluno.id, db)
                    
                    # Garantir que todos os valores são do tipo float (não decimal)
                    for key, value in features.items():
                        if hasattr(value, 'quantize'):  # Verifica se é um decimal.Decimal
                            features[key] = float(value)
                    
                    # Preparar os dados no formato esperado pelo modelo
                    X = pd.DataFrame([features])
                    
                    # Fazer previsão
                    probabilidade = modelo.predict_proba(X)[0, 1]  # Probabilidade da classe 1 (churn)
                    
                    # Identificar fatores de risco
                    fatores_risco = identificar_fatores_risco(features)
                    
                    # Atualizar ou criar o registro na tabela de probabilidades
                    churn_prob = db.query(ChurnProbability).filter(
                        ChurnProbability.aluno_id == aluno.id
                    ).first()
                    
                    if churn_prob:
                        # Atualizar registro existente
                        churn_prob.probabilidade = float(probabilidade)
                        churn_prob.fatores_risco = ",".join(fatores_risco)
                        churn_prob.ultima_atualizacao = datetime.datetime.now()
                    else:
                        # Criar novo registro
                        churn_prob = ChurnProbability(
                            aluno_id=aluno.id,
                            probabilidade=float(probabilidade),
                            fatores_risco=",".join(fatores_risco)
                        )
                        db.add(churn_prob)
                    
                    atualizados += 1
                    alunos_atualizados.append(aluno.id)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar aluno {aluno.id}: {e}")
                    erros += 1
            
            # Commit das alterações
            db.commit()
            logger.info(f"Cálculo de probabilidades concluído. {atualizados} alunos atualizados. {erros} erros.")
            
            # Invalidar cache para os alunos atualizados
            try:
                cache = get_cache()
                if cache.is_available():
                    logger.info("Invalidando cache de probabilidades de churn para alunos atualizados...")
                    
                    # Limpar cache individual para cada aluno
                    for aluno_id in alunos_atualizados:
                        cache.delete(f"churn:aluno:{aluno_id}")
                    
                    logger.info(f"Cache invalidado para {len(alunos_atualizados)} alunos")
                else:
                    logger.warning("Cache não disponível para invalidação após cálculo de probabilidades")
            except Exception as cache_error:
                logger.error(f"Erro ao invalidar cache após cálculo de probabilidades: {cache_error}")
            
            # Confirmar mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao calcular probabilidades: {e}")
            # Não confirmar mensagem para que seja reprocessada
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        # Confirmar de qualquer forma para não ficar em loop com mensagens inválidas
        ch.basic_ack(delivery_tag=method.delivery_tag)


def extrair_features_aluno(aluno_id: int, db: Session) -> dict:
    """
    Extrai as características relevantes de um aluno para previsão de churn.
    """
    # Obter informações básicas do aluno
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    
    # Obter checkins do aluno
    checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno_id).all()
    
    # Calcular estatísticas
    total_checkins = len(checkins)
    
    # Última visita e dias desde a última visita
    ultima_visita = db.query(Checkin.data_entrada).filter(
        Checkin.aluno_id == aluno_id
    ).order_by(Checkin.data_entrada.desc()).first()
    
    dias_desde_ultima_visita = 365  # Valor padrão alto
    if ultima_visita:
        dias_desde_ultima_visita = (datetime.datetime.now() - ultima_visita[0]).days
    
    # Duração média das visitas
    duracoes = [c.duracao_minutos for c in checkins if c.duracao_minutos is not None]
    duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
    
    # Média de visitas semanais
    if total_checkins > 0 and checkins:
        primeira_visita = min(c.data_entrada for c in checkins)
        semanas = max(1, (datetime.datetime.now() - primeira_visita).days / 7)
        media_visitas_semanais = total_checkins / semanas
    else:
        media_visitas_semanais = 0
    
    # Plano do aluno
    plano = db.query(Plano).filter(Plano.id == aluno.plano_id).first()
    
    # Obter valor_mensal e converter para float se for decimal
    valor_mensal = 0
    if plano and plano.valor_mensal:
        valor_mensal = float(plano.valor_mensal) if hasattr(plano.valor_mensal, 'quantize') else plano.valor_mensal
    
    # Criar dicionário de features
    features = {
        'total_checkins': total_checkins,
        'dias_desde_ultima_visita': dias_desde_ultima_visita,
        'duracao_media': duracao_media,
        'media_visitas_semanais': media_visitas_semanais,
        'plano_id': aluno.plano_id,
        'plano_nome': plano.nome if plano else "Desconhecido",
        'valor_mensal': valor_mensal
    }
    
    return features


def identificar_fatores_risco(features: dict) -> list:
    """
    Identifica os fatores de risco com base nas características do aluno.
    """
    fatores_risco = []
    
    # Avaliar fatores de risco
    if features['dias_desde_ultima_visita'] > 30:
        fatores_risco.append(f"Inatividade há {features['dias_desde_ultima_visita']} dias")
    
    if features['media_visitas_semanais'] < 1:
        fatores_risco.append("Frequência menor que 1 visita por semana")
    
    if features['duracao_media'] < 30:
        fatores_risco.append(f"Duração média das visitas de apenas {int(features['duracao_media'])} minutos")
    
    if features['total_checkins'] < 5:
        fatores_risco.append("Poucas visitas à academia")
    
    return fatores_risco


def start_consumers():
    """
    Inicia os consumidores para as filas.
    """
    try:
        # Criar cliente RabbitMQ
        client = RabbitMQClient()
        
        # Iniciar consumidor para checkins em massa
        client.consume_messages(CHECKIN_QUEUE, process_checkin_message)
        
        # Iniciar consumidor para relatórios
        client.consume_messages(REPORT_QUEUE, process_report_message)
        
        # Iniciar consumidor para atualizações do modelo
        client.consume_messages(MODEL_UPDATE_QUEUE, process_model_update_message)
        
        # Iniciar consumidor para cálculo de probabilidades de churn
        client.consume_messages(CHURN_PROB_QUEUE, process_churn_probabilities_message)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar consumidores: {e}")
        raise 

