import os

from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter

os.environ['HUGGINGFACEHUB_API_TOKEN'] = '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'
os.environ["OPENAI_API_KEY"] = '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'
os.environ["GOOGLE_CSE_ID"] = "53b9c3fd76d8d4cbb"
os.environ["GOOGLE_API_KEY"] = "AIzaSyAYEpRPu24tU41bFn4QQB_2cZFmlOZxEEE"
from langchain.document_loaders import DirectoryLoader, TextLoader,powerpoint,word_document,excel,PyPDFLoader,PyMuPDFLoader,markdown,html,web_base,AsyncChromiumLoader,csv_loader
# from langchain.chains import ConversationalRetrievalChain
# from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import TokenTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from util import image_to_base64


"""
 pip install chromadb==0.4.24
 pip install tiktoken
"""
#导入文档加载器
from langchain.document_loaders import DirectoryLoader, TextLoader


def savevector(filepath,persist_directory,embedding_model_name,emb_type="openai",chunk_size=500, chunk_overlap=20):

    #指定chroma持久化的目录，当我们不知道目录时,chroma会将数据存储在内存中，随着程序的关闭就会删除
    # persist_directory = "C:\\dev\\ai-sns\\PyTalk\\pytalk\\vector_store"
    #按目录加载文档
    # loader = DirectoryLoader('C:\\0资料\\12.Omniverse\\青田项目\\经商局\\km\\cleaned\\', glob='**/*.txt')
    # docs = loader.load()
    #加载单个文档 可以自由选择
    # loader = TextLoader(filepath, encoding='utf8')
    ext = os.path.splitext(filepath)[1].lower()  # 获取文件扩展名并转为小写
    loaders = {
        '.txt': lambda path: TextLoader(path, encoding='utf8'),
        '.js': lambda path: TextLoader(path, encoding='utf8'),
        '.sql': lambda path: TextLoader(path, encoding='utf8'),
        '.pdf': PyPDFLoader,
        '.docx': word_document.UnstructuredWordDocumentLoader,
        '.xls': excel.UnstructuredExcelLoader,
        '.xlsx': excel.UnstructuredExcelLoader,
        '.csv': csv_loader.UnstructuredCSVLoader,
        '.pptx': powerpoint.UnstructuredPowerPointLoader,
        '.md': markdown.UnstructuredMarkdownLoader,
        '.html': html.UnstructuredHTMLLoader,
        '.htm': html.UnstructuredHTMLLoader,
    }

    if ext in loaders:
        loader = loaders[ext](filepath)
        docs = loader.load()  # 数据转换


    file_name=os.path.basename(filepath)




    if emb_type == "openai":
        # 调用openai Embeddings  OPENAI_API_BASE
        # embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
        embeddings = OpenAIEmbeddings(openai_api_key="sk-FgmkVGYRirTVzJrjDMZ5Wi27ekHKq57xGHL2lZO6lTMuUAj3",openai_api_base="https://api.chatanywhere.tech/v1/")
        # embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
    else:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)


    # 文档切块目的是为了防止超出GPTAPI的token限制 RecursiveCharacterTextSplitter,CharacterTextSplitter,TokenTextSplitter,CodeTextSplitter
    text_splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    # text_splitter = RecursiveCharacterTextSplitter()
    # text_splitter = CharacterTextSplitter()
    doc_texts = text_splitter.split_documents(docs)
    for doc in doc_texts:
        print(doc)
        doc.metadata["source"]=file_name
    # 向量化
    vectordb = Chroma.from_documents(doc_texts, embeddings, persist_directory=persist_directory)
    # 持久化
    vectordb.persist()
    #执行到这里你会发现public目录下多了一些以parquest结尾的文件,这些文件就是chroma持久化本地的向量数据
    del embeddings


def update_vector(filepath,persist_directory,embedding_model_name,emb_type="openai",chunk_size=500, chunk_overlap=20):

    delete_vector(filepath, persist_directory, embedding_model_name, emb_type)
    savevector(filepath, persist_directory, embedding_model_name, emb_type, chunk_size, chunk_overlap)




def delete_vector(filepath,persist_directory,embedding_model_name,emb_type = "openai"):
    file_name = os.path.basename(filepath)
    # if emb_type == "openai":
    #     # 调用openai Embeddings
    #     embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    #     # embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
    # else:
    #     embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    persist_directory = os.path.abspath(persist_directory)
    # vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    vectordb = Chroma(persist_directory=persist_directory)
    docs = vectordb.get(where={"source": file_name})
    if len(docs["ids"])>0:
        vectordb.delete(ids=docs["ids"])
    # del embeddings



def getvectorkm_String(question,persist_directory,embedding_model_name,emb_type = "openai"):
    if emb_type == "openai":
        # 调用openai Embeddings
        # embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
        embeddings = OpenAIEmbeddings(openai_api_key="sk-FgmkVGYRirTVzJrjDMZ5Wi27ekHKq57xGHL2lZO6lTMuUAj3", openai_api_base="https://api.chatanywhere.tech/v1/")
        # embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
    else:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)


    # 搜索
    # question = "对经国家、省、市等有关部门认定的企业技术中心及制造业创新中心，奖补政策是怎样的？"
    # 通过目录加载向量 这里的目录就是我们持久化的目录
    # persist_directory="C:\\dev\\ai-sns\\PyTalk\\pytalk\\vector_store\\vector"
    persist_directory = os.path.abspath(persist_directory)
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    # 向量搜索 根据你的问题进行本地向量搜索
    docs = vectordb.similarity_search_with_score(question, k=4)
    print(docs)
    # 将搜索到的信息重新转换为向量 (直接查到向量数据还不会😑😑）
    return docs


def get_file_content_tuple(file_path):
    # 判断文件扩展名
    _, file_extension = os.path.splitext(file_path)

    # 设定图片文件扩展名
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}

    if file_extension.lower() in image_extensions:
        # 如果是图片文件，调用 image_to_base64 函数
        content = image_to_base64(file_path)
        return ("image", content, file_path)
    else:
        # 否则调用 get_file_content 函数
        content = get_file_content(file_path)
        return ("document", content, file_path)


def get_file_content(file_path):
    ext = os.path.splitext(file_path)[1].lower()  # 获取文件扩展名并转为小写

    loaders = {
        '.js': lambda path: TextLoader(path, encoding='utf8'),
        '.txt': lambda path: TextLoader(path, encoding='utf8'),
        '.sql': lambda path: TextLoader(path, encoding='utf8'),
        '.pdf': PyPDFLoader,
        '.docx': word_document.UnstructuredWordDocumentLoader,
        '.xls': excel.UnstructuredExcelLoader,
        '.xlsx': excel.UnstructuredExcelLoader,
        '.csv': csv_loader.UnstructuredCSVLoader,
        '.pptx': powerpoint.UnstructuredPowerPointLoader,
        '.md': markdown.UnstructuredMarkdownLoader,
        '.html': html.UnstructuredHTMLLoader,
        '.htm': html.UnstructuredHTMLLoader,
    }

    if ext in loaders:
        loader = loaders[ext](file_path)
        docs = loader.load()  # 数据转换
        return ''.join(doc.page_content for doc in docs)  # 连接所有的 page_content

    raise ValueError(f"Unsupported file extension: {ext}")
