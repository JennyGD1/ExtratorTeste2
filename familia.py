from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, date

@dataclass
class MembroFamilia:
    tipo: str  # 'titular', 'conjuge', 'dependente', 'agregado_jovem', 'agregado_maior'
    data_nascimento: date
    parcela_risco: bool = False
    data_exclusao: Optional[date] = None
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
    
    def adicionar_membro(self, tipo: str, data_nascimento: str, risco: bool = False, data_exclusao: Optional[str] = None) -> bool:
        try:
            nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            exclusao = datetime.strptime(data_exclusao, '%Y-%m-%d').date() if data_exclusao else None
            
            novo_membro = MembroFamilia(
                tipo=tipo,
                data_nascimento=nasc,
                parcela_risco=risco,
                data_exclusao=exclusao
            )
            
            self.membros[tipo].append(novo_membro)
            return True
        except Exception:
            return False
    
    def contar_por_tipo(self, tipo: str, ano: Optional[int] = None) -> int:
        return len(self.obter_membros_por_tipo(tipo, ano))
    
    def obter_membros_por_tipo(self, tipo: str, ano: Optional[int] = None) -> List[MembroFamilia]:
        membros = self.membros.get(tipo, [])
        
        if not ano:
            return membros
            
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
    
    def calcular_contribuicoes(self, ano: int, mes_num: int) -> Dict[str, int]:
        contribuicoes = {
            'titular': 0,
            'conjuge': 0,
            'dependente': 0,
            'agregado_jovem': 0,
            'agregado_maior': 0,
            'parcelas_risco': 0
        }
        
        for tipo, membros in self.membros.items():
            for membro in membros:
                # Verificar se o membro estava ativo no mês/ano
                ativo = True
                if membro.data_exclusao:
                    if (membro.data_exclusao.year < ano or 
                        (membro.data_exclusao.year == ano and 
                         membro.data_exclusao.month < mes_num)):
                        ativo = False
                
                if ativo:
                    contribuicoes[tipo] += 1
                    if membro.parcela_risco:
                        contribuicoes['parcelas_risco'] += 1
        
        return contribuicoes
