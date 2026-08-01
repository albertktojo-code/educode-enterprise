# Sprint 13.2 — Implantação, Recuperação e Continuidade Operacional

A Sprint 13.2 transforma os recursos de segurança e observabilidade das versões anteriores em um processo controlado de release.

## Entregas

- releases planejadas e versionadas;
- artefatos imutáveis com SHA-256 e digest de imagem;
- checklist de implantação por etapas;
- aprovações técnica, segurança, negócio e produção;
- validação offline das migrations;
- bloqueio de revision IDs acima de 32 caracteres;
- identificação de operações SQL destrutivas;
- backup obrigatório e vínculo com release;
- restauração seletiva com prévia de impacto;
- RPO e RTO por serviço;
- janelas de manutenção e modo somente leitura;
- drenagem e retomada de workers;
- inventário de segredos sem exposição de conteúdo;
- registro de rotação de segredos;
- Docker Compose separado para homologação e produção;
- Nginx HTTPS e proxy reverso;
- CI/CD de release, SBOM e bloqueio de vulnerabilidades críticas.

## Migration

`0025_ops_observability -> 0026_release_recovery`

## Regra operacional

Nenhuma implantação sem validação. Nenhuma migration sem backup. Nenhuma release sem rastreabilidade. Nenhum backup sem teste de restauração.
