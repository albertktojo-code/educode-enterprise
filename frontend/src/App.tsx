import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'
import { AdminAssetLibraryPage } from './pages/AdminAssetLibraryPage'
import { AdaptiveDashboardPage } from './pages/AdaptiveDashboardPage'
import { AdaptivePathsPage } from './pages/AdaptivePathsPage'
import { AdaptiveRecommendationsPage } from './pages/AdaptiveRecommendationsPage'
import { AdaptiveStudentPage } from './pages/AdaptiveStudentPage'
import { StudentLearningPathPage } from './pages/StudentLearningPathPage'
import { StudentNotificationsPage } from './pages/StudentNotificationsPage'
import { AdminAIPage } from './pages/AdminAIPage'
import { AIFabricPage } from './pages/AIFabricPage'
import { AIAdvancedPage } from './pages/AIAdvancedPage'
import { AdminOperationsPage } from './pages/AdminOperationsPage'
import { AdminObservabilityPage } from './pages/AdminObservabilityPage'
import { AdminAuditPage } from './pages/AdminAuditPage'
import { AdminPlatformPage } from './pages/AdminPlatformPage'
import { AdminPrivacyPage } from './pages/AdminPrivacyPage'
import { AdminReleaseRecoveryPage } from './pages/AdminReleaseRecoveryPage'
import { AdminInfrastructurePage } from './pages/AdminInfrastructurePage'
import { JobDetailPage } from './pages/JobDetailPage'
import { JobsPage } from './pages/JobsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { AssessmentsHubPage } from './pages/AssessmentsHubPage'
import { AnalyticsAlertsPage } from './pages/AnalyticsAlertsPage'
import { AnalyticsDashboardPage } from './pages/AnalyticsDashboardPage'
import { AssignmentAnalyticsPage } from './pages/AssignmentAnalyticsPage'
import { ClassroomAnalyticsPage } from './pages/ClassroomAnalyticsPage'
import { StudentAnalyticsPage } from './pages/StudentAnalyticsPage'
import { StatisticsLabPage } from './pages/StatisticsLabPage'
import { StatisticsAdvancedPage } from './pages/StatisticsAdvancedPage'
import { StudentProgressPage } from './pages/StudentProgressPage'
import { StudentPortfolioPage } from './pages/StudentPortfolioPage'
import { AssignmentDetailPage } from './pages/AssignmentDetailPage'
import { AssignmentsPage } from './pages/AssignmentsPage'
import { ClassroomsPage } from './pages/ClassroomsPage'
import { CreativeLibraryPage } from './pages/CreativeLibraryPage'
import { CreativeProjectSettingsPage } from './pages/CreativeProjectSettingsPage'
import { ComicEditorPage } from './pages/ComicEditorPage'
import { ComicsPage } from './pages/ComicsPage'
import { ComicPreviewPage } from './pages/ComicPreviewPage'
import { DashboardPage } from './pages/DashboardPage'
import { DocumentStructurePage } from './pages/DocumentStructurePage'
import { DocumentsPage } from './pages/DocumentsPage'
import { LearningUnitsPage } from './pages/LearningUnitsPage'
import { IndexingPage } from './pages/IndexingPage'
import { RagLabPage } from './pages/RagLabPage'
import { RagContextsPage } from './pages/RagContextsPage'
import { LoginPage } from './pages/LoginPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { SecuritySessionsPage } from './pages/SecuritySessionsPage'
import { SchoolSecretariatPage } from './pages/SchoolSecretariatPage'
import { SchoolSecretariatLayout } from './pages/SchoolSecretariatLayout'
import { SchoolAdmissionsPage } from './pages/SchoolAdmissionsPage'
import { SchoolDocumentsPage } from './pages/SchoolDocumentsPage'
import { SchoolCapacityPage } from './pages/SchoolCapacityPage'
import { SchoolContractsPage } from './pages/SchoolContractsPage'
import { SchoolMovementsPage } from './pages/SchoolMovementsPage'
import { MockAiPage } from './pages/MockAiPage'
import { OrganizationPage } from './pages/OrganizationPage'
import { PedagogicalStudioPage } from './pages/PedagogicalStudioPage'
import { ProfilePage } from './pages/ProfilePage'
import { ProductDirectoryPage } from './pages/ProductDirectoryPage'
import { PublicCertificatePage } from './pages/PublicCertificatePage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { StudentAssignmentPage } from './pages/StudentAssignmentPage'
import { StudentAssignmentsPage } from './pages/StudentAssignmentsPage'
import { StudentPortalPage } from './pages/StudentPortalPage'
import { StoryboardPage } from './pages/StoryboardPage'
import { SubjectsPage } from './pages/SubjectsPage'
import { TeachingSequencesPage } from './pages/TeachingSequencesPage'
import { TeacherCanvasPage } from './pages/TeacherCanvasPage'
import { TeacherStudioPage } from './pages/TeacherStudioPage'
import { TeacherCertificatesPage } from './pages/TeacherCertificatesPage'
import { UsersPage } from './pages/UsersPage'
import { AdvancedResourcesPage } from './pages/AdvancedResourcesPage'
import { consolidatedFeatureRoutes } from './features/consolidation/routeRegistry'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/credentials/verificar" element={<PublicCertificatePage />} />
          <Route path="/credentials/verificar/:verificationCode" element={<PublicCertificatePage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="produtos" element={<ProductDirectoryPage />} />
              <Route path="projetos" element={<ProjectsPage />} />
              <Route
                path="projetos/:projectId"
                element={<ProjectDetailPage />}
              />
              <Route path="turmas" element={<ClassroomsPage />} />
              <Route path="publicacoes" element={<AssignmentsPage />} />
              <Route path="avaliacoes" element={<AssessmentsHubPage />} />
              <Route path="admin/biblioteca-elementos" element={<AdminAssetLibraryPage />} />
              <Route path="admin/inteligencia-artificial" element={<AdminAIPage />} />
              <Route path="ia" element={<AIFabricPage />} />
              <Route path="ia/avancado" element={<AIAdvancedPage />} />
              <Route path="tarefas" element={<JobsPage />} />
              <Route path="tarefas/:jobId" element={<JobDetailPage />} />
              <Route path="notificacoes" element={<NotificationsPage />} />
              <Route path="secretaria" element={<SchoolSecretariatLayout />}>
                <Route index element={<SchoolSecretariatPage />} />
                <Route path="matriculas" element={<SchoolAdmissionsPage />} />
                <Route path="documentos" element={<SchoolDocumentsPage />} />
                <Route path="contratos" element={<SchoolContractsPage />} />
                <Route path="movimentacoes" element={<SchoolMovementsPage />} />
                <Route path="turmas-vagas" element={<SchoolCapacityPage />} />
              </Route>
              <Route path="admin/operacao" element={<AdminOperationsPage />} />
              <Route path="admin/observabilidade" element={<AdminObservabilityPage />} />
              <Route path="admin/plataforma" element={<AdminPlatformPage />} />
              <Route path="admin/privacidade" element={<AdminPrivacyPage />} />
              <Route path="admin/auditoria" element={<AdminAuditPage />} />
              <Route path="admin/releases" element={<AdminReleaseRecoveryPage />} />
              <Route path="admin/infraestrutura" element={<AdminInfrastructurePage />} />
              <Route path="analytics" element={<AnalyticsDashboardPage />} />
              <Route path="adaptativo" element={<AdaptiveDashboardPage />} />
              <Route path="adaptativo/recomendacoes" element={<AdaptiveRecommendationsPage />} />
              <Route path="adaptativo/trilhas" element={<AdaptivePathsPage />} />
              <Route path="adaptativo/estudantes/:studentId" element={<AdaptiveStudentPage />} />
              <Route path="estatistica" element={<StatisticsLabPage />} />
              <Route path="estatistica/avancado" element={<StatisticsAdvancedPage />} />
              <Route path="analytics/turmas/:classroomId" element={<ClassroomAnalyticsPage />} />
              <Route path="analytics/estudantes/:studentId" element={<StudentAnalyticsPage />} />
              <Route path="analytics/atividades/:assignmentId" element={<AssignmentAnalyticsPage />} />
              <Route path="analytics/alertas" element={<AnalyticsAlertsPage />} />
              <Route path="publicacoes/:assignmentId" element={<AssignmentDetailPage />} />
              <Route path="aluno" element={<StudentPortalPage />} />
              <Route path="aluno/atividades" element={<StudentAssignmentsPage />} />
              <Route path="aluno/progresso" element={<StudentProgressPage />} />
              <Route path="aluno/portfolio" element={<StudentPortfolioPage />} />
              <Route path="aluno/notificacoes" element={<StudentNotificationsPage />} />
              <Route path="credentials/certificados" element={<TeacherCertificatesPage />} />
              <Route path="aluno/minha-trilha" element={<StudentLearningPathPage />} />
              <Route path="aluno/atividades/:assignmentId" element={<StudentAssignmentPage />} />
              <Route path="disciplinas" element={<SubjectsPage />} />
              <Route path="documentos" element={<DocumentsPage />} />
              <Route path="unidades-pedagogicas" element={<LearningUnitsPage />} />
              <Route path="estudio-professor" element={<TeacherStudioPage />} />
              <Route path="canvas/:comicId" element={<TeacherCanvasPage />} />
              <Route path="estudio-pedagogico" element={<PedagogicalStudioPage />} />
              <Route
                path="estudio-pedagogico/:generationProjectId/criativo"
                element={<CreativeProjectSettingsPage />}
              />
              <Route path="biblioteca-criativa" element={<CreativeLibraryPage />} />
              <Route path="sequencias-didaticas" element={<TeachingSequencesPage />} />
              <Route path="indexacao" element={<IndexingPage />} />
              <Route path="laboratorio-rag" element={<RagLabPage />} />
              <Route path="contextos-rag" element={<RagContextsPage />} />
              <Route path="hqs" element={<ComicsPage />} />
              <Route path="hqs/:comicId" element={<ComicEditorPage />} />
              <Route path="hqs/:comicId/preview" element={<ComicPreviewPage />} />
              <Route path="storyboards/:comicId" element={<StoryboardPage />} />
              <Route
                path="documentos/:documentId"
                element={<DocumentStructurePage />}
              />
              <Route path="ia-mock" element={<MockAiPage />} />
              <Route path="usuarios" element={<UsersPage />} />
              <Route path="organizacao" element={<OrganizationPage />} />
              <Route path="perfil" element={<ProfilePage />} />
              <Route path="account/security" element={<SecuritySessionsPage />} />
              <Route path="conta/seguranca" element={<SecuritySessionsPage />} />
              <Route path="recursos-avancados" element={<AdvancedResourcesPage />} />
              {consolidatedFeatureRoutes.map((route) => (
                <Route key={route.path} path={route.path} element={route.element} />
              ))}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
