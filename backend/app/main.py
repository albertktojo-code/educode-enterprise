import os
import shutil
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, String, Text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column
from dotenv import load_dotenv
from openai import OpenAI

# 1. Configurações
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL or not OPENAI_API_KEY:
    raise ValueError("Verifique seu arquivo .env: DATABASE_URL e OPENAI_API_KEY são obrigatórios.")

client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase): pass

class Material(Base):
    __tablename__ = "materiais"
    id: Mapped[int] = mapped_column(primary_key=True)
    formato: Mapped[str] = mapped_column(String)
    disciplina: Mapped[str] = mapped_column(String)
    ano: Mapped[str] = mapped_column(String)
    tema: Mapped[str] = mapped_column(String)
    cenario: Mapped[str] = mapped_column(Text, nullable=True)
    roteiro: Mapped[str] = mapped_column(Text, nullable=True)
    personagens: Mapped[str] = mapped_column(Text, nullable=True)
    resultado: Mapped[str] = mapped_column(Text)

Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def extrair_texto_pdf(caminho: str) -> str:
    """Extrai texto de PDF garantindo compatibilidade de tipos para o join."""
    try:
        doc = fitz.open(caminho)
        # Garantia de que cada página seja convertida explicitamente para string
        textos = [str(p.get_text()) for p in doc if p.get_text() is not None]
        return "\n".join(textos)
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return ""

@app.post("/gerar-conteudo")
async def gerar_conteudo(
    formato: str = Form(...), disciplina: str = Form(...), ano: str = Form(...),
    tema: str = Form(...), cenario: str = Form(""), roteiro: str = Form(""), 
    personagens: str = Form(""), arquivo_cenario: UploadFile = File(None), 
    arquivo_personagens: UploadFile = File(None), db: Session = Depends(get_db)
):
    # Processamento de arquivos e extração de contexto
    contexto = ""
    if not os.path.exists("uploads"): os.makedirs("uploads")
    
    for f in [arquivo_cenario, arquivo_personagens]:
        if f:
            caminho = f"uploads/{f.filename}"
            with open(caminho, "wb") as buffer: shutil.copyfileobj(f.file, buffer)
            if f.filename and str(f.filename).lower().endswith(".pdf"):
                contexto += f"\n--- CONTEXTO DO ARQUIVO {f.filename} ---\n" + extrair_texto_pdf(caminho)

    # Chamada IA
    prompt = f"Use este contexto para embasar a resposta: {contexto}. Crie um material no formato {formato} para disciplina {disciplina}, ano {ano}. Tema: {tema}. Cenário: {cenario}. Roteiro: {roteiro}. Personagens: {personagens}."
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    resultado_ia = response.choices[0].message.content

    # Salvar
    novo = Material(
        formato=formato, disciplina=disciplina, ano=ano, tema=tema, 
        cenario=cenario, roteiro=roteiro, personagens=personagens, 
        resultado=resultado_ia
    )
    db.add(novo)
    db.commit()
    
    return {"resultado": resultado_ia}