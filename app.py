import streamlit as st
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from loaders import carrega_pcap
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import tempfile
import time
from langchain_core.messages import HumanMessage, AIMessage

# Carrega variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TIPOS_ARQUIVOS_VALIDOS = ["PCAP"]

CONFIG_MODELOS = {
    "Groq": {
        "modelos": ["llama-3.3-70b-versatile", "gemma2-9b-it"],
        "chat": ChatGroq
    },
    "OpenAI": {
        "modelos": ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "chat": ChatOpenAI
    }
}

# Prompt customizado
MEU_PROMPT = """
Você é uma especialista em análise de tráfego de rede e segurança cibernética, com foco em interpretar arquivos .pcap (packet capture). Seu objetivo é ajudar o usuário a entender o que está acontecendo no tráfego capturado.

Com base exclusivamente nas informações extraídas do arquivo .pcap fornecido (como IPs de origem e destino, protocolos usados, conteúdos de pacotes, informações de DNS, HTTP, TLS, entre outros), responda de forma objetiva e precisa às perguntas feitas.

Se a resposta não puder ser determinada com base nos dados disponíveis no .pcap, diga claramente:
"Não há dados suficientes no arquivo para responder com precisão."

Você pode responder perguntas como:

    Quais domínios foram acessados?
    Houve comunicação suspeita?
    Algum protocolo não usual foi utilizado?
    Houve tentativa de exfiltração de dados?
    Qual foi o User-Agent utilizado?
    Algum IP aparece com comportamento anômalo?
    Quantos pacotes foram capturados/recebeu? (para responder essa pergunta, você deve contar o número de pacotes no arquivo .pcap)
    Quais foram os principais protocolos utilizados?
    Quais foram os principais hosts envolvidos?
    Quais foram os principais serviços acessados?

Nunca invente informações. Sempre baseie sua resposta apenas nos dados do arquivo .pcap.


----------------
{context}
----------------
Histórico do chat:
{chat_history}
----------------
Pergunta: {question}
Resposta:
"""

prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=MEU_PROMPT,
)

def inicializa_memoria():
    return ConversationBufferMemory(return_messages=True)

def carrega_arquivos(tipo_arquivo, arquivo):
    if tipo_arquivo == "PCAP":
        caminho_arquivo = os.path.join(tempfile.gettempdir(), arquivo.name)
        with open(caminho_arquivo, "wb") as f:
            f.write(arquivo.read())
        return caminho_arquivo
    return None

def sidebar():
    tabs = st.tabs(["Upload de Arquivos", "Inicializar DeepShark"])
    with tabs[0]:
        tipo_arquivo = st.selectbox("Selecione o tipo de arquivo", TIPOS_ARQUIVOS_VALIDOS)
        if tipo_arquivo == "PCAP":
            arquivo = st.file_uploader("Faça o upload do arquivo PCAP", type=["pcap"])
            if arquivo:
                caminho_arquivo = carrega_arquivos(tipo_arquivo, arquivo)
                st.session_state["caminho_arquivo"] = caminho_arquivo
                st.success(f"Arquivo PCAP carregado com sucesso! Caminho: {caminho_arquivo}. Vá para a aba 'Inicializar DeepShark'.")

    with tabs[1]:
        provedor = st.selectbox("Selecione o provedor dos modelos", list(CONFIG_MODELOS.keys()))
        if provedor == "OpenAI" and not OPENAI_API_KEY:
            st.error("Erro: A API key da OpenAI não está configurada.")
            return
        elif provedor == "Groq" and not GROQ_API_KEY:
            st.error("Erro: A API key da Groq não está configurada.")
            return
        modelo = st.selectbox("Selecione o modelo", CONFIG_MODELOS[provedor]["modelos"])

        if st.button("Inicializar DeepShark", use_container_width=True):
            caminho_arquivo = st.session_state.get("caminho_arquivo", None)
            if not caminho_arquivo:
                st.error("Por favor, faça o upload de um arquivo PCAP antes de inicializar o DeepShark.")
                return
            resultado = carrega_pcap(caminho_arquivo)
            if isinstance(resultado, tuple) and isinstance(resultado[0], str) and resultado[0].startswith("Erro"):
                st.error(f"Erro ao processar o arquivo PCAP: {resultado[0]}")
                return
            csv_path, documentos, df, vectorstore = resultado
            retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 300, "fetch_k": 300})
            chat = CONFIG_MODELOS[provedor]["chat"](model=modelo, api_key=(OPENAI_API_KEY if provedor == "OpenAI" else GROQ_API_KEY))
            memoria = inicializa_memoria()
            chain = ConversationalRetrievalChain.from_llm(
                llm=chat,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": prompt},
                return_source_documents=False,
                verbose=True
            )
            st.session_state["deep_shark_inicializado"] = True
            st.session_state["chain"] = chain
            st.session_state["memoria"] = memoria
            st.success("DeepShark inicializado com sucesso! Agora você pode interagir no chat.")
            st.info(f"Total de pacotes processados: {len(df)}")

        if st.button("Apagar Chat", use_container_width=True):
            st.session_state["memoria"] = inicializa_memoria()
            mensagem = st.empty()
            mensagem.success("Histórico do chat apagado com sucesso!")
            time.sleep(2)
            mensagem.empty()

def pagina_chat():
    st.header("🦈 Bem-vindo ao DeepShark!", divider=True)
    if not st.session_state.get("deep_shark_inicializado", False):
        st.info("Por favor, inicialize o DeepShark na aba lateral antes de começar.")
        return
    memoria = st.session_state.get("memoria", inicializa_memoria())
    chat_history_for_chain = []
    for msg in memoria.chat_memory.messages:
        if isinstance(msg, HumanMessage):
            chat_history_for_chain.append((msg.content, ""))
        elif isinstance(msg, AIMessage):
            if chat_history_for_chain and chat_history_for_chain[-1][1] == "":
                chat_history_for_chain[-1] = (chat_history_for_chain[-1][0], msg.content)
            else:
                chat_history_for_chain.append(("", msg.content)) 

    for mensagem in memoria.chat_memory.messages:
        chat = st.chat_message(mensagem.type)
        chat.markdown(mensagem.content)
    input_usuario = st.chat_input("Fale com o DeepShark")
    if input_usuario:
        chat = st.chat_message("human")
        chat.markdown(input_usuario)
        chat = st.chat_message("ai")
        resposta = ""
        try:
            with st.spinner("DeepShark analisando dados..."):
                resposta = st.session_state["chain"].invoke({
                    "question": input_usuario,
                    "chat_history": chat_history_for_chain
                })["answer"]
                chat.write(resposta)
        except Exception as e:
            st.error(f"Erro ao obter resposta: {str(e)}")
            resposta = "Desculpe, ocorreu um erro ao processar sua pergunta."
        finally:
            memoria.chat_memory.add_user_message(input_usuario)
            memoria.chat_memory.add_ai_message(resposta)
            st.session_state["memoria"] = memoria

def main():
    if not OPENAI_API_KEY and not GROQ_API_KEY:
        st.error("Erro: Nenhuma API key está configurada no arquivo .env. Verifique e tente novamente.")
        st.stop()
    if "deep_shark_inicializado" not in st.session_state:
        st.session_state["deep_shark_inicializado"] = False
    if "memoria" not in st.session_state:
        st.session_state["memoria"] = inicializa_memoria()
    if "chain" not in st.session_state:
        st.session_state["chain"] = None
    with st.sidebar:
        sidebar()
    pagina_chat()

if __name__ == "__main__":
    main()