from dataclasses import dataclass
from typing import List, Dict
from datetime import date

@dataclass
class MembroFamilia:
    tipo: str  # 'titular', 'conjuge', 'dependente', 'agregado_jovem', 'agregado_maior'
    data_nascimento: date
    parcela_risco: bool = False
    id: int = 0  # Para identificação única

class GrupoFamiliar:
   def __init__(self):
        self.membros = {
            'titular': [],
            'conjuge': [],
            'dependente': [],
            'agregado_jovem': [],
            'agregado_maior': []
        }
    
    def adicionar_membro(self, tipo, data_nascimento, risco=False, data_exclusao=None):
        try:
            nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            exclusao = datetime.strptime(data_exclusao, '%Y-%m-%d').date() if data_exclusao else None
            
            self.membros[tipo].append({
                'data_nascimento': nasc,
                'risco': risco,
                'data_exclusao': exclusao
            })
            return True
        except:
            return False
    
    def contar_por_tipo(self, tipo: str, ano: int = None) -> int:
        return len(self.obter_membros_por_tipo(tipo, ano))
    
    def obter_membros_por_tipo(self, tipo: str, ano: int = None) -> List[MembroFamilia]:
        membros = [m for m in self.membros if m.tipo == tipo]
        
        if ano:
            membros_filtrados = []
            for m in membros:
                idade = ano - m.data_nascimento.year
                if tipo == 'dependente' and idade >= 18:
                    continue
                if tipo == 'agregado_jovem' and not (18 <= idade < 24):
                    continue
                if tipo == 'agregado_maior' and idade < 24:
                    continue
                membros_filtrados.append(m)
            return membros_filtrados
        
        return membros
    
    def calcular_contribuicoes(self, ano: int, mes_num: int) -> Dict:
    contribuicoes = {
        'titular': 0,
        'conjuge': 0,
        'dependente': 0,
        'agregado_jovem': 0,
        'agregado_maior': 0,
        'parcelas_risco': 0
    }
    
    # Contar membros ativos no mês/ano especificado
    for tipo, membros in self.membros.items():
        for membro in membros:
            # Verificar se o membro estava ativo no mês/ano
            ativo = True
            if membro['data_exclusao']:
                exclusao = membro['data_exclusao']
                if exclusao.year < int(ano) or (exclusao.year == int(ano) and exclusao.month < mes_num):
                    ativo = False
            
            if ativo:
                contribuicoes[tipo] += 1
                if membro['risco']:
                    contribuicoes['parcelas_risco'] += 1
    
    return contribuicoes
