# Integracao frontend da Sprint 16.3

O modulo esta em `src/features/comicVisualLibrary`.

```tsx
import { comicVisualLibraryRoutes } from './features/comicVisualLibrary';
const routes = [...rotasExistentes, ...comicVisualLibraryRoutes];
```

Rotas: `/teacher/comic-studio/visual-library/:projectId`, `/teacher/my-comics/:projectId/visual-library` e `/admin/comic-visual-library`.
