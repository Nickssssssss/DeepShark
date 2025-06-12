import subprocess
import platform
import tempfile
import pandas as pd
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def hex_to_ascii(hexstr):
    try:
        hexstr = hexstr.replace(":", "").replace(" ", "")
        if not hexstr or hexstr.lower() in ["n/d", "nan"]:
            return ""
        bytes_data = bytes.fromhex(hexstr)
        return bytes_data.decode("ascii", errors="ignore")
    except Exception:
        return ""

def carrega_pcap(caminho_arquivo):
    try:
        tshark_cmd = "tshark.exe" if platform.system() == "Windows" else "tshark"
        csv_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

        campos = [
            "frame.number",
            "frame.time", "frame.len", "ip.src", "ip.dst", "ip.proto",
            "tcp.srcport", "tcp.dstport", "tcp.flags",
            "udp.srcport", "udp.dstport",
            "http.host", "http.request.uri", "http.user_agent", "http.request.full_uri",
            "http.response.code", "http.response.phrase", "tls.handshake.extensions_server_name",
            "dns.qry.name", "dns.resp.name", "data.data", "_ws.col.Info", "_ws.col.Protocol"
        ]

        comando = [tshark_cmd, "-r", caminho_arquivo, "-T", "fields"]
        for campo in campos:
            comando += ["-e", campo]
        comando += ["-E", "header=y", "-E", "separator=,", "-E", "quote=d"]

        with open(csv_temp.name, "w", encoding="utf-8") as f:
            subprocess.run(comando, stdout=f, check=True)

        df = pd.read_csv(csv_temp.name, sep=",")
        df = df.astype(str).fillna("N/D")
        df = df.head(300)
        df.to_csv(csv_temp.name, index=False)

        # Converte data.data para ascii_payload
        if "data.data" in df.columns:
            df["ascii_payload"] = df["data.data"].apply(lambda x: hex_to_ascii(x) if x not in ["N/D", "nan", ""] else "")

        documentos = []
        for i, linha in df.iterrows():
            conteudo = "\n".join(
                [f"{col}: {linha[col]}" for col in df.columns if str(linha[col]).lower() not in ["nan", "n/d", ""]]
            )
            # Adiciona ascii_payload destacado, se existir
            if "ascii_payload" in linha and linha["ascii_payload"]:
                conteudo += f"\nascii_payload: {linha['ascii_payload']}"
            documentos.append(Document(page_content=conteudo, metadata={"linha": i}))

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = splitter.split_documents(documentos)

        vectorstore = FAISS.from_documents(chunks, embedding=OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small"))

        return csv_temp.name, documentos, df, vectorstore

    except subprocess.CalledProcessError as e:
        return f"Erro ao executar o tshark: {str(e)}", [], pd.DataFrame(), None
    except FileNotFoundError:
        return "Erro: O tshark não está instalado ou não está no PATH do sistema.", [], pd.DataFrame(), None
    except Exception as e:
        return f"Erro ao processar o arquivo PCAP: {str(e)}", [], pd.DataFrame(), None