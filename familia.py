# familia.py
from dataclasses import dataclass
from typing import List

@dataclass
class MembroFamilia:
    tipo: str  # 'titular', 'conjuge', 'filho', 'neto'
    idade: int
    posicao: int = 1  # Para diferenciar filho1, filho2, etc.

class GrupoFamiliar:
    def __init__(self):
        self.membros = []
    
    def adicionar_membro(self, tipo: str, idade: int):
        # Conta quantos membros do mesmo tipo já existem para definir a posição
        posicao = sum(1 for m in self.membros if m.tipo == tipo) + 1
        self.membros.append(MembroFamilia(tipo, idade, posicao))
    
    def contar_por_tipo(self, tipo: str) -> int:
        return sum(1 for m in self.membros if m.tipo == tipo)
    
    def obter_membros_por_tipo(self, tipo: str) -> List[MembroFamilia]:
        return [m for m in self.membros if m.tipo == tipo]
