import random
import secrets
import string
import uuid

import streamlit as st
from supabase import create_client


st.set_page_config(
    page_title="Jogo 21 Online",
    page_icon="🃏"
)

st.title("🃏 Jogo 21 Online")
st.write("Chegue perto de 21 pontos sem ultrapassar.")


def criar_baralho():
    naipes = ["♠", "♥", "♦", "♣"]
    valores = [
        "A", "2", "3", "4", "5", "6", "7",
        "8", "9", "10", "J", "Q", "K"
    ]

    baralho = [
        [valor, naipe]
        for naipe in naipes
        for valor in valores
    ]

    random.shuffle(baralho)
    return baralho


def calcular_pontos(cartas):
    pontos = 0
    ases = 0

    for valor, naipe in cartas:
        if valor in ["J", "Q", "K"]:
            pontos += 10
        elif valor == "A":
            pontos += 11
            ases += 1
        else:
            pontos += int(valor)

    while pontos > 21 and ases > 0:
        pontos -= 10
        ases -= 1

    return pontos


def guardar_identificacao(codigo, token, numero):
    st.session_state.codigo_sala = codigo
    st.session_state.token_jogador = token
    st.session_state.numero_jogador = numero


def mostrar_resultado(sala):
    pontos1 = calcular_pontos(sala["cartas_jogador1"])
    pontos2 = calcular_pontos(sala["cartas_jogador2"])

    st.subheader("Resultado")
    st.write(f"{sala['jogador1']}: {pontos1} pontos")
    st.write(f"{sala['jogador2']}: {pontos2} pontos")

    if pontos1 > 21 and pontos2 > 21:
        st.warning("Os dois ultrapassaram 21. Ninguém venceu.")
    elif pontos1 > 21:
        st.success(f"{sala['jogador2']} venceu!")
    elif pontos2 > 21:
        st.success(f"{sala['jogador1']} venceu!")
    elif pontos1 == pontos2:
        st.info("Empate!")
    elif pontos1 > pontos2:
        st.success(f"{sala['jogador1']} venceu!")
    else:
        st.success(f"{sala['jogador2']} venceu!")


try:
    banco = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    )
except Exception:
    st.error("Confira os dados da conexão nos Secrets do aplicativo.")
    st.stop()


def atualizar_partida(
    sala,
    alteracoes,
    exigir_vez=True,
    status_esperado="jogando"
):
    codigo = st.session_state.codigo_sala
    numero = st.session_state.numero_jogador
    token = st.session_state.token_jogador

    dados = dict(alteracoes)
    dados["versao"] = sala["versao"] + 1

    try:
        consulta = (
            banco.table("salas")
            .update(dados)
            .eq("codigo", codigo)
            .eq(f"token_jogador{numero}", token)
            .eq("status", status_esperado)
            .eq("versao", sala["versao"])
        )

        if exigir_vez:
            consulta = consulta.eq("vez", numero)

        resposta = consulta.execute()

    except Exception:
        st.error(
            "Não foi possível confirmar a ação. "
            "Aguarde a atualização da sala antes de tentar novamente."
        )
        return

    if resposta.data:
        st.rerun()
    else:
        st.warning(
            "A sala mudou. Aguarde a atualização automática."
        )


# Atualiza somente o painel da partida a cada 2 segundos.
@st.fragment(run_every="2s")
def mostrar_partida():
    codigo = st.session_state.codigo_sala
    numero = st.session_state.numero_jogador
    token = st.session_state.token_jogador

    st.write("Código da sala:")
    st.code(codigo, language=None)
    st.caption("A sala atualiza automaticamente a cada 2 segundos.")

    try:
        resposta = (
            banco.table("salas")
            .select(
                "jogador1, jogador2, status, vez, baralho, "
                "cartas_jogador1, cartas_jogador2, versao"
            )
            .eq("codigo", codigo)
            .eq(f"token_jogador{numero}", token)
            .execute()
        )
    except Exception:
        st.error(
            "Não foi possível consultar a sala. "
            "Tentaremos novamente automaticamente."
        )
        return

    if not resposta.data:
        st.warning("Sala não encontrada ou identificação inválida.")
        return

    sala = resposta.data[0]

    st.write(f"Jogador 1: {sala['jogador1']}")
    st.write(
        f"Jogador 2: {sala['jogador2'] or 'Aguardando...'}"
    )

    # Aguarda o segundo jogador.
    if not sala["jogador2"]:
        st.info(
            "Compartilhe o código e aguarde o segundo jogador."
        )
        return

    # Distribuição inicial.
    if not sala["cartas_jogador1"]:
        st.success("Os dois jogadores estão na sala!")

        if numero == 1:
            if st.button("Distribuir cartas"):
                baralho = criar_baralho()
                cartas1 = [baralho.pop(), baralho.pop()]
                cartas2 = [baralho.pop(), baralho.pop()]

                atualizar_partida(sala, {
                    "baralho": baralho,
                    "cartas_jogador1": cartas1,
                    "cartas_jogador2": cartas2,
                    "vez": 1
                })
        else:
            st.info(
                "Aguarde o jogador 1 distribuir as cartas."
            )

        return

    # Mostra apenas a mão do jogador desta janela.
    minhas_cartas = sala[f"cartas_jogador{numero}"]
    meu_nome = sala[f"jogador{numero}"]

    st.subheader(f"Cartas de {meu_nome}")

    for valor, naipe in minhas_cartas:
        st.write(f"**{valor} {naipe}**")

    pontos = calcular_pontos(minhas_cartas)
    st.info(f"Seus pontos: {pontos}")

    # Resultado e nova rodada.
    if sala["status"] == "finalizada":
        mostrar_resultado(sala)

        if numero == 1:
            if st.button("Nova rodada"):
                baralho = criar_baralho()
                cartas1 = [baralho.pop(), baralho.pop()]
                cartas2 = [baralho.pop(), baralho.pop()]

                atualizar_partida(
                    sala,
                    {
                        "baralho": baralho,
                        "cartas_jogador1": cartas1,
                        "cartas_jogador2": cartas2,
                        "vez": 1,
                        "status": "jogando"
                    },
                    exigir_vez=False,
                    status_esperado="finalizada"
                )
        else:
            st.info(
                "Aguarde o jogador 1 iniciar uma nova rodada."
            )

        return

    # Controle de vez.
    if sala["vez"] != numero:
        nome_da_vez = sala[f"jogador{sala['vez']}"]

        st.info(f"É a vez de {nome_da_vez}. Aguarde.")
        return

    st.success("É a sua vez!")

    if pontos == 21:
        st.success("Você fez 21! Encerre sua vez.")
    elif pontos > 21:
        st.error("Você ultrapassou 21! Encerre sua vez.")
    elif not sala["baralho"]:
        st.warning("O baralho acabou. Encerre sua vez.")

    coluna_pedir, coluna_parar = st.columns(2)

    with coluna_pedir:
        if st.button(
            "Pedir carta",
            disabled=pontos >= 21 or not sala["baralho"]
        ):
            baralho = list(sala["baralho"])
            cartas = list(minhas_cartas)
            cartas.append(baralho.pop())

            atualizar_partida(sala, {
                "baralho": baralho,
                f"cartas_jogador{numero}": cartas
            })

    with coluna_parar:
        if st.button("Parar / Encerrar minha vez"):
            if numero == 1:
                atualizar_partida(sala, {"vez": 2})
            else:
                atualizar_partida(
                    sala,
                    {"status": "finalizada"}
                )


# Tela de entrada.
if "codigo_sala" not in st.session_state:
    nome = st.text_input("Seu nome", max_chars=30)

    aba_criar, aba_entrar = st.tabs([
        "Criar sala",
        "Entrar em sala"
    ])

    with aba_criar:
        if st.button("Criar sala"):
            if not nome.strip():
                st.warning("Digite seu nome.")
            else:
                caracteres = (
                    string.ascii_uppercase + string.digits
                )
                codigo = "".join(
                    secrets.choice(caracteres)
                    for _ in range(8)
                )
                token = str(uuid.uuid4())

                try:
                    banco.table("salas").insert({
                        "codigo": codigo,
                        "jogador1": nome.strip(),
                        "token_jogador1": token
                    }).execute()

                except Exception:
                    st.error(
                        "Não foi possível criar a sala. "
                        "Tente novamente."
                    )
                else:
                    guardar_identificacao(codigo, token, 1)
                    st.rerun()

    with aba_entrar:
        codigo_digitado = st.text_input(
            "Código da sala",
            max_chars=8
        ).strip().upper()

        if st.button("Entrar na sala"):
            if not nome.strip() or not codigo_digitado:
                st.warning(
                    "Digite seu nome e o código da sala."
                )
            else:
                token = str(uuid.uuid4())

                try:
                    resposta = (
                        banco.table("salas")
                        .update({
                            "jogador2": nome.strip(),
                            "token_jogador2": token,
                            "status": "jogando"
                        })
                        .eq("codigo", codigo_digitado)
                        .eq("status", "aguardando")
                        .is_("jogador2", "null")
                        .execute()
                    )

                except Exception:
                    st.error(
                        "Não foi possível entrar. "
                        "Tente novamente."
                    )
                else:
                    if not resposta.data:
                        st.warning(
                            "Sala não encontrada ou já ocupada."
                        )
                    else:
                        guardar_identificacao(
                            codigo_digitado,
                            token,
                            2
                        )
                        st.rerun()

else:
    mostrar_partida()
