from fastapi import APIRouter, HTTPException, status, Query, Response
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import os
from fastapi.responses import FileResponse

from app.queue.producers import solicitar_relatorio_diario, solicitar_atualizacao_modelo, solicitar_calculo_probabilidades_churn
from app.queue.consumers import REPORTS_DIR

router = APIRouter(prefix="/relatorio", tags=["relatorios"])


@router.post("/diario", status_code=status.HTTP_202_ACCEPTED)
def gerar_relatorio_diario(data: Optional[date] = None):
    """
    Solicita a geração de um relatório diário de frequência.
    
    Este endpoint envia os dados para uma fila do RabbitMQ, que serão processados
    por um worker em segundo plano. O relatório será gerado assincronamente.
    
    Args:
        data: Data opcional para o relatório no formato YYYY-MM-DD. 
              Se não for fornecida, será usada a data atual.
    """
    # Converter data para string no formato YYYY-MM-DD
    data_str = data.isoformat() if data else None
    
    # Enviar para a fila do RabbitMQ - garantir que é só uma string de data
    sucesso = solicitar_relatorio_diario(data_str)
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar geração de relatório. Tente novamente mais tarde."
        )
    
    data_exibicao = data.strftime("%d/%m/%Y") if data else "hoje"
    return {"message": f"Relatório diário para {data_exibicao} solicitado com sucesso. Aguarde alguns instantes e atualize a página para baixar."}


@router.get("/listar", response_model=List[Dict[str, Any]])
def listar_relatorios():
    """
    Lista todos os relatórios diários gerados.
    """
    try:
        if not os.path.exists(REPORTS_DIR):
            return []
        
        # Listar arquivos no diretório de relatórios
        arquivos = os.listdir(REPORTS_DIR)
        relatorios = []
        
        for arquivo in arquivos:
            if arquivo.startswith("relatorio_diario_") and arquivo.endswith(".csv"):
                # Obter informações do arquivo
                caminho_completo = os.path.join(REPORTS_DIR, arquivo)
                data_modificacao = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
                tamanho = os.path.getsize(caminho_completo)
                
                # Extrair a data do relatório do nome do arquivo
                try:
                    # Formato esperado: relatorio_diario_2023-04-03_20230403_123456.csv
                    partes = arquivo.split("_")
                    data_relatorio = partes[2]
                except:
                    data_relatorio = "Desconhecida"
                
                relatorios.append({
                    "arquivo": arquivo,
                    "data_relatorio": data_relatorio,
                    "data_geracao": data_modificacao.isoformat(),
                    "tamanho_bytes": tamanho
                })
        
        # Ordenar por data de geração (mais recentes primeiro)
        relatorios.sort(key=lambda x: x["data_geracao"], reverse=True)
        return relatorios
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar relatórios: {str(e)}"
        )


@router.get("/download/{nome_arquivo}")
def download_relatorio(nome_arquivo: str):
    """
    Faz o download de um relatório específico.
    """
    try:
        caminho_arquivo = os.path.join(REPORTS_DIR, nome_arquivo)
        
        if not os.path.exists(caminho_arquivo):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relatório não encontrado"
            )
        
        return FileResponse(
            path=caminho_arquivo,
            filename=nome_arquivo,
            media_type="text/csv"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer download do relatório: {str(e)}"
        )


@router.post("/churn/atualizar-modelo", status_code=status.HTTP_202_ACCEPTED)
def atualizar_modelo_churn():
    """
    Solicita a atualização do modelo de previsão de churn.
    
    Este endpoint envia uma solicitação para a fila do RabbitMQ, que será processada
    por um worker em segundo plano. O modelo será treinado/atualizado assincronamente.
    """
    # Enviar para a fila do RabbitMQ
    sucesso = solicitar_atualizacao_modelo()
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar atualização do modelo. Tente novamente mais tarde."
        )
    
    return {"message": "Atualização do modelo de previsão de churn solicitada com sucesso"}


@router.post("/churn/calcular-probabilidades", status_code=status.HTTP_202_ACCEPTED)
def calcular_probabilidades_churn():
    """
    Solicita o cálculo das probabilidades de churn para todos os alunos.
    
    Este endpoint envia uma solicitação para a fila do RabbitMQ, que será processada
    por um worker em segundo plano. As probabilidades serão calculadas assincronamente
    com base no modelo já treinado.
    """
    # Enviar para a fila do RabbitMQ
    sucesso = solicitar_calculo_probabilidades_churn()
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar cálculo de probabilidades. Tente novamente mais tarde."
        )
    
    return {"message": "Cálculo de probabilidades de churn para todos os alunos solicitado com sucesso"} 