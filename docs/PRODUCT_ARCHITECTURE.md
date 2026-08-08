# Arquitetura oficial de produtos EduCode

## Decisão

O EduCode Enterprise passa a ser apresentado como um ecossistema de nove
produtos integrados. A decisão organiza posicionamento, navegação, roadmap e
comunicação. Ela não fragmenta a arquitetura técnica nem cria bancos de dados,
autenticações ou fontes de verdade independentes.

| Produto | Missão | Domínios canônicos principais |
| --- | --- | --- |
| EduCode Learn | Organizar a jornada de aprendizagem | projetos, conteúdos, unidades, trilhas e currículo |
| EduCode Studio | Criar experiências e materiais | HQ, Anime Studio, biblioteca visual, mídia e publicação |
| EduCode Practice | Promover prática formativa | atividades, quizzes e itens do Assessment Hub executados pelo Delivery |
| EduCode Assess | Avaliar formalmente | Assessment Hub, Delivery, Review e instrumentos protegidos |
| EduCode Tutor | Recomendar e orientar | IA orquestrada, adaptive learning, evolution e insights |
| EduCode Analytics | Transformar evidências em ação | analytics, alertas, intervenções e eficácia |
| EduCode Connect | Comunicar e colaborar | notificações, comentários, fóruns e colaboração |
| EduCode Credentials | Reconhecer evolução e autoria | portfólio, competências, produções e certificados |
| EduCode Admin | Administrar e governar | organizações, usuários, RBAC, segurança, auditoria e operação |

## Limites obrigatórios

### Practice e Assess

Practice representa prática formativa, feedback e novas tentativas. Assess
representa aplicação formal, instrumentos, notas e regras protegidas. Ambos
reutilizam questões do Assessment Hub e sessões do Assessment Delivery; não
devem possuir bancos de questões ou respostas paralelos.

### Learn e Tutor

Learn apresenta a jornada. Tutor recomenda próximos passos com explicação,
confiança e revisão humana. O Tutor não mantém uma trilha alternativa.

### Studio e Credentials

Studio cria e publica produções. Credentials referencia releases e evidências
imutáveis para portfólio e certificação, sem copiar os arquivos de origem.

### Analytics

Analytics agrega eventos e resultados dos produtos. Não substitui tentativas,
respostas, checkpoints, publicações ou evidências canônicas.

### Connect e Admin

Connect trata interação pedagógica e colaboração. Admin concentra políticas,
configuração, segurança e governança institucional.

## Navegação por perfil

- **Estudante:** Início, Learn, Practice, Studio, Tutor, Credentials e Connect.
- **Professor:** Learn, Studio, Practice, Assess, Tutor, Analytics e Connect.
- **Gestor:** Analytics, Credentials, Connect e Admin, além das visões
  pedagógicas autorizadas.

O diretório `/produtos` adapta o destino de cada produto ao papel da sessão.
As rotas históricas permanecem válidas durante a transição.

## Política de evolução

1. Novas sprints devem declarar a quais produtos pertencem.
2. Um recurso pode aparecer em vários produtos, mas mantém um único domínio
   técnico responsável.
3. Nomes de tabelas e APIs não são alterados apenas por reposicionamento.
4. A migração da navegação será incremental e preservará URLs existentes.
5. Permissões continuam definidas por RBAC e organização, não pelo produto
   exibido.
6. Métricas e auditoria devem registrar o domínio canônico e, quando útil, o
   produto de origem da interação.

## Próxima aplicação

A Sprint 18.4 será a primeira planejada explicitamente nesta arquitetura:

- Studio define pontos interativos em HQs e animes;
- Practice apresenta a atividade formativa;
- Assess fornece questões, sessões, respostas e correção;
- Analytics recebe as evidências resultantes.

## Rollback

A reversão remove o catálogo visual e as referências documentais. Nenhuma
migration ou alteração de dados é necessária, pois os domínios técnicos e as
rotas existentes permanecem inalterados.
