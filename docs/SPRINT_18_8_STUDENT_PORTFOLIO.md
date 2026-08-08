# Sprint 18.8 — Portfólio de aprendizagem do estudante

## Produtos e domínio

- **EduCode Credentials:** apresenta o portfólio e as competências.
- **EduCode Assess:** continua sendo a fonte das atividades, tentativas e resultados.
- **EduCode Analytics:** continua sendo a fonte das métricas de competência.
- **EduCode Studio:** fornece somente as HQs e publicações audiovisuais autorizadas.

O incremento não cria tabelas, endpoints ou cópias de evidências. A nova rota `/aluno/portfolio` compõe dados canônicos já filtrados pelo estudante e pela organização.

## Incremento entregue

- resumo pessoal de evidências concluídas, média, competências e conteúdos;
- lista de atividades concluídas com melhor resultado e acesso à revisão;
- competências em destaque com quantidade de evidências;
- galeria de HQs e vídeos disponíveis na jornada;
- acesso pelo menu do estudante, Portal do Estudante e diretório EduCode Credentials;
- estados independentes de carregamento, falha parcial e vazio;
- navegação responsiva e foco visível.

## Limites desta versão

HQs e vídeos da galeria são conteúdos autorizados para aprendizagem, não produções atribuídas ao estudante. Reflexões autorais, produções próprias e certificados não são simulados nesta entrega: serão incrementos posteriores com regras canônicas de autoria, revisão, emissão, revogação e auditoria.

## Banco e rollback

Não há migration. O rollback remove a página, a rota e os três pontos de navegação, sem alterar dados existentes.

## Critérios de aceite

- somente evidências oficiais dos domínios existentes são apresentadas;
- atividades não concluídas não aparecem como evidência concluída;
- falha em uma fonte não bloqueia as demais seções;
- nenhum ranking ou comparação entre estudantes é exibido;
- a área é acessível pelo produto Credentials e pela navegação do estudante.
