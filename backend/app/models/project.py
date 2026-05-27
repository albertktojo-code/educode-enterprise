from sqlalchemy import Column, Integer, String, Text
from app.database.database import Base


class Project(Base):

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    tema = Column(String)

    disciplina = Column(String)

    estilo = Column(String)

    resultado = Column(Text)