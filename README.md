# DeepShark 🦈

Análise de tráfego de rede orientada por IA em segundos.

---

## Visão geral

O **DeepShark** é uma aplicação web construída com **Streamlit** que permite carregar um arquivo `.pcap` (captura de pacotes) e fazer perguntas em linguagem natural sobre o tráfego capturado. Ele utiliza:

- **TShark** para extrair os campos relevantes de cada pacote;
- **Pandas** para organizar os dados em um _DataFrame_;
- **LangChain** + **OpenAI** ou **Groq** para gerar embeddings, armazenar vetores (FAISS) e responder às perguntas usando uma _Conversational Retrieval Chain_;
- Um _prompt_ especializado para garantir respostas concisas e baseadas apenas nos dados presentes no arquivo.

---

## Principais recursos

| Recurso                | Descrição                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Upload de `.pcap`      | Arraste o arquivo e deixe o DeepShark processar até **300 pacotes** (valor ajustável) |
| Chat interativo        | Converse em PT-BR ou EN sobre domínios, protocolos, anomalias etc.                    |
| Modelos LLM            | Selecione **OpenAI GPT-4o / o3** ou **Groq Llama-3 / Gemma-2**                        |
| Memória de conversação | Histórico persistente durante a sessão (apagar com 1 clique)                          |
| Segurança              | Nunca inventa dados; respostas sempre justificadas pelo conteúdo do `.pcap`           |

---

## Pré-requisitos

- Python **3.10+**
- **TShark** disponível no `PATH` (instalado com Wireshark)
- Chave de API válida para **OpenAI** ou **Groq**

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/usuario/deepshark.git
cd deepshark

# Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate    # Windows

# Instale as dependências
pip install -r requirements.txt
```

---

## Configuração

Crie um arquivo **`.env`** na raiz do projeto e defina pelo menos uma das chaves:

```
OPENAI_API_KEY=""   # opcional se usar OpenAI
GROQ_API_KEY=""    # opcional se usar Groq
```

## Como executar

```bash
streamlit run app.py
```

Abra o navegador indicado pelo Streamlit (geralmente `http://localhost:8501`) e:

1. Faça upload do arquivo `.pcap` na aba **Upload de Arquivos**;
2. Selecione o provedor (OpenAI ou Groq) e o modelo desejado na aba **Inicializar DeepShark**;
3. Clique em **Inicializar DeepShark** e aguarde o processamento;
4. Abra a aba **🦈 Bem-vindo ao DeepShark** para começar a conversar!

---

## Ajustando a quantidade de pacotes analisados

Por padrão o DeepShark processa **300 pacotes**. Para mudar esse limite:

| Arquivo      | Linha(s)            | O que alterar                        |
| ------------ | ------------------- | ------------------------------------ |
| `loaders.py` | `df = df.head(300)` | Substitua `300` pelo número desejado |
| `app.py`     |                     |                                      |

````python
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 300, "fetch_k": 300}
)
``` | Ajuste os valores de `k` e `fetch_k` para o mesmo número escolhido acima |

> Mantenha os três valores coerentes para evitar perguntas sobre pacotes que não foram indexados.

---

## Contribuições são bem-vindas 🤝
Toda sugestão, melhoria ou nova funcionalidade será muito bem recebida! Sinta-se à vontade para:
- Abrir uma *issue* com bugs ou ideias;
- Criar um *pull request* com suas contribuições;
- Adaptar o projeto para outros contextos e usos!

Este projeto está em constante evolução — participe! 💡
````
