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
        self.membros = []
        self._id_counter = 1
    
    def adicionar_membro(self, tipo: str, data_nascimento: str, parcela_risco: bool = False):
        try:
            nascimento = date.fromisoformat(data_nascimento)
            membro = MembroFamilia(
                tipo=tipo,
                data_nascimento=nascimento,
                parcela_risco=parcela_risco,
                id=self._id_counter
            )
            self._id_counter += 1
            self.membros.append(membro)
            return True
        except ValueError:
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
    
    def calcular_contribuicoes(self, ano: int) -> Dict[str, float]:
        """Retorna a estrutura esperada para cálculo das contribuições"""
        return {
            'titular': self.contar_por_tipo('titular'),
            'conjuge': self.contar_por_tipo('conjuge'),
            'dependente': self.contar_por_tipo('dependente', ano),
            'agregado_jovem': self.contar_por_tipo('agregado_jovem', ano),
            'agregado_maior': self.contar_por_tipo('agregado_maior', ano),
            'parcelas_risco': {
                m.id: m.tipo for m in self.membros if m.parcela_risco
            }
        }
