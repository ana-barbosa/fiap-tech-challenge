from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ValeDoParaibaCity(str, Enum):
    SAO_JOSE_DOS_CAMPOS = "São José dos Campos"
    TAUBATE = "Taubaté"
    GUARATINGUETA = "Guaratinguetá"
    PINDAMONHANGABA = "Pindamonhangaba"
    JACAREI = "Jacareí"
    CACAPAVA = "Caçapava"
    LORENA = "Lorena"
    CRUZEIRO = "Cruzeiro"
    CAMPOS_DO_JORDAO = "Campos do Jordão"
    CUNHA = "Cunha"
    SAO_BENTO_DO_SAPUCAI = "São Bento do Sapucaí"
    MONTEIRO_LOBATO = "Monteiro Lobato"
    SAO_LUIZ_DO_PARAITINGA = "São Luiz do Paraitinga"
    UBATUBA = "Ubatuba"
    CARAGUATATUBA = "Caraguatatuba"
    SAO_SEBASTIAO = "São Sebastião"
    ILHABELA = "Ilhabela"


class Intent(str, Enum):
    BUY = "comprar"
    RENT = "alugar"
    INVEST = "investir"


class Urgency(str, Enum):
    IMMEDIATE = "imediata"
    FEW_MONTHS = "poucos_meses"
    JUST_BROWSING = "so_olhando"


class InvestorProfile(str, Enum):
    FIRST_TIME = "iniciante"
    EXPERIENCED = "experiente"


class Qualification(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    intent: Intent | None = Field(
        default=None, alias="intencao", description="O que o cliente está tentando fazer."
    )
    price_min: float | None = Field(
        default=None,
        ge=0,
        alias="preco_min",
        description=(
            "Valor mínimo em reais (R$). Preço de venda se a intenção for comprar/investir, valor "
            "do aluguel mensal se for alugar. Sempre preencha junto com preco_max - se o cliente der "
            "um valor aproximado (ex: 'por volta de R$2000'), transforme em uma faixa (ex: ±15%) em "
            "vez de deixar preco_max vazio."
        ),
    )
    price_max: float | None = Field(
        default=None,
        ge=0,
        alias="preco_max",
        description="Valor máximo em reais (R$), mesma unidade de preco_min. Veja preco_min para valores aproximados.",
    )
    rooms: int | None = Field(default=None, gt=0, alias="quartos", description="Número de quartos desejado.")
    region: list[ValeDoParaibaCity] | None = Field(
        default=None,
        alias="regiao",
        description=(
            "Uma ou mais cidades candidatas que o cliente mencionou explicitamente, pelo nome exato "
            "da cidade. Se o cliente descrever uma cidade por características (tamanho, clima, "
            "'cidade de montanha') em vez de nomear uma, não adivinhe uma cidade aqui - isso é "
            "resolvido conversacionalmente com uma busca de dados geográficos primeiro, e só é "
            "registrado aqui depois de confirmado."
        ),
    )

    @field_validator("region", mode="before")
    @classmethod
    def _wrap_single_city_in_list(cls, value):
        if isinstance(value, str):
            return [value]
        return value

    urgency: Urgency | None = Field(
        default=None, alias="urgencia", description="Prazo para se mudar. Só relevante quando a intenção é comprar."
    )

    lease_duration_months: int | None = Field(
        default=None,
        gt=0,
        alias="duracao_contrato_meses",
        description="Duração desejada do contrato de aluguel, em meses. Só relevante quando a intenção é alugar.",
    )
    move_in_date: str | None = Field(
        default=None,
        alias="data_mudanca",
        description=(
            "Data desejada de mudança/vacância, no formato ISO 8601 (AAAA-MM-DD). Só relevante "
            "quando a intenção é alugar."
        ),
    )

    investor_profile: InvestorProfile | None = Field(
        default=None,
        alias="perfil_investidor",
        description="Nível de experiência do investidor. Só relevante quando a intenção é investir.",
    )
    ticket_size: float | None = Field(
        default=None,
        ge=0,
        alias="valor_investimento",
        description="Valor em reais (R$) que o investidor pretende aplicar. Só relevante quando a intenção é investir.",
    )
    expected_return: float | None = Field(
        default=None,
        ge=0,
        alias="retorno_esperado",
        description=(
            "Retorno anual esperado pelo cliente, como fração (0.08 para 8%), não como porcentagem. "
            "Essa unidade precisa ser igual ao gross_yield salvo no roi_summary, já que é comparado "
            "depois com o rendimento real calculado. Só relevante quando a intenção é investir."
        ),
    )

    @model_validator(mode="after")
    def _price_min_not_above_max(self) -> "Qualification":
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError(f"price_min ({self.price_min}) cannot be greater than price_max ({self.price_max})")
        return self
