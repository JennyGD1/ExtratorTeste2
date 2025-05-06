import fitz  # PyMuPDF
import re
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler
from familia import GrupoFamiliar

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-aqui'

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=100000, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Valores fixos para agregados
VALORES_AGREGADOS = {
    'agregado_jovem': {
        '2023': 75.91,
        '2021': 72.99,
        'default': 70.18
    },
    'agregado_maior': 'titular'
}

MESES_ORDEM = {
    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
    'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
    'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12,
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
}

# Configurações
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config.update({
    'UPLOAD_FOLDER': UPLOAD_FOLDER,
    'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,
    'ALLOWED_EXTENSIONS': {'pdf'}
})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extrair_valor_linha(linha):
    padrao_valor = r'(\d{1,3}(?:[\.\s]?\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})'
    valores = re.findall(padrao_valor, linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        try:
            return float(valor_str)
        except ValueError:
            return 0.0
    return 0.0

def extrair_mes_ano_do_texto(texto_pagina):
    padrao_mes_ano = r'(Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s*[/.-]?\s*(\d{4})'
    match = re.search(padrao_mes_ano, texto_pagina, re.IGNORECASE)
    if match:
        mes = match.group(1).capitalize()
        ano = match.group(2)
        for k, v in MESES_ORDEM.items():
            if mes.upper() == k.upper():
                mes_padrao = k.capitalize() if len(k) > 3 else k
                if len(mes_padrao) <= 3:
                    for nome_completo, num in MESES_ORDEM.items():
                        if num == v and len(nome_completo) > 3:
                            mes_padrao = nome_completo
                            break
                return f"{mes_padrao} {ano}", ano
    return "Período não identificado", None

def extrair_remuneracao_do_pdf(texto_pagina):
    padrao_remuneracao = r'TOTAL DE VANTAGENS\s*(\d{1,3}(?:[\.\s]?\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})'
    match = re.search(padrao_remuneracao, texto_pagina, re.IGNORECASE)
    if match:
        valor_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(valor_str)
        except ValueError:
            return None
    return None

def processar_pdf(caminho_pdf):
    try:
        doc = fitz.open(caminho_pdf)
        resultados_por_pagina = []

        CODIGOS = {
            '7033': 'titular',
            '7035': 'conjuge',
            '7034': 'dependente',
            '7038': 'agregado_jovem',
            '7039': 'agregado_maior',
            '7037': 'plano_especial',
            '7040': 'coparticipacao',
            '7049': 'retroativo',
            '7088': 'parcela_risco',
            '7089': 'parcela_risco',
            '7090': 'parcela_risco',
            '7091': 'parcela_risco'
        }

        for page in doc:
            texto_pagina = page.get_text("text")
            mes_ano, ano = extrair_mes_ano_do_texto(texto_pagina)
            remuneracao = extrair_remuneracao_do_pdf(texto_pagina)

            valores = {
                'titular': 0.0, 'conjuge': 0.0, 'dependente': 0.0,
                'agregado_jovem': 0.0, 'agregado_maior': 0.0,
                'plano_especial': 0.0, 'coparticipacao': 0.0,
                'retroativo': 0.0, 'parcela_risco': 0.0
            }

            for linha in texto_pagina.split('\n'):
                linha = linha.strip()
                codigo_match = re.match(r'^(\d{4})\b', linha)
                codigo = codigo_match.group(1) if codigo_match else None
                campo = CODIGOS.get(codigo) if codigo else None

                if not campo:
                    if re.search(r'Assistência a Saúde|PLANO DE SAUDE DOS SERV', linha, re.IGNORECASE):
                        campo = 'titular'
                    elif re.search(r'Planserv Especial|PLANSERV ESPECIAL', linha, re.IGNORECASE):
                        campo = 'plano_especial'
                    elif re.search(r'Planserv Agregado Jovem', linha, re.IGNORECASE):
                        campo = 'agregado_jovem'
                    elif re.search(r'CO-PARTICIPAÇÃO PLANSERV|coparticipacao', linha, re.IGNORECASE):
                        campo = 'coparticipacao'

                if campo:
                    valor = extrair_valor_linha(linha)
                    if valor > 0:
                        valores[campo] += valor

            resultados_por_pagina.append({
                'mes_ano': mes_ano,
                'ano': ano,
                'remuneracao': remuneracao,
                'valores': valores
            })

        return resultados_por_pagina

    except Exception as e:
        logger.error(f"Erro ao processar PDF {caminho_pdf}: {str(e)}")
        return []


def calcular_contribuicoes_esperadas(valor_titular: float, ano: int, familia: GrupoFamiliar, mes_num: int) -> Dict:
    contribuicoes = familia.calcular_contribuicoes(ano, mes_num)
    valor_agregado_jovem = VALORES_AGREGADOS['agregado_jovem'].get(str(ano), VALORES_AGREGADOS['agregado_jovem']['default'])
    
    return {
        'titular': valor_titular * contribuicoes['titular'],
        'conjuge': (valor_titular * 0.5) * contribuicoes['conjuge'],
        'dependente': (valor_titular * 0.22) * contribuicoes['dependente'],
        'agregado_jovem': valor_agregado_jovem * contribuicoes['agregado_jovem'],
        'agregado_maior': valor_titular * contribuicoes['agregado_maior'],
        'parcelas_risco': contribuicoes['parcelas_risco']
    }

def verificar_consistencia(valores_reais: Dict, valores_esperados: Dict, mes_ano: str) -> Dict:
    inconsistencias = {}
    for campo in ['titular', 'conjuge', 'dependente', 'agregado_jovem', 'agregado_maior']:
        real = valores_reais.get(campo, 0)
        esperado = valores_esperados.get(campo, 0)
        if esperado > 0 and abs(real - esperado) > (esperado * 0.05):
            inconsistencias[campo] = {
                'real': real,
                'esperado': esperado,
                'diferenca': real - esperado,
                'mes_ano': mes_ano
            }
    return inconsistencias

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/familia', methods=['GET', 'POST'])
def cadastrar_familia():
    if request.method == 'POST':
        familia = GrupoFamiliar()
        errors = []
        
        # Processar titular (obrigatório)
        titular_nasc = request.form.get('titular_nascimento')
        if not titular_nasc:
            errors.append("Data de nascimento do titular é obrigatória")
        else:
            if not familia.adicionar_membro('titular', titular_nasc, False):
                errors.append("Data de nascimento do titular inválida")
        
        # Processar cônjuge (se marcado)
        if 'incluir_conjuge' in request.form:
            conjuge_nasc = request.form.get('conjuge_nascimento')
            conjuge_exclusao = request.form.get('conjuge_exclusao') if 'interrompido_conjuge' in request.form else None
            
            if conjuge_nasc:
                if not familia.adicionar_membro(
                    'conjuge', 
                    conjuge_nasc, 
                    'conjuge_risco' in request.form,
                    conjuge_exclusao
                ):
                    errors.append("Data de nascimento do cônjuge inválida")
            else:
                errors.append("Data de nascimento do cônjuge é obrigatória")
        
        # Processar dependentes
        for key, value in request.form.items():
            if key.startswith('tipo_'):
                prefix = key.split('_')[1]
                tipo = value
                nascimento = request.form.get(f'nascimento_{prefix}')
                risco = f'risco_{prefix}' in request.form
                interrompido = f'interrompido_{prefix}' in request.form
                data_exclusao = request.form.get(f'data_exclusao_{prefix}') if interrompido else None
                
                if tipo in ['filho', 'enteado', 'tutelado']:
                    categoria = 'dependente'
                elif tipo == 'neto':
                    try:
                        nasc_date = datetime.strptime(nascimento, '%Y-%m-%d')
                        idade = datetime.now().year - nasc_date.year
                        categoria = 'agregado_jovem' if idade < 24 else 'agregado_maior'
                    except:
                        errors.append(f"Data de nascimento inválida para {tipo}")
                        continue
                
                if not familia.adicionar_membro(categoria, nascimento, risco, data_exclusao):
                    errors.append(f"Data de nascimento inválida para {tipo}")
        
        if not errors:
            session['familia'] = familia.__dict__
            flash('Família cadastrada com sucesso!', 'success')
            return redirect(url_for('index'))
        
        for error in errors:
            flash(error, 'error')
    
    return render_template('index.html')
    
@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(url_for('index'))

    if 'familia' not in session:
        flash('Cadastre os dados familiares antes de enviar contracheques', 'error')
        return redirect(url_for('cadastrar_familia'))

    files = [f for f in request.files.getlist('files') if f.filename != '' and allowed_file(f.filename)]
    if not files:
        flash('Nenhum arquivo PDF válido selecionado', 'error')
        return redirect(url_for('index'))

    resultados_por_ano = {}
    erros = []
    familia = GrupoFamiliar()
    familia.__dict__ = session['familia']

    for file in files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            resultados = processar_pdf(filepath)
            
            if not resultados:
                erros.append(f"{filename} - Não foi possível extrair dados")
                continue

            for resultado in resultados:
                ano = resultado['ano']
                if not ano or len(ano) != 4:
                    erros.append(f"{filename} - Ano inválido")
                    continue

                if ano not in resultados_por_ano:
                    resultados_por_ano[ano] = {
                        'geral': {
                            'titular': 0.0, 'conjuge': 0.0, 'dependente': 0.0,
                            'agregado_jovem': 0.0, 'agregado_maior': 0.0,
                            'parcela_risco': 0.0, 'total': 0.0
                        },
                        'detalhes_mensais': []
                    }

                valores_esperados = calcular_contribuicoes_esperadas(
                    resultado['valores']['titular'],
                    int(ano),
                    familia,
                    MESES_ORDEM[resultado['mes_ano'].split()[0]]
                )

                for campo in ['titular', 'conjuge', 'dependente', 'agregado_jovem', 'agregado_maior', 'parcela_risco']:
                    resultados_por_ano[ano]['geral'][campo] += resultado['valores'].get(campo, 0)
                
                resultados_por_ano[ano]['geral']['total'] += sum(resultado['valores'].values())

                resultados_por_ano[ano]['detalhes_mensais'].append({
                    'mes': resultado['mes_ano'],
                    'valores': resultado['valores'],
                    'valores_esperados': valores_esperados,
                    'inconsistencias': verificar_consistencia(
                        resultado['valores'],
                        valores_esperados,
                        resultado['mes_ano']
                    ),
                    'remuneracao': resultado['remuneracao']
                })

        except Exception as e:
            logger.error(f"Erro processando {filename}: {str(e)}")
            erros.append(f"{filename} - Erro no processamento")
        finally:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

    if not resultados_por_ano:
        flash('Nenhum dado válido extraído dos arquivos', 'error')
        return redirect(url_for('index'))

    session['resultados_por_ano'] = resultados_por_ano
    
    if erros:
        flash(f"Processamento completo com {len(erros)} erro(s)", 'warning')
    
    return redirect(url_for('mostrar_resultados'))

@app.route('/resultados')
def mostrar_resultados():
    if 'resultados_por_ano' not in session:
        flash('Nenhum resultado disponível', 'error')
        return redirect(url_for('index'))
    
    familia = GrupoFamiliar()
    if 'familia' in session:
        familia.__dict__ = session['familia']
    
    return render_template(
        'resultados.html',
        anos=sorted(session['resultados_por_ano'].keys(), reverse=True),
        resultados=session['resultados_por_ano'],
        familia=familia
    )

@app.route('/analise/<ano>')
def analise_ano(ano):
    if 'resultados_por_ano' not in session or ano not in session['resultados_por_ano']:
        flash('Dados não encontrados', 'error')
        return redirect(url_for('mostrar_resultados'))
    
    dados_ano = session['resultados_por_ano'][ano]
    familia = GrupoFamiliar()
    
    if 'familia' in session:
        familia.__dict__ = session['familia']
    
    resumo = {
        'total_cobrado': sum(m['valores']['titular'] for m in dados_ano['detalhes_mensais']),
        'total_esperado': sum(m['valores_esperados']['titular'] for m in dados_ano['detalhes_mensais']),
        'inconsistencias': sum(len(m['inconsistencias']) for m in dados_ano['detalhes_mensais'])
    }
    
    return render_template(
        'analise.html',
        ano=ano,
        dados_ano=dados_ano,
        familia=familia,
        resumo=resumo
    )

if __name__ == '__main__':
    app.run(debug=True)
