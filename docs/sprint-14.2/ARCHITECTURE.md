# Arquitetura — Sprint 14.2

## Módulo backend

`app.adaptive_insights`

- `services/recommendations.py`: recomendação por histórico;
- `services/effectiveness.py`: métricas descritivas;
- `services/dashboard.py`: consolidação institucional;
- `services/simulation.py`: execução sem efeitos;
- `services/experiments.py`: atribuição e comparação;
- `models.py`: persistência organizacional;
- `router.py`: API e RBAC;
- `compat.py`: integração com banco e autenticação existentes.

## Persistência

- `intervention_outcomes`;
- `material_effectiveness_metrics`;
- `adaptive_model_versions`;
- `recommendation_simulations`;
- `controlled_experiments`;
- `experiment_assignments`;
- `experiment_observations`.

## Fluxo

```text
Evidências e intervenções
        ↓
Métricas descritivas
        ↓
Modelo adaptativo versionado
        ↓
Simulação isolada
        ↓
Revisão institucional
        ↓
Experimento controlado autorizado
        ↓
Comparação descritiva
```

## Princípio

O sistema mede, simula e compara. Ele não transforma automaticamente uma correlação em decisão pedagógica definitiva.
