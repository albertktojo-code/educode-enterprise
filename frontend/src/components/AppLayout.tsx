import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  NavLink,
  Outlet,
  useLocation,
} from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { useInterfacePreferences } from "../features/uiPreferences/useInterfacePreferences";
import type { SidebarMode } from "../features/uiPreferences/types";

const roleLabels = {
  owner: "Proprietário",
  admin: "Administrador",
  teacher: "Professor",
  member: "Membro",
} as const;

interface NavItem {
  to: string;
  label: string;
  icon: string;
  end?: boolean;
  manageOnly?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const teacherGroups: NavGroup[] = [
  {
    label: "Área do professor",
    items: [
      { to: "/produtos", label: "Produtos EduCode", icon: "◈" },
      { to: "/estudio-professor", label: "Criar material", icon: "✦" },
      { to: "/publicacoes", label: "Publicar e acompanhar", icon: "◉" },
      { to: "/avaliacoes", label: "Avaliações integradas", icon: "✓" },
      { to: "/ia", label: "Assistência por IA", icon: "⚡" },
      { to: "/ia/avancado", label: "IA avançada", icon: "◆" },
      { to: "/tarefas", label: "Tarefas e processamentos", icon: "◷" },
      { to: "/notificacoes", label: "Notificações", icon: "●" },
      { to: "/analytics", label: "Evolução dos alunos", icon: "↗" },
      { to: "/credentials/certificados", label: "Certificados", icon: "◆" },
      { to: "/adaptativo", label: "Aprendizagem adaptativa", icon: "∞" },
      { to: "/estatistica", label: "Laboratório estatístico", icon: "▥" },
      { to: "/estatistica/avancado", label: "Pesquisa avançada", icon: "⌕" },
      { to: "/hqs", label: "Minhas HQs", icon: "▤" },
      { to: "/anime-studio", label: "Estúdio Anime", icon: "▶" },
      { to: "/comic-reader", label: "Leitor e apresentações", icon: "▶" },
      {
        to: "/teacher/comic-reader-analytics",
        label: "Analytics de HQs",
        icon: "▧",
      },
      {
        to: "/teacher/interventions",
        label: "Intervenções com HQs",
        icon: "✚",
      },
      {
        to: "/teacher/intervention-effectiveness",
        label: "Eficácia das intervenções",
        icon: "◎",
      },
      {
        to: "/admin/institutional-governance",
        label: "Governança institucional",
        icon: "⚖",
      },
      { to: "/turmas", label: "Minhas turmas", icon: "♟" },
      {
        to: "/sequencias-didaticas",
        label: "Sequências didáticas",
        icon: "≣",
      },
      {
        to: "/biblioteca-criativa",
        label: "Biblioteca criativa",
        icon: "▣",
      },
      {
        to: "/recursos-avancados",
        label: "Recursos avançados",
        icon: "⬡",
      },
    ],
  },
  {
    label: "Planejamento",
    items: [
      { to: "/", label: "Visão geral", icon: "⌂", end: true },
      { to: "/projetos", label: "Projetos", icon: "◇" },
      { to: "/disciplinas", label: "Disciplinas", icon: "◫" },
      { to: "/documentos", label: "Fontes e documentos", icon: "▱" },
      {
        to: "/unidades-pedagogicas",
        label: "Unidades pedagógicas",
        icon: "▦",
      },
      {
        to: "/estudio-pedagogico",
        label: "Planejamento avançado",
        icon: "✎",
      },
    ],
  },
  {
    label: "Área técnica",
    items: [
      { to: "/indexacao", label: "Indexação pedagógica", icon: "⌗" },
      { to: "/laboratorio-rag", label: "Laboratório RAG", icon: "⬢" },
      { to: "/contextos-rag", label: "Contextos RAG", icon: "◈" },
      { to: "/ia-mock", label: "Diagnóstico IA mock", icon: "⚙" },
      {
        to: "/admin/biblioteca-elementos",
        label: "Biblioteca institucional",
        icon: "▤",
        manageOnly: true,
      },
      {
        to: "/admin/inteligencia-artificial",
        label: "Administração da IA",
        icon: "✦",
        manageOnly: true,
      },
      {
        to: "/admin/operacao",
        label: "Operação e filas",
        icon: "⇄",
        manageOnly: true,
      },
      {
        to: "/admin/observabilidade",
        label: "Observabilidade e SLOs",
        icon: "◔",
        manageOnly: true,
      },
      {
        to: "/admin/plataforma",
        label: "Homologação e backups",
        icon: "☁",
        manageOnly: true,
      },
      {
        to: "/admin/releases",
        label: "Releases e continuidade",
        icon: "↺",
        manageOnly: true,
      },
      {
        to: "/admin/infraestrutura",
        label: "Infraestrutura e DR",
        icon: "▰",
        manageOnly: true,
      },
      {
        to: "/admin/privacidade",
        label: "Privacidade e retenção",
        icon: "◐",
        manageOnly: true,
      },
      {
        to: "/admin/auditoria",
        label: "Auditoria e integridade",
        icon: "✓",
        manageOnly: true,
      },
      { to: "/usuarios", label: "Usuários", icon: "♙", manageOnly: true },
      {
        to: "/organizacao",
        label: "Organização",
        icon: "▦",
        manageOnly: true,
      },
    ],
  },
];

const studentGroups: NavGroup[] = [
  {
    label: "Área do estudante",
    items: [
      {
        to: "/produtos",
        label: "Produtos EduCode",
        icon: "◈",
      },
      {
        to: "/aluno",
        label: "Início",
        icon: "⌂",
        end: true,
      },
      {
        to: "/aluno/atividades",
        label: "Minhas atividades",
        icon: "✓",
      },
      {
        to: "/aluno/progresso",
        label: "Meu progresso",
        icon: "↗",
      },
      {
        to: "/aluno/notificacoes",
        label: "Minhas notificações",
        icon: "●",
      },
      {
        to: "/aluno/portfolio",
        label: "Meu portfólio",
        icon: "◆",
      },
      {
        to: "/aluno/minha-trilha",
        label: "Minha trilha",
        icon: "⌁",
      },
      {
        to: "/student/interventions",
        label: "Meu plano de apoio",
        icon: "✚",
      },
      {
        to: "/student/assessments",
        label: "Avaliações interativas",
        icon: "▣",
      },
      {
        to: "/comic-reader",
        label: "HQs interativas",
        icon: "▤",
      },
      {
        to: "/anime-library",
        label: "Vídeos da turma",
        icon: "▶",
      },
    ],
  },
];

const accountItems: NavItem[] = [
  { to: "/perfil", label: "Meu perfil", icon: "●" },
  {
    to: "/account/security",
    label: "Segurança da conta",
    icon: "◆",
  },
];

function nextCompactMode(mode: SidebarMode): SidebarMode {
  return mode === "expanded" ? "compact" : "expanded";
}

function matchesRoute(pathname: string, item: NavItem): boolean {
  if (item.end || item.to === "/") {
    return pathname === item.to;
  }
  return (
    pathname === item.to || pathname.startsWith(`${item.to}/`)
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const membership = user?.memberships[0];
  const canManage = ["owner", "admin"].includes(
    membership?.role ?? "",
  );
  const isStudent = membership?.role === "member";
  const { preferences, update, setMode } =
    useInterfacePreferences();

  const [focusMode, setFocusMode] = useState(false);
  const [autoOpen, setAutoOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [resizing, setResizing] = useState(false);
  const resizeOrigin = useRef({
    x: 0,
    width: preferences.sidebarWidth,
  });

  const editorRoute = location.pathname.includes(
    "/teacher/comic-studio/editor",
  );

  const effectiveMode: SidebarMode = focusMode
    ? "hidden"
    : preferences.sidebarMode;
  const visualMode =
    effectiveMode === "auto" && autoOpen
      ? "expanded"
      : effectiveMode === "auto"
        ? "compact"
        : effectiveMode;

  const groups = useMemo(() => {
    const source = isStudent ? studentGroups : teacherGroups;
    return source.map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.manageOnly || canManage,
      ),
    }));
  }, [canManage, isStudent]);

  const navigationGroups = useMemo(
    () => [...groups, { label: "Conta", items: accountItems }],
    [groups],
  );
  const activeGroupLabel = useMemo(
    () =>
      navigationGroups.find((group) =>
        group.items.some((item) =>
          matchesRoute(location.pathname, item),
        ),
      )?.label ?? null,
    [location.pathname, navigationGroups],
  );
  const [expandedGroup, setExpandedGroup] = useState<string | null>(
    activeGroupLabel ?? navigationGroups[0]?.label ?? null,
  );

  useEffect(() => {
    setExpandedGroup(
      activeGroupLabel ?? navigationGroups[0]?.label ?? null,
    );
  }, [activeGroupLabel, navigationGroups]);

  useEffect(() => {
    const onFocus = (event: Event) => {
      const custom = event as CustomEvent<{ enabled: boolean }>;
      setFocusMode(Boolean(custom.detail?.enabled));
    };
    window.addEventListener(
      "educode:set-focus-mode",
      onFocus as EventListener,
    );
    return () =>
      window.removeEventListener(
        "educode:set-focus-mode",
        onFocus as EventListener,
      );
  }, []);

  useEffect(() => {
    if (
      editorRoute &&
      preferences.editorFocusDefault &&
      !focusMode
    ) {
      setFocusMode(true);
    }
  }, [
    editorRoute,
    focusMode,
    preferences.editorFocusDefault,
  ]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        if (focusMode) {
          setFocusMode(false);
          window.dispatchEvent(
            new CustomEvent("educode:focus-mode-changed", {
              detail: { enabled: false },
            }),
          );
        }
        return;
      }
      if (
        event.ctrlKey &&
        !event.shiftKey &&
        event.key.toLowerCase() === "b"
      ) {
        event.preventDefault();
        setMode(nextCompactMode(preferences.sidebarMode));
      }
      if (
        event.ctrlKey &&
        event.shiftKey &&
        event.key.toLowerCase() === "f"
      ) {
        event.preventDefault();
        const enabled = !focusMode;
        setFocusMode(enabled);
        window.dispatchEvent(
          new CustomEvent("educode:focus-mode-changed", {
            detail: { enabled },
          }),
        );
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [focusMode, preferences.sidebarMode, setMode]);

  useEffect(() => {
    if (!resizing) return undefined;
    const onMove = (event: PointerEvent) => {
      const width = Math.max(
        210,
        Math.min(
          340,
          resizeOrigin.current.width +
            event.clientX -
            resizeOrigin.current.x,
        ),
      );
      update({
        sidebarMode: "expanded",
        sidebarWidth: width,
      });
    };
    const onUp = () => setResizing(false);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [resizing, update]);

  function startResize(
    event: ReactPointerEvent<HTMLButtonElement>,
  ): void {
    if (visualMode !== "expanded") return;
    resizeOrigin.current = {
      x: event.clientX,
      width: preferences.sidebarWidth,
    };
    setResizing(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function closeMobile(): void {
    setMobileOpen(false);
  }

  const shellStyle = {
    "--sidebar-width":
      visualMode === "expanded"
        ? `${preferences.sidebarWidth}px`
        : visualMode === "compact"
          ? "64px"
          : "0px",
  } as CSSProperties;

  return (
    <div
      className={[
        "app-shell",
        `sidebar-mode-${visualMode}`,
        focusMode ? "is-focus-mode" : "",
        resizing ? "is-resizing-sidebar" : "",
        mobileOpen ? "is-mobile-menu-open" : "",
        preferences.reduceMotion ? "reduce-motion" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={shellStyle}
    >
      <button
        type="button"
        className="mobile-menu-trigger"
        aria-label="Abrir menu principal"
        aria-expanded={mobileOpen}
        onClick={() => setMobileOpen(true)}
      >
        ☰
      </button>

      {visualMode === "hidden" ? (
        <button
          type="button"
          className="sidebar-floating-trigger"
          aria-label="Reabrir menu lateral"
          title="Reabrir menu lateral (Ctrl+B)"
          onClick={() => setMode("expanded")}
        >
          ☰
        </button>
      ) : null}

      <aside
        className="sidebar"
        aria-label="Menu lateral do EduCode"
        aria-hidden={visualMode === "hidden" && !mobileOpen}
        onMouseEnter={() => {
          if (effectiveMode === "auto") setAutoOpen(true);
        }}
        onMouseLeave={() => {
          if (effectiveMode === "auto") setAutoOpen(false);
        }}
      >
        <div className="sidebar-top">
          <div className="brand">
            <span className="brand-mark">EC</span>
            <div className="sidebar-label">
              <strong>EduCode</strong>
              <small>Enterprise 2.0</small>
            </div>
          </div>

          <div className="sidebar-mode-controls">
            <button
              type="button"
              className="sidebar-collapse-button"
              aria-label={
                visualMode === "expanded"
                  ? "Minimizar menu lateral"
                  : "Expandir menu lateral"
              }
              title={
                visualMode === "expanded"
                  ? "Minimizar menu (Ctrl+B)"
                  : "Expandir menu (Ctrl+B)"
              }
              onClick={() =>
                setMode(
                  visualMode === "expanded"
                    ? "compact"
                    : "expanded",
                )
              }
            >
              {visualMode === "expanded" ? "‹" : "›"}
              <span className="sidebar-label">
                {visualMode === "expanded"
                  ? "Minimizar"
                  : "Expandir"}
              </span>
            </button>

            {visualMode === "expanded" ? (
              <select
                aria-label="Comportamento do menu lateral"
                value={preferences.sidebarMode}
                onChange={(event) =>
                  setMode(event.target.value as SidebarMode)
                }
              >
                <option value="expanded">Expandido</option>
                <option value="compact">Compacto</option>
                <option value="hidden">Oculto</option>
                <option value="auto">Automático</option>
              </select>
            ) : null}
          </div>
        </div>

        <nav aria-label="Navegação principal">
          {navigationGroups.map((group) => {
            const showAllGroups =
              visualMode !== "expanded" && !mobileOpen;
            const isGroupExpanded =
              showAllGroups || expandedGroup === group.label;
            const groupId = `sidebar-group-${group.label
              .normalize("NFD")
              .replace(/[\u0300-\u036f]/g, "")
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")}`;

            return (
              <div className="sidebar-nav-group" key={group.label}>
                <button
                  type="button"
                  className="sidebar-group-toggle sidebar-label"
                  aria-expanded={isGroupExpanded}
                  aria-controls={groupId}
                  onClick={() =>
                    setExpandedGroup((current) =>
                      current === group.label ? null : group.label,
                    )
                  }
                >
                  <span>{group.label}</span>
                  <span
                    className="sidebar-group-chevron"
                    aria-hidden="true"
                  >
                    ⌄
                  </span>
                </button>
                <div
                  id={groupId}
                  className="sidebar-nav-items"
                  hidden={!isGroupExpanded}
                >
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      title={
                        visualMode !== "expanded"
                          ? item.label
                          : undefined
                      }
                      aria-label={item.label}
                      onClick={closeMobile}
                    >
                      <span
                        className="sidebar-nav-icon"
                        aria-hidden="true"
                      >
                        {item.icon}
                      </span>
                      <span className="sidebar-label">
                        {item.label}
                      </span>
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            {(user?.full_name ?? "U").slice(0, 1).toUpperCase()}
          </div>
          <div className="sidebar-user-copy sidebar-label">
            <strong>{user?.full_name}</strong>
            <span>{membership?.organization.name}</span>
            {membership ? (
              <span className="role-chip">
                {roleLabels[membership.role]}
              </span>
            ) : null}
          </div>
          <button
            onClick={() => void logout()}
            type="button"
            title="Sair"
            aria-label="Sair do EduCode"
          >
            <span aria-hidden="true">↪</span>
            <span className="sidebar-label">Sair</span>
          </button>
        </div>

        <button
          type="button"
          className="sidebar-resize-handle"
          aria-label="Redimensionar menu lateral"
          title="Arraste para ajustar a largura"
          onPointerDown={startResize}
        />
      </aside>

      <button
        type="button"
        className="sidebar-mobile-overlay"
        aria-label="Fechar menu"
        onClick={closeMobile}
      />

      <main className="content">
        {focusMode ? (
          <button
            type="button"
            className="exit-focus-button"
            onClick={() => {
              setFocusMode(false);
              window.dispatchEvent(
                new CustomEvent("educode:focus-mode-changed", {
                  detail: { enabled: false },
                }),
              );
            }}
          >
            Sair do modo foco · Esc
          </button>
        ) : null}
        <div className="route-stage" key={location.pathname}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
