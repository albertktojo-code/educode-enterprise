# Sprint 18.10 — Produções autorais no portfólio

## Incremento

O EduCode Credentials passa a apresentar projetos, HQs e animes cuja autoria já está
registrada nos domínios canônicos do EduCode Learn e Studio. A consulta restringe cada
fonte por organização e usuário autenticado e não copia arquivos, releases ou metadados.

## Entrega

- endpoint privado `/student/portfolio/productions`;
- projetos vinculados por `Project.owner_id`;
- HQs e animes vinculados por `created_by_user_id`;
- galeria autoral com tipo, estado, descrição e acesso à produção original;
- loading, falha parcial e estado vazio integrados ao portfólio existente.

## Banco e rollback

Não há migration. O rollback remove o endpoint, o schema de leitura e a seção visual.
Nenhuma produção ou evidência existente é alterada.

## Limites

Esta sprint reconhece autoria técnica já registrada. Compartilhamento público, revisão
docente e certificação permanecem fora do escopo e não são inferidos pelo portfólio.
