from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parent

DOCUMENTS = {
    "financiamento_programas": {
        "title": "Programas de Financiamento Imobiliário",
        "paragraphs": [
            "No Brasil, a compra de um imóvel financiado costuma passar pelo Sistema "
            "Financeiro de Habitação (SFH) ou pelo Sistema de Financiamento Imobiliário "
            "(SFI). O SFH é voltado a imóveis residenciais de valor mais baixo (o teto "
            "varia por banco e por região, e é reajustado periodicamente) e costuma "
            "oferecer taxas de juros mais baixas, além de usar a Tabela Price ou o "
            "Sistema de Amortização Constante (SAC) para calcular as parcelas. O SFI, "
            "por sua vez, é usado para imóveis de valor mais alto ou fora dos critérios "
            "do SFH, com taxas geralmente um pouco maiores e mais liberdade de negociação "
            "entre banco e comprador.",
            "O programa Minha Casa Minha Vida (MCMV) é a principal linha de financiamento "
            "subsidiado do governo federal para famílias de baixa e média renda. Ele "
            "oferece taxas de juros reduzidas e, para as faixas de renda mais baixas, "
            "subsídio direto no valor do imóvel - ou seja, parte do preço é abatida pelo "
            "governo. As faixas de renda e os limites de valor do imóvel são reajustados "
            "de tempos em tempos, então vale sempre confirmar as condições vigentes com "
            "um banco ou a Caixa Econômica Federal antes de fechar negócio.",
            "O FGTS (Fundo de Garantia do Tempo de Serviço) pode ser usado de duas formas "
            "na compra de um imóvel: como parte do valor de entrada (reduzindo o quanto "
            "precisa ser financiado) ou para amortizar/quitar parcelas do financiamento "
            "ao longo do tempo. Em geral, é preciso ter pelo menos 3 anos de contribuição "
            "ao FGTS (não necessariamente no mesmo emprego) e o imóvel precisa ser "
            "residencial, urbano e destinado à moradia do comprador, entre outras regras "
            "que variam conforme o programa de financiamento escolhido.",
            "As taxas de juros de financiamento imobiliário no Brasil costumam ficar, de "
            "forma geral, entre 8% e 12% ao ano, variando bastante conforme o programa, "
            "o banco, o relacionamento do cliente com a instituição e o cenário econômico "
            "no momento da contratação. Vale sempre simular o financiamento em mais de um "
            "banco antes de decidir, já que as condições podem variar significativamente.",
        ],
    },
    "itbi": {
        "title": "ITBI - Imposto sobre Transmissão de Bens Imóveis",
        "paragraphs": [
            "O ITBI é um imposto municipal cobrado sempre que um imóvel muda de "
            "proprietário por meio de venda (não incide em heranças, que têm o ITCMD, um "
            "imposto estadual diferente). Como é um tributo municipal, tanto a alíquota "
            "quanto a forma de cálculo variam de cidade para cidade - de forma geral, o "
            "ITBI costuma ficar entre 2% e 3% do valor da transação ou do valor venal do "
            "imóvel (o que for maior), mas é sempre importante confirmar o percentual "
            "exato e a base de cálculo junto à prefeitura da cidade onde o imóvel está "
            "localizado.",
            "O pagamento do ITBI geralmente é responsabilidade do comprador (embora isso "
            "possa ser negociado entre as partes no contrato) e costuma ser uma condição "
            "para o registro da escritura em cartório - ou seja, sem o comprovante de "
            "pagamento do ITBI, normalmente não é possível formalizar a transferência da "
            "propriedade. Em compras financiadas, o banco costuma exigir a guia do ITBI "
            "quitada antes da liberação final do crédito.",
            "Algumas prefeituras oferecem descontos ou condições especiais de pagamento do "
            "ITBI para imóveis financiados por programas habitacionais de interesse "
            "social, como o Minha Casa Minha Vida - as regras e percentuais variam por "
            "município, então vale sempre consultar a prefeitura local para confirmar se "
            "algum benefício se aplica ao caso específico do comprador.",
        ],
    },
    "escritura_registro": {
        "title": "Escritura e Registro de Imóveis",
        "paragraphs": [
            "A escritura pública é o documento lavrado em cartório de notas que formaliza "
            "a venda de um imóvel entre comprador e vendedor. Em compras à vista acima de "
            "um determinado valor (definido por lei e reajustado periodicamente), a "
            "escritura pública é obrigatória; em compras financiadas, o próprio contrato "
            "de financiamento com o banco costuma ter força de escritura pública, "
            "dispensando esse passo separado - mas isso pode variar conforme o banco e o "
            "tipo de financiamento, então vale sempre confirmar com a instituição "
            "financeira.",
            "Depois de lavrada a escritura (ou assinado o contrato de financiamento com "
            "força de escritura), é necessário registrá-la no Cartório de Registro de "
            "Imóveis da região onde o imóvel está localizado. É esse registro - e não a "
            "escritura em si - que efetivamente transfere a propriedade para o nome do "
            "comprador perante a lei. Antes do registro, o comprador ainda não é "
            "considerado o dono legal do imóvel, mesmo já tendo pago por ele.",
            "Os custos de escritura e registro variam por cartório e por estado, mas "
            "costumam somar, de forma geral, entre 1% e 3% do valor do imóvel - vale "
            "sempre pedir um orçamento detalhado ao cartório local antes de fechar "
            "negócio, já que esses valores não são padronizados nacionalmente.",
        ],
    },
    "condominio_iptu": {
        "title": "Condomínio e IPTU",
        "paragraphs": [
            "A taxa de condomínio é cobrada apenas em imóveis que fazem parte de um "
            "condomínio (a maioria dos apartamentos e alguns conjuntos de casas), e cobre "
            "despesas comuns como manutenção de áreas coletivas, segurança, limpeza, "
            "salários de funcionários e fundo de reserva do prédio. O valor varia muito "
            "conforme o padrão do empreendimento, a quantidade de amenidades (piscina, "
            "academia, portaria 24h) e o número de unidades que dividem os custos - não "
            "há um valor de referência único, e vale sempre pedir a convenção de "
            "condomínio e o histórico de cobranças antes de decidir pela compra.",
            "O IPTU (Imposto Predial e Territorial Urbano) é um imposto municipal anual "
            "cobrado de todo proprietário de imóvel urbano, esteja ele em condomínio ou "
            "não. O valor é calculado com base no valor venal do imóvel (uma estimativa "
            "feita pela prefeitura, que pode diferir do valor de mercado) e na alíquota "
            "definida pelo município - por isso, o IPTU de um mesmo tipo de imóvel pode "
            "variar bastante entre cidades diferentes, ou até entre bairros da mesma "
            "cidade.",
            "Tanto o valor do condomínio quanto o do IPTU costumam ser considerados pelos "
            "bancos na hora de avaliar a capacidade de pagamento de quem está financiando "
            "um imóvel, já que são custos recorrentes que se somam à parcela do "
            "financiamento. Vale sempre incluir essas despesas no planejamento financeiro "
            "geral, e não apenas o valor da parcela do financiamento em si.",
        ],
    },
    "elegibilidade_documentacao": {
        "title": "Elegibilidade e Documentação para Financiamento",
        "paragraphs": [
            "De forma geral, para financiar um imóvel no Brasil é preciso comprovar renda "
            "compatível com o valor das parcelas (os bancos costumam trabalhar com um "
            "limite de comprometimento de renda mensal, tipicamente na faixa de 20% a "
            "30%, mas isso varia por instituição), ter idade mínima (geralmente 18 anos) "
            "e não estar com o nome negativado em órgãos de proteção ao crédito. Cada "
            "banco tem seus próprios critérios de análise de crédito, então é comum que "
            "um comprador seja aprovado em uma instituição e não em outra.",
            "A documentação básica geralmente inclui documento de identidade e CPF, "
            "comprovante de renda (holerites, declaração de imposto de renda ou extratos "
            "bancários, dependendo se a renda é formal ou informal), comprovante de "
            "residência, certidão de estado civil e, quando aplicável, extrato do FGTS. "
            "Autônomos e profissionais liberais costumam precisar apresentar documentação "
            "adicional para comprovar renda de forma consistente ao longo dos últimos "
            "meses ou anos.",
            "Antes de sair procurando imóveis, muitos compradores optam por buscar uma "
            "pré-análise de crédito ou uma carta de crédito pré-aprovada junto ao banco - "
            "isso ajuda a entender de forma realista qual faixa de valor de imóvel está "
            "ao alcance, e agiliza o processo quando o imóvel certo é encontrado. As "
            "condições exatas de pré-aprovação e sua validade variam por instituição "
            "financeira.",
        ],
    },
}


def build_pdf(title: str, paragraphs: list[str]) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    for paragraph in paragraphs:
        pdf.multi_cell(0, 7, paragraph)
        pdf.ln(4)
    return pdf


def main() -> None:
    for doc_id, spec in DOCUMENTS.items():
        pdf = build_pdf(spec["title"], spec["paragraphs"])
        output_path = OUTPUT_DIR / f"{doc_id}.pdf"
        pdf.output(str(output_path))
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
