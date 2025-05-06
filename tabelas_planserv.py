# tabelas_planserv.py

import os
import tabula
import re
import logging

logger = logging.getLogger(__name__)

def extrair_tabela_de_pdf(caminho_pdf):
    """Extrai a tabela de contribuição de um PDF."""
    try:
        tabelas = tabula.read_pdf(caminho_pdf, pages='all', multiple_tables=True)
        tabela_crua = None
        for tabela in tabelas:
          if 'FAIXAS DE REMUNERAÇÃO' in tabela.columns:
            tabela_crua = tabela
            break

        if tabela_crua is None:
          logger.warning(f"Tabela de remuneração não encontrada em {caminho_pdf}")
          return []

        dados_limpos = []
        for index, row in tabela_crua.iterrows():
          if pd.isna(row['FAIXAS DE REMUNERAÇÃO']) or pd.isna(row['TITULARES (Em\rR$)']) or pd.isna(row['CÔNJUGES OU\rCOMPANHEIROS']) or pd.isna(row['OUTROS\rDEPENDENTES']):
            continue # Ignora linhas com valores faltantes

          faixa_remuneracao = str(row['FAIXAS DE REMUNERAÇÃO'])
          titular = str(row['TITULARES (Em\rR$)'])
          conjuge = str(row['CÔNJUGES OU\rCOMPANHEIROS'])
          dependente = str(row['OUTROS\rDEPENDENTES'])

          # Remova caracteres indesejados e converta para float
          titular = float(re.sub(r'[^\d,]', '', titular).replace(',', '.'))
          conjuge = float(re.sub(r'[^\d,]', '', conjuge).replace(',', '.'))
          dependente = float(re.sub(r'[^\d,]', '', dependente).replace(',', '.'))

          dados_limpos.append({
              'faixa_remuneracao': faixa_remuneracao,
              'titular': titular,
              'conjuge': conjuge,
              'dependente': dependente
          })
        return dados_limpos

    except Exception as e:
        logger.error(f"Erro ao extrair tabela de {caminho_pdf}: {e}")
        return []

def carregar_tabelas(pasta_tabelas):
    """Carrega todas as tabelas de uma pasta."""
    tabelas = {}
    for arquivo in os.listdir(pasta_tabelas):
        if arquivo.endswith('.pdf'):  # Ajuste conforme necessário
            ano = re.search(r'Tabela-(\d{4})', arquivo)
            if ano:
                ano_tabela = int(ano.group(1))
                caminho_completo = os.path.join(pasta_tabelas, arquivo)
                tabelas[ano_tabela] = extrair_tabela_de_pdf(caminho_completo)
    return tabelas

def obter_valor_por_faixa(tabela, faixa_remuneracao, categoria):
    """Obtém o valor correspondente à faixa de remuneração e categoria."""
    for linha in tabela:
        faixa_str = linha['faixa_remuneracao']

        # Adaptação para lidar com diferentes formatos de faixa
        if 'ou mais' in faixa_str:
          limite_inferior = float(re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})', faixa_str).group(1).replace('.', '').replace(',', '.'))
          if faixa_remuneracao >= limite_inferior:
            return linha[categoria]
        elif '~a~' in faixa_str:
          limites = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', faixa_str)
          if limites:
            limite_inferior = float(limites[0].replace('.', '').replace(',', '.'))
            limite_superior = float(limites[1].replace('.', '').replace(',', '.'))
            if limite_inferior <= faixa_remuneracao <= limite_superior:
              return linha[categoria]
        elif 'a' in faixa_str:
          limites = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', faixa_str)
          if limites:
            limite_inferior = float(limites[0].replace('.', '').replace(',', '.'))
            limite_superior = float(limites[1].replace('.', '').replace(',', '.'))
            if limite_inferior <= faixa_remuneracao <= limite_superior:
              return linha[categoria]


    return None  # Retorna None se não encontrar

if __name__ == '__main__':
    # Para testar o módulo diretamente
    logging.basicConfig(level=logging.INFO)
    pasta_tabelas = 'tabelas'  # Pasta onde você colocará os PDFs
    tabelas_planserv = carregar_tabelas(pasta_tabelas)

    if tabelas_planserv:
        print("Tabelas carregadas com sucesso!")
        for ano, tabela in tabelas_planserv.items():
            print(f"\n--- Tabela {ano} ---")
            for linha in tabela:
                print(linha)

        # Exemplo de uso para obter um valor
        remuneracao = 2000.00
        valor_titular = obter_valor_por_faixa(tabelas_planserv[2023], remuneracao, 'titular')
        print(f"\nValor Titular para faixa {remuneracao}: {valor_titular}")
    else:
        print("Erro ao carregar tabelas.")
