# Sprint 18.13 — Verificação pública de certificados

## Incremento entregue

- Consulta pública por código em `/credentials/verificar/:verificationCode`.
- Estado explícito para certificados válidos, revogados e não encontrados.
- Documento visual responsivo com estudante, instituição, emissor e evidências.
- QR Code SVG gerado pela própria API, sem serviço externo.
- Impressão e exportação em PDF usando o diálogo nativo do navegador.
- Atalhos de verificação nas áreas do professor e do estudante.

## Privacidade e segurança

A resposta pública não contém e-mail, identificadores internos, respostas de atividades ou organização completa do portfólio. O código usa 24 caracteres hexadecimais aleatórios e é normalizado na consulta. A origem recebida pelo gerador de QR aceita somente HTTP/HTTPS sem credenciais embutidas.

## Persistência

A sprint reutiliza `student_certificates` e `student_portfolio_entries`. Nenhuma migration é criada ou aplicada; o head permanece `0058_student_certificates`.

## Critérios de aceitação

- Um código existente exibe o documento e as evidências vinculadas.
- Um certificado revogado exibe data e motivo da revogação.
- Um código inexistente não revela dados adicionais.
- O QR aponta para a rota pública da origem atual.
- A impressão remove navegação, busca e botões da folha.
