# Integracao frontend da Sprint 16.2

O modulo esta em `src/features/comicLayoutStudio`.

```tsx
import { comicLayoutStudioRoutes } from './features/comicLayoutStudio';
const routes = [...rotasExistentes, ...comicLayoutStudioRoutes];
```

Rotas: `/teacher/comic-studio/layout/:projectId/:pageId` e `/teacher/my-comics/:projectId/layout/:pageId`.
