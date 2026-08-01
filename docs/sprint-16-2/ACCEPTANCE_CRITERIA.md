# Criterios de aceitacao - Sprint 16.2

1. Uma pagina da Sprint 16.1 pode receber um documento de layout livre.
2. Camadas podem ser criadas, movidas, redimensionadas, rotacionadas e ordenadas.
3. Camadas bloqueadas nao podem ser alteradas ou excluidas.
4. O sistema impede z-index duplicado depois da reorganizacao.
5. O usuario pode criar e remover guias.
6. A interface mostra sangria, area de corte e area segura.
7. O historico permite solicitar desfazer e refazer.
8. O pre-flight identifica pagina vazia, baixa resolucao, texto pequeno, ausencia de texto alternativo e elementos fora da area segura.
9. Erros de pre-flight impedem a exportacao.
10. Presets de PDF, PNG e leitura web ficam disponiveis.
11. O instalador exige a Sprint 16.1 e usa revision Alembic com menos de 32 caracteres.
12. A instalacao pode ser reaplicada sem duplicar imports, rotas ou migrations.
13. O rollback restaura a Sprint 16.1.
14. O backend deve ficar `healthy` ao final da instalacao Docker.
