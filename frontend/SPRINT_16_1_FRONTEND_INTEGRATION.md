# Integracao frontend da Sprint 16.1

O modulo esta em `src/features/comicPageEditor`.

```tsx
import { comicPageEditorRoutes } from './features/comicPageEditor';
const routes = [...rotasExistentes, ...comicPageEditorRoutes];
```

Rotas: `/teacher/comic-studio`, `/teacher/comic-studio/editor/:projectId`, `/teacher/comic-studio/generation/:jobId` e `/teacher/my-comics/:projectId/pages`.
