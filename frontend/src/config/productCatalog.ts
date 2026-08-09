export type EduCodeProductCode =
  | 'learn'
  | 'studio'
  | 'practice'
  | 'assess'
  | 'tutor'
  | 'analytics'
  | 'connect'
  | 'credentials'
  | 'admin'

export interface EduCodeProduct {
  code: EduCodeProductCode
  name: string
  tagline: string
  description: string
  icon: string
  capabilities: string[]
  routes: {
    student: string
    educator: string
    admin: string
  }
}

export const productCatalog: EduCodeProduct[] = [
  { code: 'learn', name: 'EduCode Learn', tagline: 'Aprender com propósito', description: 'Cursos, aulas, trilhas e conteúdos que organizam a jornada de aprendizagem.', icon: '◎', capabilities: ['Cursos e aulas', 'Conteúdos', 'Trilhas'], routes: { student: '/aluno', educator: '/projetos', admin: '/projetos' } },
  { code: 'studio', name: 'EduCode Studio', tagline: 'Criar para ensinar', description: 'HQs, animes, vídeos, áudios e materiais educacionais em um estúdio integrado.', icon: '✦', capabilities: ['HQs', 'Anime e vídeo', 'Materiais'], routes: { student: '/comic-reader', educator: '/estudio-professor', admin: '/estudio-professor' } },
  { code: 'practice', name: 'EduCode Practice', tagline: 'Praticar para avançar', description: 'Exercícios, quizzes, programação e simulações com feedback formativo.', icon: '⌁', capabilities: ['Exercícios', 'Quizzes', 'Simulações'], routes: { student: '/aluno/atividades', educator: '/publicacoes', admin: '/publicacoes' } },
  { code: 'assess', name: 'EduCode Assess', tagline: 'Avaliar com evidências', description: 'Avaliações, banco de questões, instrumentos, aplicação, correção e revisão.', icon: '✓', capabilities: ['Banco de questões', 'Avaliações', 'Instrumentos'], routes: { student: '/student/assessments', educator: '/avaliacoes', admin: '/avaliacoes' } },
  { code: 'tutor', name: 'EduCode Tutor', tagline: 'Orientar cada jornada', description: 'Tutoria de IA, recomendações explicáveis e aprendizagem adaptativa com decisão humana.', icon: '∞', capabilities: ['Tutoria de IA', 'Recomendações', 'Adaptação'], routes: { student: '/aluno/minha-trilha', educator: '/adaptativo', admin: '/adaptativo' } },
  { code: 'analytics', name: 'EduCode Analytics', tagline: 'Compreender para intervir', description: 'Desempenho, alertas, intervenções e eficácia baseados em evidências rastreáveis.', icon: '↗', capabilities: ['Desempenho', 'Intervenções', 'Eficácia'], routes: { student: '/aluno/progresso', educator: '/analytics', admin: '/analytics' } },
  { code: 'connect', name: 'EduCode Connect', tagline: 'Comunicar e colaborar', description: 'Comunicação, fóruns e colaboração entre estudantes, educadores e instituições.', icon: '◉', capabilities: ['Comunicação', 'Fóruns', 'Colaboração'], routes: { student: '/aluno/notificacoes', educator: '/notificacoes', admin: '/notificacoes' } },
  { code: 'credentials', name: 'EduCode Credentials', tagline: 'Reconhecer conquistas', description: 'Portfólio, competências, produções, reflexões e certificações do estudante.', icon: '◆', capabilities: ['Portfólio', 'Competências', 'Certificados'], routes: { student: '/aluno/portfolio', educator: '/credentials/certificados', admin: '/credentials/certificados' } },
  { code: 'admin', name: 'EduCode Admin', tagline: 'Governar com segurança', description: 'Instituições, usuários, segurança, operação e governança da plataforma.', icon: '▦', capabilities: ['Instituições', 'Segurança', 'Governança'], routes: { student: '/perfil', educator: '/organizacao', admin: '/admin/plataforma' } },
]

export function productRoute(
  product: EduCodeProduct,
  role: string | undefined,
): string {
  if (role === 'member') return product.routes.student
  if (role === 'owner' || role === 'admin') return product.routes.admin
  return product.routes.educator
}
