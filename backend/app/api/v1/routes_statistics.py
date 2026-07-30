from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from html import escape
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.delivery import AttemptStatus, StudentAttempt
from app.models.statistics import (
    AnalysisStatus, DatasetStatus, StatisticalAnalysis, StatisticalChart,
    StatisticalDataset, StatisticalReport, StatisticalStudy, StudyStatus,
)
from app.schemas.statistics import (
    AnalysisCreate, AnalysisRead, ChartCreate, ChartRead, DatasetCreate, DatasetRead,
    ReportCreate, ReportRead, StudyCreate, StudyRead, TestRecommendationRead,
    TestRecommendationRequest,
)
from app.services.statistics_advanced import configuration_checksum, result_signature
from app.services.statistics_engine import execute, recommend

router = APIRouter(prefix="/statistics", tags=["Laboratório Estatístico"])

def _render_chart_svg(chart: StatisticalChart) -> str:
    cfg=chart.configuration; xk=cfg.get("x_key") or "group"; yk=cfg.get("y_key") or "score"; rows=chart.data_snapshot[:20]
    vals=[]
    for row in rows:
        try: vals.append((str(row.get(xk,"")),float(row.get(yk,0))))
        except (TypeError,ValueError): continue
    maxv=max((v for _,v in vals),default=1); width=720; height=420; bars=[]
    for index,(label,value) in enumerate(vals):
        bar_width=max(12,(width-100)//max(1,len(vals))-8); x=60+index*(bar_width+8); bar_height=300*value/maxv if maxv else 0; y=350-bar_height
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="4"/><text x="{x+bar_width/2}" y="370" text-anchor="middle" font-size="11">{escape(label[:10])}</text><text x="{x+bar_width/2}" y="{y-6:.1f}" text-anchor="middle" font-size="11">{value:.1f}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="{escape(chart.alt_text)}"><style>rect{{fill:#4f46e5}} text{{font-family:Arial;fill:#111827}}</style><text x="30" y="28" font-size="20" font-weight="bold">{escape(chart.title)}</text><line x1="50" y1="350" x2="700" y2="350" stroke="#111827"/>{"".join(bars)}</svg>'

ROLES=(OrganizationRole.OWNER,OrganizationRole.ADMIN,OrganizationRole.TEACHER)

def org_id(m: Membership)->UUID: return m.organization_id

@router.post('/recommend-test', response_model=TestRecommendationRead)
async def recommend_test(data: TestRecommendationRequest, membership: Membership=Depends(require_roles(*ROLES))) -> dict[str,Any]:
    _=membership
    return recommend(data.goal,data.same_participants,data.variable_type,data.group_count)

@router.post('/studies',response_model=StudyRead,status_code=201)
async def create_study(data:StudyCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)),user:User=Depends(get_current_user))->StatisticalStudy:
    study=StatisticalStudy(organization_id=org_id(membership),created_by_user_id=user.id,**data.model_dump())
    session.add(study); await session.commit(); await session.refresh(study); return study

@router.get('/studies',response_model=list[StudyRead])
async def list_studies(session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->list[StatisticalStudy]:
    return list((await session.scalars(select(StatisticalStudy).where(StatisticalStudy.organization_id==org_id(membership)).order_by(StatisticalStudy.created_at.desc()))).all())

@router.get('/studies/{study_id}',response_model=StudyRead)
async def get_study(study_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->StatisticalStudy:
    obj=await session.scalar(select(StatisticalStudy).where(StatisticalStudy.id==study_id,StatisticalStudy.organization_id==org_id(membership)))
    if obj is None: raise HTTPException(404,'Estudo não encontrado')
    return obj

async def _attempt_rows(session:AsyncSession, organization_id:UUID, data:DatasetCreate)->list[dict[str,Any]]:
    stmt=select(StudentAttempt).where(StudentAttempt.organization_id==organization_id,StudentAttempt.status.in_([AttemptStatus.SUBMITTED,AttemptStatus.GRADED]))
    if data.assignment_ids: stmt=stmt.where(StudentAttempt.assignment_id.in_(data.assignment_ids))
    attempts=list((await session.scalars(stmt.order_by(StudentAttempt.student_id,StudentAttempt.assignment_id,StudentAttempt.attempt_number))).all())
    grouped:dict[tuple[UUID,UUID],list[StudentAttempt]]={}
    for a in attempts: grouped.setdefault((a.student_id,a.assignment_id),[]).append(a)
    chosen:list[StudentAttempt]=[]
    for values in grouped.values():
        if data.attempt_policy=='first': chosen.append(min(values,key=lambda x:x.attempt_number))
        elif data.attempt_policy=='latest': chosen.append(max(values,key=lambda x:x.attempt_number))
        elif data.attempt_policy=='best': chosen.append(max(values,key=lambda x:x.percentage or 0))
        else: chosen.extend(values)
    anon:dict[UUID,str]={}
    rows=[]
    for a in chosen:
        anon.setdefault(a.student_id,f'EST-{len(anon)+1:04d}')
        rows.append({'student_id':anon[a.student_id] if data.anonymized else str(a.student_id),'assignment_id':str(a.assignment_id),'attempt_number':a.attempt_number,'score':a.score,'percentage':a.percentage,'group':str(a.assignment_id),'submitted_at':a.submitted_at.isoformat() if a.submitted_at else None})
    return rows

@router.post('/studies/{study_id}/datasets',response_model=DatasetRead,status_code=201)
async def freeze_dataset(study_id:UUID,data:DatasetCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)),user:User=Depends(get_current_user))->StatisticalDataset:
    study=await session.scalar(select(StatisticalStudy).where(StatisticalStudy.id==study_id,StatisticalStudy.organization_id==org_id(membership)))
    if study is None: raise HTTPException(404,'Estudo não encontrado')
    rows=data.manual_rows or await _attempt_rows(session,org_id(membership),data)
    payload=json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str).encode()
    participant_count=len({str(r.get('student_id')) for r in rows if r.get('student_id') is not None})
    missing=sum(1 for r in rows for v in r.values() if v is None)
    dictionary=data.variable_dictionary or [{'name':k,'type':'numeric' if isinstance(v,(int,float)) else 'categorical','description':k} for k,v in (rows[0].items() if rows else [])]
    ds=StatisticalDataset(study_id=study_id,organization_id=org_id(membership),title=data.title,status=DatasetStatus.FROZEN,filters={'assignment_ids':[str(x) for x in data.assignment_ids],'classroom_ids':[str(x) for x in data.classroom_ids]},attempt_policy=data.attempt_policy,participant_count=participant_count,row_count=len(rows),dataset_checksum=hashlib.sha256(payload).hexdigest(),quality_summary={'missing_values':missing,'complete_rows':sum(1 for r in rows if all(v is not None for v in r.values())),'status':'good' if rows else 'empty'},variable_dictionary=dictionary,rows_snapshot=rows,anonymized=data.anonymized,created_by_user_id=user.id)
    session.add(ds); study.status=StudyStatus.ACTIVE; await session.commit(); await session.refresh(ds); return ds

@router.get('/studies/{study_id}/datasets',response_model=list[DatasetRead])
async def list_datasets(study_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->list[StatisticalDataset]:
    return list((await session.scalars(select(StatisticalDataset).where(StatisticalDataset.study_id==study_id,StatisticalDataset.organization_id==org_id(membership)).order_by(StatisticalDataset.created_at.desc()))).all())

@router.post('/studies/{study_id}/analyses',response_model=AnalysisRead,status_code=201)
async def run_analysis(study_id:UUID,data:AnalysisCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)),user:User=Depends(get_current_user))->StatisticalAnalysis:
    study=await session.scalar(select(StatisticalStudy).where(StatisticalStudy.id==study_id,StatisticalStudy.organization_id==org_id(membership)))
    ds=await session.scalar(select(StatisticalDataset).where(StatisticalDataset.id==data.dataset_id,StatisticalDataset.study_id==study_id,StatisticalDataset.organization_id==org_id(membership)))
    if study is None or ds is None: raise HTTPException(404,'Estudo ou dataset não encontrado')
    analysis=StatisticalAnalysis(study_id=study_id,dataset_id=ds.id,organization_id=org_id(membership),title=data.title,analysis_type=data.analysis_type,parameters=data.parameters,created_by_user_id=user.id,status=AnalysisStatus.PENDING,software_versions={'engine':'educode-statistics-1.1','scipy':'runtime','python':'3.12'},configuration_checksum=configuration_checksum(ds.dataset_checksum,data.analysis_type,data.parameters))
    session.add(analysis); await session.flush()
    try:
        result=execute(ds.rows_snapshot,data.analysis_type,data.parameters,study.significance_level)
        for key,val in result.items(): setattr(analysis,key,val)
        analysis.result_signature=result_signature(result)
        analysis.status=AnalysisStatus.COMPLETED; analysis.executed_at=datetime.now(UTC)
    except (ValueError,RuntimeError) as exc:
        analysis.status=AnalysisStatus.FAILED; analysis.limitations=[str(exc)]
        await session.commit(); raise HTTPException(422,str(exc)) from exc
    await session.commit(); await session.refresh(analysis); return analysis

@router.get('/studies/{study_id}/analyses',response_model=list[AnalysisRead])
async def list_analyses(study_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->list[StatisticalAnalysis]:
    return list((await session.scalars(select(StatisticalAnalysis).where(StatisticalAnalysis.study_id==study_id,StatisticalAnalysis.organization_id==org_id(membership)).order_by(StatisticalAnalysis.created_at.desc()))).all())

@router.get('/analyses/{analysis_id}',response_model=AnalysisRead)
async def get_analysis(analysis_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->StatisticalAnalysis:
    a=await session.scalar(select(StatisticalAnalysis).where(StatisticalAnalysis.id==analysis_id,StatisticalAnalysis.organization_id==org_id(membership)))
    if a is None: raise HTTPException(404,'Análise não encontrada')
    return a

@router.post('/analyses/{analysis_id}/charts',response_model=ChartRead,status_code=201)
async def create_chart(analysis_id:UUID,data:ChartCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->StatisticalChart:
    a=await session.scalar(select(StatisticalAnalysis).where(StatisticalAnalysis.id==analysis_id,StatisticalAnalysis.organization_id==org_id(membership)))
    if a is None: raise HTTPException(404,'Análise não encontrada')
    ds=await session.get(StatisticalDataset,a.dataset_id)
    rows=ds.rows_snapshot if ds else []
    chart=StatisticalChart(analysis_id=a.id,organization_id=org_id(membership),chart_type=data.chart_type,title=data.title,description=data.description,configuration={'x_key':data.x_key,'y_key':data.y_key,'group_key':data.group_key,'before_key':a.parameters.get('x_key','pre'),'after_key':a.parameters.get('y_key','post')},data_snapshot=rows,alt_text=f'{data.title}. Gráfico baseado em {len(rows)} registros do dataset congelado.',display_order=0,include_in_report=data.include_in_report)
    session.add(chart); await session.commit(); await session.refresh(chart); return chart

@router.get('/analyses/{analysis_id}/charts',response_model=list[ChartRead])
async def list_charts(analysis_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->list[StatisticalChart]:
    return list((await session.scalars(select(StatisticalChart).where(StatisticalChart.analysis_id==analysis_id,StatisticalChart.organization_id==org_id(membership)).order_by(StatisticalChart.display_order))).all())

@router.get('/charts/{chart_id}/svg')
async def chart_svg(chart_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->HTMLResponse:
    chart=await session.scalar(select(StatisticalChart).where(StatisticalChart.id==chart_id,StatisticalChart.organization_id==org_id(membership)))
    if chart is None: raise HTTPException(404,'Gráfico não encontrado')
    return HTMLResponse(_render_chart_svg(chart),media_type='image/svg+xml')

@router.post('/analyses/{analysis_id}/reports',response_model=ReportRead,status_code=201)
async def create_report(analysis_id:UUID,data:ReportCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)),user:User=Depends(get_current_user))->StatisticalReport:
    a=await session.scalar(select(StatisticalAnalysis).where(StatisticalAnalysis.id==analysis_id,StatisticalAnalysis.organization_id==org_id(membership)))
    if a is None: raise HTTPException(404,'Análise não encontrada')
    charts=list((await session.scalars(select(StatisticalChart).where(StatisticalChart.analysis_id==a.id,StatisticalChart.include_in_report.is_(True)))).all()) if data.include_charts else []
    sections=[{'type':'summary','title':'Resumo','content':a.interpretation_teacher},{'type':'technical','title':'Resultado estatístico','content':a.interpretation_researcher},{'type':'descriptive','title':'Estatística descritiva','content':a.descriptive_results}]
    if data.include_assumptions: sections.append({'type':'assumptions','title':'Pressupostos','content':a.assumptions})
    if data.include_limitations: sections.append({'type':'limitations','title':'Limitações','content':a.limitations})
    sections.extend({'type':'chart','title':c.title,'chart_id':str(c.id),'alt_text':c.alt_text} for c in charts)
    html=f'<h1>{escape(data.title)}</h1><p><strong>Rascunho para revisão.</strong></p><h2>Resumo pedagógico</h2><p>{escape(a.interpretation_teacher)}</p><h2>Resultado estatístico</h2><p>{escape(a.interpretation_researcher)}</p><pre>{escape(json.dumps(a.descriptive_results,ensure_ascii=False,indent=2))}</pre>'
    for c in charts: html+=f'<h2>{escape(c.title)}</h2><p>{escape(c.alt_text)}</p>{_render_chart_svg(c)}'
    report=StatisticalReport(study_id=a.study_id,analysis_id=a.id,organization_id=org_id(membership),report_type=data.report_type,title=data.title,content_html=html,sections=sections,created_by_user_id=user.id)
    session.add(report); await session.commit(); await session.refresh(report); return report

@router.get('/reports/{report_id}',response_model=ReportRead)
async def get_report(report_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->StatisticalReport:
    r=await session.scalar(select(StatisticalReport).where(StatisticalReport.id==report_id,StatisticalReport.organization_id==org_id(membership)))
    if r is None: raise HTTPException(404,'Relatório não encontrado')
    return r

@router.get('/reports/{report_id}/html')
async def report_html(report_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->HTMLResponse:
    r=await session.scalar(select(StatisticalReport).where(StatisticalReport.id==report_id,StatisticalReport.organization_id==org_id(membership)))
    if r is None: raise HTTPException(404,'Relatório não encontrado')
    return HTMLResponse(r.content_html)

@router.get('/datasets/{dataset_id}/csv')
async def dataset_csv(dataset_id:UUID,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ROLES)))->StreamingResponse:
    ds=await session.scalar(select(StatisticalDataset).where(StatisticalDataset.id==dataset_id,StatisticalDataset.organization_id==org_id(membership)))
    if ds is None: raise HTTPException(404,'Dataset não encontrado')
    output=io.StringIO(); keys=sorted({k for r in ds.rows_snapshot for k in r})
    writer=csv.DictWriter(output,fieldnames=keys); writer.writeheader(); writer.writerows(ds.rows_snapshot)
    return StreamingResponse(iter([output.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="dataset-{dataset_id}.csv"'})
