# Integração das rotas da Sprint 14.1

Os componentes foram copiados para `src/features/adaptiveEvolution`.

## Aplicação baseada em RouteObject/useRoutes

```tsx
import { adaptiveEvolutionRoutes } from './features/adaptiveEvolution';

const routes = [
  ...rotasExistentes,
  ...adaptiveEvolutionRoutes,
];
```

## Aplicação com createBrowserRouter

```tsx
import { adaptiveEvolutionRoutes } from './features/adaptiveEvolution';

const router = createBrowserRouter([
  ...rotasExistentes,
  ...adaptiveEvolutionRoutes,
]);
```

Adicione ao menu docente o endereço `/teacher/adaptive-evolution`.
