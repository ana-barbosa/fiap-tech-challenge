# Consultation Scripts — Audio Simulation (14 patients)

Audio generated from these scripts should be saved to `dataset/synthetic/audio/`, named as `OAWXX_consultation.wav`, to keep the same naming convention as the video data. This is not raw data, so it lives under `synthetic/`, not `raw/`.

## Gait risk → audio scenario mapping

| Level | risk_score range | Participants | Scenario |
|---|---|---|---|
| Low | < 40 | OAW02, OAW08, OAW09, OAW11 | Routine check-up, no complaints |
| Moderate | 40–52 | OAW01, OAW03, OAW05, OAW06, OAW07, OAW10, OAW13, OAW14 | Mild fatigue OR mild pain (varies by patient) |
| High | > 52 | OAW04, OAW12 | Fatigue + moderate/severe pain, or anxiety |

---

## OAW01 — Moderate (mild fatigue)
```
Médico: Como você tem se sentido desde a última consulta?
Paciente: Ando um pouco mais cansada que o normal, principalmente no fim da tarde.
Médico: Isso tem atrapalhado suas atividades do dia a dia?
Paciente: Um pouco. Às vezes preciso parar para descansar antes de terminar as tarefas de casa.
Médico: Notou alguma dor ao caminhar ou se movimentar?
Paciente: Não, dor não. Só mesmo esse cansaço.
Médico: Entendido. Vamos acompanhar de perto e ajustar se necessário.
```

## OAW02 — Low (routine)
```
Médico: Como você tem passado?
Paciente: Bem, graças a Deus. Sem novidades.
Médico: Sono e apetite normais?
Paciente: Sim, tudo certo.
Médico: Alguma dor ou desconforto?
Paciente: Não, nenhum.
Médico: Ótimo, vamos manter o acompanhamento de rotina então.
```

## OAW03 — Moderate (mild pain)
```
Médico: Bom dia. Como está se sentindo?
Paciente: Bem, só senti uma dorzinha no joelho direito essa semana.
Médico: Essa dor aparece ao caminhar ou em repouso também?
Paciente: Mais ao caminhar, principalmente em escadas.
Médico: Está tomando alguma medicação para isso?
Paciente: Só um analgésico quando incomoda mais.
Médico: Vamos observar e se piorar, me avise.
```

## OAW04 — High (fatigue + moderate pain)
```
Médico: Como você tem estado desde a última visita?
Paciente: Não tenho passado muito bem, doutor. Estou muito cansada, quase sem energia.
Médico: Há quanto tempo isso vem acontecendo?
Paciente: Já faz umas duas semanas. E tenho sentido uma dor incômoda no quadril também.
Médico: Essa dor é constante ou vai e volta?
Paciente: É quase o tempo todo, piora quando ando mais.
Médico: Isso está afetando seu sono?
Paciente: Sim, tenho dormido mal por causa da dor.
Médico: Vamos reavaliar sua medicação e pedir alguns exames.
```

## OAW05 — Moderate (mild fatigue)
```
Médico: Como você está?
Paciente: Bem, só um pouco mais cansada que o costume.
Médico: Isso é constante ou só em certos momentos do dia?
Paciente: Mais de manhã, depois melhora um pouco.
Médico: Dor em algum lugar?
Paciente: Não, sem dor.
Médico: Entendido, vamos manter o acompanhamento.
```

## OAW06 — Moderate (mild pain)
```
Médico: Bom dia. Tudo bem?
Paciente: Tudo bem, só uma dorzinha nas costas de vez em quando.
Médico: Isso piora com algum movimento específico?
Paciente: Um pouco quando fico muito tempo em pé.
Médico: Está fazendo algum exercício ou fisioterapia?
Paciente: Ainda não, mas posso começar se for indicado.
Médico: Vou te encaminhar para avaliação com a fisioterapia.
```

## OAW07 — Moderate (mild fatigue)
```
Médico: Como tem se sentido?
Paciente: Um pouco cansada, mas nada muito diferente do normal.
Médico: Consegue fazer suas atividades normalmente?
Paciente: Consigo, só preciso de mais pausas do que antes.
Médico: Dor ou desconforto?
Paciente: Não, nada disso.
Médico: Tudo bem, vamos continuar observando.
```

## OAW08 — Low (routine)
```
Médico: Como vai?
Paciente: Vou bem, sem queixas.
Médico: Apetite e sono normais?
Paciente: Sim, tudo em ordem.
Médico: Nenhuma dor?
Paciente: Nenhuma.
Médico: Perfeito, seguimos com o acompanhamento de rotina.
```

## OAW09 — Low (routine)
```
Médico: Bom dia. Tudo bem com você?
Paciente: Tudo ótimo, sem novidades.
Médico: Consegue fazer suas caminhadas normalmente?
Paciente: Sim, sem nenhuma dificuldade.
Médico: Ótimo, nada a ajustar por enquanto.
Paciente: Que bom.
```

## OAW10 — Moderate (mild pain)
```
Médico: Como você está?
Paciente: Bem, só uma dor leve no tornozelo esquerdo.
Médico: Isso começou depois de algum esforço?
Paciente: Acho que sim, andei mais que o normal na semana passada.
Médico: Vamos observar, se persistir fazemos um exame de imagem.
Paciente: Combinado.
```

## OAW11 — Low (routine)
```
Médico: Como tem passado?
Paciente: Muito bem, sem queixas.
Médico: Sem dores, sem cansaço?
Paciente: Nada disso, estou bem disposta.
Médico: Ótimo, mantemos o acompanhamento de rotina.
```

## OAW12 — High (fatigue + anxiety)
```
Médico: Como você tem se sentido ultimamente?
Paciente: Não muito bem, doutor. Estou muito cansada e ando ansiosa também.
Médico: Consegue dormir bem?
Paciente: Não, tenho acordado várias vezes à noite, preocupada com quedas.
Médico: Notou alguma dificuldade a mais para caminhar?
Paciente: Sim, sinto que minhas pernas não respondem como antes, fico insegura.
Médico: Isso tem te deixado mais isolada ou evitando sair de casa?
Paciente: Um pouco, sim. Tenho medo de cair sozinha.
Médico: Vamos conversar sobre um acompanhamento mais próximo e possíveis ajustes no tratamento.
```

## OAW13 — Moderate (mild pain)
```
Médico: Bom dia. Como está?
Paciente: Bem, só uma dorzinha no quadril de vez em quando.
Médico: Isso atrapalha para caminhar?
Paciente: Um pouco, mas nada grave.
Médico: Vamos manter o acompanhamento e observar se piora.
Paciente: Está bem.
```

## OAW14 — Moderate (mild fatigue)
```
Médico: Como você tem estado?
Paciente: Um pouco cansada, mas nada fora do normal para minha idade.
Médico: Isso interfere nas suas atividades diárias?
Paciente: Só um pouco, preciso descansar mais entre as tarefas.
Médico: Sem dores?
Paciente: Sem dores, só o cansaço mesmo.
Médico: Entendido, seguimos observando.
```
