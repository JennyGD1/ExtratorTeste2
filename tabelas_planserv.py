# tabelas_planserv.py

import os
import tabula
import re
import logging
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class FaixaContribuicao:
    faixa: str
    min_val: float
    max_val: float
    titular: float
    conjuge: float
    dependente: float

@dataclass
class TabelaPlanserv:
    ano: int
    faixas: List[FaixaContribuicao]

def setup_logging():
    """Configura o logging para o módulo."""
    logger = logging.getLogger('planserv')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def extract_value(val_str: str) -> float:
    """Extrai valor numérico de strings como 'R$ 1.234,56'."""
    num_str = re.sub(r'[^\d,]', '', val_str).replace(',', '.')
    return float(num_str) if num_str else 0.0

def parse_faixa(faixa_str: str) -> tuple[float, float]:
    """Analisa a string de faixa salarial retornando (min, max)."""
    faixa_str = faixa_str.lower()

    if 'ou mais' in faixa_str:
        min_val_str = re.search(r'([\d\.,]+)', faixa_str)
        min_val = extract_value(min_val_str.group(1)) if min_val_str else 0.0
        return (min_val, float('inf'))

    if 'a' in faixa_str:
        valores_str = re.findall(r'([\d\.,]+)', faixa_str)
        if len(valores_str) == 2:
            return (extract_value(valores_str[0]), extract_value(valores_str[1]))
        elif len(valores_str) == 1:
            return (extract_value(valores_str[0]), float('inf')) # Adaptação para faixas como "acima de..."
        else:
            return (0.0, 0.0)

    return (0.0, 0.0)

def extrair_tabela_de_pdf(caminho_pdf: str) -> Optional[List[dict]]:
    """Extrai a tabela de contribuição de um PDF."""
    try:
        tabelas = tabula.read_pdf(caminho_pdf, pages='all', multiple_tables=True)
        if not tabelas:
            logger.warning(f"Nenhuma tabela encontrada em {caminho_pdf}")
            return None

        tabela_crua = None
        # Tenta encontrar a tabela com as colunas esperadas
        for tabela in tabelas:
            if all(col in tabela.columns for col in ['FAIXAS DE REMUNERAÇÃO', 'TITULARES (Em\rR$)', 'CÔNJUGES OU\rCOMPANHEIROS', 'OUTROS\rDEPENDENTES']):
                tabela_crua = tabela
                break
            elif all(col in tabela.columns for col in ['FAIXAS DE REMUNERAÇÃO', 'TITULARES (Em R$)', 'CÔNJUGES OU COMPANHEIROS', 'OUTROS DEPENDENTES']):
                tabela_crua = tabela
                tabela_crua.rename(columns={'TITULARES (Em R$)': 'TITULARES (Em\rR$)',
                                            'CÔNJUGES OU COMPANHEIROS': 'CÔNJUGES OU\rCOMPANHEIROS',
                                            'OUTROS DEPENDENTES': 'OUTROS\rDEPENDENTES'}, inplace=True)
                break


        if tabela_crua is None:
            logger.warning(f"Tabela de remuneração não encontrada em {caminho_pdf}")
            return None

        dados_limpos: List[dict] = []
        for index, row in tabela_crua.iterrows():
            if pd.isna(row['FAIXAS DE REMUNERAÇÃO']) or pd.isna(row['TITULARES (Em\rR$)']) or pd.isna(row['CÔNJUGES OU\rCOMPANHEIROS']) or pd.isna(row['OUTROS\rDEPENDENTES']):
                continue # Ignora linhas com valores faltantes

            faixa_remuneracao = str(row['FAIXAS DE REMUNERAÇÃO'])
            titular_str = str(row['TITULARES (Em\rR$)'])
            conjuge_str = str(row['CÔNJUGES OU\rCOMPANHEIROS'])
            dependente_str = str(row['OUTROS\rDEPENDENTES'])

            titular = extract_value(titular_str)
            conjuge = extract_value(conjuge_str)
            dependente = extract_value(dependente_str)

            min_val, max_val = parse_faixa(faixa_remuneracao)

            dados_limpos.append({
                'faixa_remuneracao': faixa_remuneracao,
                'min_val': min_val,
                'max_val': max_val,
                'titular': titular,
                'conjuge': conjuge,
                'dependente': dependente
            })
        return dados_limpos

    except tabula.errors.JavaNotFoundError:
        logger.error("Java não encontrado. Tabula requer Java 8+ instalado.")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar {caminho_pdf}: {str(e)}")
        return None

def carregar_tabelas(pasta_tabelas: str, use_cache: bool = True) -> dict[int, List[dict]]:
    """Carrega todas as tabelas de uma pasta, com opção de cache."""
    cache_file = Path(pasta_tabelas) / 'tabelas_cache.json'
    tabelas: dict[int, List[dict]] = {}

    if use_cache and cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                # Desserializar os dados carregados para garantir a estrutura esperada
                for ano_str, lista_de_dicionarios in cached_data.items():
                    tabelas[int(ano_str)] = lista_de_dicionarios
            logger.info("Tabelas carregadas do cache.")
            return tabelas
        except (json.JSONDecodeError, ValueError):
            logger.warning("Arquivo de cache corrompido ou inválido. Recarregando tabelas dos PDFs.")

    for arquivo in os.listdir(pasta_tabelas):
        if arquivo.endswith('.pdf'):
            ano_match = re.search(r'Tabela-(\d{4})', arquivo)
            if ano_match:
                ano_tabela = int(ano_match.group(1))
                caminho_completo = os.path.join(pasta_tabelas, arquivo)
                tabela_extraida = extrair_tabela_de_pdf(caminho_completo)
                if tabela_extraida:
                    tabelas[ano_tabela] = tabela_extraida

    if use_cache and tabelas:
        try:
            with open(cache_file, 'w') as f:
                json.dump(tabelas, f, indent=4)
            logger.info("Tabelas salvas no cache.")
        except IOError as e:
            logger.error(f"Erro ao salvar o cache: {e}")

    return tabelas

def obter_valor_por_faixa(tabela: List[dict], salario: float, categoria: str) -> Optional[float]:
    """Obtém o valor correspondente à faixa de remuneração e categoria usando busca linear."""
    try:
        salario = float(salario)
    except (ValueError, TypeError):
        logger.error(f"Salário inválido para busca: {salario}")
        return None

    for faixa_data in tabela:
        if faixa_data['min_val'] <= salario <= faixa_data['max_val']:
            return faixa_data.get(categoria)
    return None

if __name__ == '__main__':
    setup_logging()
    pasta_tabelas = 'tabelas'  # Pasta onde você colocará os PDFs
    tabelas_planserv = carregar_tabelas(pasta_tabelas)

    if tabelas_planserv:
        logger.info("Tabelas carregadas com sucesso!")
        for ano, tabela in tabelas_planserv.items():
            logger.info(f"\n--- Tabela {ano} ---")
            for linha in tabela:
                logger.info(linha)

        # Exemplo de uso para obter um valor
        remuneracao = 2500.00
        ano_consulta = 2023
        if ano_consulta in tabelas_planserv:
            valor_titular = obter_valor_por_faixa(tabelas_planserv[ano_consulta], remuneracao, 'titular')
            if valor_titular is not None:
                print(f"\nValor Titular para R$ {remuneracao:.2f} em {ano_consulta}: R$ {valor_titular:.2f}")
            else:
                print(f"\nFaixa salarial não encontrada para R$ {remuneracao:.2f} em {ano_consulta}.")
        else:
            print(f"\nTabela para o ano {ano_consulta} não encontrada.")
    else:
        logger.error("Erro ao carregar tabelas.")
