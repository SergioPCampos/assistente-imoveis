import glob
import os
from google import genai
from google.genai import types
import pandas as pd
import streamlit as st

# A sua chave de API do Gemini
os.environ["GEMINI_API_KEY"] = ""GEMINI_API_KEY""

client = genai.Client()

# Caminho da pasta onde ficam os arquivos dos imóveis
PASTA_IMOVEIS = "catalogo_imoveis"
os.makedirs(PASTA_IMOVEIS, exist_ok=True)


# Função para ler os dados dos imóveis nos arquivos de forma automática
def consultar_imoveis(termo_busca: str) -> str:
  """Lê os arquivos de imóveis (.xlsx, .csv ou .txt) na pasta e busca detalhes, preços e características."""
  arquivos = glob.glob(os.path.join(PASTA_IMOVEIS, "*.*"))

  if not arquivos:
    return (
        f"Aviso: Nenhum arquivo de imóvel encontrado na pasta"
        f" '{PASTA_IMOVEIS}'."
    )

  dados_consolidados = ""

  for arq in arquivos:
    extensao = arq.lower().split(".")[-1]
    try:
      if extensao in ["xlsx", "xls"]:
        df = pd.read_excel(arq)
        dados_consolidados += (
            f"\n--- Dados do arquivo {os.path.basename(arq)} ---\n"
            + df.to_string(index=False)
        )
      elif extensao == "csv":
        df = pd.read_csv(arq)
        dados_consolidados += (
            f"\n--- Dados do arquivo {os.path.basename(arq)} ---\n"
            + df.to_string(index=False)
        )
      elif extensao == "txt":
        with open(arq, "r", encoding="utf-8") as f:
          dados_consolidados += (
              f"\n--- Dados do arquivo {os.path.basename(arq)} ---\n"
              + f.read()
          )
    except Exception as e:
      dados_consolidados += f"\nErro ao ler o arquivo {arq}: {e}\n"

  prompt_busca = (
      f"Com base exclusivamente nas informações dos imóveis abaixo, responda"
      f" sobre: '{termo_busca}'. Informe valores, características e"
      f" detalhes de forma acolhedora e profissional para o"
      f" interessado:\n\n{dados_consolidados}"
  )

  resposta_ia = client.models.generate_content(
      model="gemini-1.5-flash",
      contents=prompt_busca,
  )
  return resposta_ia.text


# Interface Visual com Streamlit
st.set_page_config(page_title="Atendimento Imóveis", page_icon="🏠")
st.markdown("### 🏠 Assistente Virtual - Casa & Apartamento")
st.write(
    "Tire dúvidas em tempo real sobre os imóveis disponíveis para venda."
)

# Configurar o chat com o Gemini focado em imóveis
if "chat_imoveis" not in st.session_state:
  st.session_state.chat_imoveis = client.chats.create(
      model="gemini-1.5-flash",
      config=types.GenerateContentConfig(
          system_instruction=(
              "Você é um assistente imobiliário cordial e prestativo. "
              "O seu objetivo é ajudar potenciais compradores a tirarem dúvidas sobre "
              "a casa e o apartamento disponíveis. Utilize sempre a ferramenta consultar_imoveis "
              "para dar informações precisas baseadas nos arquivos."
          ),
          tools=[consultar_imoveis],
          temperature=0.3,
      ),
  )

# Histórico de mensagens
if "mensagens_imoveis" not in st.session_state:
  st.session_state.mensagens_imoveis = []

for msg in st.session_state.mensagens_imoveis:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# Entrada de texto do cliente
if prompt := st.chat_input("Ex: Qual o valor da casa? O apartamento tem garagem?"):
  st.session_state.mensagens_imoveis.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  with st.chat_message("assistant"):
    with st.spinner("A consultar detalhes dos imóveis..."):
      try:
        resposta_modelo = st.session_state.chat_imoveis.send_message(prompt)
        st.markdown(resposta_modelo.text)
        st.session_state.mensagens_imoveis.append(
            {"role": "assistant", "content": resposta_modelo.text}
        )
      except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
          mensagem_amigavel = (
              "Ops! O nosso atendimento está com muitas consultas neste"
              " momento e precisou de uma pausa rápida. 🕒 Por favor, aguarde"
              " só um minutinho e tente enviar a sua pergunta novamente!"
          )
        else:
          mensagem_amigavel = f"ERRO TÉCNICO DETALHADO: {e}"

        st.markdown(mensagem_amigavel)
        st.session_state.mensagens_imoveis.append(
            {"role": "assistant", "content": mensagem_amigavel}
        )